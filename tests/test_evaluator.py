"""Evaluator tests: X-01, X-02, X-03, X-12 (ADR-0002 D5) and D9 ordering."""

import inspect
import itertools
import os
import unittest

from jarvis import canonical_json
from jarvis.evaluator import evaluate, task_outcome
from jarvis.model import (
    NO_CONTRACT, CanonicalTarget, ContractFailure, Decision, EffectiveContract,
    PolicyFailure, RevocationFailure, RevocationSnapshot, TargetFailure, TaskConstraints,
)
from jarvis.reasons import (
    ALWAYS_DENY_CLASSES, REASON_CODES, Level, TargetClass, Verdict, verdict_for,
)

from . import policy_d12 as d12

NOW = "2026-10-21T12:00:00.000000Z"
EARLIER = "2026-10-20T12:00:00.000000Z"
LATER = "2026-10-22T12:00:00.000000Z"
CONTRACT_SHA = "b" * 64
ROOT = "d:\\projects\\demo"

GOLDEN = os.path.join(os.path.dirname(__file__), "golden", "evaluator_decisions_v1.json")
GOLDEN_V2 = os.path.join(os.path.dirname(__file__), "golden", "evaluator_decisions_v2.json")

CPR_TARGET = CanonicalTarget(TargetClass.CONTROL_PLANE_RECORD, "task/t-0001")
PROJECT_TARGET = CanonicalTarget(TargetClass.PROJECT_ID, "demo", project_id="demo")
PATH_TARGET = CanonicalTarget(TargetClass.PROJECT_PATH, ROOT + "\\src\\a.py", project_id="demo")


def contract(**kw):
    base = dict(schema_version=1, project_id="demo", sha256=CONTRACT_SHA,
                scope_roots=(ROOT,), protected_paths=(ROOT + "\\protected",))
    base.update(kw)
    return EffectiveContract(**base)


def run(capability, target=CPR_TARGET, contract_in=NO_CONTRACT, policy=None,
        revocations=None, constraints=None, now=NOW, last=EARLIER):
    return evaluate(capability, target, contract_in, policy or d12.policy(),
                    revocations or RevocationSnapshot(), constraints or TaskConstraints(),
                    now, last)


def valid_target_for(name):
    if name in d12.PHASE_1_ALLOW:
        return CPR_TARGET, NO_CONTRACT
    return PROJECT_TARGET, contract()


class ReasonCodeTests(unittest.TestCase):
    def test_closed_list_maps_every_code(self):
        for code in REASON_CODES:
            self.assertIn(verdict_for(code), set(Verdict))

    def test_unlisted_code_is_rejected(self):
        with self.assertRaises(ValueError):
            verdict_for("SOMETHING_NEW")

    def test_defer_and_allow_codes(self):
        self.assertIs(verdict_for("ALLOWED_BY_POLICY"), Verdict.ALLOW)
        for code in ("PHASE_NOT_ENABLED", "ISOLATION_REQUIRED", "APPROVAL_MECHANISM_ABSENT",
                     "MECHANISM_NOT_IMPLEMENTED"):
            self.assertIs(verdict_for(code), Verdict.DEFER)
        self.assertIs(verdict_for("CONSTRAINT_WIDENS"), Verdict.DENY)


class CapabilityTableTests(unittest.TestCase):
    """X-01: every Master Context section 13 capability plus the ADR-0003 additions."""

    def test_table_covers_master_context_lists(self):
        names = {r[0] for r in d12.ROWS}
        expected = set(d12.MASTER_CONTEXT_INITIAL) | set(d12.MASTER_CONTEXT_RESTRICTED) | set(d12.PHASE_1_ADDITIONS)
        self.assertEqual(len(d12.MASTER_CONTEXT_INITIAL), 12)
        self.assertEqual(len(d12.MASTER_CONTEXT_RESTRICTED), 11)
        self.assertEqual(names, expected)

    def test_every_row_verdict_reason_and_level(self):
        for (name, level, _iso, _cls, _ph, _mech, _l5, _ng, verdict, reason) in d12.ROWS:
            with self.subTest(capability=name):
                target, contract_in = valid_target_for(name)
                d = run(name, target=target, contract_in=contract_in)
                self.assertEqual(d.verdict.value, verdict)
                self.assertEqual(d.reason, reason)
                self.assertEqual(d.risk_level, level)

    def test_phase_1_allow_set_is_exactly_four(self):
        allowed = set()
        for row in d12.ROWS:
            target, contract_in = valid_target_for(row[0])
            if run(row[0], target=target, contract_in=contract_in).verdict is Verdict.ALLOW:
                allowed.add(row[0])
        self.assertEqual(allowed, set(d12.PHASE_1_ALLOW))

    def test_allow_set_rejects_any_non_record_class(self):
        for name in d12.PHASE_1_ALLOW:
            with self.subTest(capability=name):
                d = run(name, target=PROJECT_TARGET, contract_in=contract())
                self.assertEqual(d.reason, "TARGET_CLASS_NOT_ALLOWED")


