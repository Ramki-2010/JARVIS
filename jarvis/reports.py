"""Reports (ADR-0002 D1 row 9; ADR-0004 D2: reports live in the data root).

Plain text built from the store. A report states what the audit chain records and
nothing more. It never says a task was verified: no Phase 1 task can be
(ADR-0002 D5, verification statement).
"""

import os

from .store import Store

REPORTS_DIR = "reports"


def render_task_report(store: Store, task_id: str) -> str:
    task = store.get_task(task_id)
    lines = ["JARVIS task report",
             "task: %s" % task["task_id"], "project: %s" % task["project"],
             "objective: %s" % task["objective"], "state: %s" % task["state"],
             "risk: %s" % task["risk_level"],
             "verification: %s (no independent verifier in Phase 1)" % task["verification"],
             "policy_version: %s" % task["policy_version"],
             "created: %s" % task["created_utc"], "updated: %s" % task["updated_utc"],
             "events:"]
    for record in store.task_history(task_id):
        detail = record.get("detail") or {}
        lines.append("  seq=%d %s %s -> %s" % (
            record["seq"], record["event"], detail.get("from"), detail.get("to")))
        for d in detail.get("decisions", ()):
            lines.append("    decision: %s %s %s %s" % (
                d["capability"], d["target"], d["verdict"], d["reason"]))
        for step in (detail.get("plan") or {}).get("steps", ()):
            lines.append("    plan step %d: %s %s" % (step["n"], step["capability"], step["action"]))
        for error in record.get("errors") or ():
            lines.append("    error: %s" % error)
    return "\n".join(lines) + "\n"


def render_summary(store: Store) -> str:
    result = store.verify()
    counts = store.count_by_state()
    lines = ["JARVIS summary report",
             "audit_tail_seq: %s" % result.tail_seq,
             "audit_chain: %s" % ("OK" if result.ok and not store.halted else "PROBLEMS"),
             "tasks: %s" % (", ".join("%s=%d" % kv for kv in sorted(counts.items())) or "none")]
    for row in store.list_tasks():
        lines.append("  %s %s %s %s" % (row["task_id"], row["state"], row["risk_level"], row["project"]))
    return "\n".join(lines) + "\n"


def write_task_report(data_root: str, task_id: str, text: str) -> str:
    """Write the report into <data_root>/reports/<task_id>.txt and return the path.
    The task id is validated by the caller (a lowercase slug). The file is written
    to a temporary name and renamed into place."""
    directory = os.path.join(data_root, REPORTS_DIR)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, task_id + ".txt")
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(temp, path)
    return path
