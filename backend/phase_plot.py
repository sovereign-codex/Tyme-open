from __future__ import annotations
import os
import json
from typing import List, Dict, Any
import numpy as np


class PhasePlotEngine:
    """
    PhasePlotEngine v0.1

    Converts high-dimensional embeddings into 2D phase coordinates using PCA.

    Output:
        phase_points:
            [
              { "version": "1", "x": 0.12, "y": -0.44 },
              { "version": "2", "x": 0.21, "y": -0.27 },
              ...
            ]

    """

    OUTPUT_DIR = "visuals/phase"

    def __init__(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def load_embeddings(self):
        from backend.embedding_engine import EmbeddingEngine
        eng = EmbeddingEngine()
        versions = eng.list_versions()

        points: List[Any] = []
        for v in versions:
            emb = eng.load_embedding(v)
            if not emb:
                continue
            points.append((v, emb["vector"]))
        return points

    def compute(self) -> Dict[str, Any]:
        points = self.load_embeddings()
        if len(points) < 2:
            return {"error": "Not enough embeddings for PCA"}

        versions = [p[0] for p in points]
        vecs = np.array([p[1] for p in points])

        # PCA via SVD
        vecs_centered = vecs - vecs.mean(axis=0)
        U, S, Vt = np.linalg.svd(vecs_centered, full_matrices=False)
        coords = U[:, :2]  # first 2 principal components

        result: List[Dict[str, Any]] = []
        for i, v in enumerate(versions):
            result.append({
                "version": v,
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1])
            })

        # Save output
        out_path = os.path.join(self.OUTPUT_DIR, "phase.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)

        return {
            "path": out_path,
            "points": result
        }