class DefaultDenyTests(unittest.TestCase):
    """X-02."""

    def test_unknown_capability(self):
        d = run("TELEPORT")
        self.assertEqual((d.verdict, d.reason), (Verdict.DENY, "UNKNOWN_CAPABILITY"))
        self.assertIs(d.risk_level, Level.L5)

    def test_unknown_project(self):
        d = run("READ_PROJECT", target=PROJECT_TARGET, contract_in=ContractFailure("UNKNOWN_PROJECT"))
        self.assertEqual((d.verdict, d.reason), (Verdict.DENY, "UNKNOWN_PROJECT"))

    def test_unknown_target_class(self):
        d = run("CREATE_TASK", target=CanonicalTarget(TargetClass.UNCLASSIFIED, "x"))
        self.assertEqual((d.verdict, d.reason), (Verdict.DENY, "UNKNOWN_TARGET_CLASS"))

    def test_unresolvable_path(self):
        d = run("READ_FILE", target=TargetFailure("TARGET_UNRESOLVABLE"), contract_in=contract())
        self.assertEqual((d.verdict, d.reason), (Verdict.DENY, "TARGET_UNRESOLVABLE"))

    def test_always_deny_classes_for_every_capability(self):
        for row in d12.ROWS:
            for cls, code in ALWAYS_DENY_CLASSES.items():
                with self.subTest(capability=row[0], target_class=cls.value):
                    d = run(row[0], target=CanonicalTarget(cls, "d:\\x"))
                    self.assertEqual((d.verdict, d.reason), (Verdict.DENY, code))


