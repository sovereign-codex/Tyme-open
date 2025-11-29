from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import numpy as np


class PanopticEngine:
    """
    PanopticEngine v0.1

    Provides:
      - Panoptic Evolution Graph (PEG)
      - Meta-Predictor (MP)
      - Panoptic Stability Index (PSI)
      - Panoptic Drift Forecast
      - Evolution Timeline Projection (ETP)

    Operates ABOVE the continuum (C36).
    """

    OUTDIR = "visuals/panoptic"
    CONTINUUM_DIR = "visuals/continuum"

    def __init__(self):
        os.makedirs(self.OUTDIR, exist_ok=True)

    def list_continuum_vectors(self) -> List[Tuple[str, Dict[str, Any]]]:
        if not os.path.exists(self.CONTINUUM_DIR):
            return []

        paths = [p for p in os.listdir(self.CONTINUUM_DIR) if p.endswith(".json")]
        versions: List[Tuple[str, Dict[str, Any]]] = []
        for path in paths:
            full_path = os.path.join(self.CONTINUUM_DIR, path)
            try:
                with open(full_path) as f:
                    data = json.load(f)
                version = path.replace("continuum-v", "").replace(".json", "")
                versions.append((version, data))
            except (OSError, json.JSONDecodeError):
                continue
        versions.sort(key=lambda x: int(x[0]))
        return versions

    def build_graph(self, versions: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Dict[str, float]]:
        graph: Dict[str, Dict[str, float]] = {}
        prev_vec = None

        for version, data in versions:
            vec = np.array(data.get("csv", []))
            if prev_vec is not None:
                delta = float(np.linalg.norm(vec - prev_vec))
            else:
                delta = 0.0

            graph[version] = {
                "delta_from_prev": delta,
                "score": data.get("score", 0),
                "alignment": data.get("alignment", 0),
                "drift": data.get("drift", 0),
            }
            prev_vec = vec

        return graph

    def predict_future(self, versions: List[Tuple[str, Dict[str, Any]]], horizon: int = 10):
        if len(versions) < 3:
            return {"error": "not enough data"}

        vecs = [np.array(data.get("csv", [])) for _, data in versions]

        # simple linear extrapolation in high-dim space
        diffs = [vecs[i] - vecs[i - 1] for i in range(1, len(vecs))]
        avg_step = np.mean(diffs, axis=0)

        future = []
        last = vecs[-1]

        for _ in range(horizon):
            last = last + avg_step
            # normalize
            last = last / (np.linalg.norm(last) or 1)
            future.append(last.tolist())

        return future

    def panoptic_metrics(self, graph: Dict[str, Dict[str, float]]):
        deltas = [g.get("delta_from_prev", 0) for g in graph.values()]
        scores = [g.get("score", 0) for g in graph.values()]
        drifts = [g.get("drift", 0) for g in graph.values()]
        aligns = [g.get("alignment", 0) for g in graph.values()]

        if not graph:
            return {"psi": 0.0, "drift_trend": 0.0, "delta_variance": 0.0}

        # Panoptic Stability Index
        psi = float(
            np.mean(scores) * 0.4 + (1 - np.mean(drifts)) * 0.3 + np.mean(aligns) * 0.3
        )

        # Drift forecast = trend of drift
        drift_trend = float(np.polyfit(range(len(drifts)), drifts, 1)[0]) if len(drifts) > 1 else 0.0

        delta_variance = float(np.var(deltas)) if deltas else 0.0

        return {"psi": psi, "drift_trend": drift_trend, "delta_variance": delta_variance}

    def process(self, version: str):
        versions = self.list_continuum_vectors()
        graph = self.build_graph(versions)
        future = self.predict_future(versions, horizon=15)
        metrics = self.panoptic_metrics(graph)

        out = {
            "graph": graph,
            "future_vectors": future,
            "panoptic_metrics": metrics,
            "versions": [v for v, _ in versions],
        }

        path = f"{self.OUTDIR}/panoptic-v{version}.json"
        with open(path, "w") as f:
            json.dump(out, f, indent=2)

        latest_path = os.path.join(self.OUTDIR, "panoptic-latest.json")
        with open(latest_path, "w") as f:
            json.dump({**out, "version": version}, f, indent=2)

        out["path"] = path
        out["latest_path"] = latest_path
        out["version"] = version
        return out
