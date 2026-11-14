"""Read the live voice signal for the ring (ADR-0012 D3 item 5, ADR-0011 D4). Read-only; invents nothing.

A state counts only if the file is small, well formed, names a known state and is fresh. Anything else is IDLE, so a
missing, damaged or stale file can never make the ring say LISTENING or SPEAKING.
"""

import json
import os
import time

STALE_S = 3.0
MAX_BYTES = 512
STATES = ("LISTENING", "SPEAKING")


def default_path(config: str) -> str:
    """The voice folder sits next to the governance folder (install/governance/jarvis.toml gives install/voice)."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(config))), "voice", "state", "voice_state.json")


def read(path: str, now=time.time) -> dict:
    idle = {"state": "IDLE"}
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return idle
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        state, at = data.get("state"), data.get("at")
        if state not in STATES or isinstance(at, bool) or not isinstance(at, (int, float)):
            return idle
        age = now() - float(at)
        if age < -2.0 or age > STALE_S:
            return idle
        return {"state": state}
    except (OSError, ValueError, AttributeError):
        return idle
