#!/usr/bin/env python3
"""
TYME CMS Bindings – Sovereign Edition

Authoritative autonomous repository editor.
Safe for GitHub Actions.
Deterministic. Auditable. Extendable.
"""

import os
import sys
import json
import re
import subprocess
import datetime
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_INDEX_PATH = REPO_ROOT / "chronicle" / "system-index.json"
DEFAULT_MODEL = os.getenv("TYME_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------
# Shell Execution
# ---------------------------------------------------------

def sh(cmd: str, allow_fail: bool = False):
    print(f"$ {cmd}")
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    print(proc.stdout)
    if proc.returncode != 0 and not allow_fail:
        raise RuntimeError(f"Command failed: {cmd}")
    return proc.stdout

# ---------------------------------------------------------
# Git Identity (CI Safe)
# ---------------------------------------------------------

def ensure_git_identity():
    sh('git config user.email "tyme@sovereign.system"', allow_fail=True)
    sh('git config user.name "TYME Autonomous System"', allow_fail=True)

# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------

def ensure_parent(path: Path):
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

def write_text_safe(path: Path, content: Any):
    ensure_parent(path)
    if isinstance(content, (dict, list)):
        content = json.dumps(content, indent=2, ensure_ascii=False)
    path.write_text(str(content), encoding="utf-8")

# ---------------------------------------------------------
# System Index Engine
# ---------------------------------------------------------

def scan_repository() -> Dict[str, Any]:
    index = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "system_integrity": "ok",
        "directories": [],
        "files": [],
        "scrolls": [],
        "forge_objects": [],
        "backend_modules": [],
        "frontend_assets": [],
        "run_count": 0,
        "version": "1.0.0"
    }

    for p in REPO_ROOT.rglob("*"):
        if ".git" in p.parts:
            continue
        rel = str(p.relative_to(REPO_ROOT))
        if p.is_dir():
            index["directories"].append(rel)
        else:
            index["files"].append(rel)
            if rel.startswith("scrolls/"):
                index["scrolls"].append(rel)
            if rel.startswith("forge/"):
                index["forge_objects"].append(rel)
            if rel.startswith("backend/"):
                index["backend_modules"].append(rel)
            if rel.startswith("frontend/"):
                index["frontend_assets"].append(rel)

    return index

def refresh_system_index():
    index = scan_repository()
    SYSTEM_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_text_safe(SYSTEM_INDEX_PATH, index)
    return index

# ---------------------------------------------------------
# CMS Operation Engine
# ---------------------------------------------------------

def apply_step(step: Dict[str, Any]):
    op = step.get("op")
    file = step.get("file")
    content = step.get("content", "")
    mode = step.get("mode", "overwrite")

    if not op or not file:
        raise ValueError(f"Invalid CMS step: {step}")

    path = (REPO_ROOT / file).resolve()

    if op == "mkdir":
        path.mkdir(parents=True, exist_ok=True)
        return

    if op in ("create", "replace", "overwrite"):
        write_text_safe(path, content)
        return

    if op == "append":
        ensure_parent(path)
        with path.open("a", encoding="utf-8") as f:
            f.write(str(content))
        return

    if op == "delete":
        if path.exists():
            path.unlink()
        return

    raise ValueError(f"Unknown operation: {op}")

def run_plan(plan: Dict[str, Any]):
    steps = plan.get("steps", [])
    summary = plan.get("summary", "TYME CMS update")

    if not steps:
        print("No steps to apply.")
        return

    for step in steps:
        apply_step(step)

    ensure_git_identity()
    sh("git add .")
    sh(f'git commit -m "{summary}"', allow_fail=True)

# ---------------------------------------------------------
# Natural Language Command Engine (NLC)
# ---------------------------------------------------------

def run_nlc(raw: str):
    raw = raw.strip()
    print("RAW INPUT:", raw)

    cleaned = re.sub(r'^[a-zA-Z_]+\(|\)$', '', raw)
    cleaned = cleaned.replace('"', "").replace("'", "")

    system_prompt = """
You are TYME CMS.

Convert instructions into JSON:
{
  "summary": "...",
  "steps": [
    { "op": "...", "file": "...", "content": "...", "mode": "overwrite|append" }
  ]
}

Rules:
- Always output valid JSON
- Never include comments or markdown
- File content must be string-safe
"""

    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": cleaned}
        ],
        temperature=0.1
    )

    text = response.choices[0].message.content
    plan = json.loads(text)
    run_plan(plan)

# ---------------------------------------------------------
# Directive Layer
# ---------------------------------------------------------

def directive_dispatch(raw: str):
    lowered = raw.lower()

    if "refresh system index" in lowered:
        index = refresh_system_index()
        ensure_git_identity()
        sh("git add chronicle/system-index.json")
        sh('git commit -m "System index refresh"', allow_fail=True)
        return

    run_nlc(raw)

# ---------------------------------------------------------
# Entry Point
# ---------------------------------------------------------

def main():
    raw = " ".join(sys.argv[1:]).strip()
    if not raw:
        print("No command provided.")
        return

    directive_dispatch(raw)

if __name__ == "__main__":
    main()