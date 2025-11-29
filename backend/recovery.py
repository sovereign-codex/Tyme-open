from __future__ import annotations
import os, json, numpy as np
from typing import Dict, Any


class RecoveryEngine:
    """
    RecoveryEngine v0.1

    Detects coherence collapse and performs:
      - structural recovery
      - harmonic recovery
      - epoch recovery
      - identity anchoring
      - lattice healing pulses
    """

    OUTDIR = "visuals/recovery"

    def __init__(self):
        os.makedirs(self.OUTDIR, exist_ok=True)

    # -----------------------------------------------------------------
    # Degradation detection
    # -----------------------------------------------------------------
    def needs_recovery(self, continuum, basin, attractor):
        score = continuum.get("score", 1)
        align = continuum.get("alignment", 1)
        drift = continuum.get("drift", 0)
        basin_class = basin.get("class", "")
        attractor_type = attractor.get("attractor", {}).get("type", "")

        if score < 0.45: return True
        if align < 0.25: return True
        if drift > 0.40: return True
        if basin_class in ["chaotic_valley", "entropy_sink_basin"]: return True
        if attractor_type in ["strange_attractor", "drift_attractor"]: return True

        return False

    # -----------------------------------------------------------------
    # Structural recovery
    # -----------------------------------------------------------------
    def structural_recover(self, spec):
        new_spec = dict(spec)
        layers = list(spec.get("layers", []))

        # baseline copy of layers
        new_spec["layers"] = layers

        if len(layers) > 3:
            # prune last layer
            new_spec["layers"] = layers[:-1]

        # reduce semantic noise
        for l in new_spec["layers"]:
            notes = l.get("notes", "")
            if len(notes) > 200:
                l["notes"] = notes[:200]

        return new_spec

    # -----------------------------------------------------------------
    # Harmonic recovery
    # -----------------------------------------------------------------
    def harmonic_recover(self, continuum, resonance):
        rv = np.array(resonance.get("resonance_vector", []))
        identity = np.array(continuum.get("identity", rv.tolist()))

        # pull resonance vector toward identity
        corrected = 0.7 * rv + 0.3 * identity
        corrected = (corrected / (np.linalg.norm(corrected) or 1)).tolist()

        return corrected

    # -----------------------------------------------------------------
    # Epoch recovery
    # -----------------------------------------------------------------
    def epoch_recover(self, tuned):
        out = dict(tuned)
        out["epoch_mode"] = "stabilization"
        out["evolution_rate"] = max(0.2, tuned.get("evolution_rate", 1.0) * 0.5)
        out["horizon"] = max(1, int(tuned.get("horizon", 3) * 0.5))
        out["strictness"] = min(1, tuned.get("strictness", 0.5) + 0.2)
        return out

    # -----------------------------------------------------------------
    # Lattice healing pulse
    # -----------------------------------------------------------------
    def healing_pulse(self, wave_path):
        energy = 0.5
        if wave_path and os.path.exists(wave_path):
            with open(wave_path) as f:
                wave = json.load(f)
                if wave:
                    energy = float(np.mean(list(wave.values())))
        return max(0.1, min(1.0, energy + 0.2))

    # -----------------------------------------------------------------
    # Process
    # -----------------------------------------------------------------
    def process(self, version, spec, continuum, resonance, basin, attractor, epoch, simulation):
        if not self.needs_recovery(continuum, basin, attractor):
            return {"recovered": False}

        # Perform layered recovery
        new_spec = self.structural_recover(spec)
        corrected_rv = self.harmonic_recover(continuum, resonance)
        epoch_fixed = self.epoch_recover(epoch.get("parameters", {}))
        pulse = self.healing_pulse(simulation.get("wave_path"))

        out = {
            "recovered": True,
            "new_spec": new_spec,
            "corrected_resonance_vector": corrected_rv,
            "epoch_recovered": epoch_fixed,
            "healing_pulse_energy": pulse
        }

        path = f"{self.OUTDIR}/recovery-v{version}.json"
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
        out["path"] = path

        return out
