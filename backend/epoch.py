from __future__ import annotations
import os
from typing import Dict, Any
from datetime import datetime
import json


class EpochRecorder:
    """
    EpochRecorder v0.1

    Maintains a written chronicle of all evolution cycles.

    For each evolution, stores:
        - version
        - timestamp
        - guardian score
        - convergence score
        - drift count
        - healing events
        - textual summary (Tyme narrative)
        - paths to visuals & topology
    """

    LOG_PATH = "chronicle/epoch-log.md"
    EPOCH_DIR = "chronicle/epochs"

    def __init__(self):
        os.makedirs("chronicle", exist_ok=True)
        os.makedirs(self.EPOCH_DIR, exist_ok=True)
        if not os.path.exists(self.LOG_PATH):
            with open(self.LOG_PATH, "w") as f:
                f.write("# Sovereign Epoch Chronicle\n\n")

    def write_epoch(self, data: Dict[str, Any]) -> str:
        version = data.get("version")
        timestamp = datetime.utcnow().isoformat() + "Z"

        entry = []
        entry.append(f"## Epoch v{version} — {timestamp}\n")
        entry.append(f"**Guardian:** {data.get('guardian_score')}\n")
        entry.append(f"**Convergence:** {data.get('convergence_score')}\n")
        entry.append(f"**Drift Count:** {data.get('drift_count', 0)}\n")
        entry.append(f"**Healed:** {data.get('healed', False)}\n")

        entry.append("\n### Summary\n")
        entry.append(data.get("summary", "No summary provided.") + "\n")

        if "steering_score" in data:
            entry.append("\n### Steering\n")
            entry.append(f"Score: {data['steering_score']}\n")
            entry.append(f"Actions: {data.get('steering_actions',[])}\n")

        if "predictive_convergence" in data:
            pc = data["predictive_convergence"]
            entry.append("\n### Predictive Convergence Gate\n")
            entry.append(f"- Predictive Guardian: {pc.get('predictive_guardian_score')}\n")
            entry.append(f"- Predictive Convergence: {pc.get('predictive_convergence_score')}\n")
            entry.append(f"- Predictive Score: {pc.get('predictive_score')}\n")
            entry.append(f"- Threshold: {pc.get('predictive_threshold')}\n")
            entry.append(f"- Approved: {pc.get('predictive_approved')}\n")
            entry.append(f"- Recommended Action: {pc.get('recommended_action')}\n")

        if "strategy" in data:
            s = data["strategy"]
            entry.append("\n### Strategy\n")
            entry.append(f"- Recommended: {s.get('recommended')}\n")
            entry.append(f"- Score: {s.get('score')}\n")
            entry.append("Strategy Scores:\n")
            for k,v in s["strategies"].items():
                entry.append(f"  - {k}: {v['score']}\n")

        if "field" in data:
            f = data["field"]
            entry.append("\n### Field Coherence\n")
            entry.append(f"- Coherence Index: {f.get('coherence_index')}\n")
            entry.append(f"- Field Strength File: {f.get('field_path')}\n")
            entry.append(f"- Heatmap File: {f.get('heatmap_path')}\n")

        if "phase" in data:
            p = data.get("phase") or {}
            entry.append("\n### Phase Plot\n")
            if isinstance(p, dict) and p.get("path"):
                entry.append(f"- Phase Data: {p.get('path')}\n")
            entry.append("- View: /panel/phase.html\n")

        if "attractor" in data:
            a = data.get("attractor") or {}
            entry.append("\n### Attractor Forecast\n")
            forecast = a.get("attractor", {}) if isinstance(a, dict) else {}
            entry.append(f"- Type: {forecast.get('type')}\n")
            entry.append(f"- Strength: {forecast.get('strength')}\n")
            if a.get("version"):
                entry.append(f"- Version: {a.get('version')}\n")
            if a.get("path"):
                entry.append(f"- Map: {a.get('path')}\n")

        if "delta" in data:
            entry.append("\n### Structural Delta\n")
            entry.append("```")
            entry.append("\n")
            entry.append(json.dumps(data["delta"], indent=2))
            entry.append("\n```\n")

        entry.append("\n### Navigation\n")
        if "architecture_path" in data:
            entry.append(f"- [Architecture Scroll]({data['architecture_path']})\n")
        if "visuals" in data:
            entry.append(f"- [Diagram PNG]({data['visuals'].get('png','')})\n")
            entry.append(f"- [Diagram SVG]({data['visuals'].get('svg','')})\n")
        if "topology" in data:
            entry.append(f"- [Lattice Graph](/panel/lattice.html?version={version})\n")

        entry.append("\n---\n\n")

        entry_text = "".join(entry)

        # Append to main log
        with open(self.LOG_PATH, "a") as f:
            f.write(entry_text)

        # Write per-epoch file
        epoch_path = os.path.join(self.EPOCH_DIR, f"epoch-v{version}.md")
        with open(epoch_path, "w") as f:
            f.write(entry_text)

        return epoch_path
