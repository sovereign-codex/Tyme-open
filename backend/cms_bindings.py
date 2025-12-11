import os
import sys
import json
import re
import subprocess

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def run(cmd, cwd="."):
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout

# ---------------------------------------------------------
# Natural Language Command Engine (NLC)
# ---------------------------------------------------------

def run_nlc(raw: str):
    """
    Interpret a natural-language CMS command into structured operations
    and execute them using an OpenAI model.
    """

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
- "op": one of "patch", "create", "replace", "delete"
- "file": the relative file path (e.g. "README.md" or "scrolls/xyz.md")
- "content": string content to write or append (omit for delete)
- "mode": "append" or "overwrite" (only for op = patch/replace)

You may return multiple steps to perform a sequence of changes.

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

    response = client.chat.completions.create(
        model=os.environ.get("TYME_MODEL", "gpt-4o-mini"),
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
        raise RuntimeError(f"Model did not return valid JSON: {e}\nRaw: {content}")

    run_plan(plan)


def ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def run_plan(plan: dict):
    """
    Execute a JSON CMS plan: apply file operations & commit.
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

        print(f"STEP: {op} {file_path} (mode={mode})")

        if op in ("patch", "create", "replace"):
            ensure_dir(file_path)
            write_mode = "a" if (op == "patch" and mode == "append") else "w"
            with open(file_path, write_mode, encoding="utf-8") as f:
                f.write(content)

        elif op == "delete":
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            raise RuntimeError(f"Unknown op: {op}")

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
