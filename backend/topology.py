from __future__ import annotations
from typing import Dict, Any, List
import os
import json
from backend.delta_engine import DeltaEngine


class TopologyExtractor:
    """
    TopologyExtractor v0.1

    Converts an architecture spec into a graph topology:
      - nodes: layers + root
      - edges: layer connections and lifecycle calls

    Output saved to:
      visuals/lattice/topology-v{version}.json
    """

    OUTPUT_DIR = "visuals/lattice"

    def __init__(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def extract(self, version: str, spec: Dict[str, Any]) -> str:
        root = spec.get("root_node", "sovereign")
        layers = spec.get("layers", [])
        lifecycle = spec.get("lifecycle", {})

        # Compute delta against previous version (if exists)
        delta = {}
        try:
            old_version = str(float(version) - 1)
            de = DeltaEngine()
            delta = de.compute_delta(version, old_version)
        except:
            delta = {}

        nodes = [{"id": root, "type": "root"}]

        for idx, layer in enumerate(layers, start=1):
            nodes.append({
                "id": f"layer_{idx}",
                "label": layer.get("role", f"Layer {idx}"),
                "type": "layer",
            })

        edges = []
        for idx in range(1, len(layers) + 1):
            edges.append({
                "source": root,
                "target": f"layer_{idx}",
                "type": "root_to_layer"
            })

        # Lifecycle flow dependencies
        for (state, nxt) in lifecycle.items():
            edges.append({
                "source": state,
                "target": nxt,
                "type": "lifecycle"
            })
            nodes.append({"id": state, "type": "lifecycle"})
            nodes.append({"id": nxt, "type": "lifecycle"})

        topology = {
            "nodes": nodes,
            "edges": edges,
            "delta": delta
        }

        path = os.path.join(self.OUTPUT_DIR, f"topology-v{version}.json")
        with open(path, "w") as f:
            json.dump(topology, f, indent=2)

        return path
