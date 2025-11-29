from __future__ import annotations
import os, json
from typing import Dict, Any


class HarmonicSimEngine:
    """
    HarmonicSimEngine v0.1

    Simulates resonance propagation across the lattice using:
      - field strengths (C28)
      - tension matrix (C28)
      - basin depth/escape energy (C32)
      - resonance vector/gradient (C33)
      - epoch mode (C34)

    Produces:
      - per-node coherence trajectory (time-series)
      - wave propagation map
    """

    OUTPUT_DIR = "visuals/simulation"

    def __init__(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def simulate(self, version: str, spec: Dict[str, Any], field: Dict[str, Any], basin: Dict[str,Any], resonance: Dict[str,Any], epoch: Dict[str,Any], steps: int = 50):

        layers = spec.get("layers", [])
        tension_matrix = field.get("tension_matrix", {})
        field_strengths = field.get("field_strengths", {})

        # initial resonance = normalized field strength
        state = {
            l.get("name", f"L{i}"): field_strengths.get(l.get("name", f"L{i}"), 0)
            for i, l in enumerate(layers)
        }

        # simulation params influenced by basin & epoch
        depth = basin.get("basin_depth", 0.5)
        escape_energy = basin.get("escape_energy", 0.5)
        mode = resonance.get("mode", "stability_preservation")
        epoch_mode = epoch.get("parameters", {}).get("epoch_mode", "neutral")

        # global coefficients
        alpha = 0.15 + depth * 0.1             # neighbor coupling
        beta  = 0.05 + escape_energy * 0.05     # tension damping
        gamma = 0.05                             # base resonance input

        if mode == "harmonic_ascension":
            gamma += 0.05

        if epoch_mode == "harmonic_deepening":
            alpha += 0.05

        timeline = []  # save time-series states for visualization

        for t in range(steps):
            new_state = {}

            for name in state:
                # neighbors: all other nodes
                neighbors = [n for n in state if n != name]

                if neighbors:
                    neighbor_avg = sum(state[n] for n in neighbors)/len(neighbors)
                else:
                    neighbor_avg = state[name]

                tension = 0
                if name in tension_matrix:
                    tension = sum(tension_matrix[name].values())/(len(tension_matrix[name]) or 1)

                new_state[name] = (
                    state[name]
                    + alpha * neighbor_avg
                    - beta  * tension
                    + gamma
                )

            # normalize to avoid explosion
            max_val = max(new_state.values()) or 1
            new_state = {k: v/max_val for k,v in new_state.items()}

            timeline.append(new_state)
            state = new_state

        # Save output
        sim_path = os.path.join(self.OUTPUT_DIR, f"sim-v{version}.json")
        wave_path = os.path.join(self.OUTPUT_DIR, f"wave-v{version}.json")

        with open(sim_path, "w") as f:
            json.dump(timeline, f, indent=2)

        with open(wave_path, "w") as f:
            # wave summary: amplitude variation per node
            waves = {
                node: max(ts[node] for ts in timeline)
                for node in timeline[-1]
            }
            json.dump(waves, f, indent=2)

        return {
            "sim_path": sim_path,
            "wave_path": wave_path,
            "steps": steps
        }
