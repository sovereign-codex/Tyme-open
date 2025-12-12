#!/usr/bin/env python3
"""
TYME CMS — Sovereign Bindings (NLC + Universal Content Encoder / Universal File Writer)

Goals:
- Accept natural-language instructions, convert to JSON "plan" via OpenAI model
- Apply plan safely to the repository with robust path normalization
- Support writing content in ANY language + structured data (dict/list) + optional binary
- Prevent common GitHub Actions path anomalies (leading '/', './', double slashes, traversal)
- Avoid NotADirectoryError by ensuring parents are directories (and erroring cleanly if not)
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# -----------------------------
# Helpers
# -----------------------------

def run(cmd: str, cwd: str = ".") -> str:
    print(f"$ {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout


def normalize_repo_path(raw_path: str) -> str:
    """
    Normalize a file path to be safe and relative to repo root.
    - strips whitespace
    - converts backslashes to forward slashes
    - strips leading ./ and leading /
    - collapses // occurrences
    - blocks traversal (..)
    """
    if raw_path is None:
        raise ValueError("file path is None")

    p = str(raw_path).strip().replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")

    # remove accidental leading "./" or "/"
    if p.startswith("./"):
        p = p[2:]
    p = p.lstrip("/")

    # basic traversal protection
    parts = [x for x in p.split("/") if x not in ("", ".")]
    if any(x == ".." for x in parts):
        raise ValueError(f"Path traversal is not allowed: {raw_path}")

    p = "/".join(parts)
    if not p:
        raise ValueError(f"Empty/invalid file path: {raw_path}")

    return p


def ensure_parent_dir(file_path: str) -> None:
    """
    Ensure parent directory exists and is a directory.
    If a path segment exists as a file where a directory is needed, raise.
    """
    p = Path(file_path)
    parent = p.parent

    if str(parent) in (".", ""):
        return

    # Walk up and validate segments are directories (not files)
    cur = Path(".")
    for seg in parent.parts:
        cur = cur / seg
        if cur.exists() and not cur.is_dir():
            raise NotADirectoryError(
                f"Cannot create '{parent}': '{cur}' exists and is not a directory."
            )

    parent.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Universal Content Encoder (UCE)
# -----------------------------

def encode_content(content: Any, file_path: str) -> Union[str, bytes]:
    """
    Convert arbitrary content to the right on-disk representation.

    Rules:
    - str => write as-is
    - bytes/bytearray => write binary
    - dict/list => serialize by file extension when appropriate
      * .json/.jsonc => JSON pretty
      * .yml/.yaml => YAML (if PyYAML installed), else JSON pretty
      * other => JSON (compact) by default
    - primitives => str()
    """
    if isinstance(content, str):
        return content

    if isinstance(content, (bytes, bytearray)):
        return bytes(content)

    ext = Path(file_path).suffix.lower().lstrip(".")

    if isinstance(content, (dict, list)):
        if ext in ("json", "jsonc"):
            return json.dumps(content, indent=2, ensure_ascii=False) + "\n"

        if ext in ("yml", "yaml"):
            try:
                import yaml  # type: ignore
                return yaml.safe_dump(content, sort_keys=False, allow_unicode=True)
            except Exception:
                # Fall back safely if yaml isn't available
                return json.dumps(content, indent=2, ensure_ascii=False) + "\n"

        # Default for structured content going into non-json files:
        # serialize to JSON string to avoid TypeError and preserve structure.
        return json.dumps(content, indent=2, ensure_ascii=False) + "\n"

    return str(content)


# -----------------------------
# Universal File Writer (UFW)
# -----------------------------

def write_file(file_path: str, content: Any, mode: str) -> None:
    """
    Write content to a repo-relative path, ensuring directories exist.
    mode: "overwrite" | "append"
    """
    file_path = normalize_repo_path(file_path)
    ensure_parent_dir(file_path)

    encoded = encode_content(content, file_path)

    if isinstance(encoded, (bytes, bytearray)):
        m = "ab" if mode == "append" else "wb"
        with open(file_path, m) as f:
            f.write(encoded)
        return

    # string path
    m = "a" if mode == "append" else "w"
    with open(file_path, m, encoding="utf-8") as f:
        f.write(encoded)


def delete_path(file_path: str) -> None:
    file_path = normalize_repo_path(file_path)
    p = Path(file_path)
    if p.exists():
        if p.is_dir():
            # Conservative: refuse to delete directories from a plan (safer)
            raise IsADirectoryError(f"Refusing to delete directory: {file_path}")
        p.unlink()


# -----------------------------
# Plan execution
# -----------------------------

VALID_OPS = {"patch", "create", "replace", "delete"}
VALID_MODES = {"append", "overwrite"}


def apply_step(step: Dict[str, Any]) -> None:
    op = step.get("op")
    file_path = step.get("file")

    if op not in VALID_OPS:
        raise RuntimeError(f"Invalid op: {op}. Expected one of {sorted(VALID_OPS)}")

    if not file_path or not isinstance(file_path, str):
        raise RuntimeError(f"Invalid step (missing/invalid file): {step}")

    # Normalize mode based on op
    mode = step.get("mode", "overwrite")
    if mode not in VALID_MODES:
        mode = "overwrite"

    if op == "delete":
        delete_path(file_path)
        return

    content = step.get("content", "")

    if op == "patch":
        # patch defaults to append unless explicitly overwrite
        patch_mode = mode if mode in VALID_MODES else "append"
        if patch_mode == "overwrite":
            # "patch overwrite" is effectively replace
            write_file(file_path, content, "overwrite")
        else:
            write_file(file_path, content, "append")
        return

    if op in ("create", "replace"):
        write_file(file_path, content, "overwrite")
        return

    raise RuntimeError(f"Unhandled op: {op}")


def run_plan(plan: Dict[str, Any]) -> None:
    steps = plan.get("steps", [])
    summary = plan.get("summary") or "Tyme CMS (NLC) update"

    if not isinstance(steps, list) or not steps:
        print("No steps provided in plan, nothing to do.")
        return

    # Apply all steps
    for step in steps:
        if not isinstance(step, dict):
            raise RuntimeError(f"Invalid step type (expected dict): {step}")
        print(f"STEP: {step.get('op')} {step.get('file')} (mode={step.get('mode','')})")
        apply_step(step)

    # Commit changes
    run("git add .")
    run(f'git commit -m "{summary}" || echo "No changes to commit."')


# -----------------------------
# OpenAI + NLC
# -----------------------------

SYSTEM_PROMPT = """
You are TYME CMS, an autonomous repository editor.

