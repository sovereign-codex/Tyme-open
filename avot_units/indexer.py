from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, List

from avot_core.protocols import BaseAVOT
from avot_core.models import AvotTask
from avot_core.registry import register_avot


INDEX_PATH = "docs/MASTER-ARCHITECTURE-INDEX.md"


@register_avot("AVOT-indexer")
class AvotIndexer(BaseAVOT):
    """
    AVOT-indexer v0.1

    Responsible for updating the Master Architecture Index (MAI)
    every time a new Sovereign Architecture scroll is added.

    Inputs:
        - version
        - filename
        - guardian_score
        - convergence_score
        - timestamp
    """

    description = "Maintains the MASTER-ARCHITECTURE-INDEX.md scroll."

    def act(self, task: AvotTask) -> Dict[str, Any]:
        payload = task.payload or {}
        version = payload.get("version", "unknown")
        filename = payload.get("filename")
        metadata = payload.get("metadata", {})

        guardian = metadata.get("guardian_score", "unknown")
        convergence = metadata.get("convergence_score", "unknown")
        timestamp = metadata.get("timestamp", "")

        # Build entry
        entry = (
            f"## Version v{version}\n"
            f"- **Filename:** `{filename}`\n"
            f"- **Guardian Score:** {guardian}\n"
            f"- **Convergence Score:** {convergence}\n"
            f"- **Timestamp:** {timestamp}\n"
            f"- **Path:** `docs/{filename}`\n"
            "\n---\n"
        )

        # Ensure docs directory exists
        os.makedirs("docs", exist_ok=True)

        # If index doesn't exist, create a header
        if not os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, "w") as f:
                f.write("# Master Architecture Index (MAI)\n")
                f.write("Autonomously maintained by AVOT-indexer.\n\n")

        # Append entry
        with open(INDEX_PATH, "a") as f:
            f.write(entry)

        return {
            "success": True,
            "index_path": INDEX_PATH,
            "version_recorded": version,
        }
