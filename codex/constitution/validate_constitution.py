import argparse
import datetime as dt
import json
import os
from pathlib import Path
import importlib.util

REQUIRED_INVARIANTS = {
    "default_authority": "off",
    "no_silent_enforcement": True,
    "no_automatic_escalation": True,
    "reversible_activation": True,
    "explicit_human_consent_required": True,
    "enforceable_policies_must_be_opt_in": True,
    "enforcement_must_be_scoped": True,
    "enforcement_requires_attestation": True,
    "enforcement_requires_stability_threshold": True,
}

ALLOWED_ATTESTATION_PURPOSES = {
    "enable_authority",
    "disable_authority",
    "grant_scope",
    "revoke_scope",
}

ALLOWED_MODES = {"simulation_only", "enforce_opt_in"}


def _load_yaml(path: Path, warnings: list[str]):
    if not path.exists():
        warnings.append(f"Missing constitution file: {path}")
        return None
    if importlib.util.find_spec("yaml") is None:
        warnings.append("PyYAML is not installed; unable to parse constitution.v1.yaml")
        return None
    import yaml

    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - intentional warning only
        warnings.append(f"Failed to parse {path}: {exc}")
        return None


def _load_json(path: Path, warnings: list[str]):
    if not path.exists():
        warnings.append(f"Missing JSON file: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - intentional warning only
        warnings.append(f"Failed to parse {path}: {exc}")
        return None


def _parse_timestamp(value: str | None):
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def validate_constitution(base_dir: Path, strict: bool) -> tuple[dict, int]:
    warnings: list[str] = []
    errors: list[str] = []

    constitution_path = base_dir / "constitution.v1.yaml"
    authority_path = base_dir / "authority_state.json"
    attestations_dir = base_dir / "attestations"

    constitution = _load_yaml(constitution_path, warnings)
    if constitution is not None and not isinstance(constitution, dict):
        warnings.append("constitution.v1.yaml should be a mapping at the top level.")
        constitution = None

    invariants = None
    if constitution:
        invariants = constitution.get("invariants")
        if not isinstance(invariants, dict):
            warnings.append("Constitution invariants section is missing or invalid.")
            invariants = None

    if invariants:
        for key, expected in REQUIRED_INVARIANTS.items():
            if key not in invariants:
                warnings.append(f"Missing invariant: {key}")
            elif invariants[key] != expected:
                warnings.append(
                    f"Invariant {key} should be {expected!r}, found {invariants[key]!r}"
                )

    if constitution:
        eligibility = constitution.get("enforcement_eligibility") or {}
        default_mode = eligibility.get("default_policy_mode")
        if default_mode and default_mode != "simulation_only":
            warnings.append("default_policy_mode should remain simulation_only by default.")

    authority_state = _load_json(authority_path, warnings)
    if authority_state is not None and not isinstance(authority_state, dict):
        warnings.append("authority_state.json must be an object.")
        authority_state = None

    effective_authority = {
        "enabled": False,
        "mode": "simulation_only",
        "allowed_scopes": [],
        "allowed_policies": [],
        "granted_by": None,
        "granted_at": None,
        "expires_at": None,
    }

    if authority_state:
        for key in effective_authority:
            if key not in authority_state:
                warnings.append(f"authority_state.json missing key: {key}")
            else:
                effective_authority[key] = authority_state.get(key)

        if not isinstance(effective_authority["enabled"], bool):
            warnings.append("authority_state.enabled must be boolean.")
            effective_authority["enabled"] = False
        if effective_authority["mode"] not in ALLOWED_MODES:
            warnings.append("authority_state.mode must be simulation_only or enforce_opt_in.")
            effective_authority["mode"] = "simulation_only"
        for list_key in ("allowed_scopes", "allowed_policies"):
            if not isinstance(effective_authority[list_key], list):
                warnings.append(f"authority_state.{list_key} must be a list.")
                effective_authority[list_key] = []

    attestations: list[dict] = []
    if attestations_dir.exists():
        for item in sorted(attestations_dir.glob("*.json")):
            attestation = _load_json(item, warnings)
            if not isinstance(attestation, dict):
                warnings.append(f"Attestation {item.name} must be a JSON object.")
                continue

            missing_fields = [
                field
                for field in (
                    "attestation_id",
                    "author",
                    "timestamp_utc",
                    "purpose",
                    "scope",
                    "mode",
                    "duration",
                    "reason",
                )
                if field not in attestation
            ]
            if missing_fields:
                warnings.append(
                    f"Attestation {item.name} missing fields: {', '.join(missing_fields)}"
                )
                continue

            if attestation.get("purpose") not in ALLOWED_ATTESTATION_PURPOSES:
                warnings.append(f"Attestation {item.name} has invalid purpose.")
                continue
            if attestation.get("mode") not in ALLOWED_MODES:
                warnings.append(f"Attestation {item.name} has invalid mode.")
                continue

            scope = attestation.get("scope")
            if not isinstance(scope, dict):
                warnings.append(f"Attestation {item.name} scope must be an object.")
                continue
            for scope_key in ("workflows", "paths", "policy_ids"):
                if scope_key not in scope or not isinstance(scope.get(scope_key), list):
                    warnings.append(
                        f"Attestation {item.name} scope.{scope_key} must be a list."
                    )
                    continue

            duration = attestation.get("duration")
            if not isinstance(duration, dict) or "expires_at" not in duration:
                warnings.append(f"Attestation {item.name} duration.expires_at required.")
                continue

            attestations.append(attestation)
    else:
        warnings.append("Attestations directory missing.")

    enabling_attestation = any(
        att.get("purpose") == "enable_authority" for att in attestations
    )

    if effective_authority["enabled"] and not enabling_attestation:
        errors.append("Authority enabled without enable_authority attestation.")

    attestation_present = len(attestations) > 0

    enforceable_policy_ids: set[str] = set()
    if effective_authority["enabled"]:
        for att in attestations:
            if att.get("mode") == "enforce_opt_in":
                policy_ids = (att.get("scope") or {}).get("policy_ids") or []
                enforceable_policy_ids.update(str(pid) for pid in policy_ids)

    report = {
        "authority_enabled": bool(effective_authority["enabled"]),
        "mode": effective_authority["mode"],
        "attestation_present": attestation_present,
        "expires_at": effective_authority["expires_at"],
        "enforceable_policies_count": len(enforceable_policy_ids)
        if effective_authority["enabled"]
        else 0,
        "warnings": warnings,
        "errors": errors,
        "constitution_loaded": constitution is not None,
        "authority_state_loaded": authority_state is not None,
        "attestations_checked": len(attestations),
        "checked_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }

    if strict and errors:
        return report, 1
    return report, 0


def render_summary(report: dict) -> str:
    status = "OK" if not report["errors"] else "WARN"
    lines = ["### Constitution status", f"- Health: {status}"]
    lines.append(f"- Authority enabled? {report['authority_enabled']}")
    lines.append(f"- Mode: {report['mode']}")
    lines.append(f"- Attestation present? {'yes' if report['attestation_present'] else 'no'}")
    expires_at = report.get("expires_at") or "n/a"
    lines.append(f"- Expires at: {expires_at}")
    lines.append(
        f"- Enforceable policies count: {report['enforceable_policies_count']}"
    )

    if report["warnings"]:
        lines.append("- Warnings:")
        for warning in report["warnings"]:
            lines.append(f"  - {warning}")

    if report["errors"]:
        lines.append("- Errors:")
        for error in report["errors"]:
            lines.append(f"  - {error}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate constitutional artifacts.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if validation errors are found.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Optional path to write a JSON report.",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=None,
        help="Optional path to write a markdown summary.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    report, exit_code = validate_constitution(base_dir, args.strict)

    if args.report_path:
        args.report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary_text = render_summary(report)
    if args.summary_path:
        args.summary_path.write_text(summary_text, encoding="utf-8")
    else:
        print(summary_text)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
