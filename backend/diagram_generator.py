from __future__ import annotations

import os
from typing import Dict, Any

import graphviz


class DiagramGenerator:
    """
    DiagramGenerator v0.1

    Automatically generates:
      - layered architecture diagrams
      - lifecycle flow visuals
      - high-level node relationship graphs

    Output saved as:
      visuals/architecture/ARCH-v{version}.svg
      visuals/architecture/ARCH-v{version}.png
    """

    OUTPUT_DIR = "visuals/architecture"

    def __init__(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def generate(self, version: str, spec: Dict[str, Any]) -> Dict[str, str]:
        layers = spec.get("layers", [])
        root = spec.get("root_node", "sovereign")
        lifecycle = spec.get("lifecycle", {})

        # -------------------------
        # Generate layered diagram
        # -------------------------
        layered = graphviz.Digraph(comment="Architecture Layers")
        layered.node("ROOT", root, shape="hexagon", style="filled", fillcolor="#6dd5fa")

        for idx, layer in enumerate(layers, start=1):
            label = f"L{idx}: {layer.get('role','Layer')}"
            layered.node(label, label, shape="box", style="rounded,filled", fillcolor="#b2f7ef")
            layered.edge("ROOT", label)

        svg_path = os.path.join(self.OUTPUT_DIR, f"ARCH-v{version}.svg")
        png_path = os.path.join(self.OUTPUT_DIR, f"ARCH-v{version}.png")

        layered.render(svg_path, format="svg", cleanup=True)
        layered.render(png_path, format="png", cleanup=True)

        return {
            "svg": svg_path + ".svg",
            "png": png_path + ".png",
        }
