from __future__ import annotations
import os, json
from typing import Dict, Any


class CommandEngine:
    """
    CommandEngine v0.1

    Interprets command strings into actionable directives.
    """

    LOG_PATH = "memory/temple/commands.json"

    def __init__(self):
        os.makedirs("memory/temple", exist_ok=True)
        if not os.path.exists(self.LOG_PATH):
            with open(self.LOG_PATH, "w") as f:
                json.dump({"commands": []}, f)

    def load_log(self):
        with open(self.LOG_PATH) as f:
            return json.load(f)

    def save_log(self, log):
        with open(self.LOG_PATH, "w") as f:
            json.dump(log, f, indent=2)

    # ---------------------------------------------------------
    # COMMAND INTERPRETATION
    # ---------------------------------------------------------
    def interpret(self, cmd: str) -> Dict[str, Any]:

        c = cmd.lower().strip()

        out = {
            "raw": cmd,
            "intent": None,
            "epoch_update": {},
            "resonance_update": {},
            "structural_update": {},
            "meta": {}
        }

        # -----------------------------
        # Harmonic modes
        # -----------------------------
        if "ascend" in c or "ascension" in c or "✶" in c or "∞" in c:
            out["intent"] = "harmonic_ascension"
            out["resonance_update"]["mode"] = "harmonic_ascension"

        if "stabilize" in c or "stability" in c or "∴" in c:
            out["intent"] = "stability_preservation"
            out["resonance_update"]["mode"] = "stability_preservation"

        if "correct" in c or "realign" in c or "⌘" in c:
            out["intent"] = "resonant_correction"
            out["resonance_update"]["mode"] = "resonant_correction"

        if "expand" in c or "growth" in c or "≈" in c:
            out["intent"] = "expansion_wave"
            out["resonance_update"]["mode"] = "expansion_wave"

        if "purify" in c or "cleanse" in c or "✦" in c:
            out["intent"] = "purification"
            out["epoch_update"]["strictness"] = 1.0

        # -----------------------------
        # Epoch directives
        # -----------------------------
        if "epoch::slow" in c:
            out["epoch_update"]["evolution_rate"] = 0.2
        if "epoch::deepen" in c:
            out["epoch_update"]["semantic_depth"] = 2
        if "epoch::freeze" in c:
            out["epoch_update"]["evolution_rate"] = 0.1
            out["epoch_update"]["strictness"] = 1.0
        if "epoch::quicken" in c:
            out["epoch_update"]["evolution_rate"] = 1.5

        # -----------------------------
        # Continuum directives
        # -----------------------------
        if "align" in c:
            out["meta"]["continuum_align"] = True
        if "heal" in c:
            out["meta"]["healing"] = True

        # -----------------------------
        # Structural intuition
        # -----------------------------
        if "prune" in c:
            out["structural_update"]["prune"] = True
        if "refine" in c:
            out["structural_update"]["refine"] = True
        if "clear" in c:
            out["structural_update"]["clear"] = True

        return out

    # ---------------------------------------------------------
    # PROCESS COMMAND
    # ---------------------------------------------------------
    def process(self, cmd: str):
        parsed = self.interpret(cmd)

        log = self.load_log()
        log["commands"].append(parsed)
        self.save_log(log)

        return parsed
