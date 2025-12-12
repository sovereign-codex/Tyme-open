import os
import sys
import json
import re
import time
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================================================
# TYME CMS Bindings (Sovereign UCE/UFW Rewrite)
# - Safe file ops: patch/create/replace/delete/mkdir
# - JSON-safe writes (dict/list auto-serialized)
# - Proposal Mode (plan-only + proposal artifact)
# - Directive Layer (local directives without OpenAI)
# - Index-Driven Reasoning (system-index load + refresh)
# - Scheduled Autonomy (task file + schedule hints)
# =========================================================

REPO_ROOT = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
CHRONICLE_DIR = Path("chronicle")
FORGE_DIR = Path("forge")
PROPOSALS_DIR = Path("proposals")

SYSTEM_INDEX_PATH = CHRONICLE_DIR / "system-index.json"
SYSTEM_INDEX_VERSION = 1

DEFAULT_MODEL = os.environ.get("TYME_MODEL", "gpt-4o-mini")

ALLOWED_OPS = {"patch", "create", "replace", "delete", "mkdir"}
ALLOWED_MODES = {"append", "overwrite"}

# Safety: block path traversal and absolute paths
FORBIDDEN_SEGMENTS = {"..", "~"}
FORBIDDEN_PREFIXES = ("/", "\\")  # absolute paths


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def sh(cmd: str, cwd: Path = REPO_ROOT) -> str:
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


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def slugify(s: str, max_len: int = 64) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:max_len] if s else "untitled"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_parent(path: Path) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def normalize_rel_path(p: str) -> Path:
    """
    Normalize a user/model-provided relative path:
    - strips whitespace
    - strips leading './'
    - rejects absolute paths
    - rejects traversal segments
    - collapses repeated slashes
    """
    if p is None:
        raise ValueError("file path missing")

    p = p.strip()
    p = p.replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    if p.startswith("./"):
        p = p[2:]

    for pref in FORBIDDEN_PREFIXES:
        if p.startswith(pref):
            raise ValueError(f"absolute paths forbidden: {p}")

    parts = [x for x in p.split("/") if x != ""]
    for seg in parts:
        if seg in FORBIDDEN_SEGMENTS:
            raise ValueError(f"path traversal forbidden: {p}")

    # Extra guard: prevent ".git" mutations
    if parts and parts[0] == ".git":
        raise ValueError("mutating .git is forbidden")

    return Path(*parts)


def coerce_content_for_write(file_path: Path, content: Any) -> str:
    """
    If model returns dict/list for JSON files, serialize cleanly.
    Otherwise coerce to string safely.
    """
    if isinstance(content, (dict, list)):
        # Prefer JSON for .json or for structured content
        return json.dumps(content, indent=2, ensure_ascii=False) + "\n"
    if content is None:
        return ""
    if isinstance(content, (int, float, bool)):
        return str(content)
    if isinstance(content, str):
        return content
    # last resort
    return str(content)


def extract_json_object(text: str) -> str:
    """
    Robust JSON extraction:
    - If the model outputs extra text, extract the first {...} block.
    """
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text

    # Find first balanced JSON object
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object start found in model output.")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("Unbalanced JSON object in model output.")


# ---------------------------------------------------------
# System Index (Index-Driven Reasoning)
# ---------------------------------------------------------

