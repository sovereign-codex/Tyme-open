#!/usr/bin/env python3
"""
Phase-3 Lattice Trend Awareness
OBSERVATIONAL ONLY — NO ENFORCEMENT
"""

import json
import math
from pathlib import Path

LATTICE_DIR = Path("codex/lattice")
HISTORY_FILE = LATTICE_DIR / "history.json"
TRENDS_FILE = LATTICE_DIR / "trends.json"

SEVERITY_KEYS = ["info", "low", "medium", "high"]
SCOPE_KEYS = ["guardian", "cms", "directive"]


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def average(values: list[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def std_dev(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0
    avg = average(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def extract_series(entries: list[dict]) -> tuple[list[int], dict, dict]:
    total_series: list[int] = []
    by_severity_series = {key: [] for key in SEVERITY_KEYS}
    by_scope_series = {key: [] for key in SCOPE_KEYS}

    for entry in entries:
        delta = entry.get("delta") or {}
        changes = delta.get("changes") or {}
        total_series.append(int(changes.get("total_signals", 0) or 0))

        by_severity = changes.get("by_severity") or {}
        for key in SEVERITY_KEYS:
            by_severity_series[key].append(int(by_severity.get(key, 0) or 0))

        by_scope = changes.get("by_scope") or {}
        for key in SCOPE_KEYS:
            by_scope_series[key].append(int(by_scope.get(key, 0) or 0))

    return total_series, by_severity_series, by_scope_series


def detect_spike(latest: int, avg: float) -> dict:
    threshold = max(2.0, abs(avg) * 0.5)
    delta = latest - avg
    spike = abs(delta) >= threshold
    direction = "increase" if delta > 0 else "decrease" if delta < 0 else "flat"
    return {
        "latest": latest,
        "average": round(avg, 2),
        "delta": round(delta, 2),
        "threshold": round(threshold, 2),
        "spike": spike,
        "direction": direction,
    }


def detect_drift(series: list[int]) -> dict:
    if len(series) < 2:
        return {"pattern": "insufficient_data", "mean_delta": 0.0, "recent_deltas": []}

    deltas = [series[index + 1] - series[index] for index in range(len(series) - 1)]
    mean_delta = average(deltas)
    monotonic_increase = all(delta >= 0 for delta in deltas)
    monotonic_decrease = all(delta <= 0 for delta in deltas)
    avg_series = average(series)
    sudden_threshold = max(3.0, abs(avg_series) * 1.0)
    sudden_change = abs(deltas[-1]) >= sudden_threshold

    if sudden_change:
        pattern = "sudden_change"
    elif monotonic_increase and mean_delta > 0.5:
        pattern = "slow_increase"
    elif monotonic_decrease and mean_delta < -0.5:
        pattern = "slow_decrease"
    else:
        pattern = "no_clear_drift"

    return {
        "pattern": pattern,
        "mean_delta": round(mean_delta, 2),
        "recent_deltas": deltas[-3:],
    }


def classify_stability(series: list[int], drift_pattern: str) -> dict:
    if len(series) < 3:
        return {"classification": "emerging", "reason": "insufficient history"}

    avg_series = average(series)
    deviation = std_dev(series)
    sudden_or_volatile = deviation > max(2.0, abs(avg_series) * 0.75)

    if sudden_or_volatile:
        return {"classification": "volatile", "reason": "high variance"}
    if drift_pattern == "slow_increase":
        return {"classification": "emerging", "reason": "consistent upward drift"}
    if drift_pattern == "slow_decrease":
        return {"classification": "declining", "reason": "consistent downward drift"}
    return {"classification": "stable", "reason": "no significant drift"}


def main() -> None:
    history = load_json(HISTORY_FILE, {"window_size": 10, "entries": []})
    entries = history.get("entries") or []

    total_series, by_severity_series, by_scope_series = extract_series(entries)

    total_avg = average(total_series)
    by_severity_avg = {key: round(average(values), 2) for key, values in by_severity_series.items()}
    by_scope_avg = {key: round(average(values), 2) for key, values in by_scope_series.items()}

    latest_total = total_series[-1] if total_series else 0
    drift = detect_drift(total_series)
    stability = classify_stability(total_series, drift["pattern"])

    spikes = {
        "total_signals": detect_spike(latest_total, total_avg),
        "by_severity": {
            key: detect_spike(values[-1] if values else 0, average(values))
            for key, values in by_severity_series.items()
        },
        "by_scope": {
            key: detect_spike(values[-1] if values else 0, average(values))
            for key, values in by_scope_series.items()
        },
    }

    trends = {
        "window_size": history.get("window_size", 10),
        "generated_at": history.get("generated_at"),
        "entry_count": len(entries),
        "rolling_average": {
            "total_signals": round(total_avg, 2),
            "by_severity": by_severity_avg,
            "by_scope": by_scope_avg,
        },
        "spikes": spikes,
        "drift": {"total_signals": drift},
        "stability": stability,
    }

    TRENDS_FILE.write_text(json.dumps(trends, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
