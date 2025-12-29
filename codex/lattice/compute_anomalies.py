#!/usr/bin/env python3
"""
Phase-4 Lattice Anomaly Narratives
OBSERVATIONAL ONLY — NO ENFORCEMENT
"""

import json
import math
from pathlib import Path

LATTICE_DIR = Path("codex/lattice")
HISTORY_FILE = LATTICE_DIR / "history.json"
TRENDS_FILE = LATTICE_DIR / "trends.json"
ANOMALIES_FILE = LATTICE_DIR / "anomalies.md"

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


def format_number(value: float) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}"


def confidence_from_magnitude(magnitude: float, threshold: float, entry_count: int) -> str:
    if entry_count < 3:
        return "low"
    if threshold > 0 and magnitude >= threshold * 1.5:
        return "high"
    return "medium"


def build_spike_anomalies(spikes: dict, entry_count: int, scope_label: str) -> list[dict]:
    anomalies = []
    scope_prefix = f"{scope_label} " if scope_label else ""
    for key, spike in spikes.items():
        if not spike.get("spike"):
            continue
        latest = spike.get("latest", 0)
        avg = spike.get("average", 0.0)
        delta = spike.get("delta", 0.0)
        threshold = spike.get("threshold", 0.0)
        direction = spike.get("direction", "flat")
        magnitude = abs(float(delta))
        descriptor = "increase" if direction == "increase" else "decrease" if direction == "decrease" else "flat"
        anomalies.append(
            {
                "title": f"Spike in {scope_prefix}{key}",
                "type": "spike",
                "window": f"{entry_count} runs",
                "explanation": (
                    f"The latest {scope_prefix}{key} count shows a sudden {descriptor} compared to "
                    "the recent rolling average."
                ),
                "evidence": [
                    f"Latest: {format_number(latest)}",
                    f"Rolling average: {format_number(avg)}",
                    f"Delta: {format_number(delta)}",
                    f"Spike threshold: {format_number(threshold)}",
                ],
                "confidence": confidence_from_magnitude(magnitude, float(threshold), entry_count),
            }
        )
    return anomalies


def detect_trend_reversal(series: list[int]) -> dict | None:
    if len(series) < 2:
        return None
    prev_value = series[-2]
    latest_value = series[-1]
    if prev_value == 0 or latest_value == 0:
        return None
    if (prev_value > 0 and latest_value < 0) or (prev_value < 0 and latest_value > 0):
        avg = average(series)
        threshold = max(2.0, abs(avg) * 0.5)
        return {
            "previous": prev_value,
            "latest": latest_value,
            "threshold": threshold,
        }
    return None


def detect_volatility(series: list[int], entry_count: int) -> dict | None:
    if entry_count < 3:
        return None
    avg = average(series)
    deviation = std_dev(series)
    threshold = max(2.0, abs(avg) * 0.75)
    if deviation > threshold:
        return {"average": avg, "deviation": deviation, "threshold": threshold}
    return None


def detect_stability_disruption(series: list[int]) -> dict | None:
    if len(series) < 4:
        return None
    baseline = series[:-1]
    latest = series[-1]
    avg = average(baseline)
    deviation = std_dev(baseline)
    threshold = max(2.0, abs(avg) * 0.75)
    if deviation <= threshold * 0.5 and abs(latest - avg) >= threshold:
        return {
            "baseline_average": avg,
            "baseline_deviation": deviation,
            "latest": latest,
            "threshold": threshold,
        }
    return None


