#!/usr/bin/env python3
"""Validate stewardship artifacts (warn-only)."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


STEWARDSHIP_DIR = Path(__file__).resolve().parent
ARTIFACTS = {
    "stewardship_charter": STEWARDSHIP_DIR / "stewardship_charter.md",
    "steward_registry": STEWARDSHIP_DIR / "steward_registry.json",
    "succession_protocol": STEWARDSHIP_DIR / "succession_protocol.md",
    "continuity_checklist": STEWARDSHIP_DIR / "continuity_checklist.md",
}


@dataclass
class StewardStatus:
    active_count: int
    roles_present: List[str]
    succession_ready: str
    archival_mode: bool


def parse_datetime(value: Optional[str], field: str, warnings: List[str]) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        warnings.append(f"{field} must be a string in ISO-8601 UTC format")
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        warnings.append(f"{field} must be a valid ISO-8601 datetime")
        return None


def load_registry(path: Path, warnings: List[str]) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        warnings.append("steward_registry.json is missing")
        return {}
    except json.JSONDecodeError as exc:
        warnings.append(f"steward_registry.json contains invalid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        warnings.append("steward_registry.json must contain a JSON object")
        return {}
    return payload


def validate_registry(payload: Dict[str, Any], warnings: List[str]) -> StewardStatus:
    archival_mode = bool(payload.get("archival_mode"))
    stewards = payload.get("stewards", [])
    if not isinstance(stewards, list):
        warnings.append("stewards must be a list")
        stewards = []

    if not stewards:
        warnings.append("steward registry is empty")

    active_count = 0
    roles_present: List[str] = []
    now = datetime.now(timezone.utc)

    for idx, steward in enumerate(stewards):
        entry_path = f"stewards[{idx}]"
        if not isinstance(steward, dict):
            warnings.append(f"{entry_path} must be an object")
            continue
        missing = [
            key
            for key in (
                "steward_id",
                "name_or_alias",
                "roles",
                "appointed_by",
                "appointed_at",
                "term",
                "status",
                "notes",
            )
            if key not in steward
        ]
        if missing:
            warnings.append(f"{entry_path} missing required fields: {', '.join(missing)}")

        roles = steward.get("roles")
        if isinstance(roles, list):
            roles_present.extend([role for role in roles if isinstance(role, str)])
        else:
            warnings.append(f"{entry_path}.roles must be a list of strings")

        appointed_at = parse_datetime(steward.get("appointed_at"), f"{entry_path}.appointed_at", warnings)
        term = steward.get("term")
        if not isinstance(term, dict):
            warnings.append(f"{entry_path}.term must be an object")
            term = {}
        term_start = parse_datetime(term.get("start"), f"{entry_path}.term.start", warnings)
        term_end = parse_datetime(term.get("end"), f"{entry_path}.term.end", warnings)

        status = steward.get("status")
        if status not in {"active", "emeritus", "retired", "revoked"}:
            warnings.append(f"{entry_path}.status must be one of active, emeritus, retired, revoked")

        if status == "active":
            active_count += 1
            if term_end and term_end < now:
                warnings.append(f"{entry_path} term has expired")

        if appointed_at is None or term_start is None:
            warnings.append(f"{entry_path} missing required date fields")

    if active_count == 0 and not archival_mode:
        warnings.append("no active stewards and archival mode is not declared")

    succession_ready = "ok" if (archival_mode or active_count > 0) else "warning"

    return StewardStatus(
        active_count=active_count,
        roles_present=sorted(set(roles_present)),
        succession_ready=succession_ready,
        archival_mode=archival_mode,
    )


def validate_artifacts(warnings: List[str]) -> None:
    for name, path in ARTIFACTS.items():
        if not path.exists():
            warnings.append(f"missing stewardship artifact: {name} ({path})")


def write_summary(path: Path, status: StewardStatus) -> None:
    lines = ["### Stewardship Status"]
    lines.append(f"- Active stewards: {status.active_count}")
    roles = ", ".join(status.roles_present) if status.roles_present else "none"
    lines.append(f"- Roles present: {roles}")
    lines.append(f"- Succession readiness: {status.succession_ready}")
    lines.append(f"- Archival mode: {str(status.archival_mode).lower()}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate stewardship artifacts (warn-only).")
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=None,
        help="Optional path to write a stewardship status summary markdown.",
    )
    args = parser.parse_args()

    warnings: List[str] = []
    validate_artifacts(warnings)

    registry = load_registry(ARTIFACTS["steward_registry"], warnings)
    status = validate_registry(registry, warnings)

    if args.summary_path:
        write_summary(args.summary_path, status)

    for warning in warnings:
        print(f"Warning: {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
