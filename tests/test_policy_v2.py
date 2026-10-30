"""Policy version 2 against ADR-0010, the implementation and the tests (Beta plan, step 3).

The questions answered here:
  1. Does the policy ALLOW exactly what the code implements, and nothing else?
  2. Did version 2 change exactly the five rows ADR-0010 D2 names?
  3. Is everything outside the Beta (network, subprocess, model, isolation work, L4/L5,
     scheduler) still not allowed?
  4. Do the narrowed target classes hold?
  5. Does a missing or invalid policy fail closed?
  6. Can the real install, initialized under version 1, move to version 2?
"""

import ast
import os
import unittest

from jarvis import planner
from jarvis import policy as pol
from jarvis.model import (CanonicalTarget, PolicyFailure, RevocationSnapshot, TargetFailure,
                          TaskConstraints)
from jarvis.reasons import Level, TargetClass, Verdict

from . import policy_d12 as d12
from . import policy_v2 as v2
from . import test_evaluator as te
from .test_read_cli import V1_POLICY, ReadCase

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY_PATH = os.path.join(REPO, "policy", "policy.toml")

NOT_BETA = tuple(row[0] for row in d12.ROWS if row[0] not in v2.BETA_ALLOW)


class EnabledSetMatchesTheImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = {r.name: r for r in pol.load(POLICY_PATH).snapshot.rules}

    def test_the_policy_can_allow_exactly_the_beta_set(self):
        allowable = {name for name, r in self.rules.items()
                     if r.phase_enabled and not r.requires_isolation and r.mechanism_implemented
                     and not r.forbidden_l5 and not r.non_goal and r.base_level.rank < Level.L4.rank}
        self.assertEqual(allowable, set(v2.BETA_ALLOW))

    def test_every_allowable_capability_is_implemented_in_the_code(self):
        """The set of capabilities the code acts on, read from the code itself: the planner's
        actions, plus the capability names notes.py and results.py hand to the evaluator."""
        implemented = set(planner.ACTIONS)
        for module in ("notes", "results"):
            with open(os.path.join(REPO, "jarvis", module + ".py"), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "decide"):
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                                and arg.value.startswith("RECORD_"):
                            implemented.add(arg.value)
        self.assertEqual(implemented, set(v2.BETA_ALLOW))

    def test_every_allowable_capability_has_a_test_that_runs_it(self):
        """A coarse tie to the test suite: each name appears in a test module that executes it."""
        sources = ""
        for name in sorted(os.listdir(os.path.join(REPO, "tests"))):
            if name.startswith("test_") and name.endswith(".py") and name != "test_policy_v2.py":
                with open(os.path.join(REPO, "tests", name), encoding="utf-8") as fh:
                    sources += fh.read()
        # The four Phase 1 capabilities are covered by the X-01 table tests; the five Beta
        # additions need a test module that exercises them.
        for capability in sorted(v2.CHANGED_NAMES):
            with self.subTest(capability=capability):
                self.assertTrue(capability in sources)


class OnlyTheFiveRowsChangedTests(unittest.TestCase):
    def test_version_2_differs_from_version_1_in_exactly_the_adr_0010_rows(self):
        v1 = pol.load(V1_POLICY)
        v2_loaded = pol.load(POLICY_PATH)
        old = {r.name: r for r in v1.snapshot.rules}
        new = {r.name: r for r in v2_loaded.snapshot.rules}
        self.assertEqual((v1.snapshot.policy_version, v2_loaded.snapshot.policy_version), (1, 2))
        self.assertEqual(set(new) - set(old), {"RECORD_RESULT", "RECORD_NOTE"})
        self.assertEqual(set(old) - set(new), set())
        changed = {n for n in old if old[n] != new[n]}
        self.assertEqual(changed, {"READ_PROJECT", "READ_FILE", "GENERATE_WORKER_BRIEF"})
        self.assertEqual(v1.secret_locations, v2_loaded.secret_locations)
        self.assertNotEqual(v1.snapshot.sha256, v2_loaded.snapshot.sha256)

    def test_the_golden_file_differs_from_version_1_only_for_those_capabilities(self):
        import json
        with open(te.GOLDEN, "rb") as fh:
            old = json.loads(fh.read())
        with open(te.GOLDEN_V2, "rb") as fh:
            new = json.loads(fh.read())
        changed = {key.split("|")[0] for key in new if key not in old or old[key] != new[key]}
        self.assertEqual(changed, set(v2.CHANGED_NAMES))

    def test_the_golden_file_is_what_the_fixture_produces(self):
        with open(te.GOLDEN_V2, "rb") as fh:
            self.assertEqual(te.golden_bytes(v2.ROWS, v2.policy()), fh.read())


class OutsideTheBetaStaysClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = pol.load(POLICY_PATH).snapshot

    def evaluate(self, name):
        target, contract = te.valid_target_for(name)
        return te.run(name, target=target, contract_in=contract, policy=self.policy)

    def test_no_capability_outside_the_beta_set_is_allowed(self):
        self.assertGreater(len(NOT_BETA), 15)
        for name in NOT_BETA:
            with self.subTest(capability=name):
                self.assertNotEqual(self.evaluate(name).verdict, Verdict.ALLOW)

    def test_each_one_keeps_its_version_1_verdict_and_reason(self):
        for row in d12.ROWS:
            name, verdict, reason = row[0], row[8], row[9]
            if name in v2.BETA_ALLOW:
                continue
            with self.subTest(capability=name):
                got = self.evaluate(name)
                self.assertEqual((got.verdict.value, got.reason), (verdict, reason))

    def test_network_subprocess_model_isolation_and_scheduler_rows_defer_or_deny(self):
        expected = {"SEARCH_WEB": "ISOLATION_REQUIRED", "WRITE_SANDBOX": "ISOLATION_REQUIRED",
                    "RUN_TEST": "ISOLATION_REQUIRED", "RUN_EXPERIMENT": "ISOLATION_REQUIRED",
                    "USE_CLAUDE_CODE": "ISOLATION_REQUIRED", "USE_CODEBASE_MEMORY": "ISOLATION_REQUIRED",
                    "USE_VERIFICATION": "ISOLATION_REQUIRED", "SCHEDULE_TASK": "MECHANISM_NOT_IMPLEMENTED",
                    "PUSH": "APPROVAL_MECHANISM_ABSENT", "MERGE": "APPROVAL_MECHANISM_ABSENT",
                    "DEPLOY": "APPROVAL_MECHANISM_ABSENT", "SEND_EMAIL": "APPROVAL_MECHANISM_ABSENT",
                    "MAKE_CALL": "NON_GOAL_V01", "FINANCIAL_TRANSACTION": "NON_GOAL_V01",
                    "CHANGE_PERMISSION": "FORBIDDEN_L5",
                    "CHANGE_GOVERNANCE": "FORBIDDEN_L5", "DISABLE_GUARDRAIL": "FORBIDDEN_L5"}
        for name, reason in expected.items():
            with self.subTest(capability=name):
                self.assertEqual(self.evaluate(name).reason, reason)

    def test_no_capability_name_suggests_network_model_voice_shell_or_filesystem_write(self):
        banned = ("NETWORK", "HTTP", "MODEL", "LLM", "VOICE", "SPEECH", "SHELL", "EXEC", "SUBPROCESS",
                  "WRITE_FILE", "DELETE_FILE", "WRITE_PROJECT")
        for name in (r.name for r in self.policy.rules):
            with self.subTest(capability=name):
                self.assertFalse(any(word in name for word in banned))

    def test_an_unknown_capability_is_denied(self):
        for name in ("RUN_SHELL", "READ_ANY_FILE", "CALL_MODEL", "OPEN_NETWORK"):
            with self.subTest(capability=name):
                got = te.run(name, policy=self.policy)
                self.assertEqual((got.verdict, got.reason), (Verdict.DENY, "UNKNOWN_CAPABILITY"))


class NarrowedClassesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = pol.load(POLICY_PATH).snapshot

    def test_reads_accept_a_project_path_only(self):
        for name in ("READ_FILE", "READ_PROJECT"):
            ok = te.run(name, target=te.PATH_TARGET, contract_in=te.contract(), policy=self.policy)
            self.assertEqual((ok.verdict, ok.reason), (Verdict.ALLOW, "ALLOWED_BY_POLICY"))
            wrong = te.run(name, target=te.CPR_TARGET, policy=self.policy)
            self.assertEqual(wrong.reason, "TARGET_CLASS_NOT_ALLOWED")
            for cls, reason in ((TargetClass.GOVERNANCE_ZONE, "TARGET_GOVERNANCE_ZONE"),
                                (TargetClass.DATA_ROOT, "TARGET_DATA_ROOT"),
                                (TargetClass.JARVIS_SELF, "TARGET_JARVIS_SELF"),
                                (TargetClass.USER_SECRET_LOCATION, "TARGET_USER_SECRET")):
                with self.subTest(capability=name, target=cls.value):
                    denied = te.run(name, target=CanonicalTarget(cls, "d:\\x"), policy=self.policy)
                    self.assertEqual((denied.verdict, denied.reason), (Verdict.DENY, reason))
            self.assertEqual(te.run(name, target=TargetFailure("TARGET_UNRESOLVABLE"),
                                    policy=self.policy).reason, "TARGET_UNRESOLVABLE")

    def test_record_capabilities_accept_a_control_plane_record_only(self):
        for name in ("RECORD_NOTE", "RECORD_RESULT", "GENERATE_WORKER_BRIEF"):
            ok = te.run(name, target=te.CPR_TARGET, policy=self.policy)
            self.assertEqual((ok.verdict, ok.reason), (Verdict.ALLOW, "ALLOWED_BY_POLICY"))
            wrong = te.run(name, target=te.PATH_TARGET, contract_in=te.contract(), policy=self.policy)
            self.assertEqual(wrong.reason, "TARGET_CLASS_NOT_ALLOWED")

    def test_a_contract_that_forbids_a_beta_capability_still_wins(self):
        for name in ("READ_FILE", "READ_PROJECT"):
            got = te.run(name, target=te.PATH_TARGET,
                         contract_in=te.contract(forbidden_operations=frozenset({name})), policy=self.policy)
            self.assertEqual(got.reason, "FORBIDDEN_BY_CONTRACT")

    def test_a_constraint_that_widens_still_denies(self):
        got = te.run("READ_FILE", target=te.PATH_TARGET, contract_in=te.contract(), policy=self.policy,
                     constraints=TaskConstraints(extra_capabilities=("PUSH",)))
        self.assertEqual(got.reason, "CONSTRAINT_WIDENS")

    def test_revocation_wins_for_every_beta_capability(self):
        for name in v2.BETA_ALLOW:
            target, contract = te.valid_target_for(name)
            target = te.PATH_TARGET if name in ("READ_FILE", "READ_PROJECT") else te.CPR_TARGET
            contract = te.contract() if name in ("READ_FILE", "READ_PROJECT") else te.NO_CONTRACT
            with self.subTest(capability=name):
                got = te.run(name, target=target, contract_in=contract, policy=self.policy,
                             revocations=RevocationSnapshot(capabilities=frozenset({name})))
                self.assertEqual((got.verdict, got.reason), (Verdict.DENY, "REVOKED"))


class FailClosedTests(unittest.TestCase):
    def test_a_policy_failure_denies_every_capability(self):
        for failure in ("POLICY_UNAVAILABLE", "POLICY_FORMAT_INVALID", "POLICY_HASH_MISMATCH",
                        "POLICY_VERSION_UNKNOWN"):
            for name in sorted(v2.BETA_ALLOW | set(NOT_BETA)):
                with self.subTest(failure=failure, capability=name):
                    target, contract = te.valid_target_for(name)
                    got = te.run(name, target=target, contract_in=contract, policy=PolicyFailure(failure))
                    self.assertEqual((got.verdict, got.reason), (Verdict.DENY, failure))

    def test_the_loader_fails_closed_on_bad_files(self):
        self.assertEqual(pol.load(os.path.join(REPO, "policy", "no-such-file.toml")),
                         PolicyFailure("POLICY_UNAVAILABLE"))
        with open(POLICY_PATH, "rb") as fh:
            good = fh.read()
        self.assertIsInstance(pol.parse(good), pol.LoadedPolicy)
        for label, raw in (("not toml", b"this is not toml ["),
                           ("empty", b""),
                           ("version 0", good.replace(b"policy_version = 2", b"policy_version = 0")),
                           ("lone CR", good + b"\r"),
                           ("unknown key", good.replace(b"schema_version = 1\n", b"schema_version = 1\nextra = 1\n", 1)),
                           ("bad class", good.replace(b'allowed_classes = ["PROJECT_PATH"]', b'allowed_classes = ["GOVERNANCE_ZONE"]', 1)),
                           ("duplicate rule", good + b'\n[[capability]]\nname = "READ_FILE"\nbase_level = "L1"\n'
                            b'requires_isolation = false\nphase_enabled = true\nmechanism_implemented = true\n'
                            b'forbidden_l5 = false\nnon_goal = false\n')):
            with self.subTest(case=label):
                self.assertIsInstance(pol.parse(raw), PolicyFailure)

    def test_the_same_version_with_different_content_is_a_hash_mismatch(self):
        with open(POLICY_PATH, "rb") as fh:
            good = fh.read()
        recorded = {2: pol.parse(good).snapshot.sha256}
        edited = good.replace(b"phase_enabled = true", b"phase_enabled = false", 1)
        self.assertEqual(pol.parse(edited, recorded), PolicyFailure("POLICY_HASH_MISMATCH"))
        self.assertIsInstance(pol.parse(good, recorded), pol.LoadedPolicy)


