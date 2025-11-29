from __future__ import annotations
import os, json, math
from typing import Dict, Any


class FieldCoherenceEngine:
    """
    FieldCoherenceEngine v0.1

    Computes a coherence score for the architecture as a "field" by
    combining:

      - semantic resonance from layers
      - lifecycle continuity
      - complexity balance
      - embedding geometry (from C26)
      - long-horizon strategy slope (C27)
      - predictive drift potential

    Output:
        {
          "coherence_index": float(0–1),
          "field_strengths": {...},
          "tension_matrix": {...}
        }
    """

    OUTPUT_DIR = "visuals/field"

    def __init__(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def compute(self, version: str, spec: Dict[str, Any], embedding: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        layers = spec.get("layers", [])
        lifecycle = spec.get("lifecycle", {})

        # -----------------------------------
        # Layer resonance (semantic density)
        # -----------------------------------
        sem_depth = sum(len(l.get("notes", "")) for l in layers)
        sem_norm = sem_depth / (len(layers) + 1)

        # -----------------------------------
        # Complexity balance
        # -----------------------------------
        comp = len(layers)
        comp_score = math.exp(-abs(comp - 3))  # 3 layers ~ ideal

        # -----------------------------------
        # Embedding smoothness
        # -----------------------------------
        emb_vec = embedding.get("vector", [])
        if len(emb_vec) > 0:
            emb_energy = 1 - abs(sum(emb_vec)/len(emb_vec))
        else:
            emb_energy = 0.5

        # -----------------------------------
        # Strategy slope (C27)
        # -----------------------------------
        strat_score = strategy.get("score", 0.6)

        # -----------------------------------
        # Lifecycle continuity
        # -----------------------------------
        lc_score = 1 - (len(lifecycle) * 0.05)

        # -----------------------------------
        # Combine into coherence index
        # -----------------------------------
        coherence_index = max(0, min(1, (
            0.20 * sem_norm +
            0.20 * comp_score +
            0.20 * emb_energy +
            0.20 * strat_score +
            0.20 * lc_score
        )))

        # -----------------------------------
        # Node field strengths
        # -----------------------------------
        field_strengths = {}
        for i, l in enumerate(layers):
            field_strengths[l.get("name", f"layer_{i}")] = round(
                (len(l.get("notes", "")) + 1) * coherence_index, 4
            )

        # -----------------------------------
        # Tension matrix (simple placeholder)
        # -----------------------------------
        tension_matrix = {}
        for i, src in enumerate(layers):
            row = {}
            for j, dst in enumerate(layers):
                if i == j:
                    row[dst.get("name", "")] = 0.0
                else:
                    row[dst.get("name", "")] = round(
                        abs(i-j) * (1 - coherence_index), 4
                    )
            tension_matrix[src.get("name", "")] = row

        # -----------------------------------
        # Save outputs
        # -----------------------------------
        field_path = os.path.join(self.OUTPUT_DIR, f"field-v{version}.json")
        heatmap_path = os.path.join(self.OUTPUT_DIR, f"heatmap-v{version}.json")

        with open(field_path, "w") as f:
            json.dump({
                "coherence_index": coherence_index,
                "field_strengths": field_strengths,
                "tension_matrix": tension_matrix
            }, f, indent=2)

        with open(heatmap_path, "w") as f:
            json.dump(tension_matrix, f, indent=2)

        return {
            "coherence_index": coherence_index,
            "field_strengths": field_strengths,
            "tension_matrix": tension_matrix,
            "field_path": field_path,
            "heatmap_path": heatmap_path
        }
