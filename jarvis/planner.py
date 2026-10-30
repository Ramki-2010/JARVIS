"""Planner stub (ADR-0002 D1 row 5). Deterministic; no model call.

A plan is built only from the structured request recorded when the task was
created. No free text is read. Each requested capability maps to one fixed action
label. A capability with no label is not planned: the caller fails the task.

Steps run in a fixed order: reads first, then writes (ADR-0010 D4: a brief is built
from the bytes read in the same run). Within an order class, steps follow capability
name and then the request index, so the same request gives the same plan.
"""

PLAN_VERSION = 2

# capability -> (action label, order class). Only WRITE_REPORT has a side effect in
# Phase 1; READ_FILE and READ_PROJECT read inside a contract scope (ADR-0010 D3).
ACTIONS = {
    "CREATE_TASK": ("RECORD_TASK", 1),
    "CREATE_REPORT": ("WRITE_REPORT", 1),
    "READ_REGISTRY": ("LIST_REGISTRY", 1),
    "READ_CONTROL_PLANE_CONFIG": ("SHOW_CONTROL_PLANE_CONFIG", 1),
    "READ_PROJECT": ("LIST_DIRECTORY", 0),
    "READ_FILE": ("READ_FILE", 0),
}


class PlanError(ValueError):
    """Carries a fixed code, never a value."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def make_plan(request) -> dict:
    """Same request, same plan. Each step names the request it came from."""
    if not isinstance(request, dict) or not request.get("requests"):
        raise PlanError("PLAN_REQUEST_MISSING")
    entries = []
    for index, item in enumerate(request["requests"]):
        spec = ACTIONS.get(item["capability"])
        if spec is None:
            raise PlanError("PLAN_CAPABILITY_UNSUPPORTED")
        entries.append((spec[1], item["capability"], index, spec[0]))
    # One step per capability for the Phase 1 record actions; one per request for reads.
    steps, seen = [], set()
    for order, capability, index, action in sorted(entries):
        if order == 1:
            if capability in seen:
                continue
            seen.add(capability)
        step = {"n": len(steps) + 1, "capability": capability, "action": action}
        if order == 0:
            step["request"] = index  # reads name the request they act on
        steps.append(step)
    return {"plan_version": PLAN_VERSION, "steps": steps}
