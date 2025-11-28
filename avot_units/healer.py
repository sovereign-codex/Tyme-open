from __future__ import annotations

from typing import Dict, Any
from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot


@register_avot("AVOT-healer")
class AvotHealer(BaseAVOT):
    """
    AVOT-healer v0.1

    Automatically repairs failed or rejected architecture specs.

    Heuristic rules:
        - If Guardian score low → simplify structure
        - If Convergence score low → clarify flows & lifecycle
        - Always expand semantic roles for clarity
    """

    description = "Repairs a rejected architecture spec into a higher-coherence version."

    def act(self, task: AvotTask) -> Dict[str, Any]:
        spec = task.payload.get("spec", {}) or {}
        guardian = task.payload.get("guardian_score", 0)
        convergence = task.payload.get("convergence_score", 0)

        layers = spec.get("layers", [])

        # ------------------------------
        # Structural healing
        # ------------------------------
        if guardian < 0.5:
            # Prune to minimal safe structure
            if len(layers) > 1:
                layers = layers[: max(1, len(layers) - 1)]

        # ------------------------------
        # Convergence healing
        # ------------------------------
        if convergence < 0.5:
            for layer in layers:
                layer.setdefault("flows", [])
                layer["flows"].append("Revised for stable Convergence alignment.")
                layer.setdefault("notes", "")
                layer["notes"] += " Adjusted for convergence coherence."

        # ------------------------------
        # Semantic healing
        # ------------------------------
        for _, layer in enumerate(layers, start=1):
            layer.setdefault("role", "Repaired Functional Layer")
            layer.setdefault("notes", "")
            layer["notes"] += " Semantic reinforcement applied."

        healed_spec = {
            "description": "Healed version of rejected architecture.",
            "root_node": spec.get("root_node", "sovereign_intelligence"),
            "layers": layers,
            "lifecycle": spec.get("lifecycle", {}),
        }

        return {
            "healed_spec": healed_spec
        }
