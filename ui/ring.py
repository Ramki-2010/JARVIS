"""Status-ring state from real records only (ADR-0011 D4).

The ring is derived from the output of `task list` and `audit verify`. Nothing
here invents a state: no "thinking", no fake activity. LISTENING, SPEAKING and
INTERPRETING belong to the voice and intent layers and are never produced here.
"""

import re
from typing import Dict, List, NamedTuple

TASK_LINE = re.compile(r"^(\S+) ([A-Z_]+) (L\d) (\S+)$")


class Task(NamedTuple):
    id: str
    state: str
    risk: str
    project: str


def parse_tasks(text: str) -> List[Task]:
    return [Task(*m.groups()) for m in (TASK_LINE.match(line.strip()) for line in text.splitlines()) if m]


def derive(task_code: int, task_text: str, audit_code: int) -> Dict[str, object]:
    tasks = parse_tasks(task_text) if task_code == 0 else []
    counts: Dict[str, int] = {}
    for task in tasks:
        counts[task.state] = counts.get(task.state, 0) + 1
    if audit_code != 0:
        state, detail = "AUDIT_FAULT", "audit verify failed"
    elif task_code != 0:
        state, detail = "ERROR", "task list returned an error"
    elif counts.get("RUNNING"):
        state, detail = "RUNNING", "%d task(s) running" % counts["RUNNING"]
    elif counts.get("BLOCKED") or counts.get("DEFERRED"):
        state = "WAITING"
        detail = "%d blocked, %d deferred" % (counts.get("BLOCKED", 0), counts.get("DEFERRED", 0))
    elif tasks and tasks[-1].state in ("COMPLETED_UNVERIFIED", "CANCELLED"):
        state = "COMPLETED" if tasks[-1].state == "COMPLETED_UNVERIFIED" else "CANCELLED"
        detail = "latest task %s (not verified)" % tasks[-1].id if state == "COMPLETED" else "latest task cancelled"
    else:
        state, detail = "IDLE", "nothing in progress"
    return {"state": state, "detail": detail, "counts": counts, "tasks": len(tasks)}
