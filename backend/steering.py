from __future__ import annotations
from typing import Dict, Any


class SteeringEngine:
    """
    SteeringEngine v0.1

    Applies corrective steering to predicted specs BEFORE evolution is executed.

    Uses:
        - predictive delta overlays
        - drift/stability heuristics
        - epoch parameters
        - semantic resonance checks

    Output:
        {
            "steered_spec": {...},
            "steering_score": <0.0-1.0>,
            "actions": [...]
        }
    """

    def steer(self, predicted: Dict[str, Any], delta: Dict[str, Any], epoch_params: Dict[str, Any]) -> Dict[str, Any]:
        spec = predicted.copy()

        actions = []
        score = 0.0

        layers = spec.get("layers", [])

        # ----------------------------------------------------
        # 1. Prevent over-expansion (too many new layers)
        # ----------------------------------------------------
        added_layers = delta.get("layers_added", [])
        if len(added_layers) > 2:
            # prune predicted growth
            layers = layers[:-1]
            score += 0.25
            actions.append("pruned_predicted_layers")

        # ----------------------------------------------------
        # 2. Prevent collapse (too many removals)
        # ----------------------------------------------------
        removed_layers = delta.get("layers_removed", [])
        if len(removed_layers) > 1:
            # restore minimal stability layer
            layers.append({"name": "stability_layer", "components": ["core"], "role": "Stabilization"})
            score += 0.25
            actions.append("added_stability_layer")

        # ----------------------------------------------------
        # 3. Enforce semantic resonance depth from epoch
        # ----------------------------------------------------
        desired_depth = epoch_params.get("semantic_depth", 1)
        for l in layers:
            if "notes" not in l:
                l["notes"] = ""
            l["notes"] += f" [resonance depth {desired_depth}]"
        score += 0.15
        actions.append("applied_epoch_resonance")

        # ----------------------------------------------------
        # 4. Prevent chaotic role shifting
        # ----------------------------------------------------
        role_changes = delta.get("role_changes", [])
        if len(role_changes) > 2:
            for l in layers:
                if "role" in l:
                    l["role"] = "Harmonic Processing"
            score += 0.20
            actions.append("flattened_roles")

        # ----------------------------------------------------
        # 5. Prevent divergent lifecycle changes
        # ----------------------------------------------------
        lifecycle = spec.get("lifecycle", {})
        removed_lc = delta.get("lifecycle_removed", [])

        if len(removed_lc) > 0:
            # restore default cycle
            lifecycle["ingest"] = "process"
            lifecycle["process"] = "align"
            lifecycle["align"] = "express"
            score += 0.15
            actions.append("restored_default_lifecycle")

        spec["layers"] = layers
        spec["lifecycle"] = lifecycle

        return {
            "steered_spec": spec,
            "steering_score": round(min(score, 1.0), 3),
            "actions": actions
        }
