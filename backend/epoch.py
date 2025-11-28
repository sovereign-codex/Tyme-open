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