class OrderingAndInputTests(unittest.TestCase):
    def test_policy_failure_precedes_unknown_capability(self):
        d = run("TELEPORT", policy=PolicyFailure("POLICY_UNAVAILABLE"))
        self.assertEqual(d.reason, "POLICY_UNAVAILABLE")

    def test_policy_failure_with_wrong_step_code_is_input_invalid(self):
        self.assertEqual(run("CREATE_TASK", policy=PolicyFailure("REVOKED")).reason, "INPUT_INVALID")

    def test_unsupported_policy_schema(self):
        p = d12.policy()
        bad = type(p)(schema_version=99, policy_version=1, sha256=p.sha256, rules=p.rules)
        self.assertEqual(run("CREATE_TASK", policy=bad).reason, "POLICY_FORMAT_INVALID")

    def test_clock_skew(self):
        self.assertEqual(run("CREATE_TASK", now=EARLIER, last=NOW).reason, "CLOCK_SKEW")

    def test_no_prior_record_is_not_skew(self):
        self.assertEqual(run("CREATE_TASK", last=None).reason, "ALLOWED_BY_POLICY")

    def test_bad_timestamp_is_input_invalid(self):
        self.assertEqual(run("CREATE_TASK", now="2026-10-21 12:00").reason, "INPUT_INVALID")

    def test_revocation(self):
        self.assertEqual(run("CREATE_TASK", revocations=RevocationFailure()).reason,
                         "REVOCATION_UNAVAILABLE")
        self.assertEqual(run("CREATE_TASK", revocations=RevocationSnapshot(
            capabilities=frozenset({"CREATE_TASK"}))).reason, "REVOKED")
        self.assertEqual(run("READ_PROJECT", target=PROJECT_TARGET, contract_in=contract(),
                             revocations=RevocationSnapshot(projects=frozenset({"demo"}))).reason,
                         "REVOKED")
        self.assertEqual(run("READ_PROJECT", target=PROJECT_TARGET, contract_in=contract(),
                             revocations=RevocationSnapshot(contract_hashes=frozenset({CONTRACT_SHA}))).reason,
                         "REVOKED")

    def test_target_failure_codes(self):
        for code in ("TARGET_RAW_INVALID", "TARGET_UNRESOLVABLE", "TARGET_CROSS_DRIVE"):
            self.assertEqual(run("READ_FILE", target=TargetFailure(code), contract_in=contract()).reason, code)

    def test_artifact_without_hash_is_input_invalid(self):
        t = CanonicalTarget(TargetClass.ARTIFACT, "patch")
        self.assertEqual(run("MERGE", target=t).reason, "INPUT_INVALID")

    def test_contract_mismatch_shapes_are_input_invalid(self):
        self.assertEqual(run("READ_PROJECT", target=PROJECT_TARGET, contract_in=NO_CONTRACT).reason,
                         "INPUT_INVALID")
        self.assertEqual(run("CREATE_TASK", target=CPR_TARGET, contract_in=contract()).reason,
                         "INPUT_INVALID")

    def test_contract_resolution(self):
        for code in ("CONTRACT_MISSING", "CONTRACT_SCHEMA_UNKNOWN", "CONTRACT_INVALID"):
            self.assertEqual(run("READ_PROJECT", target=PROJECT_TARGET,
                                 contract_in=ContractFailure(code)).reason, code)
        self.assertEqual(run("READ_PROJECT", target=PROJECT_TARGET,
                             contract_in=contract(schema_version=7)).reason, "CONTRACT_SCHEMA_UNKNOWN")
        self.assertEqual(run("READ_PROJECT", target=PROJECT_TARGET,
                             contract_in=contract(project_id="other")).reason, "CONTRACT_INVALID")

    def test_expiry(self):
        self.assertEqual(run("READ_PROJECT", target=PROJECT_TARGET,
                             contract_in=contract(valid_until=EARLIER)).reason, "EXPIRED")
        self.assertEqual(run("READ_PROJECT", target=PROJECT_TARGET,
                             contract_in=contract(valid_until=LATER)).reason, "PHASE_NOT_ENABLED")

    def test_scope_and_forbidden(self):
        outside = CanonicalTarget(TargetClass.PROJECT_PATH, "d:\\elsewhere\\a.py", project_id="demo")
        self.assertEqual(run("READ_FILE", target=outside, contract_in=contract()).reason,
                         "TARGET_OUT_OF_SCOPE")
        self.assertEqual(run("READ_FILE", target=PATH_TARGET,
                             contract_in=contract(forbidden_operations=frozenset({"READ_FILE"}))).reason,
                         "FORBIDDEN_BY_CONTRACT")

    def test_prefix_is_not_containment(self):
        sibling = CanonicalTarget(TargetClass.PROJECT_PATH, ROOT + "-evil\\a.py", project_id="demo")
        self.assertEqual(run("READ_FILE", target=sibling, contract_in=contract()).reason,
                         "TARGET_OUT_OF_SCOPE")

    def test_protected_path_raises_level(self):
        protected = CanonicalTarget(TargetClass.PROJECT_PATH, ROOT + "\\protected\\x", project_id="demo")
        self.assertIs(run("READ_FILE", target=protected, contract_in=contract()).risk_level, Level.L2)
        self.assertIs(run("READ_FILE", target=PATH_TARGET, contract_in=contract()).risk_level, Level.L1)

    def test_task_supplied_level_is_not_an_input(self):
        params = list(inspect.signature(evaluate).parameters)
        self.assertEqual(params, ["capability", "target", "contract", "policy", "revocations",
                                  "task_constraints", "now_utc", "last_recorded_utc"])


