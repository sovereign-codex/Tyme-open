#!/usr/bin/env python3
"""
Phase-8: External observability export (metrics-only, no control)
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Iterable

LATTICE_DIR = Path("codex/lattice")

INDEX_FILE = LATTICE_DIR / "index.json"
DELTA_FILE = LATTICE_DIR / "delta.json"
HISTORY_FILE = LATTICE_DIR / "history.json"
TRENDS_FILE = LATTICE_DIR / "trends.json"
SUMMARY_FILE = LATTICE_DIR / "canonical_summary.json"
ANNOTATIONS_FILE = LATTICE_DIR / "annotations.json"
CONFIG_FILE = LATTICE_DIR / "export_config.json"

METRICS_PROM = LATTICE_DIR / "metrics.prom"
METRICS_JSON = LATTICE_DIR / "metrics.json"
METRICS_MANIFEST = LATTICE_DIR / "metrics_manifest.json"

SEVERITY_KEYS = ["info", "low", "medium", "high"]
SCOPE_KEYS = ["guardian", "cms", "directive"]
STABILITY_CLASSES = ["stable", "volatile", "emerging", "declining"]
CONFIDENCE_LEVELS = ["low", "medium", "high"]
INTENT_LEVELS = ["explanation", "hypothesis", "historical_note", "caution", "clarification"]

DEFAULT_CONFIG = {
    "top_signal_types_limit": 25,
    "include_annotations_counts": True,
    "include_canonical_summary": True,
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def load_config() -> dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    data = load_json(CONFIG_FILE, {})
    if isinstance(data, dict):
        for key in DEFAULT_CONFIG:
            if key in data:
                config[key] = data[key]
    return config


def normalize_label(value: str | None, allowed: Iterable[str]) -> str:
    if not value:
        return "unknown"
    if value in allowed:
        return value
    return "unknown"


def coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def pick_metadata(delta: dict, trends: dict, summary: dict, history: dict) -> dict[str, str]:
    run_id = (
        delta.get("run_id")
        or os.environ.get("GITHUB_RUN_ID")
        or os.environ.get("RUN_ID")
        or "unknown"
    )
    workflow_name = (
        delta.get("workflow_name")
        or os.environ.get("GITHUB_WORKFLOW")
        or os.environ.get("WORKFLOW_NAME")
        or "unknown"
    )
    commit_sha = (
        delta.get("commit_sha")
        or os.environ.get("GITHUB_SHA")
        or os.environ.get("COMMIT_SHA")
        or "unknown"
    )

    candidates = [
        delta.get("timestamp_utc"),
        trends.get("generated_at"),
        summary.get("generated_at"),
        history.get("generated_at"),
    ]
    timestamp_utc = max((value for value in candidates if value), default="unknown")
    if timestamp_utc == "unknown":
        timestamp_utc = datetime.datetime.now(datetime.timezone.utc)
        timestamp_utc = timestamp_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "run_id": str(run_id),
        "workflow_name": str(workflow_name),
        "commit_sha": str(commit_sha),
        "timestamp_utc": str(timestamp_utc),
    }


def top_signal_types(by_type: dict, limit: int, total: int) -> dict[str, int]:
    cleaned = {str(key): coerce_int(value) for key, value in (by_type or {}).items()}
    if not cleaned:
        if total > 0:
            return {"unknown": total}
        return {}

    sorted_items = sorted(cleaned.items(), key=lambda item: (-item[1], item[0]))
    top_items = sorted_items[:limit]
    remainder = sum(count for _, count in sorted_items[limit:])
    result = {name: count for name, count in top_items}
    if remainder:
        result["other"] = remainder
    return result


def count_labels(items: list[dict[str, Any]], key: str, allowed: list[str]) -> dict[str, int]:
    counts = {label: 0 for label in allowed}
    counts["unknown"] = 0
    for item in items:
        value = normalize_label(item.get(key), allowed)
        counts[value] = counts.get(value, 0) + 1
    return counts


def normalize_counts(source: dict[str, Any], allowed: list[str]) -> dict[str, int]:
    counts = {label: 0 for label in allowed}
    counts["unknown"] = 0
    for key, value in (source or {}).items():
        label = normalize_label(str(key), allowed)
        counts[label] = counts.get(label, 0) + coerce_int(value)
    return counts


def format_metric(name: str, value: int | float, labels: dict[str, str] | None = None) -> str:
    if labels:
        label_parts = ",".join(f'{key}="{labels[key]}"' for key in sorted(labels))
        return f"{name}{{{label_parts}}} {value}"
    return f"{name} {value}"


def build_metrics() -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    config = load_config()

    index = load_json(INDEX_FILE, {})
    delta = load_json(DELTA_FILE, {})
    history = load_json(HISTORY_FILE, {})
    trends = load_json(TRENDS_FILE, {})
    summary = load_json(SUMMARY_FILE, {}) if config.get("include_canonical_summary", True) else {}

    annotations_data: Any = {}
    if config.get("include_annotations_counts", True):
        annotations_data = load_json(ANNOTATIONS_FILE, {})

    metadata = pick_metadata(delta, trends, summary, history)

    total_signals = coerce_int(index.get("total_signals"))
    by_severity = normalize_counts(index.get("by_severity") or {}, SEVERITY_KEYS)
    by_scope = normalize_counts(index.get("by_scope") or {}, SCOPE_KEYS)

    by_signal_type = top_signal_types(
        index.get("by_type") or {},
        coerce_int(config.get("top_signal_types_limit", 25)),
        total_signals,
    )

    delta_changes = delta.get("changes") or {}
    delta_by_severity = normalize_counts(delta_changes.get("by_severity") or {}, SEVERITY_KEYS)
    delta_by_scope = normalize_counts(delta_changes.get("by_scope") or {}, SCOPE_KEYS)

    rolling = trends.get("rolling_average") or {}
    rolling_by_severity = rolling.get("by_severity") or {}
    rolling_by_scope = rolling.get("by_scope") or {}

    stability = trends.get("stability") or {}
    stability_class = normalize_label(stability.get("classification"), STABILITY_CLASSES)

    drift = (trends.get("drift") or {}).get("total_signals") or {}
    spikes = (trends.get("spikes") or {}).get("total_signals") or {}

    horizon = summary.get("horizon") or {}
    stability_assessment = summary.get("stability_assessment") or {}

    annotations_list: list[dict[str, Any]] = []
    if isinstance(annotations_data, list):
        annotations_list = [item for item in annotations_data if isinstance(item, dict)]
    elif isinstance(annotations_data, dict):
        raw_list = annotations_data.get("annotations")
        if isinstance(raw_list, list):
            annotations_list = [item for item in raw_list if isinstance(item, dict)]

    annotations_total = len(annotations_list)
    annotations_by_intent = count_labels(annotations_list, "intent", INTENT_LEVELS)
    annotations_by_confidence = count_labels(annotations_list, "confidence", CONFIDENCE_LEVELS)

    metrics_json = {
        "metadata": metadata,
        "gauges": {
            "total_signals": total_signals,
            "delta_total_signals": coerce_int(delta_changes.get("total_signals")),
            "new_signal_types_count": len(delta_changes.get("new_signal_types") or []),
            "disappeared_signal_types_count": len(delta_changes.get("removed_signal_types") or []),
            "bootstrap": int(bool(delta.get("bootstrap"))),
            "rolling_average_total_signals": rolling.get("total_signals", 0),
            "volatility_mean_delta": drift.get("mean_delta", 0),
            "volatility_spike_delta": spikes.get("delta", 0),
            "horizon_runs": coerce_int(horizon.get("number_of_runs")),
            "recurring_anomalies_count": len(summary.get("recurring_anomalies") or []),
            "annotations_total_count": annotations_total,
        },
        "labeled_counts": {
            "signals_by_severity": by_severity,
            "signals_by_scope": by_scope,
            "signals_by_type": by_signal_type,
            "delta_by_severity": delta_by_severity,
            "delta_by_scope": delta_by_scope,
            "rolling_average_by_severity": {
                key: rolling_by_severity.get(key, 0) for key in SEVERITY_KEYS
            },
            "rolling_average_by_scope": {
                key: rolling_by_scope.get(key, 0) for key in SCOPE_KEYS
            },
            "stability_classification": {stability_class: 1},
            "stability_assessment": {
                normalize_label(stability_assessment.get("classification"), STABILITY_CLASSES): 1
            }
            if summary
            else {},
            "confidence_level": {
                normalize_label(summary.get("confidence_level"), CONFIDENCE_LEVELS): 1
            }
            if summary
            else {},
            "annotations_by_intent": annotations_by_intent,
            "annotations_by_confidence": annotations_by_confidence,
        },
    }

    prom_lines: list[str] = []
    prom_lines.append(format_metric("lattice_total_signals", total_signals))

    for key in SEVERITY_KEYS + ["unknown"]:
        prom_lines.append(
            format_metric(
                "lattice_signals_by_severity",
                coerce_int(by_severity.get(key)),
                {"severity": key},
            )
        )

    for key in SCOPE_KEYS + ["unknown"]:
        prom_lines.append(
            format_metric(
                "lattice_signals_by_scope",
                coerce_int(by_scope.get(key)),
                {"scope": key},
            )
        )

    for signal_type, count in by_signal_type.items():
        prom_lines.append(
            format_metric(
                "lattice_signals_by_signal_type",
                count,
                {"signal_type": signal_type},
            )
        )

    prom_lines.append(
        format_metric(
            "lattice_delta_total_signals", coerce_int(delta_changes.get("total_signals"))
        )
    )
    for key in SEVERITY_KEYS + ["unknown"]:
        prom_lines.append(
            format_metric(
                "lattice_delta_by_severity",
                coerce_int(delta_by_severity.get(key)),
                {"severity": key},
            )
        )
    for key in SCOPE_KEYS + ["unknown"]:
        prom_lines.append(
            format_metric(
                "lattice_delta_by_scope",
                coerce_int(delta_by_scope.get(key)),
                {"scope": key},
            )
        )

    prom_lines.append(
        format_metric(
            "lattice_new_signal_types_count",
            len(delta_changes.get("new_signal_types") or []),
        )
    )
    prom_lines.append(
        format_metric(
            "lattice_disappeared_signal_types_count",
            len(delta_changes.get("removed_signal_types") or []),
        )
    )
    prom_lines.append(
        format_metric("lattice_bootstrap", int(bool(delta.get("bootstrap"))))
    )

    prom_lines.append(
        format_metric("lattice_rolling_average_total_signals", rolling.get("total_signals", 0))
    )
    for key in SEVERITY_KEYS:
        prom_lines.append(
            format_metric(
                "lattice_rolling_average_by_severity",
                rolling_by_severity.get(key, 0),
                {"severity": key},
            )
        )
    for key in SCOPE_KEYS:
        prom_lines.append(
            format_metric(
                "lattice_rolling_average_by_scope",
                rolling_by_scope.get(key, 0),
                {"scope": key},
            )
        )

    prom_lines.append(
        format_metric(
            "lattice_stability_classification", 1, {"class": stability_class}
        )
    )

    prom_lines.append(
        format_metric(
            "lattice_volatility_mean_delta", drift.get("mean_delta", 0)
        )
    )
    prom_lines.append(
        format_metric(
            "lattice_volatility_spike_delta", spikes.get("delta", 0)
        )
    )

    if summary:
        prom_lines.append(
            format_metric("lattice_horizon_runs", coerce_int(horizon.get("number_of_runs")))
        )
        prom_lines.append(
            format_metric(
                "lattice_stability_assessment",
                1,
                {
                    "class": normalize_label(
                        stability_assessment.get("classification"), STABILITY_CLASSES
                    )
                },
            )
        )
        prom_lines.append(
            format_metric(
                "lattice_recurring_anomalies_count",
                len(summary.get("recurring_anomalies") or []),
            )
        )
        prom_lines.append(
            format_metric(
                "lattice_confidence_level",
                1,
                {
                    "confidence": normalize_label(
                        summary.get("confidence_level"), CONFIDENCE_LEVELS
                    )
                },
            )
        )

    prom_lines.append(format_metric("lattice_annotations_total_count", annotations_total))
    for key in INTENT_LEVELS + ["unknown"]:
        prom_lines.append(
            format_metric(
                "lattice_annotations_by_intent",
                annotations_by_intent.get(key, 0),
                {"intent": key},
            )
        )
    for key in CONFIDENCE_LEVELS + ["unknown"]:
        prom_lines.append(
            format_metric(
                "lattice_annotations_by_confidence",
                annotations_by_confidence.get(key, 0),
                {"confidence": key},
            )
        )

    data_sources = [
        str(INDEX_FILE),
        str(DELTA_FILE),
        str(HISTORY_FILE),
        str(TRENDS_FILE),
    ]
    if config.get("include_canonical_summary", True):
        data_sources.append(str(SUMMARY_FILE))
    if config.get("include_annotations_counts", True):
        data_sources.append(str(ANNOTATIONS_FILE))

    manifest = {
        "schema_version": "v1",
        "exported_files": [
            str(METRICS_PROM),
            str(METRICS_JSON),
            str(METRICS_MANIFEST),
        ],
        "data_sources": data_sources,
        "redaction_rules": [
            "metrics-only, no control",
            "no raw narrative text",
            "no directive text",
            "no file paths in labels",
            "no secrets",
        ],
        "cardinality_bounds": {
            "signal_type_top_n": coerce_int(config.get("top_signal_types_limit", 25)),
            "severity": SEVERITY_KEYS,
            "scope": SCOPE_KEYS,
            "class": STABILITY_CLASSES,
            "confidence": CONFIDENCE_LEVELS,
            "intent": INTENT_LEVELS,
            "fallback_bucket": "unknown",
        },
    }

    return metrics_json, prom_lines, manifest


def main() -> int:
    try:
        metrics_json, prom_lines, manifest = build_metrics()
        LATTICE_DIR.mkdir(parents=True, exist_ok=True)
        METRICS_PROM.write_text("\n".join(prom_lines) + "\n", encoding="utf-8")
        METRICS_JSON.write_text(json.dumps(metrics_json, indent=2) + "\n", encoding="utf-8")
        METRICS_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"[export-metrics] Warning: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
