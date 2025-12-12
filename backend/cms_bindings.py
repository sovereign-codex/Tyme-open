import os
import sys
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# =========================================================
# TYME CMS — Sovereign UCE/UFW bindings
# Universal Command Engine (UCE) + Universal Forge/Write (UFW)
# =========================================================
#
# Goals:
# - Robustly parse/execute structured "plans" (steps) returned by an LLM
# - Provide a non-LLM Directive Layer for common actions (index refresh, forge activation, proposals)
# - Be tolerant to model imperfections (op aliases, JSON wrapped output, non-string content)
# - Guarantee filesystem safety (no escaping repo root)
# - Guarantee git commit safety (set identity if missing; don't fail on "no changes")
#
# Expected step shape:
# {
#   "op": "create"|"replace"|"patch"|"delete"|"mkdir",
#   "file": "relative/path.ext",
#   "mode": "overwrite"|"append",      # for create/replace/patch
#   "content": "string or jsonable",   # omitted for delete/mkdir
# }
#
# =========================================================


# ----------------------------
# Shell + Git helpers
# ----------------------------

def sh(cmd: str, cwd: str = ".") -> str:
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


def ensure_git_identity() -> None:
    """
    GitHub Actions runners sometimes have no identity configured.
    Without this, commits fail with "Please tell me who you are."
    """
    try:
        name = subprocess.run(
            "git config user.name",
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).stdout.strip()
        email = subprocess.run(
            "git config user.email",
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).stdout.strip()
    except Exception:
        name, email = "", ""

    if not name:
        sh('git config user.name "TYME CMS"')
    if not email:
        sh('git config user.email "tyme-cms@users.noreply.github.com"')


