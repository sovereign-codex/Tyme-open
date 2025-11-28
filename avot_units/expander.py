from __future__ import annotations

from typing import Dict, Any, List
from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot


@register_avot("AVOT-expander")
class AvotExpander(BaseAVOT):
    """
    AVOT-expander v0.1

    Adds semantic depth to an architecture spec by enriching:
        - layer descriptions
        - roles
        - flows
        - governance notes

    Input payload:
        {
          "spec": {...}
        }

    Output:
        {
          "expanded_spec": {...}
        }
    """

    description = "Semantically expands predicted specs into richer, more descriptive architectures."

    def act(self, task: AvotTask) -> Dict[str, Any]:
        payload = task.payload or {}
        spec = payload.get("spec", {}) or {}

        root = spec.get("root_node", "sovereign_intelligence")
        layers = spec.get("layers", [])
        lifecycle = spec.get("lifecycle", {})

        # Enrich lifecycle if needed
        if not lifecycle.get("governance_rhythm"):
            lifecycle["governance_rhythm"] = (
                "continuous sensing → periodic review → convergence arbitration → archive"
            )

        lifecycle.setdefault("decision_points", [
            "guardian_approval",
            "convergence_arbitration",
            "human_overview_optional"
        ])

        # Enrich layers
        expanded_layers: List[Dict[str, Any]] = []
        for idx, layer in enumerate(layers, start=1):
            name = layer.get("name") or f"layer_{idx}"
            components = layer.get("components") or []

            semantic_role = self._infer_layer_role(idx, len(layers))
            flows = [
                f"{name} receives input from previous layer (if any) and forwards coherent state to next.",
                f"{name} maintains alignment with root node '{root}'.",
            ]

            expanded_layer = {
                "name": name,
                "components": components or ["core", "governance", "flow"],
                "role": semantic_role,
                "flows": flows,
                "notes": f"This layer participates in the sovereign lattice as {semantic_role.lower()}."
            }
            expanded_layers.append(expanded_layer)

        expanded_spec = {
            "description": spec.get("description") or "Semantically expanded architecture spec.",
            "root_node": root,
            "layers": expanded_layers,
            "lifecycle": lifecycle,
        }

        return {
            "expanded_spec": expanded_spec
        }

    def _infer_layer_role(self, index: int, total: int) -> str:
        if index == 1:
            return "Foundation & Ingestion"
        if index == total:
            return "Expression & Interface"
        return "Processing & Governance Bridge"