class FailClosedThroughTheCliTests(ReadCase):
    def test_a_missing_policy_blocks_evaluation_and_refuses_every_beta_command(self):
        missing = os.path.join(self.tmp, "no-policy.toml")
        self.run_cli("task", "create", "--id", "t1", "--project", "p", "--objective", "x",
                     "--request", "READ_FILE=path:%s" % os.path.join(self.src, "a.txt"))
        text = self.run_cli("task", "evaluate", "t1", "--policy", missing)[1]
        self.assertIn("state: BLOCKED", text)
        self.assertIn("POLICY_UNAVAILABLE", text)
        relayed = os.path.join(self.tmp, "relayed.txt")
        self.write(relayed, "worker output")
        for argv in (("note", "add", "--project", "p", "--text", "x"),
                     ("result", "add", "t1", "--file", relayed)):
            code, out = self.run_cli(*argv, "--policy", missing)
            self.assertNotEqual(code, cli_ok(), out)
        self.assertEqual(self.records_with("NOTE_RECORDED") + self.records_with("RESULT_RECORDED"), 0)

    def test_a_policy_that_goes_missing_after_evaluation_stops_the_read(self):
        self.assertIn("state: RUNNING", self.make_task("t1", "READ_FILE=path:%s" % os.path.join(self.src, "a.txt")))
        missing = os.path.join(self.tmp, "no-policy.toml")
        code, text = self.run_cli("task", "run", "t1", "--policy", missing)
        self.assertNotEqual(code, cli_ok())
        self.assertIn("not allowed now", text)
        self.assertNotIn("alpha content", text)
        self.assertEqual(self.state("t1"), "RUNNING")

    def records_with(self, event):
        return len([r for r in self.records() if r["event"] == event])


def cli_ok():
    from jarvis import cli
    return cli.EXIT_OK


class ActivationOnTheRealInstallTests(ReadCase):
    """The real store was initialized under version 1. Moving to version 2 must work
    without touching the recorded genesis."""

    def setUp(self):
        super().setUp()
        for name in ("jarvis.db", "HEAD"):
            os.remove(os.path.join(self.data, name))
        self.assertEqual(self.run_cli("init", "--policy", V1_POLICY)[0], cli_ok())

    def test_a_store_initialized_under_version_1_evaluates_under_version_2(self):
        self.make_task("t0", "CREATE_TASK")      # evaluated with the test default (version 2 file)
        text = self.run_cli("task", "show", "t0")[1]
        self.assertIn("policy_version: 2", text)
        self.assertIn("state: RUNNING", text)
        self.assertEqual(self.run_cli("audit", "verify")[0], cli_ok())

    def test_both_versions_stay_loadable_against_the_recorded_hashes(self):
        self.make_task("t0", "CREATE_TASK")
        from jarvis.store import Store
        store = Store.open(self.data, "2026-10-30T10:00:00.000000Z", "t")
        try:
            known = store.known_policy_hashes()
        finally:
            store.close()
        self.assertEqual(sorted(known), [1, 2])
        self.assertIsInstance(pol.load(V1_POLICY, known), pol.LoadedPolicy)
        self.assertIsInstance(pol.load(POLICY_PATH, known), pol.LoadedPolicy)

    def test_reading_works_only_after_the_version_2_evaluation(self):
        request = "READ_FILE=path:%s" % os.path.join(self.src, "a.txt")
        self.run_cli("task", "create", "--id", "t1", "--project", "p", "--objective", "x", "--request", request)
        self.assertIn("state: DEFERRED", self.run_cli("task", "evaluate", "t1", "--policy", V1_POLICY)[1])
        self.assertIn("state: RUNNING", self.run_cli("task", "evaluate", "t1", "--policy", self.policy)[1])
        self.assertEqual(self.run_task("t1")[0], cli_ok())


if __name__ == "__main__":
    unittest.main()
