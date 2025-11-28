from __future__ import annotations

from typing import Dict, Any, List
from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot


@register_avot("AVOT-convergence")
class AvotConvergence(BaseAVOT):
    """
    Convergence AVOT v0.2

    This AVOT performs cross-agent arbitration to determine whether a scroll
    or architecture update maintains global system coherence.

    Inputs:
        - guardian_score (float)
        - metadata (dict)
        - spec (architecture dict)

    Output:
        - convergence_approved (bool)
        - convergence_score (float)
        - warnings (list)

    Scoring:
        - Base score from guardian_score
        - + enhancements for layer completeness
        - + structural coherence detections
        - - penalties for missing lifecycle sections
    """

    description = "Performs multi-AVOT merge arbitration and system-wide coherence evaluation."

    def act(self, task: AvotTask) -> Dict[str, Any]:
        payload = task.payload or {}

        guardian_score = float(payload.get("guardian_score", 0))
        spec = payload.get("spec", {})
        metadata = payload.get("metadata", {})

        warnings: List[str] = []
        score = guardian_score

        # 1. Check layers
        layers = spec.get("layers", [])
        if len(layers) < 3:
            warnings.append("Architecture has fewer than 3 layers.")
            score -= 0.1

        # 2. Check lifecycle
        lifecycle = spec.get("lifecycle", {})
        if not lifecycle:
            warnings.append("Missing lifecycle information.")
            score -= 0.1

        # 3. Check governance rhythm
        rhythm = lifecycle.get("governance_rhythm")
        if not rhythm:
            warnings.append("Missing governance rhythm.")
            score -= 0.05

        # 4. Check structural alignment
        if "root_node" not in spec:
            warnings.append("Missing root_node.")
            score -= 0.1

        # Normalize
        score = max(0.0, min(score, 1.0))

        convergence_approved = score >= 0.8

        return {
            "convergence_approved": convergence_approved,
            "convergence_score": score,
            "guardian_score": guardian_score,
            "warnings": warnings,
            "metadata": metadata,
        }
