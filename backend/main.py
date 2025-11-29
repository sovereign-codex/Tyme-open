from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from types import SimpleNamespace
from typing import Optional, Dict, Any
import os
import json

from avot_units.convergence import AvotConvergence
from avot_units.fabricator import Fabricator
from avot_units.guardian import Guardian
from avot_units.archivist import Archivist
from avot_units.pr_generator import PRGenerator
from avot_units.indexer import AvotIndexer
from backend.github_api import GitHubAPI
from backend.drift_monitor import DriftMonitor
from backend.commands import CommandEngine
from backend.epochs import EpochEngine
from backend.heatmap_analyzer import HeatmapAnalyzer
from backend.autonomous import AutonomousEvolution
from backend.rhythm import RhythmEngine
from backend.delta_engine import DeltaEngine
from backend.phase_plot import PhasePlotEngine
from backend.attractor import AttractorEngine
from backend.basin import BasinEngine
from backend.simulation import HarmonicSimEngine
from backend.continuum import ContinuumEngine
from backend.harmonic_state import HarmonicState
from backend.resonance import ResonanceEngine
from backend.epoch_tuner import EpochTuner
from backend.recovery import RecoveryEngine

app = FastAPI()
engine = SimpleNamespace(
    create_task=lambda **kwargs: SimpleNamespace(**kwargs),
    run=lambda name, task: SimpleNamespace(
        output=AvotConvergence().act(SimpleNamespace(payload=task.payload))
    ),
)

COMMAND_STATE_PATH = "memory/temple/command_state.json"


def _version_key(val: str):
    try:
        return (0, float(val))
    except ValueError:
        return (1, val)


def discover_latest_version():
    """
    Attempts to discover the latest available version across harmonic artifacts.
    """

    version_tokens = []
    patterns = [
        ("visuals/continuum", "continuum-v"),
        ("visuals/resonance", "resonance-v"),
        ("visuals/phase", "attractor-v"),
        ("visuals/phase", "basin-v"),
        ("visuals/field", "field-v"),
        (HarmonicSimEngine.OUTPUT_DIR, "wave-v"),
    ]

    for directory, prefix in patterns:
        if not os.path.exists(directory):
            continue
        for fname in os.listdir(directory):
            if fname.startswith(prefix) and fname.endswith(".json"):
                ver = fname[len(prefix) : -len(".json")]
                version_tokens.append(ver)

    if not version_tokens:
        return "latest"

    version_tokens = sorted(set(version_tokens), key=_version_key)
    return version_tokens[-1]


def load_harmonic_state(version: Optional[str] = None):
    version = version or discover_latest_version()
    harmonic_state = HarmonicState()
    state = harmonic_state.get_state(version)
    state["version"] = version
    return state


def aggregate_command_state(commands):
    state = {"resonance": {}, "epoch": {}, "structural": {}, "meta": {}}

    for entry in commands:
        if not isinstance(entry, dict):
            continue
        state["resonance"].update(entry.get("resonance_update") or {})
        state["epoch"].update(entry.get("epoch_update") or {})
        state["structural"].update(entry.get("structural_update") or {})
        state["meta"].update(entry.get("meta") or {})

    return state


