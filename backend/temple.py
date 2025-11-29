from __future__ import annotations
import os, json
from typing import Dict, Any


class MemoryTempleEngine:
    """
    MemoryTempleEngine v0.1

    Responsibilities:
      - Maintain a unified memory index of all versions.
      - Store paths to scrolls, continuum, resonance, attractor, basin,
        field, epoch, simulation, recovery, panoptic, etc.
      - Provide an ancestral reconstruction API.
    """

    INDEX_PATH = "memory/temple/index.json"

    def __init__(self):
        os.makedirs("memory/temple", exist_ok=True)
        if not os.path.exists(self.INDEX_PATH):
            with open(self.INDEX_PATH, "w") as f:
                json.dump({"versions": {}}, f)

    def load_index(self):
        with open(self.INDEX_PATH) as f:
            return json.load(f)

    def save_index(self, idx):
        with open(self.INDEX_PATH, "w") as f:
            json.dump(idx, f, indent=2)

    def update(self, version: str, output: Dict[str, Any]):
        idx = self.load_index()

        idx["versions"][version] = {
            "scroll":        output.get("scroll_path"),
            "continuum":     output.get("continuum", {}).get("path"),
            "attractor":     output.get("attractor", {}).get("path"),
            "basin":         output.get("basin", {}).get("path"),
            "field":         output.get("field", {}).get("field_path"),
            "wave":          output.get("simulation", {}).get("wave_path"),
            "epoch":         "memory/epoch/state.json" if os.path.exists("memory/epoch/state.json") else None,
            "recovery":      output.get("recovery", {}).get("path"),
            "panoptic":      output.get("panoptic", {}).get("path"),
            "resonance":     output.get("resonance", {}),
            "timestamp":     output.get("timestamp"),
            "metrics": {
                "score":    output.get("continuum", {}).get("score"),
                "alignment":output.get("continuum", {}).get("alignment"),
                "drift":    output.get("continuum", {}).get("drift"),
                "psi":      output.get("panoptic", {}).get("panoptic_metrics", {}).get("psi"),
            }
        }

        self.save_index(idx)

    def reconstruct(self, version: str):
        idx = self.load_index()
        if version not in idx["versions"]:
            return {"error": "version not found"}

        entry = idx["versions"][version]

        out = {
            "version": version,
            "scroll": self.safe_load(entry.get("scroll")),
            "continuum": self.safe_load(entry.get("continuum")),
            "attractor": self.safe_load(entry.get("attractor")),
            "basin": self.safe_load(entry.get("basin")),
            "field": self.safe_load(entry.get("field")),
            "wave": self.safe_load(entry.get("wave")),
            "panoptic": self.safe_load(entry.get("panoptic")),
            "epoch": self.safe_load(entry.get("epoch")),
            "recovery": self.safe_load(entry.get("recovery")),
            "resonance": entry.get("resonance"),
            "timestamp": entry.get("timestamp"),
            "metrics": entry.get("metrics")
        }

        return out

    def safe_load(self, path):
        if path and os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None
