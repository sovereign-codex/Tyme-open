from __future__ import annotations
import json, os
from typing import Dict, Any


class HarmonicState:
    """
    HarmonicState v0.1

    Aggregates:
      - continuum
      - resonance
      - basin
      - attractor
      - field
      - simulation summary
      - epoch tuned params
    """

    def load_json(self, path):
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    def get_state(self, version):
        return {
            "continuum":  self.load_json(f"visuals/continuum/continuum-v{version}.json"),
            "resonance":  self.load_json(f"visuals/resonance/resonance-v{version}.json"),
            "attractor":  self.load_json(f"visuals/phase/attractor-v{version}.json"),
            "basin":      self.load_json(f"visuals/phase/basin-v{version}.json"),
            "field":      self.load_json(f"visuals/field/field-v{version}.json"),
            "simulation": self.load_json(f"visuals/simulation/wave-v{version}.json"),
            "epoch":      self.load_json("memory/epoch/state.json") if os.path.exists("memory/epoch/state.json") else {},
        }
