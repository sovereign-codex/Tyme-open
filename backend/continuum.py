from __future__ import annotations
import os
import json
import numpy as np
from typing import Dict, Any


class ContinuumEngine:
    """
    ContinuumEngine v0.1

    Unifies all architectural metrics into:
      - Continuum State Vector (CSV)
      - Continuum Score
      - Continuum Drift
      - Continuum Alignment Index
      - Continuum Identity Vector (persistent)
    """

    ID_PATH = "memory/continuum/identity.json"

    def __init__(self):
        os.makedirs("memory/continuum", exist_ok=True)
        if not os.path.exists(self.ID_PATH):
            with open(self.ID_PATH, "w") as f:
                json.dump({"identity": []}, f)

    def load_identity(self):
        with open(self.ID_PATH) as f:
            return json.load(f).get("identity", [])

    def save_identity(self, vec):
        with open(self.ID_PATH, "w") as f:
            json.dump({"identity": vec}, f, indent=2)

    def normalize(self, v):
        v = np.array(v, dtype=float)
        n = np.linalg.norm(v)
        return (v / (n or 1)).tolist()

    def build_csv(
        self,
        embedding: Dict[str, Any],
        resonance: Dict[str, Any],
        basin: Dict[str, Any],
        attractor: Dict[str, Any],
        field: Dict[str, Any],
        regression: Dict[str, Any],
        epoch: Dict[str, Any],
        simulation: Dict[str, Any],
    ):
        # Construct multi-domain vector
        vector = []

        # Embedding signal
        emb_vec = embedding.get("vector", [])
        padded = (emb_vec + [0] * 32)[:32]
        vector += padded

        # Resonance signal
        vector += resonance.get("resonance_vector", [])
        vector += resonance.get("resonance_gradient", [])

        # Basin signals
        vector += [
            basin.get("basin_depth", 0),
            basin.get("basin_width", 0),
            basin.get("escape_energy", 0),
            basin.get("curvature", 0),
        ]

        # Attractor
        a = attractor.get("attractor", {})
        vector += [
            {"fixed_point": 1, "limit_cycle": 2, "strange_attractor": 3, "drift_attractor": 4, "harmonic_basin": 5}.get(
                a.get("type", ""), 0
            ),
            a.get("strength", 0),
        ]

        # Field coherence
        vector.append(field.get("coherence_index", 0))

        # Regression forecasts
        vector += [
            regression.get("predicted_coherence", 0),
            regression.get("predicted_convergence", 0),
            regression.get("predicted_complexity", 0),
            regression.get("predicted_drift_probability", 0),
        ]

        # Epoch tuning
        ep = epoch.get("parameters", {})
        vector += [
            ep.get("convergence_sensitivity", 0),
            ep.get("semantic_depth", 0),
            ep.get("horizon", 0),
            ep.get("evolution_rate", 0),
            ep.get("strictness", 0),
        ]

        # Simulation energy signature (wave summary)
        wave_path = simulation.get("wave_path")
        wave_energy = 0
        if wave_path and os.path.exists(wave_path):
            with open(wave_path) as f:
                data = json.load(f)
                if data:
                    wave_energy = float(np.mean(list(data.values())))
        vector.append(wave_energy)

        return self.normalize(vector)

    def compute_scores(self, csv):
        csv = np.array(csv)

        # Continuum Score = mean positive coherence & resonance alignment
        continuum_score = float(np.mean(np.maximum(csv, 0)))

        # Drift = magnitude of negative curvature in vector space
        continuum_drift = float(np.mean(np.minimum(csv, 0)) * -1)

        # Alignment = 1 - variance (low variance = aligned forces)
        var = float(np.var(csv))
        alignment = float(max(0, 1 - var))

        return continuum_score, continuum_drift, alignment

    def update_identity(self, identity, csv):
        identity = np.array(identity or csv)
        csv = np.array(csv)
        # exponential moving average
        new_identity = 0.9 * identity + 0.1 * csv
        return new_identity.tolist()

    def process(
        self,
        version,
        embedding: Dict[str, Any],
        resonance: Dict[str, Any],
        basin: Dict[str, Any],
        attractor: Dict[str, Any],
        field: Dict[str, Any],
        regression: Dict[str, Any],
        epoch: Dict[str, Any],
        simulation: Dict[str, Any],
    ):

        csv = self.build_csv(
            embedding,
            resonance,
            basin,
            attractor,
            field,
            regression,
            epoch,
            simulation,
        )

        score, drift, align = self.compute_scores(csv)

        identity = self.load_identity()
        new_identity = self.update_identity(identity, csv)
        self.save_identity(new_identity)

        out = {
            "version": version,
            "csv": csv,
            "score": score,
            "drift": drift,
            "alignment": align,
            "identity": new_identity,
        }

        # save
        path = f"visuals/continuum/continuum-v{version}.json"
        os.makedirs("visuals/continuum", exist_ok=True)
        with open(path, "w") as f:
            json.dump(out, f, indent=2)

        out["path"] = path
        return out
