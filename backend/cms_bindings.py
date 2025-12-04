"""
cms_bindings.py
----------------

Central CMS interpreter for Tyme-open (Option C: full natural-language + shorthand).

This module is the single source of truth for:
- Understanding CMS shorthand commands like:
    tyme.orchestrate(24)
    tyme.cycle("C07")
    avot.guardian.check()
    epoch.set("CONVERGENCE")

- Interpreting simple natural-language commands into canonical shorthand:
    "run the full orchestration"        -> tyme.orchestrate(24)
    "run cycle seven"                   -> tyme.cycle("C07")
    "check coherence"                   -> avot.guardian.check()
    "switch to convergence epoch"       -> epoch.set("CONVERGENCE")

It is designed so that:
- CLI, web, and future HTTP APIs can all use the same interpreter.
- AVOTTyme (src/agents/avot_tyme.py) can later import this module instead of
  maintaining its own internal parser.

This is v0.1: focused on robustness and clarity, not cleverness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import re

# -------------------------------------------------------------------
# Backend bindings (soft imports so early boot doesn't crash)
# -------------------------------------------------------------------

try:
    from backend.avots.avots import call_avot
except Exception:  # pragma: no cover
    call_avot = None  # type: ignore

try:
    from backend import orchestration
except Exception:  # pragma: no cover
    orchestration = None  # type: ignore

try:
    from backend.epochs import EpochEngine  # type: ignore
except Exception:  # pragma: no cover
    EpochEngine = None  # type: ignore


# -------------------------------------------------------------------
# Data structures
# -------------------------------------------------------------------

@dataclass
class CMSParseResult:
    """
    Parsed representation of a CMS command, either originating as shorthand
    or as a canonicalized form of a natural-language instruction.
    """
    ns: str                      # namespace: tyme, avot, epoch, rhythm, evolve
    name: str                    # primary name, e.g. orchestrate, guardian, set
    action: Optional[str]        # optional sub-action, e.g. check
    args: List[Any]              # positional arguments
    raw: str                     # original command string
    origin: str = "shorthand"    # 'shorthand' or 'natural'


@dataclass
class CMSExecutionResult:
    """
    Wrapper for interpreter outputs to keep things introspectable.
    """
    mode: str                    # 'shorthand', 'natural', or 'unknown'
    canonical: Optional[str]     # canonical shorthand form, if any
    parsed: Optional[CMSParseResult]
    result: Any                  # raw result from backend
    error: Optional[str] = None
    notes: Dict[str, Any] = field(default_factory=dict)


# -------------------------------------------------------------------
# Public entry points
# -------------------------------------------------------------------

def execute(text: str) -> CMSExecutionResult:
    """
    Execute a string that might be:
    - a CMS shorthand command (tyme.*, avot.*, epoch.*, rhythm.*, evolve.*)
    - a natural-language command with recognizable intent
    - a completely unknown string

    This is the main entry point for:
    - CLI
    - AVOTTyme
    - Web/API layers

    Returns a CMSExecutionResult object.
    """
    text = (text or "").strip()

    # Try strict shorthand first
    parsed = parse_shorthand(text)
    if parsed:
        try:
            result = execute_parsed(parsed)
            canonical = build_canonical(parsed)
            return CMSExecutionResult(
                mode="shorthand",
                canonical=canonical,
                parsed=parsed,
                result=result,
            )
        except Exception as exc:
            return CMSExecutionResult(
                mode="shorthand",
                canonical=build_canonical(parsed),
                parsed=parsed,
                result=None,
                error=str(exc),
            )

    # Try to interpret natural language
    nl_parsed = interpret_natural_language(text)
    if nl_parsed:
        try:
            result = execute_parsed(nl_parsed)
            canonical = build_canonical(nl_parsed)
            return CMSExecutionResult(
                mode="natural",
                canonical=canonical,
                parsed=nl_parsed,
                result=result,
            )
        except Exception as exc:
            return CMSExecutionResult(
                mode="natural",
                canonical=build_canonical(nl_parsed),
                parsed=nl_parsed,
                result=None,
                error=str(exc),
            )

    # Unknown: not recognized as a CMS command
    return CMSExecutionResult(
        mode="unknown",
        canonical=None,
        parsed=None,
        result=None,
        error=None,
        notes={"message": "Not recognized as a CMS command."},
    )


# -------------------------------------------------------------------
# Shorthand parser (tyme.*, avot.*, epoch.*, rhythm.*, evolve.*)
# -------------------------------------------------------------------

def parse_shorthand(command: str) -> Optional[CMSParseResult]:
    """
    Parses a CMS shorthand command like:

        tyme.orchestrate(24)
        tyme.cycle("C07")
        avot.guardian.check()
        epoch.set("CONVERGENCE")
        rhythm.set(3)
        evolve.next()

    Returns a CMSParseResult or None.
    """
    if not command or "." not in command:
        return None

    pattern = r"^\s*([a-z_]+)\.([a-z_]+)(?:\.([a-z_]+))?\s*(?:\((.*)\))?\s*$"
    m = re.match(pattern, command)
    if not m:
        return None

    ns, name, action, argstr = m.groups()

    if ns not in {"tyme", "avot", "epoch", "rhythm", "evolve"}:
        return None

    args: List[Any] = []
    if argstr:
        raw_args = [a.strip() for a in argstr.split(",") if a.strip()]
        for a in raw_args:
            # Try integer
            if a.isdigit():
                args.append(int(a))
                continue
            # Strip quotes if present
            if (a.startswith('"') and a.endswith('"')) or (a.startswith("'") and a.endswith("'")):
                args.append(a[1:-1])
                continue
            # Fallback: raw string
            args.append(a)

    return CMSParseResult(
        ns=ns,
        name=name,
        action=action,
        args=args,
        raw=command,
        origin="shorthand",
    )


# -------------------------------------------------------------------
# Natural-language interpretation (Option C)
# -------------------------------------------------------------------

def interpret_natural_language(text: str) -> Optional[CMSParseResult]:
    """
    Attempts to interpret a natural-language instruction as a CMS command.

    This is intentionally simple but expandable. It uses keyword and pattern
    matching to map phrases into canonical shorthand commands.

    Examples:

        "run the full orchestration"
        "run all 24 cycles"
        "do a full tyme cycle"
            -> tyme.orchestrate(24)

        "run cycle seven"
        "run c7"
            -> tyme.cycle("C07")

        "check coherence"
        "guardian check"
            -> avot.guardian.check()

        "switch to convergence epoch"
        "enter convergence mode"
            -> epoch.set("CONVERGENCE")
    """
    if not text:
        return None

    lower = text.lower()

    # ---- Tyme orchestration ----
    if any(phrase in lower for phrase in [
        "run the full orchestration",
        "run full orchestration",
        "run all 24 cycles",
        "run all twenty four cycles",
        "do a full tyme cycle",
        "run the full tyme cycle",
    ]):
        return CMSParseResult(
            ns="tyme",
            name="orchestrate",
            action=None,
            args=[24],
            raw=text,
            origin="natural",
        )

    # Generic "run orchestration" → default to full 24
    if "run orchestration" in lower or "orchestrate" in lower:
        return CMSParseResult(
            ns="tyme",
            name="orchestrate",
            action=None,
            args=[24],
            raw=text,
            origin="natural",
        )

    # ---- Specific cycle requests (e.g. run cycle seven) ----
    m = re.search(r"cycle\s+(\d+)", lower)
    if m:
        num_str = m.group(1)
        try:
            n = int(num_str)
            if 1 <= n <= 24:
                code = f"C{n:02d}"
                return CMSParseResult(
                    ns="tyme",
                    name="cycle",
                    action=None,
                    args=[code],
                    raw=text,
                    origin="natural",
                )
        except ValueError:
            pass

    # ---- Guardian / coherence checks ----
    if any(phrase in lower for phrase in [
        "check coherence",
        "coherence check",
        "guardian check",
        "run guardian",
        "guardian review",
    ]):
        return CMSParseResult(
            ns="avot",
            name="guardian",
            action="check",
            args=[],
            raw=text,
            origin="natural",
        )

    # ---- Harmonia / resonance mapping ----
    if any(phrase in lower for phrase in [
        "resonance map",
        "resonance mapping",
        "harmonia map",
        "map resonance",
        "coherence map",
    ]):
        return CMSParseResult(
            ns="avot",
            name="harmonia",
            action="map",
            args=[],
            raw=text,
            origin="natural",
        )

    # ---- Epoch changes ----
    if any(phrase in lower for phrase in [
        "switch to convergence",
        "enter convergence epoch",
        "go into convergence epoch",
        "convergence mode",
    ]):
        return CMSParseResult(
            ns="epoch",
            name="set",
            action=None,
            args=["CONVERGENCE"],
            raw=text,
            origin="natural",
        )

    if any(phrase in lower for phrase in [
        "switch to harmonic",
        "enter harmonic epoch",
        "go into harmonic epoch",
        "harmonic mode",
    ]):
        return CMSParseResult(
            ns="epoch",
            name="set",
            action=None,
            args=["HARMONIC"],
            raw=text,
            origin="natural",
        )

    # ---- Evolution hints ----
    if any(phrase in lower for phrase in [
        "evolve",
        "take the next evolution step",
        "next evolution",
        "advance yourself",
    ]):
        return CMSParseResult(
            ns="evolve",
            name="next",
            action=None,
            args=[],
            raw=text,
            origin="natural",
        )

    # If no mapping found:
    return None


# -------------------------------------------------------------------
# CMS execution
# -------------------------------------------------------------------

def execute_parsed(parsed: CMSParseResult) -> Any:
    """
    Execute a parsed CMS command by dispatching to the appropriate backend
    function or AVOT.
    """
    if parsed.ns == "tyme":
        return _execute_tyme(parsed)
    if parsed.ns == "avot":
        return _execute_avot(parsed)
    if parsed.ns == "epoch":
        return _execute_epoch(parsed)
    if parsed.ns == "rhythm":
        return _execute_rhythm(parsed)
    if parsed.ns == "evolve":
        return _execute_evolve(parsed)
    raise ValueError(f"Unknown CMS namespace: {parsed.ns}")


def _execute_tyme(parsed: CMSParseResult) -> Any:
    if parsed.name == "init":
        return {"status": "initialized"}

    if parsed.name == "orchestrate":
        if orchestration is None:
            raise RuntimeError("Orchestration engine not available.")
        count = parsed.args[0] if parsed.args else 24
        result = orchestration.orchestrate_full(context={"requested_cycles": count})  # type: ignore[attr-defined]
        return {
            "type": "orchestration",
            "requested_cycles": count,
            "results": result,
        }

    if parsed.name == "cycle":
        if orchestration is None:
            raise RuntimeError("Orchestration engine not available.")
        if not parsed.args:
            raise ValueError("tyme.cycle() requires a cycle code like 'C07'.")
        code = str(parsed.args[0])
        return orchestration.orchestrate_single(code)  # type: ignore[attr-defined]

    if parsed.name == "last":
        # This interpreter itself doesn't track history; that is a job for the
        # Tyme Brain / context layer. For now, just acknowledge.
        return {"status": "no-local-history", "note": "last() should be handled by Tyme Brain context."}

    raise ValueError(f"Unsupported tyme.* command: {parsed.name}")


def _execute_avot(parsed: CMSParseResult) -> Any:
    if call_avot is None:
        raise RuntimeError("AVOT engine not available.")
    if not parsed.action:
        raise ValueError("avot.<id>.<action>() requires an action, e.g. avot.guardian.check().")
    return call_avot(parsed.name, parsed.action)


def _execute_epoch(parsed: CMSParseResult) -> Any:
    if EpochEngine is None:
        return {
            "status": "epoch-engine-unavailable",
            "requested": {"op": parsed.name, "args": parsed.args},
        }

    engine = EpochEngine()  # type: ignore[call-arg]

    if parsed.name == "set":
        if not parsed.args:
            raise ValueError("epoch.set() requires an epoch name, e.g. epoch.set('CONVERGENCE').")
        epoch_name = str(parsed.args[0])
        return engine.set_epoch(epoch_name)  # type: ignore[attr-defined]

    if parsed.name == "get":
        return engine.get_epoch()  # type: ignore[attr-defined]

    raise ValueError(f"Unsupported epoch.* command: {parsed.name}")


def _execute_rhythm(parsed: CMSParseResult) -> Any:
    # Rhythm is acknowledged but not fully implemented yet.
    if parsed.name == "set":
        level = parsed.args[0] if parsed.args else None
        return {"status": "rhythm-set-placeholder", "level": level}
    raise ValueError(f"Unsupported rhythm.* command: {parsed.name}")


def _execute_evolve(parsed: CMSParseResult) -> Any:
    if parsed.name == "next":
        return {
            "status": "evolution-step-placeholder",
            "detail": "Tyme acknowledges a request to evolve."
        }
    if parsed.name == "expand":
        target = parsed.args[0] if parsed.args else "unspecified"
        return {"status": "evolution-expand-placeholder", "target": target}
    if parsed.name in {"continuum.integrate", "continuum_integrate"}:
        return {"status": "continuum-integration-placeholder"}
    raise ValueError(f"Unsupported evolve.* command: {parsed.name}")


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def build_canonical(parsed: CMSParseResult) -> str:
    """
    Convert a parsed command back into canonical shorthand string.
    """
    args_repr = ""
    if parsed.args:
        formatted_args = []
        for a in parsed.args:
            if isinstance(a, str):
                formatted_args.append(repr(a))
            else:
                formatted_args.append(str(a))
        args_repr = "(" + ", ".join(formatted_args) + ")"
    else:
        args_repr = "()"

    if parsed.action:
        return f"{parsed.ns}.{parsed.name}.{parsed.action}{args_repr}"
    return f"{parsed.ns}.{parsed.name}{args_repr}"
