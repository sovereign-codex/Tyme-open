#!/usr/bin/env python3
"""Human-guided annotation helper for lattice observations."""

# Phase-6: Human-guided interpretation & annotation (context-only)

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_REFERENCE_TYPES = {"index", "delta", "trend", "anomaly"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_INTENTS = {"explanation", "hypothesis", "historical_note", "caution", "clarification"}


@dataclass
class AnnotationInput:
    author: str
    reference_type: str
    interpretation_text: str
    confidence: str
    intent: str
    reference_id: str | None
    reference_window: str | None
    timestamp_utc: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Append a human-authored lattice annotation. "
            "This helper never modifies lattice facts and never enforces automation."
        )
    )
    parser.add_argument(
        "--annotations-path",
        default="codex/lattice/annotations.json",
        help="Path to annotations.json (default: codex/lattice/annotations.json)",
    )
    parser.add_argument("--author", required=True, help="Human author identifier or alias")
    parser.add_argument(
        "--reference-type",
        required=True,
        choices=sorted(ALLOWED_REFERENCE_TYPES),
        help="Reference type: index, delta, trend, anomaly",
    )
    parser.add_argument("--reference-id", help="Reference id (mutually exclusive with --reference-window)")
    parser.add_argument(
        "--reference-window",
        help="Reference window (mutually exclusive with --reference-id)",
    )
    parser.add_argument(
        "--interpretation-text",
        required=True,
        help="Free-form human interpretation text",
    )
    parser.add_argument(
        "--confidence",
        required=True,
        choices=sorted(ALLOWED_CONFIDENCE),
        help="Confidence level: low, medium, high",
    )
    parser.add_argument(
        "--intent",
        required=True,
        choices=sorted(ALLOWED_INTENTS),
        help="Intent: explanation, hypothesis, historical_note, caution, clarification",
    )
    parser.add_argument(
        "--timestamp-utc",
        help="Override timestamp in ISO-8601 UTC (default: now)",
    )
    return parser.parse_args()


def warn(message: str) -> None:
    print(f"[annotation-helper] {message}", file=sys.stderr)


def load_annotations(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return {"annotations": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warn(f"Unable to parse {path}: {exc}")
        return None
    if isinstance(data, list):
        return {"annotations": data}
    if isinstance(data, dict) and isinstance(data.get("annotations"), list):
        return data
    warn("annotations.json must be a list or an object with an 'annotations' list")
    return None


def validate_input(values: AnnotationInput) -> list[str]:
    errors: list[str] = []
    if values.reference_id and values.reference_window:
        errors.append("Provide either reference_id or reference_window, not both.")
    if not values.reference_id and not values.reference_window:
        errors.append("Provide a reference_id or reference_window.")
    if values.reference_type not in ALLOWED_REFERENCE_TYPES:
        errors.append("reference_type is invalid.")
    if values.confidence not in ALLOWED_CONFIDENCE:
        errors.append("confidence is invalid.")
    if values.intent not in ALLOWED_INTENTS:
        errors.append("intent is invalid.")
    return errors


def build_annotation(values: AnnotationInput) -> dict[str, Any]:
    timestamp = values.timestamp_utc
    if not timestamp:
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    annotation: dict[str, Any] = {
        "annotation_id": str(uuid.uuid4()),
        "author": values.author,
        "timestamp_utc": timestamp,
        "reference_type": values.reference_type,
        "interpretation_text": values.interpretation_text,
        "confidence": values.confidence,
        "intent": values.intent,
    }
    if values.reference_id:
        annotation["reference_id"] = values.reference_id
    if values.reference_window:
        annotation["reference_window"] = values.reference_window
    return annotation


def main() -> int:
    args = parse_args()
    values = AnnotationInput(
        author=args.author,
        reference_type=args.reference_type,
        interpretation_text=args.interpretation_text,
        confidence=args.confidence,
        intent=args.intent,
        reference_id=args.reference_id,
        reference_window=args.reference_window,
        timestamp_utc=args.timestamp_utc,
    )
    errors = validate_input(values)
    if errors:
        for error in errors:
            warn(error)
        warn("No annotation appended.")
        return 0

    annotations_path = Path(args.annotations_path)
    data = load_annotations(annotations_path)
    if data is None:
        warn("No annotation appended.")
        return 0

    annotation = build_annotation(values)
    data.setdefault("annotations", [])
    data["annotations"].append(annotation)

    annotations_path.parent.mkdir(parents=True, exist_ok=True)
    annotations_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Appended annotation {annotation['annotation_id']} to {annotations_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
