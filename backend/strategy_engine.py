from __future__ import annotations
from typing import Dict, Any, List
import copy
import random


class StrategyEngine:
    """
    StrategyEngine v0.1

    Generates multiple candidate long-horizon evolution paths,
    evaluates them using coherence, drift, stability, and
    complexity heuristics, and selects a recommended path.

    Strategies simulated:
        - conservative
        - expansion
        - semantic_deepen
        - resonant_transform
        - entropy_reduce
    """

    def __init__(self, engine):
        self.engine = engine

    # -------------------------------
    # Strategy generators
    # -------------------------------
    def _simulate_conservative(self, spec):
        out = copy.deepcopy(spec)
        # minimal adjustments
        for l in out.get("layers", []):
            l.setdefault("notes", "")
            l["notes"] += " [C27-conservative]"
        return out

    def _simulate_expansion(self, spec):
        out = copy.deepcopy(spec)
        # add a synthetic expansion layer
        out.setdefault("layers", []).append({
            "name": f"expansion_{random.randint(1000,9999)}",
            "role": "ExpansionLayer",
            "components": ["expander"],
            "notes": "[C27-expansion]"
        })
        return out

    def _simulate_semantic_deepen(self, spec):
        out = copy.deepcopy(spec)
        for l in out.get("layers", []):
            l.setdefault("notes", "")
            l["notes"] += " [C27-semantic-deepen]"
        return out

    def _simulate_resonant_transform(self, spec):
        out = copy.deepcopy(spec)
        # transform roles
        for l in out.get("layers", []):
            l["role"] = "Resonant-" + l.get("role", "Layer")
        return out

    def _simulate_entropy_reduce(self, spec):
        out = copy.deepcopy(spec)
        # remove small/low-value layers if too many
        if len(out.get("layers", [])) > 2:
            out["layers"] = out["layers"][:-1]
        return out

    # Mapping
    STRATEGIES = {
        "conservative": _simulate_conservative,
        "expansion": _simulate_expansion,
        "semantic_deepen": _simulate_semantic_deepen,
        "resonant_transform": _simulate_resonant_transform,
        "entropy_reduce": _simulate_entropy_reduce,
    }

    # -------------------------------
    # Horizon rollout scoring
    # -------------------------------
    def rollout(self, base_spec: Dict[str, Any], horizon: int = 3) -> float:
        """
        Roll out horizon steps and score projected coherence.
        We approximate with random drift + small heuristics for now.
        """
        score = 0.0
        for i in range(horizon):
            score += 0.8 + random.random() * 0.2  # simplified placeholder
        return score / horizon

    # -------------------------------
    # Strategy selection
    # -------------------------------
    def choose(self, spec: Dict[str, Any], horizon: int = 3):
        results = {}
        for name, fn in self.STRATEGIES.items():
            simulated = fn(self, spec)
            score = self.rollout(simulated, horizon=horizon)
            results[name] = {
                "score": round(score, 4),
                "spec": simulated
            }

        # best strategy
        best = max(results.items(), key=lambda x: x[1]["score"])
        return {
            "strategies": results,
            "recommended": best[0],
            "recommended_score": best[1]["score"],
            "recommended_spec": best[1]["spec"]
        }
