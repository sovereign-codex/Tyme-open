#!/usr/bin/env python3
"""
Phase-1 Lattice Signal Emitter
OBSERVATIONAL ONLY — NO ENFORCEMENT
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

LATTICE_DIR = Path("codex/lattice")
SIGNAL_LOG = LATTICE_DIR / "signals.jsonl"

LATTICE_DIR.mkdir(parents=True, exist_ok=True)

def emit_signal(
    signal_type: str,
    scope: str,
    severity: str,
    message: str,
    policy_id: str | None = None,
    payload_ref: str | None = None,
):
    signal = {
        "signal_id": str(uuid.uuid4()),
        "signal_type": signal_type,
        "scope": scope,
        "severity": severity,
        "policy_id": policy_id,
        "message": message,
        "payload_ref": payload_ref,
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "phase": 1,
        "mode": "observation_only",
    }

    with SIGNAL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(signal) + "\n")

    return signal


if __name__ == "__main__":
    # Smoke-test emission (safe)
    emit_signal(
        signal_type="lattice.bootstrap",
        scope="system",
        severity="info",
        message="Phase-1 lattice signal emitter initialized."
    )