def write_anomalies(lines: list[str]) -> None:
    ANOMALIES_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    try:
        history = load_json(HISTORY_FILE, {"window_size": 10, "entries": []})
        trends = load_json(TRENDS_FILE, {})

        entries = history.get("entries") or []
        entry_count = len(entries)
        window_size = history.get("window_size", 10)
        generated_at = history.get("generated_at")

        total_series, by_severity_series, by_scope_series = extract_series(entries)

        anomalies: list[dict] = []

        spikes = (trends.get("spikes") or {}).get("total_signals") or {}
        if spikes.get("spike"):
            anomalies.extend(build_spike_anomalies({"total signals": spikes}, entry_count, ""))

        severity_spikes = (trends.get("spikes") or {}).get("by_severity") or {}
        anomalies.extend(build_spike_anomalies(severity_spikes, entry_count, "severity"))

        scope_spikes = (trends.get("spikes") or {}).get("by_scope") or {}
        anomalies.extend(build_spike_anomalies(scope_spikes, entry_count, "scope"))

        reversal = detect_trend_reversal(total_series)
        if reversal:
            magnitude = max(abs(reversal["previous"]), abs(reversal["latest"]))
            anomalies.append(
                {
                    "title": "Rapid trend reversal in total signals",
                    "type": "reversal",
                    "window": "2 runs",
                    "explanation": (
                        "The total signal change flipped direction between the last two runs, "
                        "indicating a rapid reversal in recent movement."
                    ),
                    "evidence": [
                        f"Previous change: {format_number(reversal['previous'])}",
                        f"Latest change: {format_number(reversal['latest'])}",
                        f"Reversal threshold: {format_number(reversal['threshold'])}",
                    ],
                    "confidence": confidence_from_magnitude(magnitude, reversal["threshold"], entry_count),
                }
            )

        latest_delta = entries[-1].get("delta") if entries else {}
        latest_changes = (latest_delta or {}).get("changes") or {}
        new_types = sorted(set(latest_changes.get("new_signal_types") or []))
        removed_types = sorted(set(latest_changes.get("removed_signal_types") or []))

        if new_types:
            anomalies.append(
                {
                    "title": "Emerging signal types",
                    "type": "emergence",
                    "window": "1 run",
                    "explanation": "New signal types appeared in the most recent run.",
                    "evidence": [f"New types: {', '.join(new_types)}"],
                    "confidence": "medium" if entry_count >= 2 else "low",
                }
            )

        if removed_types:
            anomalies.append(
                {
                    "title": "Disappearing signal types",
                    "type": "disappearance",
                    "window": "1 run",
                    "explanation": "Some signal types present before are absent in the latest run.",
                    "evidence": [f"Removed types: {', '.join(removed_types)}"],
                    "confidence": "medium" if entry_count >= 2 else "low",
                }
            )

        volatility = detect_volatility(total_series, entry_count)
        if volatility:
            anomalies.append(
                {
                    "title": "Sustained volatility in total signals",
                    "type": "volatility",
                    "window": f"{entry_count} runs",
                    "explanation": (
                        "Total signal changes have shown elevated variability across multiple runs, "
                        "indicating sustained volatility."
                    ),
                    "evidence": [
                        f"Average change: {format_number(volatility['average'])}",
                        f"Standard deviation: {format_number(volatility['deviation'])}",
                        f"Volatility threshold: {format_number(volatility['threshold'])}",
                    ],
                    "confidence": "medium" if entry_count >= 5 else "low",
                }
            )

        disruption = detect_stability_disruption(total_series)
        if disruption:
            anomalies.append(
                {
                    "title": "Stability followed by disruption",
                    "type": "disruption",
                    "window": f"{entry_count} runs",
                    "explanation": (
                        "A previously steady pattern shifted sharply in the most recent run, "
                        "indicating disruption after prolonged stability."
                    ),
                    "evidence": [
                        f"Baseline average: {format_number(disruption['baseline_average'])}",
                        f"Baseline deviation: {format_number(disruption['baseline_deviation'])}",
                        f"Latest change: {format_number(disruption['latest'])}",
                        f"Disruption threshold: {format_number(disruption['threshold'])}",
                    ],
                    "confidence": "medium",
                }
            )

        # Phase-4: Lattice anomaly narratives (read-only, explanatory)
        lines = [
            "# Lattice Anomaly Narratives",
            "",
            "Phase-4: Lattice anomaly narratives (read-only, explanatory)",
            "",
            f"- Source: {TRENDS_FILE.as_posix()}, {HISTORY_FILE.as_posix()}",
            f"- Window size: {window_size}",
            f"- Entries observed: {entry_count}",
            f"- Generated at: {generated_at or 'n/a'}",
            "",
            "## Summary",
        ]

        if not anomalies:
            lines.append("- No anomalies detected in the current window.")
        else:
            for anomaly in anomalies:
                lines.append(f"- {anomaly['title']} ({anomaly['type']}, {anomaly['confidence']} confidence)")

        lines.append("")
        lines.append("## Narratives")

        if not anomalies:
            lines.append("- No anomaly narratives were generated for this window.")
        else:
            for index, anomaly in enumerate(anomalies, start=1):
                lines.extend(
                    [
                        f"### {index}. {anomaly['title']}",
                        f"- Anomaly type: {anomaly['type']}",
                        f"- Time window: {anomaly['window']}",
                        f"- Explanation: {anomaly['explanation']}",
                        "- Supporting evidence:",
                    ]
                )
                lines.extend([f"  - {item}" for item in anomaly["evidence"]])
                lines.append(f"- Confidence: {anomaly['confidence']}")
                lines.append("")

        write_anomalies(lines)
    except Exception:
        fallback_lines = [
            "# Lattice Anomaly Narratives",
            "",
            "Phase-4: Lattice anomaly narratives (read-only, explanatory)",
            "",
            "## Summary",
            "- No anomalies detected in the current window.",
            "",
            "## Narratives",
            "- No anomaly narratives were generated for this window.",
        ]
        write_anomalies(fallback_lines)


if __name__ == "__main__":
    main()
