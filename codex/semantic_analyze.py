#!/usr/bin/env python3
"""Best-effort semantic warning analyzer for Codex directives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


AMBIGUOUS_VERBS = {
    "consider",
    "should",
    "might",
    "may",
    "could",
    "attempt",
    "try",
    "aim",
    "seek",
    "prefer",
    "ideally",
    "sometimes",
}

DEPRECATED_VERBS = {
    "blacklist",
    "whitelist",
    "disable",
    "block",
    "forbid",
}

CONTRADICTION_PAIRS = [
    ("allow", "disallow"),
    ("permit", "deny"),
    ("must", "must not"),
    ("require", "prohibit"),
    ("enable", "disable"),
]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _extract_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _extract_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _extract_strings(item)


def _collect_directive_text(payload: dict[str, Any]) -> str:
    candidates = []
    for key in ("directive", "directives", "text", "content"):
        if key in payload:
            candidates.extend(_extract_strings(payload[key]))
    if not candidates:
        candidates.extend(_extract_strings(payload))
    return "\n".join(text for text in candidates if text.strip())


def _tokenize(text: str) -> list[str]:
    return [token.strip(".,;:!?()[]{}\"'`)." ).lower() for token in text.split()]


def _find_ambiguous_verbs(text: str) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    tokens = _tokenize(text)
    for verb in sorted(AMBIGUOUS_VERBS):
        if verb in tokens:
            warnings.append(
                {
                    "type": "ambiguity",
                    "message": f"Ambiguous verb detected: '{verb}'.",
                    "evidence": verb,
                }
            )
    return warnings


def _find_deprecated_verbs(text: str) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    tokens = _tokenize(text)
    for verb in sorted(DEPRECATED_VERBS):
        if verb in tokens:
            warnings.append(
                {
                    "type": "deprecation",
                    "message": f"Deprecated verb detected: '{verb}'.",
                    "evidence": verb,
                }
            )
    return warnings


def _find_contradictions(current_text: str, previous_text: str) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    current_tokens = " ".join(_tokenize(current_text))
    previous_tokens = " ".join(_tokenize(previous_text))

    for allow_word, deny_word in CONTRADICTION_PAIRS:
        if allow_word in current_tokens and deny_word in previous_tokens:
            warnings.append(
                {
                    "type": "contradiction",
                    "message": (
                        f"Potential contradiction: current uses '{allow_word}' while previous uses '{deny_word}'."
                    ),
                    "evidence": f"current:{allow_word} previous:{deny_word}",
                }
            )
        if deny_word in current_tokens and allow_word in previous_tokens:
            warnings.append(
                {
                    "type": "contradiction",
                    "message": (
                        f"Potential contradiction: current uses '{deny_word}' while previous uses '{allow_word}'."
                    ),
                    "evidence": f"current:{deny_word} previous:{allow_word}",
                }
            )
    return warnings


def _load_previous_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    path_value = payload.get("previous_directive_path") or payload.get("previous_metadata_path")
    if isinstance(path_value, str):
        return _read_json(Path(path_value))
    default_path = Path("codex_previous_directive_metadata.json")
    if default_path.exists():
        return _read_json(default_path)
    return {}


def main() -> None:
    payload_path = Path("codex_directive_payload.json")
    payload = _read_json(payload_path)

    current_text = _collect_directive_text(payload)
    previous_payload = _load_previous_metadata(payload)
    previous_text = _collect_directive_text(previous_payload)

    warnings: list[dict[str, str]] = []
    if current_text:
        warnings.extend(_find_ambiguous_verbs(current_text))
        warnings.extend(_find_deprecated_verbs(current_text))
    if current_text and previous_text:
        warnings.extend(_find_contradictions(current_text, previous_text))

    output = {
        "warnings": warnings,
        "warning_count": len(warnings),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
