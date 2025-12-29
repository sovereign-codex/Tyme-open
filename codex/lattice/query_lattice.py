#!/usr/bin/env python3
"""
Phase-5 Lattice Query Interface
Read-only introspection for lattice state, history, trends, and anomalies.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LATTICE_DIR = Path("codex/lattice")
INDEX_FILE = LATTICE_DIR / "index.json"
DELTA_FILE = LATTICE_DIR / "delta.json"
HISTORY_FILE = LATTICE_DIR / "history.json"
TRENDS_FILE = LATTICE_DIR / "trends.json"
ANOMALIES_FILE = LATTICE_DIR / "anomalies.md"

SEVERITY_KEYS = ["info", "low", "medium", "high"]
SCOPE_KEYS = ["guardian", "cms", "directive"]


@dataclass
class LoadedData:
    payload: dict
    source: str
    available: bool


def load_json(path: Path, default: dict) -> LoadedData:
    if not path.exists():
        return LoadedData(default, path.as_posix(), False)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = default
    return LoadedData(data, path.as_posix(), True)


def normalize_counts(raw: dict | None, keys: list[str]) -> dict:
    raw = raw or {}
    return {key: int(raw.get(key, 0) or 0) for key in keys}


def parse_anomalies_markdown(path: Path) -> dict:
    if not path.exists():
        return {
            "source": path.as_posix(),
            "available": False,
            "generated_at": None,
            "entries_observed": None,
            "anomalies": [],
        }

    lines = path.read_text(encoding="utf-8").splitlines()
    generated_at = None
    entries_observed = None

    for line in lines:
        if line.startswith("- Generated at:"):
            generated_at = line.split(":", 1)[1].strip()
        if line.startswith("- Entries observed:"):
            try:
                entries_observed = int(line.split(":", 1)[1].strip())
            except ValueError:
                entries_observed = None

    anomalies: list[dict[str, Any]] = []
    in_narratives = False
    current: dict[str, Any] | None = None

    def push_current() -> None:
        if current:
            anomalies.append(current.copy())

    for line in lines:
        if line.strip() == "## Narratives":
            in_narratives = True
            continue
        if not in_narratives:
            continue
        if line.startswith("### "):
            push_current()
            title = line[4:].strip()
            if ". " in title:
                _, title = title.split(". ", 1)
            current = {
                "title": title,
                "type": None,
                "confidence": None,
                "window": None,
            }
            continue
        if current is None:
            continue
        if line.startswith("- Anomaly type:"):
            current["type"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Time window:"):
            current["window"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Confidence:"):
            current["confidence"] = line.split(":", 1)[1].strip()
        elif line.startswith("## "):
            break

    push_current()

    return {
        "source": path.as_posix(),
        "available": True,
        "generated_at": generated_at,
        "entries_observed": entries_observed,
        "anomalies": anomalies,
    }


def build_status() -> dict:
    loaded = load_json(INDEX_FILE, {})
    payload = loaded.payload
    return {
        "source": loaded.source,
        "available": loaded.available,
        "total_signals": int(payload.get("total_signals", 0) or 0),
        "by_severity": normalize_counts(payload.get("by_severity"), SEVERITY_KEYS),
        "by_scope": normalize_counts(payload.get("by_scope"), SCOPE_KEYS),
    }


def build_delta() -> dict:
    loaded = load_json(DELTA_FILE, {})
    payload = loaded.payload
    changes = payload.get("changes") or {}
    return {
        "source": loaded.source,
        "available": loaded.available,
        "run_id": payload.get("run_id", "unknown"),
        "workflow_name": payload.get("workflow_name", "unknown"),
        "commit_sha": payload.get("commit_sha", "unknown"),
        "timestamp_utc": payload.get("timestamp_utc", "unknown"),
        "bootstrap": bool(payload.get("bootstrap", False)),
        "total_signals_delta": int(changes.get("total_signals", 0) or 0),
        "by_severity": normalize_counts(changes.get("by_severity"), SEVERITY_KEYS),
        "by_scope": normalize_counts(changes.get("by_scope"), SCOPE_KEYS),
        "new_signal_types": sorted(set(changes.get("new_signal_types") or [])),
        "removed_signal_types": sorted(set(changes.get("removed_signal_types") or [])),
    }


def build_trends() -> dict:
    loaded = load_json(TRENDS_FILE, {})
    payload = loaded.payload
    rolling = payload.get("rolling_average") or {}
    stability = payload.get("stability") or {}
    drift = payload.get("drift") or {}
    spikes = payload.get("spikes") or {}
    return {
        "source": loaded.source,
        "available": loaded.available,
        "entry_count": int(payload.get("entry_count", 0) or 0),
        "stability": {
            "classification": stability.get("classification", "n/a"),
            "reason": stability.get("reason", "n/a"),
        },
        "rolling_average": {
            "total_signals": float(rolling.get("total_signals", 0.0) or 0.0),
            "by_severity": {key: float(rolling.get("by_severity", {}).get(key, 0.0) or 0.0) for key in SEVERITY_KEYS},
            "by_scope": {key: float(rolling.get("by_scope", {}).get(key, 0.0) or 0.0) for key in SCOPE_KEYS},
        },
        "volatility_indicators": {
            "spikes": spikes,
            "drift": drift,
        },
    }


def build_anomalies(recent: int | None) -> dict:
    parsed = parse_anomalies_markdown(ANOMALIES_FILE)
    anomalies = parsed["anomalies"]
    if recent is not None:
        anomalies = anomalies[-recent:]
    return {
        "source": parsed["source"],
        "available": parsed["available"],
        "generated_at": parsed["generated_at"],
        "entries_observed": parsed["entries_observed"],
        "anomalies": anomalies,
    }


def format_text(title: str, data: dict) -> str:
    lines = [f"### {title}"]
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"- {key}:")
            for sub_key in sorted(value.keys()):
                lines.append(f"  - {sub_key}: {value[sub_key]}")
        elif isinstance(value, list):
            lines.append(f"- {key}:")
            if not value:
                lines.append("  - none")
            else:
                for item in value:
                    if isinstance(item, dict):
                        summary = ", ".join(
                            f"{k}={item.get(k)}" for k in ["title", "type", "confidence", "window"] if item.get(k)
                        )
                        lines.append(f"  - {summary}" if summary else "  - entry")
                    else:
                        lines.append(f"  - {item}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def emit_output(payload: dict, output_format: str, title: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(title, payload))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only lattice query interface (Phase-5).",
    )
    parser.add_argument("--format", choices=["json", "text"], default="text")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show current lattice signal counts.")
    subparsers.add_parser("delta", help="Show latest lattice delta summary.")
    subparsers.add_parser("trends", help="Show lattice trend summary.")

    anomalies_parser = subparsers.add_parser("anomalies", help="Show latest lattice anomalies.")
    anomalies_parser.add_argument("--recent", type=int, default=None)

    return parser


def main() -> None:
    # Phase-5: Lattice query interface (read-only introspection)
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "status":
        payload = build_status()
        emit_output(payload, args.format, "Lattice status (Phase-5, read-only)")
    elif args.command == "delta":
        payload = build_delta()
        emit_output(payload, args.format, "Lattice delta (Phase-5, read-only)")
    elif args.command == "trends":
        payload = build_trends()
        emit_output(payload, args.format, "Lattice trends (Phase-5, read-only)")
    elif args.command == "anomalies":
        payload = build_anomalies(args.recent)
        emit_output(payload, args.format, "Lattice anomalies (Phase-5, read-only)")


if __name__ == "__main__":
    main()