def persist_command_state(state):
    os.makedirs("memory/temple", exist_ok=True)
    with open(COMMAND_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


class AutoPRRequest(BaseModel):
    title: str
    summary: str
    head: str
    base: str
    repo_owner: str
    repo_name: str
    fabrication_notes: Optional[str] = None
    token: Optional[str] = None


class ResonanceInfluenceRequest(BaseModel):
    mode: str
    params: Dict[str, Any] = {}


class EpochTuneRequest(BaseModel):
    epoch_state: Dict[str, Any] = {}
    resonance: Dict[str, Any] = {}
    field: Dict[str, Any] = {}
    attractor: Dict[str, Any] = {}
    basin: Dict[str, Any] = {}
    regression: Dict[str, Any] = {}


class RecoveryRequest(BaseModel):
    version: Optional[str] = None
    spec: Dict[str, Any] = {}
    continuum: Dict[str, Any] = {}
    resonance: Dict[str, Any] = {}
    basin: Dict[str, Any] = {}
    attractor: Dict[str, Any] = {}
    epoch: Dict[str, Any] = {}
    simulation: Dict[str, Any] = {}


class SimulationRequest(BaseModel):
    version: Optional[str] = None
    spec: Dict[str, Any] = {}
    field: Dict[str, Any] = {}
    basin: Dict[str, Any] = {}
    resonance: Dict[str, Any] = {}
    epoch: Dict[str, Any] = {}
    steps: int = 50


class CommandRequest(BaseModel):
    command: str


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/harmonic/state")
def get_harmonic_state(version: Optional[str] = None):
    """
    Aggregates harmonic artifacts for a given version to drive the navigation UI.
    """

    return load_harmonic_state(version)


@app.post("/harmonic/resonance/influence")
def influence_resonance(request: ResonanceInfluenceRequest):
    engine = ResonanceEngine()
    influenced = engine.influence_parameters(request.mode, request.params or {})

    return {
        "mode": request.mode,
        "parameters": request.params or {},
        "influenced": influenced,
        "available_modes": ResonanceEngine.MODES,
    }


@app.post("/harmonic/epoch/tune")
def tune_epoch(request: EpochTuneRequest):
    tuner = EpochTuner()
    tuned = tuner.tune(
        request.epoch_state or {},
        request.resonance or {},
        request.field or {},
        request.attractor or {},
        request.basin or {},
        request.regression or {},
    )

    return {
        "tuned": tuned,
        "mode": (request.resonance or {}).get("mode"),
    }


@app.post("/harmonic/recovery")
def harmonic_recovery(request: RecoveryRequest):
    version = request.version or discover_latest_version()
    engine = RecoveryEngine()

    result = engine.process(
        version,
        request.spec or {},
        request.continuum or {},
        request.resonance or {},
        request.basin or {},
        request.attractor or {},
        request.epoch or {},
        request.simulation or {},
    )

    result["version"] = version
    return result


@app.post("/harmonic/simulate")
def harmonic_simulate(request: SimulationRequest):
    version = request.version or discover_latest_version()
    engine = HarmonicSimEngine()
    return engine.simulate(
        version,
        request.spec or {},
        request.field or {},
        request.basin or {},
        request.resonance or {},
        request.epoch or {},
        steps=request.steps or 50,
    )


@app.get("/visuals/lattice/predictive.json")
def get_predictive_topology(version: str):
    """
    Returns the predictive topology for version+1.
    """
    path = f"visuals/lattice/predictive-topology-v{version}.json"
    if not os.path.exists(path):
        return {"error": "Predictive topology not found"}
    with open(path) as f:
        return json.load(f)


@app.post("/avot/fabricator/auto-pr")
def trigger_auto_pr(request: AutoPRRequest):
    token = request.token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token is required.")

    fabricator = Fabricator()
    scroll = fabricator.create_scroll(summary=request.summary, notes=request.fabrication_notes)
    fab_output = {"spec": {}}

    guardian = Guardian()
    try:
        guardian_result = guardian.enforce(scroll)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if guardian_result is None:
        guardian_result = SimpleNamespace(output={})

    archivist_result = SimpleNamespace(output={"metadata": {}, "artifact_path": None})
    guardian_score = guardian_result.output.get("coherence_score", 0)

    # 2.5) Convergence (multi-AVOT arbitration)
    convergence_task = engine.create_task(
        name="arbitrate-sovereign-architecture",
        payload={
            "guardian_score": guardian_score,
            "spec": fab_output.get("spec"),
            "metadata": archivist_result.output.get("metadata", {}),
        },
        created_by="api",
    )
    convergence_result = engine.run("AVOT-convergence", convergence_task)
    convergence_output = convergence_result.output

    # Inject convergence_score and approval into metadata
    archivist_result.output["metadata"]["convergence_score"] = convergence_output["convergence_score"]
    archivist_result.output["metadata"]["convergence_approved"] = convergence_output["convergence_approved"]

    archivist = Archivist()
    scroll_path = archivist.archive(scroll, title=request.title, directory="docs")
    archivist_result.output["artifact_path"] = scroll_path
    archivist_result.output["metadata"]["guardian_score"] = guardian_score
    import time
    archivist_result.output["metadata"]["agent_id"] = "AVOT-fabricator"
    archivist_result.output["metadata"]["timestamp"] = str(time.time())
    version = archivist_result.output["metadata"].get("version", "unknown")
    filename = os.path.basename(scroll_path)

    # 3) Master Architecture Index Update
    indexer_task = engine.create_task(
        name="update-master-index",
        payload={
            "version": version,
            "filename": filename,
            "metadata": archivist_result.output["metadata"],
        },
        created_by="api",
    )
    indexer_result = engine.run("AVOT-indexer", indexer_task)

    pr_generator = PRGenerator()
    payload = pr_generator.generate(
        title=request.title,
        summary=request.summary,
        head=request.head,
        base=request.base,
        scroll_path=scroll_path,
        notes=request.fabrication_notes,
    )

    github_api = GitHubAPI(token)
    try:
        pr_response = github_api.create_pull_request(
            owner=request.repo_owner,
            repo=request.repo_name,
            title=payload["title"],
            body=payload["body"],
            head=payload["head"],
            base=payload["base"],
        )
    except Exception as exc:  # pragma: no cover - external API
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "submitted",
        "scroll_path": scroll_path,
        "pull_request": pr_response,
    }


