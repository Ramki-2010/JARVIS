"""Planner stub (ADR-0002 D1 row 5). Deterministic; no model call.

A plan is built only from the structured request recorded when the task was
created. No free text is read. Each requested capability maps to one fixed action
label. A capability with no label is not planned: the caller fails the task.
"""

PLAN_VERSION = 1

# Phase 1 ALLOW set only (ADR-0002 D1). Only WRITE_REPORT has a side effect.
ACTIONS = {
    "CREATE_TASK": "RECORD_TASK",
    "CREATE_REPORT": "WRITE_REPORT",
    "READ_REGISTRY": "LIST_REGISTRY",
    "READ_CONTROL_PLANE_CONFIG": "SHOW_CONTROL_PLANE_CONFIG",
}


class PlanError(ValueError):
    """Carries a fixed code, never a value."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def make_plan(request) -> dict:
    """Same request, same plan. Steps are numbered in capability order."""
    if not isinstance(request, dict) or not request.get("requests"):
        raise PlanError("PLAN_REQUEST_MISSING")
    capabilities = sorted({item["capability"] for item in request["requests"]})
    steps = []
    for number, capability in enumerate(capabilities, start=1):
        action = ACTIONS.get(capability)
        if action is None:
            raise PlanError("PLAN_CAPABILITY_UNSUPPORTED")
        steps.append({"n": number, "capability": capability, "action": action})
    return {"plan_version": PLAN_VERSION, "steps": steps}
