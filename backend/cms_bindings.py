#!/usr/bin/env python3
"""
TYME CMS Bindings (NLC)

Goal:
- Accept a natural-language instruction
- Ask an OpenAI model for a JSON "plan" describing file operations
- Apply the plan safely inside the repo workspace
- Commit changes

Key upgrades vs prior versions:
- Strict JSON parsing + optional "repair" attempt
- Typed content support: content_type = "text" | "json"
- Safe path normalization + repo-root enforcement
- Prevent directory/file collisions (e.g., "forge" as file vs folder)
- Deterministic file writes (overwrite/append) and deletes
- Clear error messages that surface the failing step
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ----------------------------
# Config
# ----------------------------

REPO_ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd())).resolve()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
TYME_MODEL = os.environ.get("TYME_MODEL", "gpt-4o-mini").strip()

# If True, tries a second model call to repair invalid JSON output
ALLOW_JSON_REPAIR = os.environ.get("TYME_ALLOW_JSON_REPAIR", "1").strip() != "0"

# If True, prints more details
DEBUG = os.environ.get("TYME_DEBUG", "1").strip() != "0"


# ----------------------------
# Utilities
# ----------------------------

def log(*args: Any) -> None:
    print(*args, flush=True)


def run(cmd: str, cwd: Optional[Path] = None, allow_fail: bool = False) -> subprocess.CompletedProcess:
    if cwd is None:
        cwd = REPO_ROOT
    log(f"$ {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log(result.stdout)
    if (result.returncode != 0) and not allow_fail:
        raise RuntimeError(f"Command failed ({result.returncode}): {cmd}\n{result.stdout}")
    return result


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------
# Path Safety
# ----------------------------

def normalize_rel_path(p: str) -> str:
    """
    Normalize a repo-relative path safely.

    - strips whitespace
    - removes accidental leading './' or '/'
    - collapses repeated slashes
    - prevents traversal (..)
    """
    p = (p or "").strip()
    p = p.replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    p = p.lstrip("/").lstrip("./")

    # Basic traversal prevention
    parts = [seg for seg in p.split("/") if seg and seg != "."]
    if any(seg == ".." for seg in parts):
        raise ValueError(f"Path traversal is not allowed: {p}")

    # Rebuild
    return "/".join(parts)


def resolve_repo_path(rel: str) -> Path:
    rel_norm = normalize_rel_path(rel)
    abs_path = (REPO_ROOT / rel_norm).resolve()
    # Ensure still under REPO_ROOT
    if REPO_ROOT not in abs_path.parents and abs_path != REPO_ROOT:
        raise ValueError(f"Resolved path escapes repo root: {rel} -> {abs_path}")
    return abs_path


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def assert_not_dir_file_collision(target: Path) -> None:
    """
    Guard against cases like:
    - trying to write forge/heartbeat.md when 'forge' exists as a FILE
    - trying to create a directory where a file already exists, etc.
    """
    # If any parent is a file, we can't create children under it.
    cur = REPO_ROOT
    rel_parts = target.relative_to(REPO_ROOT).parts
    for seg in rel_parts[:-1]:
        cur = cur / seg
        if cur.exists() and cur.is_file():
            raise NotADirectoryError(
                f"Cannot create '{target.relative_to(REPO_ROOT)}' because parent '{cur.relative_to(REPO_ROOT)}' is a FILE."
            )

    # If target exists and is a directory, writing as file is invalid.
    if target.exists() and target.is_dir():
        raise IsADirectoryError(
            f"Cannot write file '{target.relative_to(REPO_ROOT)}' because it is a DIRECTORY."
        )


# ----------------------------
# Plan Schema
# ----------------------------

@dataclass
class Step:
    op: str
    file: str
    mode: str = "overwrite"      # "overwrite" | "append"
    content: Any = ""            # str or dict
    content_type: str = "text"   # "text" | "json"

    def normalized(self) -> "Step":
        op = (self.op or "").strip().lower()
        mode = (self.mode or "overwrite").strip().lower()
        content_type = (self.content_type or "text").strip().lower()
        return Step(op=op, file=self.file, mode=mode, content=self.content, content_type=content_type)


@dataclass
class Plan:
    summary: str
    steps: List[Step]

    def normalized(self) -> "Plan":
        summary = (self.summary or "Tyme CMS update").strip()
        steps = [s.normalized() for s in self.steps]
        return Plan(summary=summary, steps=steps)


# ----------------------------
# OpenAI: NLC -> Plan
# ----------------------------

SYSTEM_PROMPT = """
You are TYME CMS, an autonomous repository editor.

