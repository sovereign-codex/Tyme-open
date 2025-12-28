#!/usr/bin/env python3
"""Validate directive JSON files against directive.v1.schema.json."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "directive.v1.schema.json"


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def is_iso_datetime(value: str) -> bool:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_value(schema: Dict[str, Any], value: Any, path: str) -> List[str]:
    errors: List[str] = []
    schema_type = schema.get("type")

    if schema_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return errors
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for req_key in required:
            if req_key not in value:
                errors.append(f"{path}: missing required property '{req_key}'")
        additional = schema.get("additionalProperties", True)
        if additional is False:
            extra_keys = sorted(set(value.keys()) - set(properties.keys()))
            for extra_key in extra_keys:
                errors.append(f"{path}: unexpected property '{extra_key}'")
        for key, item in value.items():
            if key in properties:
                errors.extend(
                    validate_value(properties[key], item, f"{path}.{key}")
                )
        return errors

    if schema_type == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
            return errors

    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(repr(item) for item in schema["enum"])
        errors.append(f"{path}: value {value!r} not in enum [{allowed}]")

    if schema.get("format") == "date-time" and isinstance(value, str):
        if not is_iso_datetime(value):
            errors.append(f"{path}: value {value!r} is not valid date-time")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate directive JSON files against directive.v1.schema.json."
    )
    parser.add_argument("json_path", type=Path, help="Path to JSON file to validate")
    args = parser.parse_args()

    schema = load_json(SCHEMA_PATH)
    payload = load_json(args.json_path)

    errors = validate_value(schema, payload, "$")
    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