def build_system_index(root: Path = REPO_ROOT) -> Dict[str, Any]:
    """
    Produces a full repository registry.
    """
    ignore_dirs = {
        ".git", "node_modules", ".next", "dist", "build", "__pycache__",
        ".venv", "venv", ".pytest_cache"
    }

    files: List[str] = []
    directories: List[str] = []
    scrolls: List[str] = []
    forge_objects: List[str] = []
    backend_modules: List[str] = []
    frontend_assets: List[str] = []

    # Collect directories first (relative)
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if any(part in ignore_dirs for part in rel.parts):
            continue

        if p.is_dir():
            directories.append(str(rel).replace("\\", "/"))
            continue

        # files
        rel_s = str(rel).replace("\\", "/")
        files.append(rel_s)

        # categorize
        if rel_s.startswith("scrolls/") or rel_s.endswith(".scroll.md"):
            scrolls.append(rel_s)
        if rel_s.startswith("forge/"):
            forge_objects.append(rel_s)
        if rel_s.startswith("backend/") and rel_s.endswith(".py"):
            backend_modules.append(rel_s)
        if rel_s.startswith(("frontend/", "public/", "assets/")):
            frontend_assets.append(rel_s)

    directories = sorted(set(directories))
    files = sorted(set(files))

    index = {
        "schema_version": SYSTEM_INDEX_VERSION,
        "updated_at": now_iso(),
        "repo_root": str(root.name),
        "counts": {
            "directories": len(directories),
            "files": len(files),
            "scrolls": len(scrolls),
            "forge_objects": len(forge_objects),
            "backend_modules": len(backend_modules),
            "frontend_assets": len(frontend_assets),
        },
        "directories": directories,
        "files": files,
        "scrolls": sorted(set(scrolls)),
        "forge_objects": sorted(set(forge_objects)),
        "backend_modules": sorted(set(backend_modules)),
        "frontend_assets": sorted(set(frontend_assets)),
        "metadata": {
            "system_integrity": "ok",
            "version": SYSTEM_INDEX_VERSION,
            "run_count": int(os.environ.get("TYME_RUN_COUNT", "0")),
        },
    }
    return index


