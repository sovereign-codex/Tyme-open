from __future__ import annotations

import time
from typing import Dict, Any

from backend.drift_monitor import DriftMonitor


class RhythmEngine:
    """
    RhythmEngine v0.1

    Determines the frequency of autonomous evolution cycles based on:
    - stability index (0–1)
    - drift anomalies
    - smoothed score trajectories

    Modes:
        * CALM     stability >= 0.85 and no drift
        * ACTIVE   stability >= 0.60
        * ALERT    stability < 0.60 or drift detected

    Output:
        {
            "mode": "CALM" | "ACTIVE" | "ALERT",
            "interval_seconds": <int>,
            "stability_index": <float>,
            "drift_count": <int>
        }
    """

    def get_rhythm(self) -> Dict[str, Any]:
        monitor = DriftMonitor()
        analysis = monitor.analyze()

        stability = analysis.get("stability_index", 0)
        drift_count = len(analysis.get("drift_flags", []))

        # Determine mode
        if stability >= 0.85 and drift_count == 0:
            mode = "CALM"
            interval = 60 * 60 * 12    # 12 hours
        elif stability >= 0.60:
            mode = "ACTIVE"
            interval = 60 * 60 * 4     # 4 hours
        else:
            mode = "ALERT"
            interval = 60 * 60 * 1     # 1 hour

        return {
            "mode": mode,
            "interval_seconds": interval,
            "stability_index": stability,
            "drift_count": drift_count,
        }
