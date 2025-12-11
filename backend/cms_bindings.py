import os
import sys
import json
import re
import subprocess
from datetime import datetime

# ---------------------------------------------------------
# Helpers: shell + filesystem
# ---------------------------------------------------------

def run(cmd, cwd="."):
    """Run a shell command and stream output."""
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


def ensure_dir(path: str):
    """Ensure the parent directory for a file path exists."""
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def normalize_path(file_path: str) -> str:
    """
    Normalize and safety-check a repository-relative path.

    - Strips leading "./" or spaces
    - Collapses repeated slashes
    - Blocks ".." traversal
    """
    if not file_path:
        return file_path

    # Strip quotes / whitespace just in case
    fp = str(file_path).strip().strip('"').strip("'")

    # Strip leading "./"
    fp = re.sub(r"^(\./)+", "", fp)

    # Collapse repeated slashes
    fp = re.sub(r"/+", "/", fp)

    # Split and block ".."
    parts = [p for p in fp.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise RuntimeError(f"Unsafe path with '..' not allowed: {file_path}")

    # Re-join
    return "/".join(parts)


# ---------------------------------------------------------
# Chronicle Layer (logs + system index)
# ---------------------------------------------------------

CHRONICLE_DIR = "chronicle"
CMS_LOG = os.path.join(CHRONICLE_DIR, "cms-log.jsonl")
ORCH_LOG = os.path.join(CHRONICLE_DIR, "orchestration-log.jsonl")
SYSTEM_INDEX = os.path.join(CHRONICLE_DIR, "system-index.json")
ERROR_LOG = os.path.join(CHRONICLE_DIR, "cms-errors.log")


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def chronicle_append(path: str, payload: dict):
    """Append a JSON line to a Chronicle log file."""
    ensure_dir(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def chronicle_load_index() -> dict:
    if not os.path.exists(SYSTEM_INDEX):
        return {}
    try:
        with open(SYSTEM_INDEX, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        # If index is corrupted, log it and start fresh
        chronicle_append(
            ERROR_LOG,
            {
                "ts": now_iso(),
                "kind": "index_load_error",
                "error": str(e),
            },
        )
        return {}


def chronicle_save_index(index: dict):
    ensure_dir(SYSTEM_INDEX)
    with open(SYSTEM_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def chronicle_update_index(plan: dict):
    """
    Update TYME System Index with the latest run + affected scrolls.
    """
    index = chronicle_load_index()
    index.setdefault("version", 1)
    index.setdefault("runs", [])
    index.setdefault("scrolls", {})

    ts = now_iso()

    # Record this run
    run_entry = {
        "ts": ts,
        "summary": plan.get("summary"),
        "step_count": len(plan.get("steps", [])),
    }
    index["runs"].append(run_entry)
    index["last_run"] = run_entry

    # Track scrolls touched in this plan
    for step in plan.get("steps", []):
        file_path = step.get("file") or ""
        norm = normalize_path(file_path)
        if norm.startswith("scrolls/"):
            scroll_entry = index["scrolls"].get(norm, {})
            scroll_entry.update(
                {
                    "last_op": step.get("op"),
                    "last_updated": ts,
                }
            )
            index["scrolls"][norm] = scroll_entry

    index["updated_at"] = ts
    chronicle_save_index(index)


# ---------------------------------------------------------
# Natural Language Command Engine (NLC)
# ---------------------------------------------------------

def run_nlc(raw: str):
    """
    Interpret a natural-language CMS command into structured operations
    and execute them using an OpenAI model + Chronicle.
    """

    original_raw = raw
    cleaned = raw.strip()
    print("RAW INPUT:", cleaned)

    # If GitHub mobile/web wrapped it like tyme.something(...), strip that.
    cleaned = re.sub(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\(', '', cleaned)
    cleaned = re.sub(r'\)\s*$', '', cleaned)

    # Remove any stray unmatched quotes (they just cause parse issues).
    cleaned = cleaned.replace('"', "").replace("'", "")

    print("CLEANED NLC COMMAND:", cleaned)

    system_prompt = """
You are TYME CMS, an autonomous repository editor.

You will receive a natural-language instruction about how to modify this Git
repository. Convert the instruction into a JSON object with a field "steps".

Each step is an object with:
- "op": one of "patch", "create", "replace", "delete", "mkdir"
- "file": the relative file path (e.g. "README.md" or "scrolls/xyz.md")
- "content": string content to write or append (omit for delete/mkdir)
- "mode": "append" or "overwrite" (only for op = patch/replace)

You may return multiple steps to perform a sequence of changes.

Always use safe, repo-relative paths. Never use absolute paths or "..".

Example:

{
  "summary": "Add Sovereign Test section to README and create activation scroll",
  "steps": [
    {
      "op": "patch",
      "file": "README.md",
      "mode": "append",
      "content": "\\n\\n## Sovereign Test\\nTyme CMS is now live.\\n"
    },
    {
      "op": "create",
      "file": "scrolls/sovereign_test.md",
      "mode": "overwrite",
      "content": "# Sovereign Test\\nTyme CMS + Forge activation scroll.\\n"
    }
  ]
}

Return ONLY JSON. No commentary, no backticks, no markdown.
"""

    user_prompt = f"Instruction: {cleaned}"

    # --- OpenAI call ---
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    try:
        response = client.chat.completions.create(
            model=os.environ.get("TYME_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
    except Exception as e:
        # Self-healing: log the failure, but don't crash the workflow
        chronicle_append(
            ERROR_LOG,
            {
                "ts": now_iso(),
                "kind": "openai_error",
                "error": str(e),
                "raw_instruction": original_raw,
            },
        )
        print(f"OpenAI call failed, logged to {ERROR_LOG}")
        return

    content = response.choices[0].message.content
    print("MODEL RAW OUTPUT:")
    print(content)

    # Self-healing JSON handling
    try:
        plan = json.loads(content)
    except Exception as e:
        chronicle_append(
            ERROR_LOG,
            {
                "ts": now_iso(),
                "kind": "json_parse_error",
                "error": str(e),
                "raw_model_output": content,
                "raw_instruction": original_raw,
            },
        )
        print("Model returned invalid JSON. Logged error; no changes applied.")
        return

    # Chronicle: log the interpreted plan
    chronicle_append(
        CMS_LOG,
        {
            "ts": now_iso(),
            "raw_instruction": original_raw,
            "cleaned_instruction": cleaned,
            "summary": plan.get("summary"),
            "step_count": len(plan.get("steps", [])),
            "model": os.environ.get("TYME_MODEL", "gpt-4o-mini"),
        },
    )

    run_plan(plan)


# ---------------------------------------------------------
# Plan execution (Forge) + orchestration logging
# ---------------------------------------------------------

def run_plan(plan: dict):
    """
    Execute a JSON CMS plan: apply file operations, update index, commit.
    """
    steps = plan.get("steps", [])
    summary = plan.get("summary", "Tyme CMS (NLC) update")

    if not steps:
        print("No steps provided in plan, nothing to do.")
        return

    for step in steps:
        op = step.get("op")
        file_path = step.get("file")
        content = step.get("content", "")
        mode = step.get("mode", "append")

        if not op or not file_path:
            raise RuntimeError(f"Invalid step (missing op or file): {step}")

        # Normalize/sanitize path
        file_path = normalize_path(file_path)

        print(f"STEP: {op} {file_path} (mode={mode})")

        # Directory operations
        if op == "mkdir":
            ensure_dir(os.path.join(file_path, "_dummy.txt"))
            # Delete the dummy file if it was created
            dummy = os.path.join(file_path, "_dummy.txt")
            if os.path.exists(dummy):
                os.remove(dummy)

        # File operations
        elif op in ("patch", "create", "replace"):
            ensure_dir(file_path)
            # "replace" behaves like overwrite; "patch" can be append or overwrite
            write_mode = "a" if (op == "patch" and mode == "append") else "w"
            with open(file_path, write_mode, encoding="utf-8") as f:
                f.write(content)

        elif op == "delete":
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            raise RuntimeError(f"Unknown op: {op}")

        # Chronicle each step
        chronicle_append(
            ORCH_LOG,
            {
                "ts": now_iso(),
                "op": op,
                "file": file_path,
                "mode": mode,
                "summary": summary,
            },
        )

    # Update system index
    chronicle_update_index(plan)

    # Git add & commit
    run("git add .")
    run(f'git commit -m "{summary}" || echo "No changes to commit."')


# ---------------------------------------------------------
# Legacy path (Python-style commands) – optional stub
# ---------------------------------------------------------

def run_legacy_python_style(raw: str):
    """
    If in the future you still want to support commands like
    tyme.patch("README.md", "..."), you can implement that here.
    For now, we just forward everything to NLC.
    """
    print("Legacy Python-style command path currently forwards to NLC.")
    run_nlc(raw)


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    raw = " ".join(sys.argv[1:]).strip()
    if not raw:
        print("No command provided.")
        sys.exit(0)

    # Very loose detection of old Python-like syntax:
    python_like = raw.startswith("tyme.") and "(" in raw and ")" in raw

    if python_like:
        print("Detected Python-like command, using legacy handler.")
        run_legacy_python_style(raw)
    else:
        print("Using Natural Language Command Engine (NLC).")
        run_nlc(raw)
