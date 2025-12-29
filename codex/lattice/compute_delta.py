#!/usr/bin/env python3
"""
Phase-2 Lattice Delta Computation
OBSERVATIONAL ONLY — NO ENFORCEMENT
"""

import datetime
import json
import os
from pathlib import Path

LATTICE_DIR = Path("codex/lattice")
CURRENT_INDEX = LATTICE_DIR / "index.json"
PREVIOUS_INDEX = LATTICE_DIR / "index.previous.json"
DELTA_FILE = LATTICE_DIR / "delta.json"

SEVERITY_KEYS = ["info", "low", "medium", "high"]
SCOPE_KEYS = ["guardian", "cms", "directive"]


def load_index(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def diff_counts(current: dict, previous: dict, keys: list[str]) -> dict:
    current_counts = current or {}
    previous_counts = previous or {}
    return {
        key: int(current_counts.get(key, 0)) - int(previous_counts.get(key, 0))
        for key in keys
    }


def gather_signal_types(index: dict) -> set:
    return set((index.get("by_type") or {}).keys())


def main() -> None:
    current_index = load_index(CURRENT_INDEX)
    previous_index = load_index(PREVIOUS_INDEX)

    bootstrap = not previous_index

    current_total = int(current_index.get("total_signals", 0) or 0)
    previous_total = int(previous_index.get("total_signals", 0) or 0)

    current_by_severity = current_index.get("by_severity") or {}
    previous_by_severity = previous_index.get("by_severity") or {}

    current_by_scope = current_index.get("by_scope") or {}
    previous_by_scope = previous_index.get("by_scope") or {}

    current_types = gather_signal_types(current_index)
    previous_types = gather_signal_types(previous_index)

    delta = {
        "run_id": os.environ.get("GITHUB_RUN_ID")
        or os.environ.get("RUN_ID")
        or "unknown",
        "workflow_name": os.environ.get("GITHUB_WORKFLOW")
        or os.environ.get("WORKFLOW_NAME")
        or "unknown",
        "commit_sha": os.environ.get("GITHUB_SHA")
        or os.environ.get("COMMIT_SHA")
        or "unknown",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "bootstrap": bootstrap,
        # Phase-2: Lattice memory (read-only, delta-only)
        "changes": {
            "total_signals": current_total - previous_total,
            "by_severity": diff_counts(current_by_severity, previous_by_severity, SEVERITY_KEYS),
            "by_scope": diff_counts(current_by_scope, previous_by_scope, SCOPE_KEYS),
            "new_signal_types": sorted(current_types - previous_types),
            "removed_signal_types": sorted(previous_types - current_types),
        },
    }

    DELTA_FILE.write_text(json.dumps(delta, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
