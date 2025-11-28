from __future__ import annotations

import os, re
from typing import Dict, Any, List


INDEX_PATH = "docs/MASTER-ARCHITECTURE-INDEX.md"


class HeatmapAnalyzer:
    """
    HeatmapAnalyzer v0.1

    Computes the "change intensity" between architecture versions by examining:
    - number of layers
    - differences in layer count
    - differences in component count
    - pattern shifts inferred from historical metadata (future extension)

    Output:
        {
          "versions": [...],
          "layer_counts": [...],
          "layer_deltas": [...],
          "heatmap_values": [...],
        }
    """

    def _load_specs(self) -> List[Dict[str, Any]]:
        """
        Loads references to scroll files from the MAI.
        Then loads the actual specs by reading docs/<filename>.
        """
        if not os.path.exists(INDEX_PATH):
            return []

        specs = []

        with open(INDEX_PATH, "r") as f:
            text = f.read()

        blocks = re.split(r"## Version ", text)

        for block in blocks[1:]:
            version = re.search(r"v([0-9.]+)", block)
            filename = re.search(r"Filename:\*\* `([^`]+)`", block)

            if not filename:
                continue

            path = os.path.join("docs", filename.group(1))
            if not os.path.exists(path):
                continue

            # Attempt to extract a JSON-like spec skeleton by scanning headers
            # This is intentionally minimal — the lattice can evolve later.
            specs.append({
                "version": version.group(1) if version else "0.0",
                "path": path,
            })

        return specs

    def _load_layer_count(self, scroll_path: str) -> int:
        """
        Extract layer count from markdown using headings like:
        - "layer_1"
        - "layer 1"
        - "## layer_1"
        etc.
        """
        with open(scroll_path, "r") as f:
            text = f.read().lower()

        matches = re.findall(r"layer[_ ]?(\d+)", text)
        nums = [int(m) for m in matches]
        return max(nums) if nums else 0

    def analyze(self) -> Dict[str, Any]:
        specs = self._load_specs()
        if not specs:
            return {
                "versions": [],
                "layer_counts": [],
                "layer_deltas": [],
                "heatmap_values": [],
            }

        layer_counts = [self._load_layer_count(s["path"]) for s in specs]

        layer_deltas = []
        heatmap_values = []

        for i in range(len(layer_counts)):
            if i == 0:
                layer_deltas.append(0)
                heatmap_values.append(0)
                continue

            delta = layer_counts[i] - layer_counts[i - 1]
            layer_deltas.append(delta)

            # Heatmap value = |delta| for now (can expand later)
            heatmap_values.append(abs(delta))

        return {
            "versions": [s["version"] for s in specs],
            "layer_counts": layer_counts,
            "layer_deltas": layer_deltas,
            "heatmap_values": heatmap_values,
        }
