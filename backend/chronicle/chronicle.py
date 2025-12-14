import os
import json
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from backend.crypto.attestation import (
    canonical_json,
    sha256_hex,
    sign_entry_hash,
)


BASE_DIR = Path(__file__).resolve().parent
CMS_LOG_PATH = BASE_DIR / "cms-log.json"
ORCH_LOG_PATH = BASE_DIR / "orchestration-log.json"


def _load_log(path):
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # If file is corrupt or empty, reset
        return []


def _write_log(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def log_cms_event(
    command_text: str,
    mode: str = "cms",
    result_summary: Optional[str] = None,
    *,
    commit_sha: Optional[str] = None,
    touched_files: Optional[List[str]] = None,
):
    """
    Append a CMS event to cms-log.json with:
    - hash chaining (tamper-evident)
    - optional Ed25519 signature (non-repudiation)
    - optional Git commit binding
    """

    entries = _load_log(CMS_LOG_PATH)

    prev_hash = entries[-1].get("entry_hash") if entries else None

    base_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "command": command_text,
        "mode": mode,
        "summary": result_summary or "",
        "commit_sha": commit_sha,
        "touched_files": touched_files or [],
        "prev_hash": prev_hash,
    }

    # Compute deterministic entry hash (no signature fields included)
    entry_hash = sha256_hex(canonical_json(base_entry))

    signature_b64 = None
    key_id = None

    signing_key_b64 = os.environ.get("TYME_SIGNING_PRIVATE_KEY_B64", "").strip()
    if signing_key_b64:
        try:
            signature_b64, key_id = sign_entry_hash(
                signing_key_b64,
                entry_hash,
            )
        except Exception as e:
            # Signing failure must never block execution
            print(f"[WARN] CMS event signing failed: {e}")

    entry = {
        **base_entry,
        "entry_hash": entry_hash,
        "signature_b64": signature_b64,
        "key_id": key_id,
    }

    entries.append(entry)
    _write_log(CMS_LOG_PATH, entries)



def log_orchestration_run(code: str, meta: dict | None = None):
    """
    Append an orchestration event to orchestration-log.json
    """
    entries = _load_log(ORCH_LOG_PATH)
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "code": code,
        "meta": meta or {}
    }
    entries.append(entry)
    _write_log(ORCH_LOG_PATH, entries)