def safe_commit(summary: str) -> None:
    """
    Add + commit, but do not fail if there are no changes.
    """
    ensure_git_identity()
    summary = (summary or "Tyme CMS update").strip()
    summary = re.sub(r'["\n\r\t]', " ", summary)[:120]

    sh("git add .")
    # If nothing to commit, exit cleanly
    status = subprocess.run(
        "git status --porcelain",
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.strip()

    if not status:
        print("No changes detected; skipping commit.")
        return

    sh(f'git commit -m "{summary}"')


# ----------------------------
# Path safety
# ----------------------------

REPO_ROOT = Path(".").resolve()

def normalize_rel_path(p: str) -> str:
    """
    Normalize a user/model-provided file path into a safe repo-relative path.
    """
    if p is None:
        return ""
    p = str(p).strip()

    # Remove accidental quoting / leading ./ or /
    p = p.strip().strip('"').strip("'")
    p = p.lstrip().lstrip("./").lstrip("/")

    # Collapse repeated slashes
    while "//" in p:
        p = p.replace("//", "/")

    # Prevent path traversal
    candidate = (REPO_ROOT / p).resolve()
    if not str(candidate).startswith(str(REPO_ROOT)):
        raise ValueError(f"Unsafe path (escapes repo): {p}")

    return p


def ensure_parent_dirs(rel_path: str) -> None:
    rel_path = normalize_rel_path(rel_path)
    parent = (REPO_ROOT / rel_path).parent
    parent.mkdir(parents=True, exist_ok=True)


# ----------------------------
# Content normalization
# ----------------------------

def normalize_content(value: Any) -> str:
    """
    The model may return dict/list/etc. Convert to deterministic string.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    # Dict/list/etc → pretty JSON
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    except Exception:
        return str(value)


# ----------------------------
# Robust JSON extraction for model output
# ----------------------------

def extract_first_json_object(text: str) -> Dict[str, Any]:
    """
    Model sometimes returns:
      - commentary + JSON
      - fenced blocks
      - partial wrappers
    We extract the first {...} that parses.
    """
    if not text:
        raise ValueError("Empty model output")

    # Try direct parse first
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Remove code fences if present
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

    # Find balanced JSON object heuristically
    # Scan for first '{' and attempt to parse progressively.
    starts = [m.start() for m in re.finditer(r"\{", cleaned)]
    for s in starts:
        for e in range(len(cleaned), s + 1, -1):
            if cleaned[e - 1] != "}":
                continue
            snippet = cleaned[s:e]
            try:
                obj = json.loads(snippet)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue

    raise ValueError(f"Could not extract valid JSON object from output:\n{text}")


# =========================================================
# Directive Layer (no LLM)
# =========================================================

def now_utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80] or "proposal"


def scan_repo_index() -> Dict[str, Any]:
    """
    Builds a repository index (system registry) with arrays for directories/files/etc.
    Stored at chronicle/system-index.json (per your conventions).
    """
    ignore_dirs = {
        ".git", ".github", "node_modules", "__pycache__", ".venv", "venv",
        ".next", "dist", "build", ".cache"
    }

    directories: List[str] = []
    files: List[str] = []
    scrolls: List[str] = []
    forge_objects: List[str] = []
    backend_modules: List[str] = []
    frontend_assets: List[str] = []

    for root, dirnames, filenames in os.walk(REPO_ROOT):
        rel_root = os.path.relpath(root, REPO_ROOT).replace("\\", "/")
        if rel_root == ".":
            rel_root = ""

        # prune ignored dirs
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith(".")]

        # record dirs (repo-relative)
        for d in dirnames:
            p = f"{rel_root}/{d}".strip("/")
            directories.append(p)

        for fn in filenames:
            if fn.startswith("."):
                continue
            rel_path = f"{rel_root}/{fn}".strip("/").replace("\\", "/")
            files.append(rel_path)

            if rel_path.startswith("scrolls/") and rel_path.endswith((".md", ".txt")):
                scrolls.append(rel_path)
            if rel_path.startswith("forge/"):
                forge_objects.append(rel_path)
            if rel_path.startswith("backend/") and rel_path.endswith(".py"):
                backend_modules.append(rel_path)
            if rel_path.startswith(("frontend/", "public/", "assets/")):
                frontend_assets.append(rel_path)

    index = {
        "version": "1.0.0",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "run_count": int(os.environ.get("TYME_RUN_COUNT", "0")) + 1,
        "system_integrity": "ok",
        "directories": sorted(set(directories)),
        "files": sorted(set(files)),
        "scrolls": sorted(set(scrolls)),
        "forge_objects": sorted(set(forge_objects)),
        "backend_modules": sorted(set(backend_modules)),
        "frontend_assets": sorted(set(frontend_assets)),
    }
    return index


def directive_plan(raw: str) -> Optional[Dict[str, Any]]:
    """
    Convert known directives into an explicit plan with steps.
    """
    r = raw.strip().lower()

    # 1) System index refresh
    if r in {"refresh system index", "system index refresh", "refresh index", "refresh system-index"}:
        idx = scan_repo_index()
        return {
            "summary": "System index refresh",
            "steps": [
                {
                    "op": "replace",
                    "file": "chronicle/system-index.json",
                    "mode": "overwrite",
                    "content": idx,  # dict ok; will be normalized to json string
                }
            ],
        }

    # 2) Forge activation
    if r in {"perform forge activation", "forge activation", "activate forge", "perform forge"}:
        ts = now_utc_stamp()
        return {
            "summary": "Forge activation",
            "steps": [
                {"op": "mkdir", "file": "forge"},
                {
                    "op": "replace",
                    "file": "forge/heartbeat.md",
                    "mode": "overwrite",
                    "content": f"# Forge Heartbeat\n\n- status: online\n- updated_at: {ts}\n",
                },
                {
                    "op": "patch",
                    "file": "README.md",
                    "mode": "append",
                    "content": f"\n\n## Forge Online\n- last_heartbeat: {ts}\n",
                },
            ],
        }

    # 3) Proposal artifact
    if r.startswith("proposal:"):
        body = raw.split(":", 1)[1].strip()
        ts = now_utc_stamp()
        title = body.split("::", 1)[0].strip() if "::" in body else body[:60]
        slug = slugify(title)
        content = body.split("::", 1)[1].strip() if "::" in body else body
        return {
            "summary": f"Proposal: {title}",
            "steps": [
                {"op": "mkdir", "file": "proposals"},
                {
                    "op": "create",
                    "file": f"proposals/{ts}_{slug}.md",
                    "mode": "overwrite",
                    "content": f"# {title}\n\nCreated: {ts}\n\n{content}\n",
                },
            ],
        }

    return None


# =========================================================
# LLM Layer (NLC)
# =========================================================

SYSTEM_PROMPT = """
You are TYME CMS, an autonomous repository editor.

Return ONLY a JSON object with fields:
- "summary": short commit message
- "steps": array of step objects

Each step object:
- "op": one of "patch", "create", "replace", "delete", "mkdir"
- "file": repo-relative path like "README.md" or "forge/heartbeat.md"
- "mode": "append" or "overwrite" (required for patch/create/replace)
- "content": text to write (omit for delete/mkdir)

Rules:
- For JSON files: set content to a STRING containing valid JSON (not an object).
- Do NOT return backticks, markdown, or commentary.
"""

def clean_user_input(raw: str) -> str:
    cleaned = raw.strip()

    # If GitHub wrapped it like tyme.something(...), strip outer call
    cleaned = re.sub(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*$begin:math:text$', "", cleaned)
    cleaned = re.sub(r"$end:math:text$\s*$", "", cleaned)

    return cleaned.strip()


def run_nlc(raw: str) -> Dict[str, Any]:
    """
    LLM-backed plan generator.
    """
    cleaned = clean_user_input(raw)
    print("RAW INPUT:", raw)
    print("CLEANED NLC COMMAND:", cleaned)

    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY (or OPENAI) in environment secrets")

    model = os.environ.get("TYME_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Instruction: {cleaned}"},
        ],
        temperature=0.2,
    )

    text = resp.choices[0].message.content or ""
    print("MODEL RAW OUTPUT:")
    print(text)

    plan = extract_first_json_object(text)
    return plan


# =========================================================
# Executor (UFW)
# =========================================================

OP_ALIASES = {
    # tolerate common drift
    "overwrite": "replace",
    "append": "patch",
    "write": "replace",
    "update": "patch",
    "add": "create",
    "remove": "delete",
    "activate": "create",   # prevents your "Unknown operation: activate" crash
}

def canonical_op(op: str) -> str:
    op = (op or "").strip().lower()
    op = OP_ALIASES.get(op, op)
    return op


def apply_step(step: Dict[str, Any]) -> None:
    op = canonical_op(step.get("op") or step.get("mode"))
    file_path = normalize_rel_path(step.get("file", ""))
    mode = (step.get("mode") or "overwrite").strip().lower()
    content = normalize_content(step.get("content"))

    if not op or not file_path:
        raise ValueError(f"Invalid step (missing op or file): {step}")

    print(f"STEP: {op} {file_path} (mode={mode})")

    # mkdir: file points to directory
    if op == "mkdir":
        p = (REPO_ROOT / file_path)
        p.mkdir(parents=True, exist_ok=True)
        return

    # delete
    if op == "delete":
        p = (REPO_ROOT / file_path)
        if p.exists():
            p.unlink()
        return

    # create/replace/patch all ensure dirs
    ensure_parent_dirs(file_path)
    p = (REPO_ROOT / file_path)

    # create: fail if exists? (we'll be tolerant and overwrite if asked)
    if op == "create":
        write_mode = "a" if mode == "append" else "w"
        with p.open(write_mode, encoding="utf-8") as f:
            f.write(content)
        return

    # replace: overwrite
    if op == "replace":
        with p.open("w", encoding="utf-8") as f:
            f.write(content)
        return

    # patch: append (default) unless overwrite explicitly requested
    if op == "patch":
        write_mode = "a" if mode != "overwrite" else "w"
        with p.open(write_mode, encoding="utf-8") as f:
            f.write(content)
        return

    raise ValueError(f"Unknown operation: {op}")


def run_plan(plan: Dict[str, Any]) -> None:
    steps = plan.get("steps") or []
    summary = plan.get("summary") or "Tyme CMS update"

    if not isinstance(steps, list) or not steps:
        print("No steps provided in plan; nothing to do.")
        return

    # Apply all steps
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError(f"Step must be an object/dict: {step}")
        apply_step(step)

    # Commit
    safe_commit(str(summary))


# =========================================================
# Main dispatcher
# =========================================================

def main() -> None:
    raw = " ".join(sys.argv[1:]).strip()
    if not raw:
        print("No command provided.")
        sys.exit(0)

    # First: directive layer (deterministic, no LLM)
    dplan = directive_plan(raw)
    if dplan is not None:
        print("Directive Layer engaged.")
        run_plan(dplan)
        return

    # Otherwise: LLM-backed NLC
    print("Using Natural Language Command Engine (NLC).")
    plan = run_nlc(raw)
    run_plan(plan)


if __name__ == "__main__":
    main()