@app.get("/governance/summary")
def get_governance_summary():
    """
    Returns a JSON summary of the latest architecture update as well
    as metadata needed for the governance panel.
    """
    import os, re, json

    index_path = "docs/MASTER-ARCHITECTURE-INDEX.md"
    latest = None

    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            text = f.read()

        # Parse the most recent version block
        blocks = re.split(r"## Version ", text)
        if len(blocks) > 1:
            last = "## Version " + blocks[-1]
            # Extract components
            version = re.search(r"v([0-9.]+)", last)
            filename = re.search(r"Filename:\*\* `([^`]+)`", last)
            guard = re.search(r"Guardian Score:\*\* ([0-9.]+)", last)
            conv = re.search(r"Convergence Score:\*\* ([0-9.]+)", last)
            ts = re.search(r"Timestamp:\*\* ([0-9.]+)", last)

            latest = {
                "version": version.group(1) if version else "unknown",
                "filename": filename.group(1) if filename else "unknown",
                "guardian_score": guard.group(1) if guard else "unknown",
                "convergence_score": conv.group(1) if conv else "unknown",
                "timestamp": ts.group(1) if ts else "unknown",
                "pr_url": f"https://github.com/sovereign-codex/Tyme-open/pull"  # placeholder
            }

    return {
        "latest": latest
    }


@app.get("/governance/command")
def get_command_state():
    """
    Returns the current harmonic command log and aggregated state.
    """

    engine = CommandEngine()
    log = engine.load_log().get("commands", [])
    state = aggregate_command_state(log)
    persist_command_state(state)

    return {
        "state": state,
        "log": list(reversed(log[-20:])),
        "log_path": CommandEngine.LOG_PATH,
        "state_path": COMMAND_STATE_PATH,
    }


@app.post("/governance/command")
def dispatch_command(request: CommandRequest):
    """
    Interprets a natural-language or symbolic command and logs it to the
    Memory Temple while updating aggregated harmonic state hints.
    """

    engine = CommandEngine()
    parsed = engine.process(request.command)
    log = engine.load_log().get("commands", [])
    state = aggregate_command_state(log)
    persist_command_state(state)

    return {
        "parsed": parsed,
        "state": state,
        "log": list(reversed(log[-20:])),
        "log_path": CommandEngine.LOG_PATH,
        "state_path": COMMAND_STATE_PATH,
    }


@app.get("/governance/epoch.json")
def get_epoch_status():
    """
    Returns the current Governance Epoch and its evolution parameters.
    """
    e = EpochEngine()
    return e.get_epoch()


@app.get("/governance/evolution.json")
def get_evolution_data():
    """
    Extracts all versions and their scores from the MAI and returns
    a JSON structure suitable for plotting the architecture evolution graph.
    """

    import os, re

    index_path = "docs/MASTER-ARCHITECTURE-INDEX.md"

    versions = []
    guardian_scores = []
    convergence_scores = []

    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            text = f.read()

        blocks = re.split(r"## Version ", text)
        for block in blocks[1:]:
            version_match = re.search(r"v([0-9.]+)", block)
            guardian_match = re.search(r"Guardian Score:\*\* ([0-9.]+)", block)
            convergence_match = re.search(r"Convergence Score:\*\* ([0-9.]+)", block)

            if version_match:
                versions.append(version_match.group(1))
                guardian_scores.append(float(guardian_match.group(1)) if guardian_match else None)
                convergence_scores.append(float(convergence_match.group(1)) if convergence_match else None)

    return {
        "versions": versions,
        "guardian_scores": guardian_scores,
        "convergence_scores": convergence_scores
    }


@app.get("/governance/drift.json")
def get_drift_data():
    """
    Provides temporal coherence smoothing, drift detection,
    stability index, and full score evolution history.
    """
    monitor = DriftMonitor()
    return monitor.analyze()


@app.get("/governance/heatmap.json")
def get_heatmap_data():
    """
    Computes layer-change intensity between versions and returns
    a numeric heatmap for UI visualization.
    """
    analyzer = HeatmapAnalyzer()
    return analyzer.analyze()


@app.get("/governance/rhythm.json")
def get_rhythm_status():
    """
    Returns the current autonomous rhythm mode and pacing interval.
    """
    r = RhythmEngine()
    return r.get_rhythm()


@app.get("/governance/phase.json")
def get_phase_plot():
    """
    Returns PCA-reduced embedding coordinates for phase visualization.
    """
    engine = PhasePlotEngine()
    return engine.compute()


