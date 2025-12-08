"""
OpenAI Codex Client for Tyme-Open
---------------------------------

This module provides a disciplined, auditable interface for invoking
OpenAI generation models to produce code modifications, patches, and
structured artifacts for Tyme’s autonomous self-development system.

It enforces:

• Deterministic, strict file-block formatting:
    === FILE: <path> ===
    <content>
    === END FILE ===

• Model selection from environment variables:
    OPENAI_MODEL, OPENAI_API_KEY

• Prompt hashing for provenance and linkage within EpochEngine

• Future extensibility:
    - guardian-aware safety gating
    - multi-model fallbacks
    - curated prompt library for patch intents
"""

import os
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("tyme.openai_client")

# ------------------------------------------------------------
#  Model availability test
# ------------------------------------------------------------

try:
    import openai
except Exception:
    openai = None


# ------------------------------------------------------------
#  Helpers
# ------------------------------------------------------------

def ensure_openai_available() -> None:
    """Ensure usable OpenAI client + required env vars exist."""
    if openai is None:
        raise RuntimeError(
            "OpenAI python package is not installed. "
            "Install with: pip install openai"
        )
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY environment variable."
        )


def default_model() -> str:
    """
    Returns the default code-generation model.

    Override via:
        export OPENAI_MODEL="gpt-4o-mini-code"
    """
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini-code")


def hash_prompt(prompt: str) -> str:
    """
    SHA-256 hash for provenance tracking (EpochEngine links).
    """
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


# ------------------------------------------------------------
#  Strict patch prompt template
# ------------------------------------------------------------

FILE_BLOCK_INSTRUCTIONS = """
IMPORTANT OUTPUT FORMAT — NO EXCEPTIONS:

For EACH file changed, added, or removed, output:

=== FILE: <relative/path/to/file> ===
<full and final file content, no backticks, no commentary>
=== END FILE ===

Rules:
1. Include ALL modified files in full.
2. Do NOT output diffs. Output FULL file contents.
3. Do NOT include extraneous text, explanations, markdown, or prose.
4. Do NOT include backticks ``` or YAML fences.
5. If deleting a file, output the block with empty content.

Example:
=== FILE: src/example.py ===
print("hello")
=== END FILE ===
"""


# ------------------------------------------------------------
#  Compose Codex patch prompt
# ------------------------------------------------------------

def build_patch_prompt(request: str) -> str:
    """
    Wrap user intent with strict instructions for safe,
    deterministic code generation.
    """
    return f"""
You are Tyme’s autonomous patch-generation engine.

Your task: Implement the following change request with the highest
possible precision, minimal side effects, and full-file output.

Request:
\"\"\"{request}\"\"\"

{FILE_BLOCK_INSTRUCTIONS}

Return ONLY the file blocks — nothing before, nothing after.
""".strip()


# ------------------------------------------------------------
#  Invoke OpenAI model to generate patch blocks
# ------------------------------------------------------------

def generate_patch_blocks(
    request: str,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_output_tokens: int = 6000,
) -> Tuple[str, str]:
    """
    Produce patch blocks via LLM, returning:

        (raw_text_output, prompt_hash)

    The caller (CodexPatchHandler) will parse file blocks.

    Raises:
        RuntimeError on missing keys or import errors.
    """
    ensure_openai_available()

    model = model or default_model()
    composed_prompt = build_patch_prompt(request)
    prompt_h = hash_prompt(request)

    logger.info(f"[CodexPatch] Calling OpenAI model={model}, hash={prompt_h}")

    try:
        # Use ChatCompletion if available (preferred modern A

