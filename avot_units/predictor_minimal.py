from __future__ import annotations
from typing import Dict, Any
from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot


@register_avot("AVOT-predictor-minimal")
class AvotPredictorMinimal(BaseAVOT):
    """
    Produces a simplified architecture with fewer layers and core essentials.
    """

    def act(self, task: AvotTask) -> Dict[str, Any]:
        base = task.payload.get("base_spec", {}) or {}

        layers = base.get("layers", [])
        new_count = max(1, len(layers) - 1)

        predicted = {
            "description": "Minimal structural evolution.",
            "root_node": base.get("root_node", "sovereign_intelligence"),
            "layers": [{"name": f"layer_{i}", "components": ["core"]} for i in range(1, new_count + 1)],
            "lifecycle": base.get("lifecycle", {}),
        }

        return {"predicted_spec": predicted, "mode": "minimal"}
