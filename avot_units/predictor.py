from __future__ import annotations

from typing import Dict, Any, List
from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot
from backend.drift_monitor import DriftMonitor


@register_avot("AVOT-predictor")
class AvotPredictor(BaseAVOT):
    """
    AVOT-predictor v0.1

    Generates a predicted next architecture spec by:
    - Analyzing version history from MAI
    - Using smoothed Guardian & Convergence trajectories
    - Detecting upward/downward structural drift
    - Identifying missing/collapsing layers
    - Projecting "next likely improvements"

    Output:
        {
          "predicted_spec": {...},
          "signals": {...}
        }
    """

    description = "Predicts the next architecture evolution based on historical trends."

    def act(self, task: AvotTask) -> Dict[str, Any]:
        monitor = DriftMonitor()
        analysis = monitor.analyze()

        entries = analysis.get("entries", [])
        if len(entries) < 2:
            return {
                "predicted_spec": {},
                "signals": {"note": "Insufficient history for predictive synthesis."}
            }

        # Extract trend signals
        sm_guard = analysis["guardian_smoothed"]
        sm_conv = analysis["convergence_smoothed"]

        guardian_trend = sm_guard[-1] - sm_guard[-2]
        convergence_trend = sm_conv[-1] - sm_conv[-2]

        # Upward drift = add complexity
        add_layer = guardian_trend > 0 or convergence_trend > 0

        # Downward drift = simplify structure
        prune_layers = guardian_trend < 0 and convergence_trend < 0

        last_version = entries[-1]

        # BEGIN: Predictive spec construction
        predicted = {
            "description": "Predicted evolution based on temporal coherence trends.",
            "root_node": "sovereign_intelligence",
            "layers": [],
            "lifecycle": {
                "governance_rhythm": "periodic review + convergence arbitration"
            }
        }

        # Baseline: inherit last layer count
        last_layer_count = 3
        if "layers" in task.payload:
            last_layer_count = len(task.payload.get("layers", []))

        # Modify based on trend direction
        if add_layer:
            new_count = last_layer_count + 1
        elif prune_layers and last_layer_count > 1:
            new_count = last_layer_count - 1
        else:
            new_count = last_layer_count

        predicted["layers"] = [
            {"name": f"layer_{i}", "components": ["core", "governance", "flow"]}
            for i in range(1, new_count + 1)
        ]

        # END: Predictive spec built.

        signals = {
            "guardian_trend": guardian_trend,
            "convergence_trend": convergence_trend,
            "prediction_type": "add_layer" if add_layer else "prune_layer" if prune_layers else "stabilize"
        }

        return {
            "predicted_spec": predicted,
            "signals": signals
        }
