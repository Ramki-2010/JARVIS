"""RK's approved model list (ADR-0013 D3).

The list is a governance file that RK writes and maintains; this module only
reads it and never writes it. A model that is not on the list cannot be used,
and a listed name whose server-reported digest differs is refused.

Format (TOML):

    [[model]]
    name = "qwen3.5:9b"
    runtime = "ollama"
    version = "0.40.16"
    digest = "<the digest the server reports for this model>"
    sha256 = "<model file SHA-256, for the record>"
    licence = "Apache-2.0"
"""

import os
import tomllib
from typing import Dict, List


class NotApproved(Exception):
    """The model may not be used. Conversation is off; nothing else changes."""


def load(path: str) -> List[Dict[str, str]]:
    if not os.path.isfile(path):
        raise NotApproved("no approved model list at the governance path")
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise NotApproved("the approved model list cannot be read: %s" % type(exc).__name__) from exc
    out = []
    for entry in data.get("model", []):
        if isinstance(entry, dict) and entry.get("name") and entry.get("digest"):
            out.append({k: str(v) for k, v in entry.items()})
    return out


def check(approved: List[Dict[str, str]], name: str, server_models: List[Dict[str, str]]) -> Dict[str, str]:
    """Return the approved entry for `name` if the server holds exactly that model."""
    entry = next((e for e in approved if e["name"] == name), None)
    if entry is None:
        raise NotApproved("%s is not on the approved list" % name)
    held = next((m for m in server_models if m["name"] == name), None)
    if held is None:
        raise NotApproved("%s is on the list but the model server does not hold it" % name)
    want = entry["digest"].replace("sha256:", "")
    have = held["digest"].replace("sha256:", "")
    if want != have:
        raise NotApproved("%s differs from the approved digest; refused" % name)
    return entry
