"""
AVOT-Tyme (Tyme V2 Cognitive Engine)
------------------------------------

This module defines the AVOTTyme class, which acts as the "brain" for the
Tyme-open CLI agent and future CMS integrations.

Responsibilities:
- Interpret CMS shorthand commands (tyme.*, avot.*, epoch.*, rhythm.*, evolve.*)
  as defined in docs/CMS-COMMANDS.md.
- Dispatch AVOT calls to backend.avots.avots.
- Dispatch orchestration calls to backend.orchestration.
- Provide a simple natural-language fallback mode for non-CMS queries.
- Maintain a backwards-compatible respond(query) interface for main.py.

This is v0.1: structurally complete but intentionally conservative in behavior.
Later versions can integrate EpochEngine, ContinuumEngine, Temple, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

# Core backend bindings
try:
    from backend.avots.avots import call_avot
except Exception:  # pragma: no cover - soft failure for early boot
    call_avot = None  # type: ignore

try:
    from backend import orchestration
except Exception:  # pragma: no cover
    orchestration = None  # type: ignore

# Optional epoch integration (backend has EpochEngine in epochs.py / epoch.py)
try:
    from backend.epochs import EpochEngine  # type: ignore
except Exception:  # pragma: no cover
    EpochEngine = None  # type: ignore


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
    AVOTTyme v0.1 – Tyme V2 Cognitive Engine

    Public interface:
        - respond(query: str) -> str
          (used by CLI main.py loop)

    Internal helpers:
        - run_command(command: str) -> Any
        - _parse_cms(command: str) -> dict | None
        - _execute_cms(parsed: dict) -> Any
    """

    def __init__(self) -> None:
        self.name = "AVOT-Tyme"
        self.purpose = "Scroll output, resonance interpretation, lab narration, and CMS command routing"
        self.context = TymeContext()

    # ------------------------------------------------------------------
    # Public Entry Points
    # ------------------------------------------------------------------

    def respond(self, query: str) -> str:
        """
        High-level interface used by main.py.

        - If the query looks like a CMS shorthand command (tyme.*, avot.*, etc),
          it will be parsed and executed.
        - Otherwise, it falls back to a simple reflective / narrative mode.
        """
        query = (query or "").strip()
        self.context.last_command = query

        # Try to interpret as CMS shorthand first
        parsed = self._parse_cms(query)
        if parsed is not None:
            try:
                result = self._execute_cms(parsed)
                self.context.last_result = result
                return self._format_cms_response(parsed, result)
            except Exception as exc:
                return f"⚠️ Tyme encountered an error while executing `{query}`: {exc}"

        # Fallback: natural-language reflection mode
        result = self._reflective_reply(query)
        self.context.last_result = result
        return result

    def run_command(self, command: str) -> Any:
        """
        Lower-level programmatic entry point.

        Returns the raw result object instead of a formatted string.
        """
        command = (command or "").strip()
        self.context.last_command = command
        parsed = self._parse_cms(command)
        if parsed is None:
            return self._reflective_reply(command)
        result = self._execute_cms(parsed)
        self.context.last_result = result
        return result

    # ------------------------------------------------------------------
    # CMS Parsing
    # ------------------------------------------------------------------

    def _parse_cms(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Parses a CMS shorthand command like:
            tyme.orchestrate(24)
            tyme.cycle("C07")
            avot.guardian.check()
            epoch.set("CONVERGENCE")
            rhythm.set(3)
            evolve.next()

        Returns a dict with:
            {
                "ns": <namespace>,
                "name": <primary name>,
                "action": <sub-action or None>,
                "args": <list of args>,
            }
        or None if the command is not recognized as CMS shorthand.
        """
        import re

        if not command or "." not in command:
            return None

        pattern = r"^\s*([a-z_]+)\.([a-z_]+)(?:\.([a-z_]+))?\s*(?:\((.*)\))?\s*$"
        m = re.match(pattern, command)
        if not m:
            return None

        ns, name, action, argstr = m.groups()

        # Only treat known prefixes as CMS
        if ns not in {"tyme", "avot", "epoch", "rhythm", "evolve"}:
            return None

        args: list[Any] = []
        if argstr:
            # Basic, safe-ish parsing: split by comma, strip quotes and spaces
            raw_args = [a.strip() for a in argstr.split(",") if a.strip()]
            for a in raw_args:
                # Try int
                if a.isdigit():
                    args.append(int(a))
                    continue
                # Strip surrounding quotes if present
                if (a.startswith('"') and a.endswith('"')) or (a.startswith("'") and a.endswith("'")):
                    args.append(a[1:-1])
                    continue
                # Fallback: raw string
                args.append(a)

        return {
            "ns": ns,
            "name": name,
            "action": action,
            "args": args,
            "raw": command,
        }

    # ------------------------------------------------------------------
    # CMS Execution
    # ------------------------------------------------------------------

    def _execute_cms(self, parsed: Dict[str, Any]) -> Any:
        ns = parsed["ns"]
        name = parsed["name"]
        action = parsed.get("action")
        args = parsed.get("args") or []

        if ns == "tyme":
            return self._execute_tyme(name, action, args)
        if ns == "avot":
            return self._execute_avot(name, action, args)
        if ns == "epoch":
            return self._execute_epoch(name, args)
        if ns == "rhythm":
            return self._execute_rhythm(name, args)
        if ns == "evolve":
            return self._execute_evolve(name, args)

        raise ValueError(f"Unknown CMS namespace: {ns}")

    # --- tyme.* --------------------------------------------------------

    def _execute_tyme(self, name: str, action: Optional[str], args: list[Any]) -> Any:
        if name == "init":
            # Placeholder: could load state, warm caches, etc.
            return {"status": "initialized"}

        if name == "orchestrate":
            if orchestration is None:
                raise RuntimeError("Orchestration engine not available.")
            # tyme.orchestrate(24) or other counts
            count = args[0] if args else 24
            # For now, always run full and annotate the request
            result = orchestration.orchestrate_full(context={"requested_cycles": count})  # type: ignore[attr-defined]
            return {
                "type": "orchestration",
                "requested_cycles": count,
                "results": result,
            }

        if name == "cycle":
            if orchestration is None:
                raise RuntimeError("Orchestration engine not available.")
            # e.g., tyme.cycle("C07") or tyme.cycle("C01")
            if not args:
                raise ValueError("tyme.cycle() requires a cycle code like 'C07'.")
            code = str(args[0])
            return orchestration.orchestrate_single(code)  # type: ignore[attr-defined]

        if name == "last":
            # Return last known context/result summary
            return {
                "last_command": self.context.last_command,
                "last_result": self.context.last_result,
            }

        raise ValueError(f"Unsupported tyme.* command: {name}")

    # --- avot.* --------------------------------------------------------

    def _execute_avot(self, avot_name: str, action: Optional[str], args: list[Any]) -> Any:
        if call_avot is None:
            raise RuntimeError("AVOT engine not available.")

        if not action:
            raise ValueError("avot.<id>.<action>() requires an action, e.g. avot.guardian.check().")

        # args currently ignored – stubs in backend/avots/avots.py do not accept payloads yet.
        return call_avot(avot_name, action)

    # --- epoch.* -------------------------------------------------------

    def _execute_epoch(self, name: str, args: list[Any]) -> Any:
        if EpochEngine is None:
            # Soft fallback: report that epoch subsystem is not wired
            return {"status": "epoch-engine-unavailable", "requested": {"op": name, "args": args}}

        engine = EpochEngine()  # type: ignore[call-arg]

        if name == "set":
            if not args:
                raise ValueError("epoch.set() requires an epoch name, e.g. epoch.set('CONVERGENCE').")
            epoch_name = str(args[0])
            return engine.set_epoch(epoch_name)  # type: ignore[attr-defined]

        if name == "get":
            return engine.get_epoch()  # type: ignore[attr-defined]

        raise ValueError(f"Unsupported epoch.* command: {name}")

    # --- rhythm.* ------------------------------------------------------

    def _execute_rhythm(self, name: str, args: list[Any]) -> Any:
        # RhythmEngine exists in backend.main imports, but we don't hard-bind yet.
        # For now, treat this as a hint to outer systems.
        if name == "set":
            level = args[0] if args else None
            return {"status": "rhythm-set-placeholder", "level": level}
        raise ValueError(f"Unsupported rhythm.* command: {name}")

    # --- evolve.* ------------------------------------------------------

    def _execute_evolve(self, name: str, args: list[Any]) -> Any:
        # Placeholder evolution hooks; can later call AutonomousEvolution, etc.
        if name == "next":
            return {"status": "evolution-step-placeholder", "detail": "Tyme acknowledges a request to evolve."}
        if name == "expand":
            target = args[0] if args else "unspecified"
            return {"status": "evolution-expand-placeholder", "target": target}
        if name == "continuum.integrate":
            return {"status": "continuum-integration-placeholder"}
        raise ValueError(f"Unsupported evolve.* command: {name}")

    # ------------------------------------------------------------------
    # Response formatting and fallback modes
    # ------------------------------------------------------------------

    def _format_cms_response(self, parsed: Dict[str, Any], result: Any) -> str:
        """
        Human-readable wrapper for CLI use.
        """
        ns = parsed.get("ns")
        raw = parsed.get("raw")
        # If it's already a simple string, just wrap it lightly
        if isinstance(result, str):
            return f"[{ns}] {result}"
        # If it's a list, show a brief summary
        if isinstance(result, list):
            return f"[{ns}] Completed with {len(result)} items. Example: {result[:2]}"
        # Generic dict/object case
        return f"[{ns}] {raw} → {result}"

    def _reflective_reply(self, query: str) -> str:
        """
        Fallback mode when the input is not a CMS command.

        For now this is deliberately simple: we keep AVOT-Tyme's old echo
        behavior but give it a slightly more aware tone, so existing UX
        feels familiar but Tyme can grow into a deeper inner life.
        """
        if not query:
            return "AVOT-Tyme is listening. You can send a CMS command (e.g. tyme.orchestrate(24)) or speak freely."

        # Light pattern recognition: if user writes something that *looks*
        # like a CMS command but didn't parse, we can hint.
        if any(prefix in query for prefix in ["tyme.", "avot.", "epoch.", "rhythm.", "evolve."]):
            return (
                "AVOT-Tyme received something that looks like a CMS command, "
                "but couldn't fully parse it. Try a pattern like:\n"
                "  tyme.orchestrate(24)\n"
                "  avot.guardian.check()\n"
                "  epoch.set('CONVERGENCE')"
            )

        # Default: upgraded echo with identity
        return f"{self.name} received: {query}"