You will receive an instruction describing how to modify this Git repository.
Convert the instruction into a JSON object with:
- "summary": short commit message
- "steps": an array of step objects

Each step object supports:
- "op": one of "create", "replace", "patch", "delete", "mkdir"
- "file": repo-relative path (e.g. "README.md", "scrolls/x.md", "forge/heartbeat.md")
- "mode": "overwrite" or "append" (for create/replace/patch)
- "content_type": "text" or "json" (default "text")
- "content": the content to write.
    - if content_type == "text": a string
    - if content_type == "json": an object/array (NOT a string); TYME CMS will serialize it.

Rules:
- Return ONLY raw JSON. No markdown, no backticks, no comments.
- Use forward slashes in paths.
- Do not use absolute paths.
- Prefer "mkdir" when you need to ensure a directory exists.
- For JSON files like *.json, you may set content_type="json" and provide a JSON object.

Example:

{
  "summary": "Add system index",
  "steps": [
    {"op":"mkdir","file":"chronicle"},
    {
      "op":"replace",
      "file":"chronicle/system-index.json",
      "mode":"overwrite",
      "content_type":"json",
      "content":{"ok":true,"updated_at":"..."}
    }
  ]
}
""".strip()


def clean_raw_instruction(raw: str) -> str:
    cleaned = (raw or "").strip()
    if not cleaned:
        return ""

    # If GitHub mobile/web wrapped it like tyme.something(...), strip that.
    # Example: tyme.patch("README.md","hi") -> patch("README.md","hi") -> we discard wrapper entirely.
    cleaned2 = re.sub(r"^[a-zA-Z_][a-zA-Z0-9_]*\s*\(", "", cleaned)
    cleaned2 = re.sub(r"\)\s*$", "", cleaned2)

    # We DO NOT strip quotes globally anymore (it breaks JSON-like instructions).
    # But we normalize weird smart quotes if present.
    cleaned2 = cleaned2.replace("“", '"').replace("”", '"').replace("’", "'")

    return cleaned2.strip()


def _openai_client():
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is missing or empty in environment.")
    from openai import OpenAI  # imported here to keep script import-safe
    return OpenAI(api_key=OPENAI_API_KEY)


def ask_model_for_plan(instruction: str, repair_from: Optional[str] = None) -> str:
    """
    Returns model output string (should be JSON).
    If repair_from is provided, asks model to repair invalid JSON.
    """
    client = _openai_client()

    if repair_from is None:
        user_prompt = f"Instruction: {instruction}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    else:
        # JSON repair mode: model must output corrected JSON only.
        messages = [
            {"role": "system", "content": "You are a strict JSON repair tool. Return ONLY valid JSON, nothing else."},
            {"role": "user", "content": "Fix this into valid JSON for the TYME CMS plan schema:"},
            {"role": "user", "content": repair_from},
        ]

    response = client.chat.completions.create(
        model=TYME_MODEL,
        messages=messages,
        temperature=0.2,
    )
    content = response.choices[0].message.content or ""
    return content.strip()


def parse_plan(model_output: str) -> Plan:
    """
    Parses model output into Plan, validating basic structure.
    Accepts content as either str or dict (if content_type json).
    """
    try:
        data = json.loads(model_output)
    except Exception as e:
        raise ValueError(f"Model did not return valid JSON: {e}\nRaw:\n{model_output}")

    if not isinstance(data, dict):
        raise ValueError(f"Plan JSON must be an object, got: {type(data)}")

    summary = data.get("summary") or "Tyme CMS update"
    steps_raw = data.get("steps", [])
    if not isinstance(steps_raw, list):
        raise ValueError('"steps" must be an array')

    steps: List[Step] = []
    for i, s in enumerate(steps_raw):
        if not isinstance(s, dict):
            raise ValueError(f"Step {i} must be an object, got: {type(s)}")
        op = s.get("op") or ""
        file = s.get("file") or ""
        mode = s.get("mode", "overwrite")
        content = s.get("content", "")
        content_type = s.get("content_type", "text")

        if not op or not file:
            raise ValueError(f"Step {i} missing required fields op/file. Step={s}")

        steps.append(Step(op=op, file=file, mode=mode, content=content, content_type=content_type))

    return Plan(summary=str(summary), steps=steps).normalized()


# ----------------------------
# Apply Plan
# ----------------------------

def serialize_content(content: Any, content_type: str) -> str:
    """
    Convert content into a file-writeable string.
    """
    ct = (content_type or "text").lower().strip()
    if ct == "json":
        # If content is already a string but meant to be json, try to parse for pretty print.
        if isinstance(content, str):
            try:
                obj = json.loads(content)
            except Exception:
                # Accept raw string as-is, but ensure newline
                return content.rstrip() + "\n"
            return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"

        # If dict/list/etc, dump it
        return json.dumps(content, indent=2, ensure_ascii=False) + "\n"

    # Default: text
    if isinstance(content, (dict, list)):
        # Safety: never write dict/list directly as Python repr
        # Convert to JSON string for durability.
        return json.dumps(content, indent=2, ensure_ascii=False) + "\n"

    return str(content)


def apply_step(step: Step) -> None:
    op = step.op
    rel = normalize_rel_path(step.file)
    abs_path = resolve_repo_path(rel)

    if op == "mkdir":
        abs_dir = abs_path
        # mkdir can be passed a dir or a file path; we treat it as directory path
        abs_dir.mkdir(parents=True, exist_ok=True)
        if DEBUG:
            log(f"OK mkdir: {abs_dir.relative_to(REPO_ROOT)}")
        return

    if op == "delete":
        if abs_path.exists():
            if abs_path.is_dir():
                # do not recursive-delete directories by default
                raise IsADirectoryError(f"Refusing to delete directory '{rel}'. Delete files only.")
            abs_path.unlink()
            if DEBUG:
                log(f"OK delete: {rel}")
        else:
            if DEBUG:
                log(f"SKIP delete (missing): {rel}")
        return

    if op not in ("create", "replace", "patch"):
        raise ValueError(f"Unknown op: {op}")

    # file write ops
    assert_not_dir_file_collision(abs_path)
    ensure_parent_dir(abs_path)

    mode = step.mode.lower().strip()
    if mode not in ("overwrite", "append"):
        mode = "overwrite"

    write_mode = "a" if (op == "patch" and mode == "append") else "w"
    payload = serialize_content(step.content, step.content_type)

    with abs_path.open(write_mode, encoding="utf-8") as f:
        f.write(payload)

    if DEBUG:
        log(f"OK {op}: {rel} (mode={mode}, content_type={step.content_type})")


def run_plan(plan: Plan) -> None:
    if not plan.steps:
        log("No steps provided in plan, nothing to do.")
        return

    # Apply steps
    for idx, step in enumerate(plan.steps):
        try:
            log(f"STEP {idx+1}/{len(plan.steps)}: {step.op} {step.file} (mode={step.mode}, type={step.content_type})")
            apply_step(step)
        except Exception as e:
            raise RuntimeError(f"Failed applying step {idx+1}: {step}\nError: {e}") from e

    # Git add & commit
    run("git add .")
    # If no changes, don't hard-fail
    run(f'git commit -m "{plan.summary}"', allow_fail=True)


# ----------------------------
# Entry / NLC
# ----------------------------

def run_nlc(raw: str) -> None:
    instruction = clean_raw_instruction(raw)
    if not instruction:
        log("No command provided.")
        return

    log("RAW INPUT:", raw)
    log("CLEANED INSTRUCTION:", instruction)
    log("MODEL:", TYME_MODEL)
    log("UTC:", utc_now_iso())

    # 1) Ask model for plan
    out = ask_model_for_plan(instruction)
    if DEBUG:
        log("MODEL RAW OUTPUT:")
        log(out)

    # 2) Parse
    try:
        plan = parse_plan(out)
    except Exception as e:
        if not ALLOW_JSON_REPAIR:
            raise

        log("Initial JSON parse failed. Attempting repair...")
        repaired = ask_model_for_plan(instruction="", repair_from=out)
        if DEBUG:
            log("MODEL REPAIRED OUTPUT:")
            log(repaired)
        plan = parse_plan(repaired)

    # 3) Execute
    run_plan(plan)


def run_legacy_python_style(raw: str) -> None:
    """
    Optional legacy stub: forward to NLC.
    (You can expand this later to interpret tyme.patch(...) directly.)
    """
    log("Legacy Python-style command path forwards to NLC.")
    run_nlc(raw)


def main(argv: List[str]) -> int:
    raw = " ".join(argv).strip()
    if not raw:
        log("No command provided.")
        return 0

    python_like = raw.startswith("tyme.") and "(" in raw and ")" in raw
    if python_like:
        log("Detected Python-like command, using legacy handler.")
        run_legacy_python_style(raw)
    else:
        log("Using Natural Language Command Engine (NLC).")
        run_nlc(raw)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))