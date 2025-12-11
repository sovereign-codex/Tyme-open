#!/usr/bin/env python3
"""
TYME CMS v2 – Natural Language Repository Engine

This script is invoked from GitHub Actions like:

  python3 backend/cms_bindings.py "<natural language command>"

It:
  1. Cleans the raw CLI string (mobile-safe).
  2. Calls an OpenAI model to transform the request into a JSON "plan".
  3. Applies the plan to the repository (creating dirs/files as needed).
  4. Commits the changes with a summary message.
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------
# Repo context
# ---------------------------------------------------------------------

# This file lives in backend/, so the repo root is one level up
REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------
# Shell helper
# ---------------------------------------------------------------------

def run(cmd: str, cwd: Path | str = REPO_ROOT) -> str:
    """Run a shell command and return stdout, raising on non-zero exit."""
    print(f"$ {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout


# ---------------------------------------------------------------------
# Path safety & normalization
# ---------------------------------------------------------------------

ALLOWED_OPS = {"patch", "create", "replace", "delete", "mkdir"}


def normalize_rel_path(raw: str) -> str:
    """
    Normalize a repo-relative path string and enforce safety invariants.

    - Strips whitespace and leading "./"
    - Rejects attempts to escape the repo (..)
    - Rejects touching .git
    - Collapses duplicate slashes
    """
    if not raw:
        raise ValueError("Empty file path")

    p = raw.strip().strip("\"'")  # strip quotes, whitespace
    p = p.lstrip("./")

    # Basic safety: no parent escapes
    parts = [part for part in p.split("/") if part not in ("", ".")]
    if ".." in parts:
        raise RuntimeError(f"Unsafe path (contains '..'): {raw}")

    # No .git meddling
    if parts and parts[0] == ".git":
        raise RuntimeError(f"Unsafe path (touches .git): {raw}")

    # Collapse duplicate / and rebuild
    clean = "/".join(parts)
    return clean


def ensure_parent_dirs(rel_path: str) -> None:
    """Ensure parent directories for the given repo-relative path exist."""
    full = REPO_ROOT / rel_path
    parent = full.parent
    if parent and not parent.exists():
        print(f"[dirs] creating parent dirs for {rel_path}")
        parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# NLC engine
# ---------------------------------------------------------------------

def clean_raw_input(raw: str) -> str:
    """
    Clean the raw CLI argument into a stable instruction string.

    Handles:
      - extra quotes injected by shells / mobile interfaces
      - accidental wrapping like tyme.something("...")
    """
    cleaned = raw.strip()

    # Strip leading and trailing quotes if they enclose the whole string
    if (cleaned.startswith('"') and cleaned.endswith('"')) or \
       (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()

    # If GitHub mobile/web wrapped it like tyme.something(...), strip that.
    cleaned = re.sub(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\(', '', cleaned)
    cleaned = re.sub(r'\)\s*$', '', cleaned)

    print("RAW INPUT :", raw)
    print("CLEANED   :", cleaned)
    return cleaned


def build_system_prompt() -> str:
    """System prompt describing the CMS JSON plan format."""
    return """
You are TYME CMS, an autonomous repository editor operating on a Git
repository. You NEVER execute shell commands; you ONLY return JSON instructions.

You will receive a natural-language instruction describing how to modify this
repository. Convert the instruction into a JSON object called a "plan".

Plan JSON format:

{
  "summary": "Short human-readable summary of the change.",
  "steps": [
    {
      "op": "patch" | "create" | "replace" | "delete" | "mkdir",
      "file": "relative/posix/path.ext or directory/",
      "mode": "append" | "overwrite",   // only for patch/create/replace
      "content": "string content"       // omit or empty for delete/mkdir
    },
    ...
  ]
}

Rules:

- All "file" paths are POSIX style and RELATIVE to the repository root.
- NEVER use absolute paths.
- NEVER use ".." to go up directories.
- NEVER touch .git or its contents.
- For "mkdir", treat "file" as a directory path and create it (parents=True).
- For "patch", "create", and "replace":
    - if mode == "append": append content to the file (create if missing)
    - if mode == "overwrite": replace the file content entirely
- For "delete": remove the file if it exists; ignore if missing.
- Prefer concise changes over large rewrites when possible.