def refresh_system_index(write: bool = True) -> Dict[str, Any]:
    index = build_system_index(REPO_ROOT)
    if write:
        ensure_parent(SYSTEM_INDEX_PATH)
        SYSTEM_INDEX_PATH.write_text(
            json.dumps(index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return index


def load_system_index() -> Optional[Dict[str, Any]]:
    p = (REPO_ROOT / SYSTEM_INDEX_PATH).resolve()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


# ---------------------------------------------------------
# Proposal Mode / Scheduled Autonomy / Directive Layer
# ---------------------------------------------------------

def write_proposal(title: str, body: str, tags: Optional[List[str]] = None) -> Path:
    tags = tags or []
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    name = f"{ts}_{slugify(title)}.md"
    p = PROPOSALS_DIR / name
    ensure_parent(p)
    header = [
        f"# {title}",
        "",
        f"- created_at: {now_iso()}",
        f"- tags: {', '.join(tags) if tags else 'none'}",
        "",
        "---",
        "",
    ]
    p.write_text("\n".join(header) + body.strip() + "\n", encoding="utf-8")
    return p


def write_scheduled_task(task_name: str, task_body: str) -> Path:
    """
    Minimal “Scheduled Autonomy” artifact: a registry file TYME can append to.
    Your GitHub Action can later read this and run it on cron.
    """
    p = CHRONICLE_DIR / "maintenance_tasks.md"
    ensure_parent(p)

    block = [
        "",
        f"## {task_name}",
        f"- created_at: {now_iso()}",
        f"- status: pending",
        "",
        "```",
        task_body.strip(),
        "```",
        "",
    ]
    with p.open("a", encoding="utf-8") as f:
        f.write("\n".join(block))
    return p


def run_directive(cleaned: str) -> Optional[Dict[str, Any]]:
    """
    Directive Layer:
    Allow some commands to execute WITHOUT calling OpenAI.
    Examples:
      - "refresh system index"
      - "forge init"
      - "forge heartbeat"
      - "proposal: <title> :: <body>"
      - "schedule: <name> :: <task>"
    """
    s = cleaned.strip().lower()

    if s in {"refresh system index", "system index refresh", "refresh index"}:
        idx = refresh_system_index(write=True)
        return {
            "summary": "System index refresh",
            "steps": [
                {
                    "op": "replace",
                    "file": str(SYSTEM_INDEX_PATH).replace("\\", "/"),
                    "mode": "overwrite",
                    "content": idx,
                }
            ],
            "directive": "index_refresh",
        }

    if s in {"forge init", "perform forge activation", "forge activation"}:
        # Minimal forge init artifacts
        steps = [
            {"op": "mkdir", "file": "forge", "mode": "overwrite"},
            {"op": "create", "file": "forge/init.md", "mode": "overwrite",
             "content": f"# Forge Init\n\nForge online at {now_iso()}.\n"},
            {"op": "create", "file": "forge/heartbeat.md", "mode": "overwrite",
             "content": f"# Forge Heartbeat\n\nHeartbeat: {now_iso()}.\n"},
        ]
        return {"summary": "Forge activation", "steps": steps, "directive": "forge_init"}

    # Proposal Mode: "proposal: Title :: Body"
    if s.startswith("proposal:"):
        raw = cleaned[len("proposal:"):].strip()
        if "::" in raw:
            title, body = [x.strip() for x in raw.split("::", 1)]
        else:
            title, body = raw.strip() or "Proposal", "No body provided."
        proposal_path = write_proposal(title, body, tags=["tyme", "proposal-mode"])
        return {
            "summary": f"Proposal: {title}",
            "steps": [
                {
                    "op": "create",
                    "file": str(proposal_path).replace("\\", "/"),
                    "mode": "overwrite",
                    "content": proposal_path.read_text(encoding="utf-8"),
                }
            ],
            "proposal_only": True,
        }

    # Scheduled Autonomy: "schedule: Name :: Task body"
    if s.startswith("schedule:"):
        raw = cleaned[len("schedule:"):].strip()
        if "::" in raw:
            name, body = [x.strip() for x in raw.split("::", 1)]
        else:
            name, body = "Scheduled Task", raw
        task_path = write_scheduled_task(name, body)
        return {
            "summary": f"Scheduled task: {name}",
            "steps": [
                {
                    "op": "patch",
                    "file": str(task_path).replace("\\", "/"),
                    "mode": "append",
                    "content": "",  # already appended
                }
            ],
            "directive": "scheduled_task",
        }

    return None


# ---------------------------------------------------------
# OpenAI NLC (Natural Language Command Engine)
# ---------------------------------------------------------

def run_nlc(raw: str) -> None:
    cleaned = sanitize_input(raw)
    print("RAW INPUT:", raw)
    print("CLEANED NLC COMMAND:", cleaned)

    # 1) Directive Layer short-circuit (no OpenAI required)
    directive_plan = run_directive(cleaned)
    if directive_plan is not None:
        print("DIRECTIVE PLAN ACTIVATED.")
        run_plan(directive_plan)
        return

    # 2) Index-Driven Reasoning: load system index, if present
    system_index = load_system_index()
    system_index_hint = ""
    if system_index:
        # Keep it compact to avoid huge prompts
        counts = system_index.get("counts", {})
        system_index_hint = (
            "\n\nSYSTEM INDEX (summary):\n"
            f"- updated_at: {system_index.get('updated_at')}\n"
            f"- counts: {json.dumps(counts)}\n"
            f"- notable_paths: {', '.join((system_index.get('files') or [])[:15])}\n"
        )

    system_prompt = f"""
You are TYME CMS, an autonomous repository editor.

You will receive a natural-language instruction about how to modify this Git repository.
Convert the instruction into a JSON object with:
- "summary": short commit message
- "steps": array of steps

Each step:
- "op": one of {sorted(ALLOWED_OPS)}
- "file": relative file path (or directory path if op=mkdir)
- "mode": "append" or "overwrite" (optional; default "overwrite" for create/replace)
- "content": string (or JSON object/array ONLY if the file is .json)

Rules:
- NEVER output markdown or backticks.
- Return ONLY ONE JSON object.
- Prefer small, safe changes.
- If asked to "refresh system index", output a step to replace "{SYSTEM_INDEX_PATH}".

{system_index_hint}
""".strip()

    user_prompt = f"Instruction: {cleaned}"

    # --- OpenAI call ---
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing in environment.")

    client = OpenAI(api_key=api_key)

    # If your OpenAI SDK supports response_format json_object, it helps prevent JSON drift.
    # We'll attempt it, but keep a fallback if unsupported.
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except TypeError:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

    content = response.choices[0].message.content or ""
    print("MODEL RAW OUTPUT:")
    print(content)

    json_text = extract_json_object(content)

    try:
        plan = json.loads(json_text)
    except Exception as e:
        raise RuntimeError(f"Model did not return valid JSON: {e}\nRaw: {content}")

    run_plan(plan)


def sanitize_input(raw: str) -> str:
    """
    Keep the user's intent but remove the common GitHub mobile wrapper noise.
    Do NOT strip all quotes (that caused JSON-like instructions to break).
    """
    s = (raw or "").strip()

    # If GitHub mobile wrapped it like tyme.something(...), strip outer call only.
    # Example: tyme.patch("README.md","x") -> patch("README.md","x") -> we keep interior.
    s = re.sub(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\(', '', s)
    s = re.sub(r'\)\s*$', '', s)

    # Normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------
# Plan Execution
# ---------------------------------------------------------

@dataclass
class Step:
    op: str
    file: str
    mode: str = "overwrite"
    content: Any = ""


def parse_steps(plan: Dict[str, Any]) -> Tuple[str, List[Step]]:
    summary = plan.get("summary") or "Tyme CMS update"
    raw_steps = plan.get("steps") or []

    if not isinstance(raw_steps, list):
        raise ValueError("plan.steps must be a list")

    steps: List[Step] = []
    for item in raw_steps:
        if not isinstance(item, dict):
            raise ValueError("each step must be an object")
        op = (item.get("op") or "").strip()
        file_ = item.get("file")
        mode = (item.get("mode") or "").strip() or ("append" if op == "patch" else "overwrite")
        content = item.get("content", "")

        if op not in ALLOWED_OPS:
            raise ValueError(f"invalid op: {op}")
        if op != "delete" and not file_:
            raise ValueError("step.file is required")
        if op == "delete":
            # file required for delete too
            if not file_:
                raise ValueError("step.file required for delete")
        if mode and mode not in ALLOWED_MODES and op != "mkdir":
            # mkdir ignores mode
            raise ValueError(f"invalid mode: {mode}")

        steps.append(Step(op=op, file=str(file_), mode=mode or "overwrite", content=content))

    return summary, steps


def apply_step(step: Step) -> None:
    rel = normalize_rel_path(step.file)
    abs_path = (REPO_ROOT / rel).resolve()

    # Ensure we stay inside repo
    if not str(abs_path).startswith(str(REPO_ROOT)):
        raise ValueError("resolved path escapes repo root")

    # Directory op
    if step.op == "mkdir":
        abs_path.mkdir(parents=True, exist_ok=True)
        print(f"STEP: mkdir {rel}")
        return

    # Delete op
    if step.op == "delete":
        if abs_path.exists():
            if abs_path.is_dir():
                # keep it safe: refuse recursive delete
                raise RuntimeError(f"Refusing to delete directory: {rel}")
            abs_path.unlink()
        print(f"STEP: delete {rel}")
        return

    # Write ops
    ensure_parent(abs_path)

    # Avoid "file treated as directory" mistakes:
    # If parent exists but is a file, we must fail.
    if abs_path.parent.exists() and abs_path.parent.is_file():
        raise NotADirectoryError(f"Parent is a file, not a directory: {abs_path.parent}")

    content_str = coerce_content_for_write(rel, step.content)

    if step.op in {"create", "replace"}:
        write_mode = "w"
    elif step.op == "patch":
        write_mode = "a" if step.mode == "append" else "w"
    else:
        raise RuntimeError(f"unknown op: {step.op}")

    with abs_path.open(write_mode, encoding="utf-8") as f:
        f.write(content_str)

    print(f"STEP: {step.op} {rel} (mode={step.mode})")


def run_plan(plan: Dict[str, Any]) -> None:
    summary, steps = parse_steps(plan)

    if not steps:
        print("No steps provided in plan, nothing to do.")
        return

    # Apply all steps
    for step in steps:
        apply_step(step)

    # Git add & commit (only if changes)
    sh("git add .")

    status = sh("git status --porcelain")
    if status.strip():
        # Keep commit message safe
        safe_summary = summary.replace('"', "'").strip()
        if not safe_summary:
            safe_summary = "Tyme CMS update"
        sh(f'git commit -m "{safe_summary}"')
    else:
        print("No changes detected; skipping commit.")


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

def main() -> None:
    raw = " ".join(sys.argv[1:]).strip()
    if not raw:
        print("No command provided.")
        sys.exit(0)

    print("Using Natural Language Command Engine (NLC).")
    run_nlc(raw)


if __name__ == "__main__":
    main()