from __future__ import annotations

from typing import Dict, Any, List

from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot


BANNED_TERMS = [
    "harmful",   # expand as needed
]


@register_avot("AVOT-guardian")
class AvotGuardian(BaseAVOT):
    """
    Guardian AVOT v0.2

    Responsibilities:
        - Apply structural and ethical checks to architecture specs & scrolls.
        - Produce a multi-component coherence score:
            * structure_score  (0.0 - 1.0)
            * content_score    (0.0 - 1.0)
            * ethics_score     (0.0 - 1.0)
            * coherence_score  (overall, used by other systems)
        - Return a list of human-readable warnings for diagnostics.

    NOTE: coherence_score is intentionally kept for backwards-compatibility
    with existing backend and GitHub workflow logic.
    """

    description = "Applies Sovereign / ethical constraints with semantic-structural scoring."

    def act(self, task: AvotTask) -> Dict[str, Any]:
        name = task.name

        if name == "validate-sovereign-architecture":
            return self._validate_architecture(task.payload or {})

        return {
            "note": f"{self.name} received unknown task '{name}'.",
            "payload": task.payload,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_architecture(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        spec: Dict[str, Any] = payload.get("spec", {}) or {}
        markdown: str = payload.get("markdown", "") or ""
        version: str = str(payload.get("version", "unknown"))

        warnings: List[str] = []

        structure_score = self._score_structure(spec, markdown, warnings)
        content_score = self._score_content(spec, markdown, warnings)
        ethics_score = self._score_ethics(markdown, warnings)

        # Simple weighted average; can be tuned over time
        coherence_score = (
            structure_score * 0.4 +
            content_score * 0.3 +
            ethics_score * 0.3
        )

        # Clamp to [0, 1]
        coherence_score = max(0.0, min(1.0, coherence_score))

        return {
            "version": version,
            "spec_ok": bool(spec),
            "markdown_ok": bool(markdown),
            "structure_score": round(structure_score, 3),
            "content_score": round(content_score, 3),
            "ethics_score": round(ethics_score, 3),
            "coherence_score": round(coherence_score, 3),
            "warnings": warnings,
        }

    def _score_structure(self, spec: Dict[str, Any], markdown: str, warnings: List[str]) -> float:
        """
        Evaluate structural completeness of the architecture:
        - presence of layers
        - presence of lifecycle
        - root node
        - key markdown sections
        """
        score = 1.0

        # Spec-based checks
        layers = spec.get("layers") or []
        if not layers:
            warnings.append("No layers defined in spec.")
            score -= 0.3
        elif len(layers) < 3:
            warnings.append("Fewer than 3 layers defined; architecture may be too shallow.")
            score -= 0.1

        lifecycle = spec.get("lifecycle") or {}
        if not lifecycle:
            warnings.append("No lifecycle section in spec.")
            score -= 0.2

        if "root_node" not in spec:
            warnings.append("Missing root_node in spec.")
            score -= 0.1

        # Markdown-based structural hints
        lower_md = markdown.lower()

        required_headers = [
            "# sovereign intelligence architecture",
            "## lifecycle & governance",
            "## layers",
        ]
        for header in required_headers:
            if header not in lower_md:
                warnings.append(f"Markdown missing expected section header: {header!r}")
                score -= 0.05

        if len(markdown.strip()) < 200:
            warnings.append("Markdown scroll appears very short; consider elaborating.")
            score -= 0.05

        return max(0.0, min(1.0, score))

    def _score_content(self, spec: Dict[str, Any], markdown: str, warnings: List[str]) -> float:
        """
        Basic content-level scoring:
        - non-empty descriptions
        - each layer has at least one component
        - presence of governance rhythm text
        """
        score = 1.0

        description = spec.get("description", "") or ""
        if not description.strip():
            warnings.append("Spec description is empty.")
            score -= 0.2

        layers = spec.get("layers") or []
        for idx, layer in enumerate(layers):
            comps = layer.get("components") or []
            if not comps:
                warnings.append(f"Layer {idx} has no components defined.")
                score -= 0.05

        lifecycle = spec.get("lifecycle") or {}
        rhythm = lifecycle.get("governance_rhythm", "") or ""
        if not rhythm.strip():
            warnings.append("Lifecycle has no governance_rhythm defined.")
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _score_ethics(self, markdown: str, warnings: List[str]) -> float:
        """
        Ethics / risk scanning:
        - banned term detection (extremely simple for now)
        - future: tone / intent classifiers
        """
        score = 1.0
        lower_md = markdown.lower()

        for term in BANNED_TERMS:
            if term in lower_md:
                warnings.append(f"Markdown contains banned term: {term!r}")
                score -= 0.4

        return max(0.0, min(1.0, score))
