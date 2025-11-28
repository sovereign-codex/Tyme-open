from __future__ import annotations
from typing import Dict, Any, List
from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot


@register_avot("AVOT-selector")
class AvotSelector(BaseAVOT):
    """
    AVOT-selector v0.1

    Chooses the best predicted spec based on:
    - guardian_score (simulated via AVOT-guardian)
    - convergence_score (simulated via AVOT-convergence)
    """

    def act(self, task: AvotTask) -> Dict[str, Any]:
        engine = self.engine

        candidates = task.payload.get("candidates", [])
        if not candidates:
            return {"selected_spec": {}, "reason": "No candidates provided."}

        best = None
        best_score = -1

        for entry in candidates:
            spec = entry.get("predicted_spec", {})

            # Simulate Guardian
            guardian_task = engine.create_task(
                name="validate-sovereign-architecture",
                payload={"version": "sim", "spec": spec, "markdown": ""},
                created_by="selector",
            )
            guardian = engine.run("AVOT-guardian", guardian_task).output
            g_score = guardian.get("coherence_score", 0)

            # Simulate Convergence
            conv_task = engine.create_task(
                name="arbitrate-sovereign-architecture",
                payload={"guardian_score": g_score, "spec": spec, "metadata": {}},
                created_by="selector",
            )
            conv = engine.run("AVOT-convergence", conv_task).output
            c_score = conv.get("convergence_score", 0)

            composite = (g_score + c_score) / 2

            if composite > best_score:
                best_score = composite
                best = spec

        return {
            "selected_spec": best,
            "score": best_score,
        }
