"""The read-only galaxy graph, built only from records the CLI printed (ADR-0011 D5).

Pure functions: CLI text in, a graph out. Nothing is read from disk or the store here, nothing is
invented, and nothing changes state. Every LIVE node is one record; every link is a field that
record really carries (a task line names its project, a note's scope names its project, a result
names its task). PREVIEW nodes are labelled, never counted, and have no links.

Placement is presentation only and deterministic: a node's position comes from a hash of its own
id, so the same records always give the same picture and a test can pin it. Nearness means
nothing but state: active work sits close to its project, finished work recedes.
"""

import hashlib
import math
import re
from typing import Dict, List, Optional

TASK_LINE = re.compile(r"^(\S+) ([A-Z_]+) (L\d) (\S+)$")
PROJECT_LINE = re.compile(r"^(\S+)\s+(.+?)\s+\[([^\]]+)\]$")  # the state can hold spaces, e.g. [no root registered]
NOTE_LINE = re.compile(r"^(\d+)\s+note\s+project/(\S+)\s+(\S+)\s+(\d+) bytes")
RESULT_LINE = re.compile(r"^(\d+)\s+task (\S+)\s+(\S+)\s+(\d+) bytes")

# distance from the project, by state (presentation only)
RADIUS = {"RUNNING": 0.22, "BLOCKED": 0.32, "DEFERRED": 0.32, "COMPLETED_UNVERIFIED": 0.55,
          "FAILED": 0.62, "CANCELLED": 0.78}
DEFAULT_RADIUS = 0.5
NOTE_RADIUS = 0.42
RESULT_OFFSET = 0.12

# Later capabilities (spec sections 24 and 26): shown only as labelled PREVIEW, never counted.
PREVIEW = (("preview-memory", "Memory"), ("preview-research", "Research"), ("preview-evidence", "Evidence"))


def _unit(key: str, salt: str) -> float:
    """A stable number in [0, 1) from text."""
    digest = hashlib.sha256((salt + ":" + key).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2.0 ** 64


def _around(centre, key: str, radius: float):
    theta = _unit(key, "theta") * 2.0 * math.pi
    height = (_unit(key, "height") - 0.5) * radius * 0.9
    return (round(centre[0] + radius * math.cos(theta), 4), round(centre[1] + height, 4),
            round(centre[2] + radius * math.sin(theta), 4))


def build(project_text: str, task_text: str, note_text: str, result_text: str) -> Dict[str, object]:
    projects = [m.groups() for m in (PROJECT_LINE.match(line.strip()) for line in project_text.splitlines()) if m]
    tasks = [m.groups() for m in (TASK_LINE.match(line.strip()) for line in task_text.splitlines()) if m]
    notes = [m.groups() for m in (NOTE_LINE.match(line.strip()) for line in note_text.splitlines()) if m]
    results = [m.groups() for m in (RESULT_LINE.match(line.strip()) for line in result_text.splitlines()) if m]

    nodes: List[dict] = []
    links: List[dict] = []
    place: Dict[str, tuple] = {}
    ids = set()

    def add(node_id: str, kind: str, label: str, status: str, position, detail: Optional[str], note: str = "") -> None:
        place[node_id] = position
        ids.add(node_id)
        nodes.append({"id": node_id, "kind": kind, "label": label, "status": status,
                      "x": position[0], "y": position[1], "z": position[2], "detail": detail, "note": note})

    spread = 0.0 if len(projects) <= 1 else 0.65
    for index, (pid, name, status) in enumerate(projects):
        angle = 2.0 * math.pi * index / max(1, len(projects))
        add("project:" + pid, "project", name, status.upper(), (round(spread * math.cos(angle), 4), 0.0, round(spread * math.sin(angle), 4)),
            "project/" + pid)
    for tid, state, risk, pid in tasks:
        anchor = place.get("project:" + pid)
        if anchor is None:  # a task whose project is not listed: still a record, placed apart and not linked
            anchor = (0.0, 0.0, 0.0)
        add("task:" + tid, "task", tid, state, _around(anchor, tid, RADIUS.get(state, DEFAULT_RADIUS)), "task/" + tid, "risk " + risk)
        if "project:" + pid in ids:
            links.append({"from": "task:" + tid, "to": "project:" + pid, "why": "task belongs to project"})
    for nid, pid, recorded, size in notes:
        anchor = place.get("project:" + pid, (0.0, 0.0, 0.0))
        add("note:" + nid, "note", "note " + nid, "RECORDED", _around(anchor, "note" + nid, NOTE_RADIUS), "note/" + nid, recorded)
        if "project:" + pid in ids:
            links.append({"from": "note:" + nid, "to": "project:" + pid, "why": "note is scoped to project"})
    for rid, tid, recorded, size in results:
        anchor = place.get("task:" + tid)
        position = _around(anchor, "result" + rid, RESULT_OFFSET) if anchor else _around((0.0, 0.0, 0.0), "result" + rid, 0.9)
        # relayed results are untrusted data: metadata only, no detail route
        add("result:" + rid, "result", "result " + rid, "UNTRUSTED", position, None, "relayed text, not verified")
        if "task:" + tid in ids:
            links.append({"from": "result:" + rid, "to": "task:" + tid, "why": "result was relayed for task"})
    for index, (pid, name) in enumerate(PREVIEW):
        angle = 2.0 * math.pi * (index + 0.5) / len(PREVIEW)
        add(pid, "preview", name, "PREVIEW", (round(1.15 * math.cos(angle), 4), 0.0, round(1.15 * math.sin(angle), 4)), None,
            "later phase; not a record")

    live = [n for n in nodes if n["kind"] != "preview"]
    return {"nodes": nodes, "links": links,
            "counts": {"projects": len(projects), "tasks": len(tasks), "notes": len(notes), "results": len(results),
                       "live_nodes": len(live), "preview_nodes": len(nodes) - len(live)}}