@app.get("/governance/attractor.json")
def get_attractor_map():
    """
    Returns the latest attractor classification using the phase history.
    """
    engine = AttractorEngine()
    points = engine.load_phase()
    if not points:
        return {"error": "Phase plot missing"}
    latest_version = str(points[-1].get("version", "unknown"))
    return engine.forecast(latest_version)


@app.get("/governance/basin.json")
def get_basin_map():
    """
    Returns the stability basin metrics for the latest version,
    computing them if missing.
    """
    basin_engine = BasinEngine()
    phase_points = basin_engine.load_phase()
    if not phase_points:
        return {"error": "Phase plot missing"}

    latest_version = str(phase_points[-1].get("version", "latest"))
    existing = basin_engine.load_basin(latest_version)
    if existing:
        return existing

    attractor_path = os.path.join(basin_engine.OUTPUT_DIR, f"attractor-v{latest_version}.json")
    field_path = os.path.join("visuals/field", f"field-v{latest_version}.json")

    attractor_data: Dict[str, Any] = {}
    if os.path.exists(attractor_path):
        with open(attractor_path) as f:
            attractor_data = json.load(f)

    if attractor_data and "attractor" not in attractor_data:
        attractor_data = {"attractor": attractor_data}

    field_data: Dict[str, Any] = {}
    if os.path.exists(field_path):
        with open(field_path) as f:
            field_data = json.load(f)

    if not field_data:
        return {"error": "Field data missing for basin computation"}

    return basin_engine.compute(latest_version, attractor_data, field_data)


@app.get("/governance/simulation.json")
def get_simulation(version: Optional[str] = None):
    """
    Returns the harmonic simulation timeline and wave summary.
    If no version is provided, the latest available simulation is served.
    """

    sim_dir = HarmonicSimEngine.OUTPUT_DIR
    if not os.path.exists(sim_dir):
        return {"error": "Simulation output missing"}

    if not version:
        versions = []
        for fname in os.listdir(sim_dir):
            if fname.startswith("sim-v") and fname.endswith(".json"):
                ver = fname[len("sim-v") : -len(".json")]
                try:
                    versions.append((float(ver), ver))
                except ValueError:
                    versions.append((ver, ver))
        if versions:
            versions.sort(key=lambda v: v[0])
            version = versions[-1][1]
        else:
            return {"error": "No simulation files found"}

    sim_path = os.path.join(sim_dir, f"sim-v{version}.json")
    wave_path = os.path.join(sim_dir, f"wave-v{version}.json")

    if not os.path.exists(sim_path):
        return {"error": f"Simulation timeline missing for v{version}"}

    with open(sim_path) as f:
        timeline = json.load(f)

    waves: Dict[str, Any] = {}
    if os.path.exists(wave_path):
        with open(wave_path) as f:
            waves = json.load(f)

    return {
        "version": version,
        "timeline": timeline,
        "waves": waves,
        "sim_path": sim_path,
        "wave_path": wave_path if os.path.exists(wave_path) else None,
        "steps": len(timeline),
    }


@app.get("/governance/continuum.json")
def get_continuum(version: Optional[str] = None):
    """
    Returns the Sovereign Continuum meta-model outputs for a given version,
    defaulting to the latest available continuum state.
    """

    output_dir = "visuals/continuum"
    if version:
        path = os.path.join(output_dir, f"continuum-v{version}.json")
        if not os.path.exists(path):
            return {"error": f"Continuum output missing for v{version}"}
    else:
        if not os.path.exists(output_dir):
            return {"error": "Continuum output missing"}

        files = [
            f for f in os.listdir(output_dir) if f.startswith("continuum-v") and f.endswith(".json")
        ]
        if not files:
            return {"error": "Continuum output missing"}

        def parse_ver(fname: str):
            ver = fname[len("continuum-v") : -len(".json")]
            try:
                return float(ver)
            except ValueError:
                return ver

        files.sort(key=parse_ver)
        latest = files[-1]
        path = os.path.join(output_dir, latest)
        version = latest[len("continuum-v") : -len(".json")]

    with open(path) as f:
        data = json.load(f)

    engine = ContinuumEngine()
    data.setdefault("identity", engine.load_identity())
    data.setdefault("version", version)
    data["path"] = path

    return data


@app.post("/autonomous/run")
def autonomous_run():
    """
    Triggers a full predictive evolution cycle.
    """
    ae = AutonomousEvolution()
    return ae.run_cycle()


@app.get("/governance/delta.json")
def get_delta(v_new: str, v_old: str):
    """
    Computes structural + semantic delta between versions.
    """
    engine = DeltaEngine()
    return engine.compute_delta(v_new, v_old)
