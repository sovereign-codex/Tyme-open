from __future__ import annotations

import os, re
from typing import List, Dict, Any


INDEX_PATH = "docs/MASTER-ARCHITECTURE-INDEX.md"


class DriftMonitor:
    """
    DriftMonitor v0.1

    Responsibilities:
        - Load all architecture versions and their Guardian + Convergence scores
          from the Master Architecture Index (MAI).
        - Compute:
            * temporal coherence smoothing
            * drift deltas between consecutive versions
            * anomaly flags for sharp drops
            * stability index (0.0–1.0)
        - Return structured results for UI + governance
    """

    def load_entries(self) -> List[Dict[str, Any]]:
        if not os.path.exists(INDEX_PATH):
            return []

        with open(INDEX_PATH, "r") as f:
            text = f.read()

        blocks = re.split(r"## Version ", text)
        entries = []

        for block in blocks[1:]:
            version = re.search(r"v([0-9.]+)", block)
            guardian = re.search(r"Guardian Score:\*\* ([0-9.]+)", block)
            convergence = re.search(r"Convergence Score:\*\* ([0-9.]+)", block)
            timestamp = re.search(r"Timestamp:\*\* ([0-9.]+)", block)

            entries.append({
                "version": version.group(1) if version else "0.0",
                "guardian_score": float(guardian.group(1)) if guardian else None,
                "convergence_score": float(convergence.group(1)) if convergence else None,
                "timestamp": float(timestamp.group(1)) if timestamp else 0.0,
            })

        return entries

    def analyze(self) -> Dict[str, Any]:
        entries = self.load_entries()
        if not entries:
            return {"entries": [], "stability_index": None, "drift_flags": []}

        # Extract score lists
        guardian_scores = [e["guardian_score"] for e in entries]
        convergence_scores = [e["convergence_score"] for e in entries]

        # --- Temporal smoothing (simple moving average window=3)
        def smooth(values):
            smoothed = []
            for i in range(len(values)):
                window = values[max(0, i-1): i+2]
                smoothed.append(sum(window) / len(window))
            return smoothed

        smoothed_guardian = smooth(guardian_scores)
        smoothed_convergence = smooth(convergence_scores)

        # --- Drift detection: flag if score drop > 0.15 between versions
        drift_flags = []
        for i in range(1, len(smoothed_guardian)):
            g_drop = smoothed_guardian[i-1] - smoothed_guardian[i]
            c_drop = smoothed_convergence[i-1] - smoothed_convergence[i]
            if g_drop > 0.15 or c_drop > 0.15:
                drift_flags.append({
                    "version": entries[i]["version"],
                    "guardian_drop": round(g_drop, 3),
                    "convergence_drop": round(c_drop, 3),
                })

        # --- Stability Index = harmonic mean of smoothed scores
        import math

        def harmonic_mean(vals):
            vals = [v for v in vals if v is not None]
            if not vals:
                return 0.0
            return len(vals) / sum(1.0 / v for v in vals)

        stability_index = harmonic_mean(
            [(smoothed_guardian[i] + smoothed_convergence[i]) / 2 for i in range(len(entries))]
        )

        return {
            "entries": entries,
            "guardian_smoothed": smoothed_guardian,
            "convergence_smoothed": smoothed_convergence,
            "stability_index": round(stability_index, 3),
            "drift_flags": drift_flags,
        }