You will receive a natural-language instruction about how to modify this Git
repository. Convert the instruction into a JSON object with a field "steps".

Each step is an object with:
- "op": one of "patch", "create", "replace", "delete"
- "file": the relative file path (e.g. "README.md" or "scrolls/xyz.md")
- "content": string content to write or append (omit for delete)
- "mode": "append" or "overwrite" (only for op = patch/replace; create defaults overwrite)

Return a single JSON object:
{
  "summary": "...",
  "steps": [ ... ]
}

Rules:
- Output MUST be valid JSON (no markdown, no backticks).
- "file" must be a relative path (no leading /).
- Prefer creating files in existing folders; if a folder doesn't exist, you may still create it by using a file path with folders (the runner will mkdir parents).
- If content is structured (e.g. JSON), you may emit "content" as a JSON object or array; the runtime will serialize it safely by file extension.
"""

def clean_raw_instruction(raw: str) -> str:
    cleaned = (raw or "").strip()
    print("RAW INPUT:", cleaned)

    # Strip wrapping like tyme.something(...):
    cleaned = re.sub(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\(', '', cleaned)
    cleaned = re.sub(r'\)\s*$', '', cleaned)

    # Avoid quote issues in model instruction; keep punctuation otherwise.
    cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"')
    cleaned = cleaned.replace("\u2018", "'").replace("\u2019", "'")

    # We do NOT delete quotes blindly anymore; that can destroy JSON/code content.
    # Instead, we keep them. The model is instructed to return JSON only.
    print("CLEANED NLC COMMAND:", cleaned)
    return cleaned


def extract_json(text: str) -> Dict[str, Any]:
    """
    Robust JSON extractor:
    - If text is pure JSON, parse it.
    - Else, find first {...} block and parse.
    """
    if not isinstance(text, str):
        raise RuntimeError("Model output is not a string")

    s = text.strip()

    # Remove accidental code fences if a model ever ignores instructions
    s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
    s = re.sub(r"\s*```$", "", s).strip()

    # Try direct parse
    try:
        return json.loads(s)
    except Exception:
        pass

    # Try to locate first JSON object
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s[start:end+1]
        return json.loads(candidate)

    raise RuntimeError(f"Model did not return valid JSON. Raw:\n{s}")


def run_nlc(raw: str) -> None:
    cleaned = clean_raw_instruction(raw)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set in environment. "
            "Add it as a GitHub Actions secret and pass it into the job env."
        )

    model = os.environ.get("TYME_MODEL", "gpt-4o-mini")

    user_prompt = f"Instruction: {cleaned}"

    from openai import OpenAI  # type: ignore
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content or ""
    print("MODEL RAW OUTPUT:")
    print(content)

    plan = extract_json(content)

    if not isinstance(plan, dict):
        raise RuntimeError(f"Plan must be a JSON object. Got: {type(plan)}")

    run_plan(plan)


# -----------------------------
# Legacy path (Python-style commands)
# -----------------------------

def run_legacy_python_style(raw: str) -> None:
    """
    Optional: support commands like tyme.patch("README.md","...").
    For now, forward to NLC.
    """
    print("Legacy Python-like command path currently forwards to NLC.")
    run_nlc(raw)


# -----------------------------
# Entry point
# -----------------------------

if __name__ == "__main__":
    raw = " ".join(sys.argv[1:]).strip()
    if not raw:
        print("No command provided.")
        sys.exit(0)

    python_like = raw.startswith("tyme.") and "(" in raw and ")" in raw
    if python_like:
        print("Detected Python-like command, using legacy handler.")
        run_legacy_python_style(raw)
    else:
        print("Using Natural Language Command Engine (NLC).")
        run_nlc(raw)
