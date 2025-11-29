from __future__ import annotations
import os, json
from typing import Dict, Any, List
import numpy as np


class BasinEngine:
    """
    BasinEngine v0.1

    Computes:
      - basin_depth
      - basin_width
      - escape_energy
      - phase_curvature
      - basin_class

    Using:
      - phase plot history (C30)
      - attractor type (C31)
      - field coherence (C28)
      - regression signals (C29)
    """

    OUTPUT_DIR = "visuals/phase"

    def __init__(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def load_phase(self) -> List[Dict[str, Any]]:
        path = os.path.join(self.OUTPUT_DIR, "phase.json")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return json.load(f)

    def load_basin(self, version: str) -> Dict[str, Any]:
        path = os.path.join(self.OUTPUT_DIR, f"basin-v{version}.json")
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            data = json.load(f)
        data["path"] = path
        return data

    def load_latest_basin(self) -> Dict[str, Any]:
        files = [f for f in os.listdir(self.OUTPUT_DIR) if f.startswith("basin-v") and f.endswith(".json")]
        if not files:
            return {}
        files.sort(key=lambda x: float(x.replace("basin-v", "").replace(".json", "")))
        latest = files[-1]
        version = latest.replace("basin-v", "").replace(".json", "")
        return self.load_basin(version)

    def compute_curvature(self, pts: List[Dict[str, Any]]) -> float:
        if len(pts) < 3:
            return 0.0

        xs = np.array([p["x"] for p in pts])
        ys = np.array([p["y"] for p in pts])

        dx = np.diff(xs)
        dy = np.diff(ys)

        ddx = np.diff(dx)
        ddy = np.diff(dy)

        curvatures = []
        for i in range(len(ddx)):
            num = abs(dx[i] * ddy[i] - dy[i] * ddx[i])
            den = (dx[i] ** 2 + dy[i] ** 2) ** 1.5 if (dx[i] ** 2 + dy[i] ** 2) > 0 else 1
            curvatures.append(num / den)

        return float(np.mean(curvatures))

    def classify_basin(self, depth: float, width: float, curvature: float) -> str:
        if depth > 0.75 and width > 0.5:
            return "deep_harmonic_basin"
        if depth > 0.5 and curvature < 0.1:
            return "stability_ridge"
        if curvature > 0.4:
            return "chaotic_valley"
        if depth < 0.3 and width > 0.6:
            return "entropy_sink_basin"
        return "shallow_expansion_basin"

    def compute(self, version: str, attractor: Dict[str, Any], field: Dict[str, Any]):
        pts = self.load_phase()
        if not pts:
            return {"error": "no phase data"}

        curvature = round(self.compute_curvature(pts), 4)

        coherence = field.get("coherence_index", 0)
        strength = 0
        if isinstance(attractor, dict):
            if "attractor" in attractor:
                strength = attractor.get("attractor", {}).get("strength", 0)
            else:
                strength = attractor.get("strength", 0)

        basin_depth = round(0.5 * coherence + 0.5 * strength, 4)

        xs = [p.get("x", 0) for p in pts]
        ys = [p.get("y", 0) for p in pts]
        basin_width = round(min(1, (np.std(xs) + np.std(ys))), 4)

        escape_energy = round(max(0, 1 - basin_depth + curvature), 4)

        basin_class = self.classify_basin(basin_depth, basin_width, curvature)

        out = {
            "version": version,
            "basin_depth": basin_depth,
            "basin_width": basin_width,
            "escape_energy": escape_energy,
            "curvature": curvature,
            "class": basin_class,
        }

        path = os.path.join(self.OUTPUT_DIR, f"basin-v{version}.json")
        with open(path, "w") as f:
            json.dump(out, f, indent=2)

        out["path"] = path
        return out
