from __future__ import annotations
import numpy as np
from typing import Dict, Any


class ResonanceEngine:
    """
    ResonanceEngine v0.1

    Computes:
      - Resonance Vector (RV)
      - Resonance Gradient (RG)
      - Resonance Mode selection

    Inputs:
      - embedding (C26)
      - field coherence (C28)
      - attractor (C31)
      - basin geometry (C32)
      - regression predictions (C29)
      - strategy score (C27)
    """

    MODES = [
        "harmonic_ascension",
        "stability_preservation",
        "drift_avoidance",
        "expansion_wave",
        "resonant_correction"
    ]

    def compute_vector(self, embedding, field, attractor, basin, regression, strategy):
        # RV is a normalized composite vector across all signals
        e = np.array(embedding.get("vector", []) or [0])
        coh = field.get("coherence_index", 0)
        att = attractor.get("attractor", {}).get("strength", 0)
        depth = basin.get("basin_depth", 0)
        reg_coh = regression.get("predicted_coherence", 0)
        strat = strategy.get("score", 0)

        rv = np.array([
            e.mean() if len(e)>0 else 0,
            coh,
            att,
            depth,
            reg_coh,
            strat
        ], dtype=float)

        norm = np.linalg.norm(rv) or 1
        return (rv / norm).tolist()

    def compute_gradient(self, rv_curr, rv_pred):
        a = np.array(rv_curr)
        b = np.array(rv_pred)
        diff = b - a
        norm = np.linalg.norm(diff) or 1
        return (diff / norm).tolist()

    def choose_mode(self, gradient):
        gx, gy, gz, ga, gb, gc = gradient

        if ga > 0.3 and gb > 0.3:
            return "harmonic_ascension"
        if gx < 0.1 and gy < 0.1:
            return "stability_preservation"
        if gx < -0.2 or gy < -0.2:
            return "drift_avoidance"
        if gc > 0.25:
            return "expansion_wave"
        return "resonant_correction"

    def influence_parameters(self, mode, params):
        out = params.copy()

        if mode == "harmonic_ascension":
            out["semantic_expand"] = True
            out["predictor_boost"] = "semantic"
        elif mode == "stability_preservation":
            out["predictor_boost"] = "minimal"
        elif mode == "drift_avoidance":
            out["steering_strength"] = 1.0
            out["predictor_boost"] = "minimal"
        elif mode == "expansion_wave":
            out["predictor_boost"] = "deep"
        elif mode == "resonant_correction":
            out["steering_strength"] = 0.7

        return out

    def process(self, version, embedding, field, attractor, basin, regression, strategy):
        rv_curr = self.compute_vector(embedding, field, attractor, basin, regression, strategy)

        # Predict future RV via simple shift
        rv_pred = [(v + 0.05) for v in rv_curr]
        grad = self.compute_gradient(rv_curr, rv_pred)
        mode = self.choose_mode(grad)

        influenced = self.influence_parameters(mode, {})

        return {
            "resonance_vector": rv_curr,
            "resonance_gradient": grad,
            "mode": mode,
            "influence": influenced
        }
