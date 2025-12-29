#!/usr/bin/env python3
"""
Phase-7 Lattice Memory Compaction
OBSERVATIONAL ONLY — NO ENFORCEMENT
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

LATTICE_DIR = Path("codex/lattice")
HISTORY_FILE = LATTICE_DIR / "history.json"
TRENDS_FILE = LATTICE_DIR / "trends.json"
ANOMALIES_FILE = LATTICE_DIR / "anomalies.md"
ANNOTATIONS_FILE = LATTICE_DIR / "annotations.json"
SUMMARY_JSON = LATTICE_DIR / "canonical_summary.json"
SUMMARY_MD = LATTICE_DIR / "canonical_summary.md"


def load_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def compute_summary_id(contents: list[str]) -> str:
    digest = hashlib.sha256("".join(contents).encode("utf-8")).hexdigest()
    return f"canonical-{digest[:12]}"


def extract_time_span(entries: list[dict]) -> tuple[str, str]:
    if not entries:
        return "n/a", "n/a"
    start = entries[0].get("timestamp_utc") or "n/a"
    end = entries[-1].get("timestamp_utc") or "n/a"
    return start, end


def pick_generated_at(candidates: list[str]) -> str:
    usable = [value for value in candidates if value and value not in {"unknown", "n/a"}]
    return max(usable) if usable else "n/a"


def parse_anomalies(anomalies_text: str) -> list[str]:
    if not anomalies_text:
        return []
    lines = anomalies_text.splitlines()
    current_section = None
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip().lower()
            continue
        if current_section in {"summary", "narratives"} and stripped.startswith("- "):
            item = stripped[2:].strip()
            lowered = item.lower()
            if item and not (lowered.startswith("no anomalies") or lowered.startswith("no anomaly")):
                collected.append(item.rstrip("."))
    seen: set[str] = set()
    deduped = []
    for item in collected:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def build_dominant_trends(trends: dict, entry_count: int) -> list[str]:
    if entry_count < 2:
        return ["Insufficient history for long-horizon trends."]
    rolling = trends.get("rolling_average", {})
    total = rolling.get("total_signals", 0)
    stability = trends.get("stability", {})
    drift = (trends.get("drift") or {}).get("total_signals", {})
    trends_list = [
        f"Rolling average total signals: {total}",
        f"Stability classification: {stability.get('classification', 'n/a')}",
    ]
    drift_pattern = drift.get("pattern")
    if drift_pattern:
        trends_list.append(f"Drift pattern: {drift_pattern}")
    return trends_list


def build_notable_shifts(trends: dict) -> list[str]:
    shifts: list[str] = []
    drift = (trends.get("drift") or {}).get("total_signals", {})
    if drift.get("pattern") == "sudden_change":
        shifts.append("Sudden change detected in total signals.")
    spikes = trends.get("spikes") or {}
    total_spike = spikes.get("total_signals") or {}
    if total_spike.get("spike"):
        shifts.append(
            f"Spike in total signals ({total_spike.get('direction', 'n/a')}, "
            f"delta {total_spike.get('delta', 0)})."
        )
    by_severity = spikes.get("by_severity") or {}
    for key, spike in by_severity.items():
        if spike.get("spike"):
            shifts.append(f"Spike in {key} severity signals ({spike.get('direction', 'n/a')}).")
    by_scope = spikes.get("by_scope") or {}
    for key, spike in by_scope.items():
        if spike.get("spike"):
            shifts.append(f"Spike in {key} scope signals ({spike.get('direction', 'n/a')}).")
    return shifts or ["No notable shifts detected."]


def build_confidence_level(run_count: int) -> str:
    if run_count >= 8:
        return "high"
    if run_count >= 3:
        return "medium"
    return "low"


def main() -> None:
    # Phase-7: Memory compaction & canonical summaries (read-only)
    history = load_json(HISTORY_FILE, {"window_size": 10, "entries": []})
    trends = load_json(TRENDS_FILE, {})
    annotations = load_json(ANNOTATIONS_FILE, {"annotations": []})
    anomalies_text = read_text(ANOMALIES_FILE)

    entries = history.get("entries") or []
    entry_count = len(entries)
    start, end = extract_time_span(entries)
    time_span = "n/a" if start == "n/a" and end == "n/a" else f"{start} → {end}"

    anomalies = parse_anomalies(anomalies_text)
    dominant_trends = build_dominant_trends(trends, entry_count)
    notable_shifts = build_notable_shifts(trends)
    stability = trends.get("stability", {})

    annotations_list = annotations.get("annotations") if isinstance(annotations, dict) else annotations
    annotation_count = len(annotations_list) if isinstance(annotations_list, list) else 0
    latest_annotation = ""
    if isinstance(annotations_list, list) and annotations_list:
        latest_annotation = max(
            (item.get("timestamp_utc", "") for item in annotations_list if isinstance(item, dict)),
            default="",
        )

    candidates = [
        history.get("generated_at"),
        trends.get("generated_at"),
        latest_annotation,
    ]
    if "Generated at:" in anomalies_text:
        for line in anomalies_text.splitlines():
            if line.strip().startswith("- Generated at:"):
                candidates.append(line.split(":", 1)[1].strip())
                break

    generated_at = pick_generated_at([str(value) for value in candidates if value is not None])
    summary_id = compute_summary_id(
        [
            read_text(HISTORY_FILE),
            read_text(TRENDS_FILE),
            anomalies_text,
            read_text(ANNOTATIONS_FILE),
        ]
    )

    summary = {
        "summary_id": summary_id,
        "generated_at": generated_at,
        "horizon": {
            "number_of_runs": entry_count,
            "time_span": time_span,
        },
        "dominant_trends": dominant_trends,
        "recurring_anomalies": anomalies,
        "stability_assessment": {
            "classification": stability.get("classification", "n/a"),
            "reason": stability.get("reason", "n/a"),
        },
        "notable_shifts": notable_shifts,
        "confidence_level": build_confidence_level(entry_count),
    }

    narrative_lines = [
        "# Canonical Lattice Summary",
        "",
        "This summary compresses long-horizon lattice history into stable reference points.",
        "",
        "## System evolution",
        f"- Runs observed: {entry_count}",
        f"- Time span: {time_span}",
        f"- Generated at: {generated_at}",
        "",
        "## Long-term patterns",
        *[f"- {item}" for item in dominant_trends],
        "",
        "## Signals that matter",
        "- Stability reflects sustained variance or steadiness across the observed window.",
        "- Drift and spikes highlight directional movement that may affect future interpretation.",
        "",
        "## Recurring anomalies",
        *([f"- {item}" for item in anomalies] if anomalies else ["- No recurring anomalies detected."]),
        "",
        "## Notable shifts",
        *[f"- {item}" for item in notable_shifts],
        "",
        "## Human context",
        f"- Annotations recorded: {annotation_count}",
        f"- Latest annotation: {latest_annotation or 'n/a'}",
        "",
        "## Uncertainty and limits",
        "- Confidence reflects the length of history available.",
        "- Limited or missing history reduces certainty in long-horizon interpretations.",
    ]

    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text("\n".join(narrative_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        fallback = {
            "summary_id": "canonical-error",
            "generated_at": "n/a",
            "horizon": {"number_of_runs": 0, "time_span": "n/a"},
            "dominant_trends": ["Insufficient data to summarize trends."],
            "recurring_anomalies": [],
            "stability_assessment": {"classification": "n/a", "reason": "n/a"},
            "notable_shifts": ["No notable shifts detected."],
            "confidence_level": "low",
        }
        SUMMARY_JSON.write_text(json.dumps(fallback, indent=2) + "\n", encoding="utf-8")
        SUMMARY_MD.write_text(
            "# Canonical Lattice Summary\n\n"
            "Summary generation encountered an error; outputs are placeholders.\n",
            encoding="utf-8",
        )
