from __future__ import annotations

import time
from typing import Dict, Any

from backend.drift_monitor import DriftMonitor
from backend.attractor import AttractorEngine


class EpochEngine:
    """
    EpochEngine v0.1

    Defines "Governance Epochs" based on:
    - stability index
    - drift intensity
    - length of previous epoch
    - evolution cycle count (optional future extension)

    Epochs:
        * GENESIS
        * HARMONIC
        * CORRECTION
        * EXPANSION
        * CONVERGENCE

    Each epoch returns:
        - predictor_weights
        - guardian_strictness
        - convergence_sensitivity
        - semantic_depth
        - recommended_rhythm_mode
    """

    def get_epoch(self) -> Dict[str, Any]:
        monitor = DriftMonitor()
        analysis = monitor.analyze()

        stability = analysis.get("stability_index", 0)
        drift_count = len(analysis.get("drift_flags", []))

        attractor_engine = AttractorEngine()
        phase_points = attractor_engine.load_phase()
        attractor = attractor_engine.detect_attractor(phase_points) if phase_points else {"type": "unknown", "strength": 0}
        attractor_type = attractor.get("type")

        # ---------------------------
        # EPOCH DETERMINATION RULES
        # ---------------------------

        # Genesis Epoch – early low stability
        if stability < 0.40:
            epoch = "GENESIS"
            params = {
                "predictor_weights": {"deep": 0.6, "semantic": 0.3, "minimal": 0.1},
                "guardian_strictness": 0.3,
                "convergence_sensitivity": 0.2,
                "semantic_depth": 1,
                "rhythm": "ALERT",
            }

        # Correction Epoch – drift detected
        elif drift_count > 0:
            epoch = "CORRECTION"
            params = {
                "predictor_weights": {"minimal": 0.6, "semantic": 0.3, "deep": 0.1},
                "guardian_strictness": 0.8,
                "convergence_sensitivity": 0.9,
                "semantic_depth": 2,
                "rhythm": "ALERT",
            }

        # Harmonic Epoch – stable & coherent
        elif stability >= 0.85:
            epoch = "HARMONIC"
            params = {
                "predictor_weights": {"semantic": 0.6, "deep": 0.3, "minimal": 0.1},
                "guardian_strictness": 0.6,
                "convergence_sensitivity": 0.5,
                "semantic_depth": 3,
                "rhythm": "CALM",
            }

        # Expansion Epoch – moderate stability but trajectory rising
        elif stability >= 0.60:
            epoch = "EXPANSION"
            params = {
                "predictor_weights": {"deep": 0.5, "semantic": 0.3, "minimal": 0.2},
                "guardian_strictness": 0.5,
                "convergence_sensitivity": 0.4,
                "semantic_depth": 2,
                "rhythm": "ACTIVE",
            }

        # Convergence Epoch – intermediate equilibrium
        else:
            epoch = "CONVERGENCE"
            params = {
                "predictor_weights": {"semantic": 0.4, "minimal": 0.4, "deep": 0.2},
                "guardian_strictness": 0.7,
                "convergence_sensitivity": 0.7,
                "semantic_depth": 2,
                "rhythm": "ACTIVE",
            }

        # Attractor-aware adjustments
        if attractor_type in ("drift_attractor", "strange_attractor"):
            epoch = "CORRECTION"
            params.update({
                "predictor_weights": {"minimal": 0.6, "semantic": 0.3, "deep": 0.1},
                "guardian_strictness": max(params.get("guardian_strictness", 0.8), 0.8),
                "convergence_sensitivity": max(params.get("convergence_sensitivity", 0.9), 0.9),
                "rhythm": "ALERT",
            })
        elif attractor_type in ("fixed_point", "harmonic_basin") and stability >= 0.60:
            epoch = "HARMONIC"
            params.update({
                "guardian_strictness": max(params.get("guardian_strictness", 0.6), 0.5),
                "convergence_sensitivity": max(params.get("convergence_sensitivity", 0.5), 0.4),
                "rhythm": "CALM",
            })
        elif attractor_type == "limit_cycle" and params.get("rhythm") != "ALERT":
            params["rhythm"] = "ACTIVE"

        return {
            "epoch": epoch,
            "stability_index": stability,
            "drift_count": drift_count,
            "parameters": params,
            "attractor": {
                "type": attractor_type,
                "strength": attractor.get("strength", 0),
                "points": len(phase_points),
            },
        }
