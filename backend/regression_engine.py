from __future__ import annotations
import os, json, math
from typing import Dict, Any, List


class RegressionEngine:
    """
    RegressionEngine v0.1

    Builds a dataset across architecture versions and learns a simple
    regression model to predict:

        - future coherence index
        - future convergence score
        - drift probability
        - complexity trend

    Utilizes embeddings + metadata from:
        - strategy
        - field coherence (C28)
        - scores
    """

    DATASET = "memory/regression/dataset.json"

    def __init__(self):
        os.makedirs("memory/regression", exist_ok=True)
        if not os.path.exists(self.DATASET):
            with open(self.DATASET, "w") as f:
                json.dump({"records": []}, f)

    # -------------------------
    # Add new record to dataset
    # -------------------------
    def add_record(self, version: str, embedding: Dict[str, Any], field: Dict[str, Any], strategy: Dict[str, Any], meta: Dict[str, Any]):
        with open(self.DATASET) as f:
            data = json.load(f)

        rec = {
            "version": version,
            "embedding": embedding.get("vector", []),
            "coherence": field.get("coherence_index", 0),
            "complexity": len(meta.get("spec", {}).get("layers", [])),
            "strategy_score": strategy.get("score", 0),
            "convergence": meta.get("convergence_score", 0),
            "guardian": meta.get("guardian_score", 0),
            "steering": meta.get("steering_score", 0),
        }

        data["records"].append(rec)

        with open(self.DATASET, "w") as f:
            json.dump(data, f, indent=2)

    # -------------------------
    # Simple linear regression
    # -------------------------
    def _linear_reg(self, X: List[List[float]], y: List[float]):
        # closed-form (X^T X)^(-1) X^T y, simplified pseudo-inverse
        import numpy as np  # numpy is allowed in vanilla python envs

        X = np.array(X)
        y = np.array(y)

        try:
            w = np.linalg.pinv(X).dot(y)
            return w.tolist()
        except Exception:
            return [0] * X.shape[1]

    # -------------------------
    # Train models
    # -------------------------
    def train(self):
        with open(self.DATASET) as f:
            data = json.load(f)
        recs = data["records"]

        if len(recs) < 5:
            return {"error": "not enough data to train"}

        # Build training data
        X = []
        y_coh = []
        y_conv = []
        y_comp = []

        for r in recs:
            emb = r["embedding"]
            if len(emb) == 0: continue

            X.append(emb)
            y_coh.append(r["coherence"])
            y_conv.append(r["convergence"])
            y_comp.append(r["complexity"])

        # Train models
        w_coh = self._linear_reg(X, y_coh)
        w_conv = self._linear_reg(X, y_conv)
        w_comp = self._linear_reg(X, y_comp)

        return {
            "weights_coherence": w_coh,
            "weights_convergence": w_conv,
            "weights_complexity": w_comp,
        }

    # -------------------------
    # Predict future values
    # -------------------------
    def predict(self, version: str):
        with open(self.DATASET) as f:
            data = json.load(f)

        recs = data["records"]
        recs_map = {r["version"]: r for r in recs}

        if version not in recs_map:
            return {"error": "version not in dataset"}

        current = recs_map[version]
        emb = current["embedding"]

        model = self.train()
        if "error" in model:
            return model

        import numpy as np
        v = np.array(emb)

        pred_coh = float(v.dot(model["weights_coherence"]))
        pred_conv = float(v.dot(model["weights_convergence"]))
        pred_comp = float(v.dot(model["weights_complexity"]))

        drift_probability = max(0, 1 - pred_coh)  # simple inversion

        return {
            "version": version,
            "predicted_coherence": pred_coh,
            "predicted_convergence": pred_conv,
            "predicted_complexity": pred_comp,
            "predicted_drift_probability": drift_probability,
        }