Return ONLY raw JSON. No commentary, no markdown, no code fences.
""".strip()


def run_nlc(raw: str) -> None:
    """
    Interpret a natural-language CMS command into a JSON plan and apply it.
    """
    cleaned = clean_raw_input(raw)

    system_prompt = build_system_prompt()
    user_prompt = f"Instruction: {cleaned}"

    # --- OpenAI call ---
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

    client = OpenAI(api_key=api_key)

    model_name = os.environ.get("TYME_MODEL", "gpt-4o-mini")

    print(f"[openai] model={model_name}")
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    print("MODEL RAW OUTPUT:")
    print(content)

    try:
        plan = json.loads(content)
    except Exception as e:
        raise RuntimeError(
            f"Model did not return valid JSON: {e}\n\nRaw content:\n{content}"
        )

    validate_plan(plan)
    apply_plan(plan)


# ---------------------------------------------------------------------
# Plan validation & execution
# ---------------------------------------------------------------------

def validate_plan(plan: dict) -> None:
    """Basic sanity checks on the returned JSON plan."""
    if not isinstance(plan, dict):
        raise RuntimeError(f"Plan must be a JSON object, got: {type(plan)}")

    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise RuntimeError("Plan must contain a non-empty 'steps' array.")

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise RuntimeError(f"Step {i} is not an object: {step!r}")

        op = step.get("op")
        file_path = step.get("file")

        if op not in ALLOWED_OPS:
            raise RuntimeError(f"Step {i} has invalid op={op!r}")

        if not isinstance(file_path, str) or not file_path.strip():
            raise RuntimeError(f"Step {i} missing valid 'file' path.")

        if op in {"patch", "create", "replace"}:
            mode = step.get("mode", "append")
            if mode not in {"append", "overwrite"}:
                raise RuntimeError(
                    f"Step {i} has invalid mode={mode!r} for op={op!r}"
                )

    print("[plan] validation OK")


def apply_plan(plan: dict) -> None:
    """
    Execute a JSON CMS plan: apply file operations & commit.
    """

    steps = plan.get("steps", [])
    summary = plan.get("summary", "Tyme CMS (NLC) update")

    for step in steps:
        op = step.get("op")
        rel_file_raw = step.get("file")
        content = step.get("content", "") or ""
        mode = step.get("mode", "append")

        # Normalize path & check safety
        rel_path = normalize_rel_path(rel_file_raw)
        full_path = REPO_ROOT / rel_path

        print(f"STEP: op={op} file={rel_path} mode={mode}")

        if op == "mkdir":
            full_path.mkdir(parents=True, exist_ok=True)
            continue

        if op in {"patch", "create", "replace"}:
            ensure_parent_dirs(rel_path)
            write_mode = "a" if mode == "append" else "w"
            with full_path.open(write_mode, encoding="utf-8") as f:
                f.write(content)

        elif op == "delete":
            if full_path.exists():
                if full_path.is_dir():
                    # Be conservative: do not recursively delete directories
                    raise RuntimeError(
                        f"Refusing to delete directory: {rel_path}"
                    )
                full_path.unlink()
        else:
            raise RuntimeError(f"Unknown op: {op}")

    # Git add & commit
    print("[git] staging and committing changes")
    run("git add .")
    run(f'git commit -m "{summary}" || echo "No changes to commit."')


# ---------------------------------------------------------------------
# Legacy (Python-style) command path – thin shim
# ---------------------------------------------------------------------

def run_legacy_python_style(raw: str) -> None:
    """
    Support for legacy invocations like:

      tyme.patch("README.md", "content...")

    For now we simply forward the entire string into NLC with a note
    so the model can infer intent.
    """
    print("Legacy Python-style command detected – forwarding to NLC.")
    # We could pre-parse here in the future; for now, NLC handles it.
    run_nlc(raw)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

def main(argv: list[str]) -> None:
    raw = " ".join(argv).strip()
    if not raw:
        print("No command provided.")
        sys.exit(0)

    # Very loose detection of old Python-like syntax:
    python_like = raw.startswith("tyme.") and "(" in raw and ")" in raw

    if python_like:
        run_legacy_python_style(raw)
    else:
        print("Using Natural Language Command Engine (NLC).")
        run_nlc(raw)


if __name__ == "__main__":
    main(sys.argv[1:])
