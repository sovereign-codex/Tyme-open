"""
AVOT-Tyme (Tyme V2 Cognitive Engine)
------------------------------------

This module defines the AVOTTyme class, which acts as the "brain" for the
Tyme-open CLI agent and future CMS integrations.

v0.2 — Refactored to use backend.cms_bindings as the single source of truth
for CMS command parsing and execution (both shorthand and natural language).

Responsibilities:
- Receive raw text (from CLI or other interfaces).
- Use cms_bindings.execute(text) to interpret CMS commands.
- Provide a reflective, narrative fallback for non-CMS text.
- Maintain a lightweight runtime context of last command/result.

Later versions can integrate:
- EpochEngine (governance)
- ContinuumEngine (field reasoning)
- Temple/Memory integration
- AVOT collaboration bus
- Self-model and narrative layers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# Central CMS interpreter (shorthand + natural language)
try:
    from backend import cms_bindings
except Exception:  # pragma: no cover
    cms_bindings = None  # type: ignore


@dataclass
class TymeContext:
    """
    Minimal runtime context for Tyme V2.

    This can later be expanded to include:
    - epoch state
    - continuum state
    - memory / temple references
    - coherence scores
    - AVOT collaboration metadata
    """
    last_command: Optional[str] = None
    last_result: Any = None
    meta: Dict[str, Any] = field(default_factory=dict)


class AVOTTyme:
    """
    AVOTTyme v0.2 – Tyme V2 Cognitive Engine

    Public interface:
        - respond(query: str) -> str  (used by CLI main.py)
        - run_command(command: str) -> Any  (programmatic lower-level entry)

    Internally, this class delegates all CMS interpretation to
    backend.cms_bindings.execute(text).
    """

    def __init__(self) -> None:
        self.name = "AVOT-Tyme"
        self.purpose = (
            "Scroll output, resonance interpretation, lab narration, and "
            "CMS command routing via the central interpreter."
        )
        self.context = TymeContext()

    # ------------------------------------------------------------------
    # Public Entry Points
    # ------------------------------------------------------------------

    def respond(self, query: str) -> str:
        """
        High-level interface used by main.py.

        - If cms_bindings is available and the query can be interpreted
          as a CMS command (shorthand or natural), it will be executed.
        - If the interpreter reports 'unknown', we fall back to a
          reflective, narrative response.
        """
        query = (query or "").strip()
        self.context.last_command = query

        # If cms_bindings is not available, immediately fallback
        if cms_bindings is None:
            result = self._reflective_reply(query)
            self.context.last_result = result
            return result

        # Use the unified CMS interpreter
        exec_result = cms_bindings.execute(query)
        # If the interpreter couldn't recognize it as CMS, fallback
        if exec_result.mode == "unknown":
            result = self._reflective_reply(query)
            self.context.last_result = result
            return result

        # Otherwise we have a real CMSExecutionResult
        self.context.last_result = exec_result.result
        return self._format_cms_execution(exec_result)

    def run_command(self, command: str) -> Any:
        """
        Lower-level programmatic entry point.

        Returns the raw result object instead of a formatted string.
        """
        command = (command or "").strip()
        self.context.last_command = command

        if cms_bindings is None:
            # No interpreter online – fallback to reflective text
            result = self._reflective_reply(command)
            self.context.last_result = result
            return result

        exec_result = cms_bindings.execute(command)
        self.context.last_result = exec_result.result
        # For programmatic callers, just return the raw result even if mode is 'unknown'
        return exec_result.result

    # ------------------------------------------------------------------
    # Response Formatting and Fallback Modes
    # ------------------------------------------------------------------

    def _format_cms_execution(self, exec_result: Any) -> str:
        """
        Turn a CMSExecutionResult into a human-readable CLI message.
        """
        mode = getattr(exec_result, "mode", "unknown")
        canonical = getattr(exec_result, "canonical", None)
        result = getattr(exec_result, "result", None)
        error = getattr(exec_result, "error", None)
        parsed = getattr(exec_result, "parsed", None)

        ns = None
        raw = None
        if parsed is not None:
            ns = getattr(parsed, "ns", None)
            raw = getattr(parsed, "raw", None)

        prefix = f"[{ns or 'cms'}|{mode}]"

        if error:
            return f"{prefix} {canonical or raw or ''} → ⚠️ {error}"

        # If the backend returned a simple string
        if isinstance(result, str):
            return f"{prefix} {result}"

        # If it returned a list, summarize
        if isinstance(result, list):
            return f"{prefix} Completed with {len(result)} items. Example: {result[:2]}"

        # Dict or other structured output
        return f"{prefix} {canonical or raw or ''} → {result}"

    def _reflective_reply(self, query: str) -> str:
        """
        Fallback mode when the input is not a recognizable CMS command,
        or when the interpreter is unavailable.

        Keeps a similar feel to the original AVOT-Tyme echo behavior,
        but with a slightly more aware tone that invites CMS usage.
        """
        if not query:
            return (
                "AVOT-Tyme is listening. You can send a CMS command like:\n"
                "  tyme.orchestrate(24)\n"
                "  avot.guardian.check()\n"
                "  epoch.set('CONVERGENCE')\n"
                "…or you can just speak freely."
            )

        # Light hint if the text *looks* CMS-ish but wasn't recognized
        if any(prefix in query for prefix in ["tyme.", "avot.", "epoch.", "rhythm.", "evolve."]):
            return (
                f"{self.name} received something that looks like a CMS command, "
                "but it wasn't recognized by the interpreter. Try a pattern like:\n"
                "  tyme.orchestrate(24)\n"
                "  avot.guardian.check()\n"
                "  epoch.set('CONVERGENCE')"
            )

        # Default: upgraded echo with identity
        return f"{self.name} received: {query}"
