import os
import sys
import json
import re
import subprocess
from pathlib import Path

# ---------------------------------------------------------
# Helper: shell runner
# ---------------------------------------------------------

def run(cmd, cwd="."):
    print(f"$ {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout


# ---------------------------------------------------------
# Natural Language Command Engine (NLC)
# ---------------------------------------------------------

def run_nlc(raw: str):
    """
    Interpret a natural-language CMS instruction into a structured JSON plan
    and execute it.
    """

    cleaned = raw.strip()
    print("RAW INPUT:", cleaned)

    # Remove accidental "tyme.xxx(...)" wrapping from GitHub mobile
    cleaned = re.sub(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*$begin:math:text$', '', cleaned)
    cleaned = re.sub(r'$end:math:text$\s*$', '', cleaned)

    # Remove stray quotes
    cleaned = cleaned.replace('"', "").replace("'", "")

    print("CLEANED NLC COMMAND:", cleaned)

    system_prompt = """
You are TYME CMS, an autonomous repository editor.

You will receive a natural-language instruction describing how to modify this
Git repository. Convert the instruction into a JSON object with a field "steps".

Each step is an object with:
- "op": one of "patch", "create", "replace", "delete"
- "file": a relative file path (e.g., "README.md", "scrolls/xyz.md")
- "content": string content to write or append (omit for delete)
- "mode": "append" or "overwrite"

Return ONLY JSON. No commentary. No markdown. No backticks.
"""

    user_prompt = f"Instruction: {cleaned}"

    # --- OpenAI API call ---
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model=os.environ.get("TYME_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    print("MODEL RAW OUTPUT:")
    print(content)

    try:
        plan = json.loads(content)
    except Exception as e:
        raise RuntimeError(f"Model did not return valid JSON: {e}\nRaw Output:\n{content}")

    run_plan(plan)


# ---------------------------------------------------------
# Directory ensure
# ---------------------------------------------------------

def ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------
# Execute JSON plan
# ---------------------------------------------------------

def run_plan(plan: dict):
    """
    Apply all file operations described in a JSON CMS plan.
    """
    steps = plan.get("steps", [])
    summary = plan.get("summary", "Tyme CMS update")

    if not steps:
        print("No steps in plan; nothing to do.")
        return

    for step in steps:
        op = step.get("op")
        file_path = step.get("file")
        content = step.get("content", "")
        mode = step.get("mode", "append")

        if not op or not file_path:
            raise RuntimeError(f"Invalid step (missing op or file): {step}")

        # ---------------------------------------------------------
        # PATH SAFETY & NORMALIZATION
        # ---------------------------------------------------------
        file_path = file_path.strip().lstrip("./")

        # Remove accidental // duplication
        while "//" in file_path:
            file_path = file_path.replace("//", "/")

        # Fix recursive directory-node duplication (common Forge error)
        parts = file_path.split("/")
        if len(parts) > 2 and parts[-1].startswith(parts[-2]):
            fixed = parts[-1].replace(parts[-2], "", 1).lstrip("/")
            parts = parts[:-1] + [fixed]
            file_path = "/".join([p for p in parts if p])

        print(f"STEP: {op} {file_path} (mode={mode})")

        # ---------------------------------------------------------
        # FILE OPERATIONS
        # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Git commit
    # ---------------------------------------------------------

    run("git add .")
    run(f'git commit -m "{summary}" || echo "No changes to commit."')


# ---------------------------------------------------------
# Legacy (optional)
# ---------------------------------------------------------

def run_legacy_python_style(raw: str):
    print("Legacy Python-style command detected → forwarding to NLC.")
    run_nlc(raw)


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    raw = " ".join(sys.argv[1:]).strip()

    if not raw:
        print("No command provided.")
        sys.exit(0)

    python_like = raw.startswith("tyme.") and "(" in raw and ")" in raw

    if python_like:
        run_legacy_python_style(raw)
    else:
        print("Using Natural Language Command Engine (NLC).")
        run_nlc(raw)
