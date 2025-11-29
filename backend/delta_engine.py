from __future__ import annotations
import os
import json
from typing import Dict, Any


class DeltaEngine:
    """
    DeltaEngine v0.1

    Computes diffs between two architecture versions (N vs N-1).

    Analyzes:
        - layer additions/removals
        - role changes
        - component changes
        - flow/lifecycle changes
        - semantic notes
    """

    def load_spec(self, version: str) -> Dict[str, Any]:
        path = f"docs/ARCH-v{version}.md"
        if not os.path.exists(path):
            return {}
        # Specs were stored as JSON inside markdown code blocks? If not, this will
        # later be upgraded. For now we rely on .json adjacency.
        json_path = f"docs/ARCH-v{version}.json"
        if os.path.exists(json_path):
            with open(json_path) as f:
                return json.load(f)
        return {}

    def compute_delta(self, v_new: str, v_old: str) -> Dict[str, Any]:
        new = self.load_spec(v_new)
        old = self.load_spec(v_old)

        layers_new = new.get("layers", [])
        layers_old = old.get("layers", [])

        # Layer sets
        new_ids = {l.get("name") for l in layers_new}
        old_ids = {l.get("name") for l in layers_old}

        added = list(new_ids - old_ids)
        removed = list(old_ids - new_ids)
        common = list(new_ids & old_ids)

        role_changes = []
        for layer in common:
            ln = next((l for l in layers_new if l.get("name") == layer), {})
            lo = next((l for l in layers_old if l.get("name") == layer), {})
            if ln.get("role") != lo.get("role"):
                role_changes.append({
                    "layer": layer,
                    "old_role": lo.get("role"),
                    "new_role": ln.get("role")
                })

        # Flow + lifecycle changes
        lifecycle_new = new.get("lifecycle", {})
        lifecycle_old = old.get("lifecycle", {})

        lifecycle_added = []
        lifecycle_removed = []

        for k in lifecycle_new:
            if k not in lifecycle_old:
                lifecycle_added.append({k: lifecycle_new[k]})
            elif lifecycle_new[k] != lifecycle_old[k]:
                lifecycle_added.append({k: lifecycle_new[k]})
                lifecycle_removed.append({k: lifecycle_old[k]})

        for k in lifecycle_old:
            if k not in lifecycle_new:
                lifecycle_removed.append({k: lifecycle_old[k]})

        return {
            "version_new": v_new,
            "version_old": v_old,
            "layers_added": added,
            "layers_removed": removed,
            "role_changes": role_changes,
            "lifecycle_added": lifecycle_added,
            "lifecycle_removed": lifecycle_removed,
        }
