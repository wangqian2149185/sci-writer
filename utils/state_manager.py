import json
from pathlib import Path

STATE_FILE = Path(__file__).parent.parent / "output" / "state.json"

DEFAULT_STATE = {
    "current_stage": 0,
    "completed_stages": [],
    "figure_order": [],
    "references": [],
    "abstract_word_count": 250,
    "merge_results_discussion": False,
    "chosen_title": "",
    "authors": [],
    "target_journal": "",
    "sections": {
        "captions": "",
        "results": "",
        "introduction": "",
        "discussion": "",
        "methods": "",
        "abstract": "",
    },
    "intro_bullets": [],
    "selected_bullets": [],
    "tone_analyzed": False,
}


def load_state() -> dict:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            data = json.load(f)
        # Merge any missing keys from DEFAULT_STATE
        for k, v in DEFAULT_STATE.items():
            if k not in data:
                data[k] = v
        return data
    return dict(DEFAULT_STATE)


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def mark_stage_complete(state: dict, stage: int) -> dict:
    if stage not in state["completed_stages"]:
        state["completed_stages"].append(stage)
    state["current_stage"] = stage + 1
    save_state(state)
    return state
