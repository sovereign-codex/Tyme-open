#!/usr/bin/env python3
"""
Phase-3 Lattice History Construction
OBSERVATIONAL ONLY — NO ENFORCEMENT
"""

import json
from pathlib import Path

LATTICE_DIR = Path("codex/lattice")
DELTA_FILE = LATTICE_DIR / "delta.json"
HISTORY_FILE = LATTICE_DIR / "history.json"

WINDOW_SIZE = 10


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def build_entry(delta: dict) -> dict:
    return {
        "run_id": delta.get("run_id", "unknown"),
        "workflow_name": delta.get("workflow_name", "unknown"),
        "commit_sha": delta.get("commit_sha", "unknown"),
        "timestamp_utc": delta.get("timestamp_utc", "unknown"),
        "delta": delta,
    }


def main() -> None:
    history = load_json(HISTORY_FILE, {"window_size": WINDOW_SIZE, "entries": []})
    entries = list(history.get("entries") or [])

    delta = load_json(DELTA_FILE, {})
    if delta:
        entry = build_entry(delta)
        entries = [item for item in entries if item.get("run_id") != entry["run_id"]]
        entries.append(entry)

    window_size = int(history.get("window_size") or WINDOW_SIZE)
    if window_size <= 0:
        window_size = WINDOW_SIZE

    if len(entries) > window_size:
        entries = entries[-window_size:]

    generated_at = entries[-1]["timestamp_utc"] if entries else None

    history_out = {
        "window_size": window_size,
        "generated_at": generated_at,
        # Phase-3: Lattice trend awareness (read-only, observational)
        "entries": entries,
    }

    HISTORY_FILE.write_text(json.dumps(history_out, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
