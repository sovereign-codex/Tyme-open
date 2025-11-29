from __future__ import annotations
import os
import json
import math
from typing import Dict, Any, List


class EmbeddingEngine:
    """
    EmbeddingEngine v0.1

    Creates a low- or mid-dimensional vector embedding for each
    architecture version, based on:

        - layer count
        - role set
        - component frequencies
        - lifecycle transitions
        - delta signal magnitudes
        - guardian & convergence scores
        - steering amplitude
        - epoch ID

    Embeddings are stored at:
        memory/embeddings/v{version}.json
    """

    OUTPUT_DIR = "memory/embeddings"

    def __init__(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    # ------------------------------
    # Embedding extraction
    # ------------------------------
    def make_embedding(self, version: str, spec: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:

        layers = spec.get("layers", [])
        lifecycle = spec.get("lifecycle", {})
        roles = [l.get("role", "") for l in layers]
        components = [c for l in layers for c in l.get("components", [])]

        # convert to numeric signature
        vec = []

        # layer count
        vec.append(len(layers))

        # distinct roles and components
        vec.append(len(set(roles)))
        vec.append(len(set(components)))

        # lifecycle size
        vec.append(len(lifecycle))

        # guardian & convergence
        vec.append(float(meta.get("guardian_score", 0.0)))
        vec.append(float(meta.get("convergence_score", 0.0)))

        # steering score
        vec.append(float(meta.get("steering_score", 0.0)))

        # predictive convergence
        pc = meta.get("predictive_convergence", {})
        vec.append(float(pc.get("predictive_score", 0.0)))

        # epoch number (coarse)
        epoch_id = meta.get("epoch_id", 0)
        vec.append(epoch_id)

        # small normalization
        norm = math.sqrt(sum(x*x for x in vec)) or 1
        vec = [round(x / norm, 6) for x in vec]

        path = os.path.join(self.OUTPUT_DIR, f"v{version}.json")
        with open(path, "w") as f:
            json.dump({"version": version, "vector": vec}, f, indent=2)

        return {"version": version, "vector": vec}

    # ------------------------------
    # Similarity computation
    # ------------------------------
    @staticmethod
    def cosine(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


    def load_embedding(self, version: str):
        path = os.path.join(self.OUTPUT_DIR, f"v{version}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    def list_versions(self):
        out = []
        for fn in os.listdir(self.OUTPUT_DIR):
            if fn.startswith("v") and fn.endswith(".json"):
                out.append(fn[1:-5])  # strip v + .json
        return sorted(out, key=lambda x: float(x))

    def similar(self, version: str, top: int = 5):
        target = self.load_embedding(version)
        if not target:
            return {"error": "no embedding for version"}

        target_vec = target["vector"]
        versions = self.list_versions()

        sims = []
        for v in versions:
            if v == version:
                continue
            emb = self.load_embedding(v)
            sim = self.cosine(target_vec, emb["vector"])
            sims.append((v, sim))

        sims.sort(key=lambda x: -x[1])
        sims = sims[:top]

        return {"version": version, "similar": sims}
