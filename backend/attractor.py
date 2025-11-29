from __future__ import annotations
import os, json, math
from typing import Dict, Any, List
import numpy as np


class AttractorEngine:
    """
    AttractorEngine v0.1

    Uses:
        - embeddings (C26)
        - phase plot coordinates (C30)
        - regression trends (C29)
        - coherence field metrics (C28)

    To classify attractor type:
        - fixed point
        - limit cycle
        - strange attractor
        - drift attractor
        - harmonic basin

    And produce an attractor forecast.
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

    def detect_attractor(self, phase_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(phase_points) < 4:
            return {"type": "insufficient-data", "strength": 0}

        # Extract coordinates in order
        xs = np.array([p["x"] for p in phase_points])
        ys = np.array([p["y"] for p in phase_points])

        # Compute velocity vectors
        vx = np.diff(xs)
        vy = np.diff(ys)

        # Norm of velocity
        speed = np.sqrt(vx**2 + vy**2)

        # Change in direction
        angle_changes = []
        for i in range(1, len(vx)):
            v1 = np.array([vx[i-1], vy[i-1]])
            v2 = np.array([vx[i], vy[i]])
            if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
                continue
            cos_a = np.dot(v1, v2) / (np.linalg.norm(v1)*np.linalg.norm(v2))
            cos_a = max(-1, min(1, cos_a))
            angle_changes.append(math.acos(cos_a))

        avg_speed = float(np.mean(speed))
        avg_turn  = float(np.mean(angle_changes)) if angle_changes else 0

        # Classify attractor based on characteristic signatures
        if avg_speed < 0.02 and avg_turn < 0.1:
            attractor_type = "fixed_point"
        elif avg_speed < 0.03 and avg_turn > 0.3:
            attractor_type = "limit_cycle"
        elif avg_speed > 0.04 and avg_turn > 0.5:
            attractor_type = "strange_attractor"
        elif avg_speed > 0.05 and avg_turn < 0.2:
            attractor_type = "drift_attractor"
        else:
            attractor_type = "harmonic_basin"

        # Strength estimate (0–1)
        strength = round(min(1.0, avg_speed + avg_turn), 3)

        return {
            "type": attractor_type,
            "strength": strength,
        }

    def forecast(self, version: str) -> Dict[str, Any]:
        points = self.load_phase()
        if not points:
            return {"error": "Phase plot missing"}

        attractor = self.detect_attractor(points)

        # Save attractor map for this version
        out_path = os.path.join(self.OUTPUT_DIR, f"attractor-v{version}.json")
        with open(out_path, "w") as f:
            json.dump(attractor, f, indent=2)

        return {
            "version": version,
            "attractor": attractor,
            "path": out_path
        }
