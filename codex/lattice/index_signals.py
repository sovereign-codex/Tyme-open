#!/usr/bin/env python3
"""
Phase-1 Lattice Signal Indexer
OBSERVATIONAL ONLY — NO ENFORCEMENT
"""

import json
from collections import defaultdict
from pathlib import Path

LATTICE_DIR = Path("codex/lattice")
SIGNAL_LOG = LATTICE_DIR / "signals.jsonl"
INDEX_FILE = LATTICE_DIR / "index.json"

def load_signals():
    if not SIGNAL_LOG.exists():
        return []
    with SIGNAL_LOG.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def build_index(signals):
    index = {
        "total_signals": len(signals),
        "by_type": defaultdict(int),
        "by_scope": defaultdict(int),
        "by_severity": defaultdict(int),
        "by_policy": defaultdict(int),
        "latest_signal_at": None,
        "phase": 1,
        "mode": "observation_only",
    }

    for s in signals:
        index["by_type"][s.get("signal_type")] += 1
        index["by_scope"][s.get("scope")] += 1
        index["by_severity"][s.get("severity")] += 1

        pid = s.get("policy_id")
        if pid:
            index["by_policy"][pid] += 1

        ts = s.get("emitted_at")
        if ts:
            if not index["latest_signal_at"] or ts > index["latest_signal_at"]:
                index["latest_signal_at"] = ts

    # Convert defaultdicts to normal dicts
    for k in ["by_type", "by_scope", "by_severity", "by_policy"]:
        index[k] = dict(index[k])

    return index

def write_index(index):
    with INDEX_FILE.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
        f.write("\n")

if __name__ == "__main__":
    signals = load_signals()
    index = build_index(signals)
    write_index(index)