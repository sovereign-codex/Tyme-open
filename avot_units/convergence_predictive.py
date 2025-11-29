from __future__ import annotations

from typing import Dict, Any
from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot


@register_avot("AVOT-convergence-predictive")
class AvotConvergencePredictive(BaseAVOT):
    """
    AVOT-convergence-predictive v0.1

    Runs a *pre-evolution* convergence check on the predicted spec
    before we actually fabricate and commit the new architecture.

    It:
      - calls AVOT-guardian on the predicted spec
      - calls AVOT-convergence on the predicted spec
      - combines those scores with the steering_score
      - factors in epoch convergence_sensitivity
      - decides whether evolution should proceed, soften, or hold
    """

    description = "Predictive convergence gate for anticipated architectures."

    def act(self, task: AvotTask) -> Dict[str, Any]:
        engine = self.engine
        payload = task.payload or {}

        predicted_spec = payload.get("predicted_spec", {}) or {}
        epoch = payload.get("epoch", {}) or {}
        epoch_params = epoch.get("parameters", {}) or {}
        steering_score = float(payload.get("steering_score", 0.0))

        # 1) Guardian on predicted spec
        guardian_task = engine.create_task(
            name="validate-predicted-architecture",
            payload={"version": "predicted", "spec": predicted_spec, "markdown": ""},
            created_by=task.created_by,
        )
        guardian_out = engine.run("AVOT-guardian", guardian_task).output
        g_pred = float(guardian_out.get("coherence_score", 0.0))

        # 2) Convergence on predicted spec
        conv_task = engine.create_task(
            name="converge-predicted-architecture",
            payload={"guardian_score": g_pred, "spec": predicted_spec, "metadata": {}},
            created_by=task.created_by,
        )
        conv_out = engine.run("AVOT-convergence", conv_task).output
        c_pred = float(conv_out.get("convergence_score", 0.0))

        # 3) Combine with epoch sensitivity + steering
        sensitivity = float(epoch_params.get("convergence_sensitivity", 0.5))

        # composite predictive score
        predictive_score = (g_pred + c_pred + steering_score) / 3.0

        # dynamic threshold: stricter when sensitivity is high
        threshold = 0.5 + 0.2 * sensitivity  # between 0.5 and 0.7 typical
        predictive_approved = predictive_score >= threshold

        # simple recommended action
        if predictive_approved and predictive_score > (threshold + 0.1):
            action = "proceed"
        elif predictive_approved:
            action = "proceed_softened"
        else:
            action = "hold"

        return {
            "predictive_guardian_score": g_pred,
            "predictive_convergence_score": c_pred,
            "predictive_score": predictive_score,
            "predictive_threshold": threshold,
            "predictive_approved": predictive_approved,
            "recommended_action": action,
        }
