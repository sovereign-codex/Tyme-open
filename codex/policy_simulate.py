#!/usr/bin/env python3
"""Policy simulation (dry-run) runner.

Loads policy definitions and optional payload/report inputs, then produces a
simulation-only summary. This script never exits non-zero and never performs
network calls.
"""

import importlib
import importlib.util
import json
import os
import sys
from typing import Any, Dict, List, Optional


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _load_json(path: str) -> Optional[Any]:
    content = _read_text(path)
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def _yaml_module():
    if importlib.util.find_spec("yaml") is None:
        return None
    return importlib.import_module("yaml")


def _load_yaml(path: str) -> Optional[Any]:
    content = _read_text(path)
    if not content:
        return None
    yaml_module = _yaml_module()
    if yaml_module is None:
        return None
    try:
        return yaml_module.safe_load(content)
    except Exception:
        return None


def _normalize_policies(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, dict):
        policies = raw.get("policies")
        if isinstance(policies, list):
            return [p for p in policies if isinstance(p, dict)]
    if isinstance(raw, list):
        return [p for p in raw if isinstance(p, dict)]
    return []


def _severity_rank(severity: str) -> int:
    order = {"info": 0, "low": 1, "medium": 2, "high": 3}
    return order.get(severity or "", 1)


def _max_severity(severities: List[str]) -> str:
    if not severities:
        return "low"
    ranked = sorted(severities, key=_severity_rank, reverse=True)
    return ranked[0]


def simulate() -> Dict[str, Any]:
    contract = _load_yaml("codex.contract.yaml")
    policies_raw = _load_yaml("codex/policies/policies.v1.yaml")
    directive_payload = _load_json("codex_directive_payload.json")
    report_payload = _load_json("codex_report.json")

    policies = _normalize_policies(policies_raw)
    violations: List[str] = []
    recommendations: List[str] = []

    for policy in policies:
        if not isinstance(policy, dict):
            continue
        if not policy.get("simulate_only", False):
            continue
        recommendation = policy.get("recommendation")
        if isinstance(recommendation, str):
            recommendations.append(recommendation)

    severity = _max_severity(
        [p.get("severity", "low") for p in policies if isinstance(p, dict)]
    )

    return {
        "attempted": True,
        "would_block": False,
        "severity": severity,
        "violated_policies": violations,
        "recommendations": recommendations,
        "inputs": {
            "contract_loaded": contract is not None,
            "policies_loaded": bool(policies),
            "directive_payload_loaded": directive_payload is not None,
            "report_payload_loaded": report_payload is not None,
        },
    }


def main() -> None:
    output_path = None
    if len(sys.argv) > 1 and sys.argv[1] == "--write":
        output_path = "policy_simulation.json"

    result = simulate()
    serialized = json.dumps(result, indent=2, sort_keys=True)

    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(serialized + "\n")
        except OSError:
            print(serialized)
    else:
        print(serialized)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        fallback = {
            "attempted": True,
            "would_block": False,
            "severity": "low",
            "violated_policies": [],
            "recommendations": [],
        }
        print(json.dumps(fallback, indent=2, sort_keys=True))
        sys.exit(0)