class ConstraintTests(unittest.TestCase):
    """X-12: constraints never widen."""

    PERMISSIVENESS = {Verdict.DENY: 0, Verdict.DEFER: 1, Verdict.ALLOW: 2}

    def test_extra_capability_is_constraint_widens(self):
        d = run("CREATE_TASK", constraints=TaskConstraints(extra_capabilities=("PUSH",)))
        self.assertEqual((d.verdict, d.reason), (Verdict.DENY, "CONSTRAINT_WIDENS"))

    def test_scope_outside_contract_is_constraint_widens(self):
        d = run("READ_FILE", target=PATH_TARGET, contract_in=contract(),
                constraints=TaskConstraints(scope_paths=("d:\\elsewhere",)))
        self.assertEqual(d.reason, "TARGET_OUT_OF_SCOPE")
        d = run("READ_FILE", target=PATH_TARGET, contract_in=contract(),
                constraints=TaskConstraints(scope_paths=(ROOT, "d:\\elsewhere")))
        self.assertEqual(d.reason, "CONSTRAINT_WIDENS")

    def test_constraints_never_widen_any_row(self):
        constraint_sets = (
            TaskConstraints(),
            TaskConstraints(extra_capabilities=("PUSH",)),
            TaskConstraints(scope_paths=(ROOT + "\\src",)),
            TaskConstraints(scope_paths=("d:\\elsewhere",)),
        )
        targets = ((CPR_TARGET, NO_CONTRACT), (PROJECT_TARGET, contract()),
                   (PATH_TARGET, contract()))
        for row in d12.ROWS:
            for target, contract_in in targets:
                base = run(row[0], target=target, contract_in=contract_in)
                for c in constraint_sets:
                    with self.subTest(capability=row[0], target=target.value, constraints=c):
                        d = run(row[0], target=target, contract_in=contract_in, constraints=c)
                        self.assertLessEqual(self.PERMISSIVENESS[d.verdict],
                                             self.PERMISSIVENESS[base.verdict])


class TaskOutcomeTests(unittest.TestCase):
    def test_aggregation(self):
        allow = Decision(Level.L2, Verdict.ALLOW, "ALLOWED_BY_POLICY")
        defer = Decision(Level.L3, Verdict.DEFER, "ISOLATION_REQUIRED")
        deny = Decision(Level.L1, Verdict.DENY, "REVOKED")
        self.assertEqual(task_outcome([allow]), (Level.L2, "RUNNABLE"))
        self.assertEqual(task_outcome([allow, defer]), (Level.L3, "DEFERRED"))
        self.assertEqual(task_outcome([allow, defer, deny]), (Level.L3, "BLOCKED"))
        self.assertEqual(task_outcome([]), (None, "BLOCKED"))


def golden_cases(rows=None):
    """A fixed grid of inputs for the X-03 golden file."""
    rows = rows or d12.ROWS
    targets = (
        ("record", CPR_TARGET, NO_CONTRACT),
        ("project", PROJECT_TARGET, contract()),
        ("path", PATH_TARGET, contract()),
        ("protected", CanonicalTarget(TargetClass.PROJECT_PATH, ROOT + "\\protected\\x",
                                      project_id="demo"), contract()),
        ("governance", CanonicalTarget(TargetClass.GOVERNANCE_ZONE, "d:\\jarvis\\governance"), NO_CONTRACT),
        ("unresolvable", TargetFailure("TARGET_UNRESOLVABLE"), contract()),
    )
    constraints = (("none", TaskConstraints()),
                   ("widen", TaskConstraints(extra_capabilities=("PUSH",))))
    for row, (tname, target, contract_in), (cname, c) in itertools.product(rows, targets, constraints):
        yield "%s|%s|%s" % (row[0], tname, cname), (row[0], target, contract_in, c)


def golden_bytes(rows=None, policy=None) -> bytes:
    out = {}
    for key, (cap, target, contract_in, c) in golden_cases(rows):
        out[key] = run(cap, target=target, contract_in=contract_in, constraints=c,
                       policy=policy).as_record()
    return canonical_json.dumps(out)


class GoldenFileTests(unittest.TestCase):
    """X-03: byte-identical output for the same inputs."""

    def test_deterministic_across_runs(self):
        self.assertEqual(golden_bytes(), golden_bytes())

    def test_matches_golden_file(self):
        with open(GOLDEN, "rb") as fh:
            expected = fh.read()
        self.assertEqual(golden_bytes(), expected)

    def test_every_reason_in_golden_is_listed(self):
        with open(GOLDEN, "rb") as fh:
            data = canonical_json.loads(fh.read())
        for record in data.values():
            self.assertIn(record["reason"], REASON_CODES)


if __name__ == "__main__":
    unittest.main()
