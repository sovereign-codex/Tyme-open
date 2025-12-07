import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CMS_LOG_PATH = BASE_DIR / "cms-log.json"
ORCH_LOG_PATH = BASE_DIR / "orchestration-log.json"


def _load_log(path):
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # If file is corrupt or empty, reset
        return []


def _write_log(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def log_cms_event(command_text: str, mode: str = "natural", result_summary: str | None = None):
    """
    Append a CMS event to cms-log.json
    """
    entries = _load_log(CMS_LOG_PATH)
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "command": command_text,
        "mode": mode,
        "summary": result_summary or ""
    }
    entries.append(entry)
    _write_log(CMS_LOG_PATH, entries)


def log_orchestration_run(code: str, meta: dict | None = None):
    """
    Append an orchestration event to orchestration-log.json
    """
    entries = _load_log(ORCH_LOG_PATH)
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "code": code,
        "meta": meta or {}
    }
    entries.append(entry)
    _write_log(ORCH_LOG_PATH, entries)
