import base64
import hashlib
import json
from typing import Any, Dict, Tuple

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
except Exception:  # pragma: no cover
    Ed25519PrivateKey = None
    Ed25519PublicKey = None
    serialization = None


def canonical_json(obj: Dict[str, Any]) -> str:
    """
    Stable, canonical JSON encoding for hashing and signing.
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def derive_key_id(public_key_bytes: bytes) -> str:
    """
    Short, stable public identifier for a signing key.
    """
    return hashlib.sha256(public_key_bytes).hexdigest()[:16]


def load_private_key_b64(priv_b64: str) -> "Ed25519PrivateKey":
    if Ed25519PrivateKey is None:
        raise RuntimeError("cryptography package not available")
    raw = base64.b64decode(priv_b64)
    return Ed25519PrivateKey.from_private_bytes(raw)


def public_key_bytes(priv: "Ed25519PrivateKey") -> bytes:
    pub = priv.public_key()
    return pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def sign_entry_hash(
    priv_b64: str,
    entry_hash_hex: str,
) -> Tuple[str, str]:
    """
    Sign a hash (hex) and return (signature_b64, key_id).
    """
    priv = load_private_key_b64(priv_b64)
    pub_bytes = public_key_bytes(priv)
    key_id = derive_key_id(pub_bytes)

    sig = priv.sign(bytes.fromhex(entry_hash_hex))
    sig_b64 = base64.b64encode(sig).decode("utf-8")
    return sig_b64, key_id


def verify_signature(
    pub_b64: str,
    entry_hash_hex: str,
    sig_b64: str,
) -> bool:
    if Ed25519PublicKey is None:
        raise RuntimeError("cryptography package not available")
    pub_raw = base64.b64decode(pub_b64)
    pub = Ed25519PublicKey.from_public_bytes(pub_raw)
    sig = base64.b64decode(sig_b64)
    try:
        pub.verify(sig, bytes.fromhex(entry_hash_hex))
        return True
    except Exception:
        return False
