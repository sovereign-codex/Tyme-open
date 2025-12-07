import json
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent
EPOCH_PATH = STATE_DIR / "epoch.json"

DEFAULT_STATE = {
    "epoch": "HARMONIC",
    "cycle": 1
}

EPOCH_ORDER = [
    "INITIATION",
    "COHERENCE",
    "ASCENT",
    "CONVERGENCE",
    "HARMONIC",
    "REVERIE",
    "CONTINUUM"
]


def _load_state():
    if not EPOCH_PATH.exists():
        return DEFAULT_STATE.copy()
    try:
        with EPOCH_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return DEFAULT_STATE.copy()
            return {**DEFAULT_STATE, **data}
    except Exception:
        return DEFAULT_STATE.copy()


def _write_state(state):
    EPOCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EPOCH_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_epoch_state():
    """
    Return current epoch state as dict {epoch, cycle}
    """
    return _load_state()


def set_epoch(name: str):
    """
    Set epoch by name, preserve cycle
    """
    state = _load_state()
    name = name.upper()
    if name not in EPOCH_ORDER:
        raise ValueError(f"Unknown epoch: {name}")
    state["epoch"] = name
    _write_state(state)
    return state


def next_epoch():
    """
    Advance epoch in EPOCH_ORDER, wrap at end.
    """
    state = _load_state()
    current = state.get("epoch", DEFAULT_STATE["epoch"])
    try:
        idx = EPOCH_ORDER.index(current)
    except ValueError:
        idx = 0
    new_epoch = EPOCH_ORDER[(idx + 1) % len(EPOCH_ORDER)]
    state["epoch"] = new_epoch
    _write_state(state)
    return state


def increment_cycle():
    """
    Increment cycle counter.
    """
    state = _load_state()
    state["cycle"] = int(state.get("cycle", 1)) + 1
    _write_state(state)
    return state
