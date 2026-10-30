"""Child-process tests: X-05, X-06, X-13b (ADR-0002 D5, ADR-0005 D2, D6, D12).

Every child is `python -m jarvis`, started by tests/harness.py under the runtime
guard. The parent test process builds fixtures in temporary directories and never
touches the real data root (ADR-0007 D7).

Two kinds of write are driven through `python -m jarvis`:
- the RECOVERY record that start-up appends when HEAD is missing or lagging
  (ADR-0005 D6), an audit-only write; and
- `task create`, which writes the task row and its TASK_CREATED audit record in
  one transaction (ADR-0002 D2, ADR-0005 D1). Crash recovery is tested for both.
Both go through the same BEGIN IMMEDIATE ... COMMIT code path. Crash recovery of
`task run` (RUNNING to a terminal state) is not covered; the runtime guard is, with
the other later commands (GuardedCommandTests).
"""

import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from jarvis import canonical_json as cj
from jarvis.store import Store

from tests import harness
from tests._child import childguard

T0 = "2026-10-21T10:00:00.000000Z"
T1 = "2026-10-21T10:00:01.000000Z"
POLICIES = ((1, "a" * 64),)
ACTOR = "tester"
CRASH_EXIT = childguard.CRASH_EXIT
GUARD_EXIT = childguard.GUARD_EXIT


class ChildCase(unittest.TestCase):
    def setUp(self):
        self.new_env()

    def new_env(self):
        """A fresh temporary data root, governance zone and configuration."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.data = os.path.join(self.tmp, "data")
        self.gov = os.path.join(self.tmp, "gov")
        os.mkdir(self.data)
        os.mkdir(self.gov)
        self.cfg = harness.write_config(self.tmp, self.data, self.gov)
        self.marker_n = 0

    def marker(self):
        self.marker_n += 1
        return os.path.join(self.tmp, "guard-%d.txt" % self.marker_n)

    def make_store(self, tasks=0):
        store = Store.create(self.data, T0, ACTOR, POLICIES)
        try:
            for i in range(tasks):
                store.create_task("t%d" % i, "p", "objective", T1, ACTOR)
        finally:
            store.close()

    def head_path(self, root=None):
        return os.path.join(root or self.data, "HEAD")

    def records(self, root=None):
        conn = sqlite3.connect(Store.db_path(root or self.data))
        try:
            rows = conn.execute("SELECT seq, record, record_hash FROM audit_log ORDER BY seq").fetchall()
        finally:
            conn.close()
        return [(seq, cj.loads(rec), digest) for seq, rec, digest in rows]

    def guarded(self, args, **kw):
        marker = self.marker()
        result = harness.run_jarvis(args, self.cfg, marker=marker, **kw)
        return result, marker

    def assertGuardClean(self, marker):
        """The runtime guard was installed in the child and recorded no violation."""
        with open(marker, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("INSTALLED", text)
        self.assertNotIn("VIOLATION", text)


class RuntimeGuardDecisionTests(unittest.TestCase):
    """X-13b: the decision function, with synthetic audit events."""

    def test_forbidden_events(self):
        for event in ("socket.connect", "socket.__new__", "subprocess.Popen", "os.system",
                      "os.spawn", "os.exec", "os.posix_spawn", "ctypes.dlopen",
                      "urllib.Request", "http.client.connect", "multiprocessing.spawn"):
            with self.subTest(event=event):
                self.assertIsNotNone(childguard.violation(event, ()))

    def test_forbidden_imports(self):
        for name in ("socket", "ssl", "http.client", "urllib.request", "subprocess",
                     "multiprocessing.pool", "ctypes", "asyncio", "pickle"):
            with self.subTest(name=name):
                self.assertIsNotNone(childguard.violation("import", (name,)))

    def test_import_outside_the_standard_library(self):
        self.assertIsNotNone(childguard.violation("import", ("requests",)))
        self.assertIsNotNone(childguard.violation("import", ("probe_nonstdlib",)))

    def test_allowed(self):
        for event, args in (("import", ("sqlite3",)), ("import", ("tomllib",)),
                            ("import", ("jarvis.cli",)), ("import", ("encodings.utf_8",)),
                            ("import", ("childguard",)), ("open", ("x", "r", 0)),
                            ("sqlite3.connect", ("x",)), ("os.remove", ("x",))):
            with self.subTest(event=event, args=args):
                self.assertIsNone(childguard.violation(event, args))


class RuntimeGuardChildTests(ChildCase):
    """X-13b: the guard is installed in real children and ends them on a violation."""

    def test_clean_run_is_guarded_and_succeeds(self):
        result, marker = self.guarded(["status"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("JARVIS status", result.stdout)
        with open(marker, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("INSTALLED", text)
        self.assertNotIn("VIOLATION", text)

    def test_audit_verify_runs_under_the_guard(self):
        self.make_store()
        result, marker = self.guarded(["audit", "verify"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("audit verify: OK", result.stdout)

    def test_guard_ends_a_child_that_breaks_the_rules(self):
        for kind in ("socket", "process", "ctypes", "nonstdlib"):
            with self.subTest(kind=kind):
                result, marker = self.guarded(["status"], selftest=kind)
                self.assertEqual(result.returncode, GUARD_EXIT, result.stderr)
                self.assertIn("GUARD VIOLATION", result.stderr)
                with open(marker, encoding="utf-8") as fh:
                    self.assertIn("VIOLATION", fh.read())

    def test_a_child_without_the_guard_is_not_ended(self):
        # The self-test only fires when a marker is set, so this child is unguarded.
        result = harness.run_jarvis(["status"], self.cfg)
        self.assertEqual(result.returncode, 0, result.stderr)


class ChildEnvironmentTests(ChildCase):
    """Children get an allow-listed environment, not a copy of the parent's."""

    def test_only_allow_listed_names_and_test_settings_are_passed(self):
        parent = {"Path": "p", "SystemRoot": "C:/Windows", "TEMP": "t", "API_TOKEN": "x",
                  "CLAUDE_CODE_MESSAGING_TOKEN": "y", "GITHUB_TOKEN": "z", "USERPROFILE": "u"}
        env = harness.child_environment(parent, marker="m", crash="before_commit")
        self.assertEqual({n for n in env if n.upper() in harness.CHILD_ENV_ALLOWLIST},
                         {"SystemRoot", "TEMP"})
        for secret in ("API_TOKEN", "CLAUDE_CODE_MESSAGING_TOKEN", "GITHUB_TOKEN", "USERPROFILE", "Path"):
            self.assertNotIn(secret, env)
        self.assertEqual(env["JARVIS_TEST_CRASH"], "before_commit")
        self.assertEqual(env["JARVIS_TEST_GUARD_MARKER"], "m")
        self.assertNotIn("JARVIS_TEST_SYNC_DIR", env)

    def test_a_secret_in_the_parent_does_not_reach_the_child(self):
        dump = os.path.join(self.tmp, "child-env-names.txt")
        with mock.patch.dict(os.environ, {"JARVIS_CANARY_TOKEN": "not-a-real-secret"}):
            result = harness.run_jarvis(["status"], self.cfg, marker=self.marker(), env_dump=dump)
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(dump, encoding="utf-8") as fh:
            names = [n for n in fh.read().splitlines() if n]
        self.assertNotIn("JARVIS_CANARY_TOKEN", names)
        allowed = harness.CHILD_ENV_ALLOWLIST | {
            "PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "PYTHONIOENCODING", "JARVIS_TEST_CHILD",
            "JARVIS_TEST_GUARD_MARKER", "JARVIS_TEST_ENV_DUMP"}
        unexpected = [n for n in names if n.upper() not in allowed and not n.startswith("=")]
        self.assertEqual(unexpected, [], "unexpected variables reached the child")


class ConcurrentWriterTests(ChildCase):
    """X-05 (C1): several children write at once; the chain stays linear."""

    CHILDREN = 4

    def test_children_contend_for_the_write_lock(self):
        self.make_store(tasks=1)
        os.remove(self.head_path())  # every child now has a RECOVERY record to write
        sync = os.path.join(self.tmp, "sync")
        os.mkdir(sync)
        procs = [harness.spawn_jarvis(["status"], self.cfg, marker=self.marker(), sync_dir=sync)
                 for _ in range(self.CHILDREN)]
        try:
            self._wait_until_all_ready(sync)
            open(os.path.join(sync, "go"), "w").close()  # release them together
            results = [harness.finish(p) for p in procs]
        finally:
            for p in procs:
                if p.poll() is None:
                    p.kill()
        for r in results:
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

        records = self.records()
        self.assertEqual([seq for seq, _, _ in records], list(range(len(records))))
        prevs = [rec["prev_hash"] for _, rec, _ in records]
        self.assertEqual(len(prevs), len(set(prevs)), "two records share a predecessor")
        for (_, prev_rec, prev_digest), (_, rec, _) in zip(records, records[1:]):
            self.assertEqual(rec["prev_hash"], prev_digest)
        events = [rec["event"] for _, rec, _ in records]
        self.assertEqual(events.count("RECOVERY"), self.CHILDREN)

    def _wait_until_all_ready(self, sync):
        import time
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if len([n for n in os.listdir(sync) if n.startswith("ready.")]) >= self.CHILDREN:
                return
            time.sleep(0.02)
        self.fail("children did not all reach the write lock")

    def test_the_chain_verifies_after_the_race(self):
        self.make_store()
        os.remove(self.head_path())
        sync = os.path.join(self.tmp, "sync")
        os.mkdir(sync)
        markers = [self.marker() for _ in range(self.CHILDREN)]
        procs = [harness.spawn_jarvis(["status"], self.cfg, marker=m, sync_dir=sync) for m in markers]
        try:
            self._wait_until_all_ready(sync)
            open(os.path.join(sync, "go"), "w").close()
            for p in procs:
                harness.finish(p)
        finally:
            for p in procs:
                if p.poll() is None:
                    p.kill()
        for m in markers:
            self.assertGuardClean(m)
        verify_marker = self.marker()
        verify = harness.run_jarvis(["audit", "verify"], self.cfg, marker=verify_marker)
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        self.assertGuardClean(verify_marker)


class CrashRecoveryTests(ChildCase):
    """X-06 (C2): a child dies at a chosen side of the COMMIT; the next run recovers.

    Covers the RECOVERY write (an audit-only write). Task creation, a state-and-audit
    write, is in TaskCreationCrashTests.
    """

    def crashed_copy(self, mode, make_lag):
        self.make_store(tasks=1)
        make_lag()
        result = harness.run_jarvis(["status"], self.cfg, marker=self.marker(), crash=mode)
        self.assertEqual(result.returncode, CRASH_EXIT, result.stdout + result.stderr)
        return result

    def lagging_head(self):
        genesis = self.records()[0]
        with open(self.head_path(), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("%d %s\n" % (genesis[0], genesis[2]))

    def missing_head(self):
        os.remove(self.head_path())

    def recover_twice(self):
        """Run recovery on two byte-identical copies; return both resulting chains."""
        other = os.path.join(self.tmp, "data-copy")
        shutil.copytree(self.data, other)
        other_cfg = harness.write_config(self.tmp, other, self.gov, name="jarvis-copy.toml")
        first = harness.run_jarvis(["status"], self.cfg, marker=self.marker())
        second = harness.run_jarvis(["status"], other_cfg, marker=self.marker())
        self.assertEqual((first.returncode, second.returncode), (0, 0), first.stderr + second.stderr)
        for cfg in (self.cfg, other_cfg):
            verify = harness.run_jarvis(["audit", "verify"], cfg, marker=self.marker())
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        return self.shape(self.data), self.shape(other)

    def shape(self, root):
        """The chain without timestamps and hashes (they depend on the clock)."""
        return [(seq, rec["event"], rec.get("detail")) for seq, rec, _ in self.records(root)]

    def assert_recovery_is_identical_and_logged(self, committed_before):
        a, b = self.recover_twice()
        self.assertEqual(a, b, "recovery differs between identical runs")
        recoveries = [row for row in a if row[1] == "RECOVERY"]
        self.assertGreaterEqual(len(recoveries), committed_before + 1)
        self.assertEqual([seq for seq, _, _ in a], list(range(len(a))))

    def test_crash_before_commit_leaves_no_partial_record(self):
        self.crashed_copy("before_commit", self.lagging_head)
        events = [rec["event"] for _, rec, _ in self.records()]
        self.assertEqual(events, ["GENESIS", "TASK_CREATED"], "a record was committed")
        self.assert_recovery_is_identical_and_logged(0)

    def test_crash_after_commit_leaves_one_record_and_a_lagging_head(self):
        self.crashed_copy("after_commit", self.lagging_head)
        events = [rec["event"] for _, rec, _ in self.records()]
        self.assertEqual(events, ["GENESIS", "TASK_CREATED", "RECOVERY"])
        with open(self.head_path(), encoding="utf-8") as fh:
            self.assertEqual(fh.read().split()[0], "0", "HEAD moved although the child died")
        self.assert_recovery_is_identical_and_logged(1)

    def test_crash_with_missing_head(self):
        for mode in ("before_commit", "after_commit"):
            with self.subTest(mode=mode):
                self.new_env()
                self.crashed_copy(mode, self.missing_head)
                a, b = self.recover_twice()
                self.assertEqual(a, b)


NL = chr(10)
BS_N = NL
REVOCATIONS_TEXT = NL.join(("schema_version = 1", "capabilities = []", "projects = []", "contract_hashes = []", ""))


def create_args(task_id, project="p"):
    return ["task", "create", "--id", task_id, "--project", project, "--objective", "x",
            "--request", "CREATE_TASK"]


class TaskCreationCrashTests(ChildCase):
    """X-06 (C2) for a state-and-audit write: `task create` is killed at either side of
    its COMMIT. The task row and its audit record are committed together or not at all,
    and the next run recovers the same way every time."""

    def task_rows(self, root=None):
        conn = sqlite3.connect(Store.db_path(root or self.data))
        try:
            return conn.execute("SELECT task_id, state, last_seq FROM tasks ORDER BY task_id").fetchall()
        finally:
            conn.close()

    def head(self):
        with open(self.head_path(), encoding="utf-8") as fh:
            return fh.read().split()

    def child(self, args, **kw):
        return harness.run_jarvis(args, self.cfg, marker=self.marker(), **kw)

    def test_crash_before_commit_leaves_no_task_and_no_record(self):
        self.make_store()
        result = self.child(create_args("t1"), crash="before_commit")
        self.assertEqual(result.returncode, CRASH_EXIT, result.stdout + result.stderr)
        self.assertEqual([rec["event"] for _, rec, _ in self.records()], ["GENESIS"])
        self.assertEqual(self.task_rows(), [])
        self.assertEqual(self.head()[0], "0")
        # Nothing was half-done: the task is unknown, the chain verifies, and the same
        # command now succeeds.
        self.assertEqual(self.child(["task", "show", "t1"]).returncode, 7)
        self.assertEqual(self.child(["audit", "verify"]).returncode, 0)
        self.assertEqual(self.child(create_args("t1")).returncode, 0)
        self.assertEqual([r[1] for r in self.task_rows()], ["PENDING"])

    def test_crash_after_commit_leaves_the_task_and_its_record_together(self):
        self.make_store()
        result = self.child(create_args("t1"), crash="after_commit")
        self.assertEqual(result.returncode, CRASH_EXIT, result.stdout + result.stderr)
        events = [(seq, rec["event"]) for seq, rec, _ in self.records()]
        self.assertEqual(events, [(0, "GENESIS"), (1, "TASK_CREATED")])
        rows = self.task_rows()
        self.assertEqual([(r[0], r[1], r[2]) for r in rows], [("t1", "PENDING", 1)],
                         "the task row must point at its own audit record")
        self.assertEqual(self.head()[0], "0", "HEAD cannot have moved: the child died first")

        # Recover twice from identical copies: same chain both times, and it verifies.
        other = os.path.join(self.tmp, "data-copy")
        shutil.copytree(self.data, other)
        other_cfg = harness.write_config(self.tmp, other, self.gov, name="jarvis-copy.toml")
        first = self.child(["task", "show", "t1"])
        second = harness.run_jarvis(["task", "show", "t1"], other_cfg, marker=self.marker())
        self.assertEqual((first.returncode, second.returncode), (0, 0), first.stderr + second.stderr)
        self.assertIn("state: PENDING", first.stdout)
        shapes = [[(seq, rec["event"], rec.get("detail")) for seq, rec, _ in self.records(root)]
                  for root in (self.data, other)]
        self.assertEqual(shapes[0], shapes[1], "recovery differs between identical runs")
        self.assertIn("RECOVERY", [event for _, event, _ in shapes[0]])
        self.assertEqual(self.child(["audit", "verify"]).returncode, 0)
        # The task exists once; creating it again is refused, not duplicated.
        self.assertEqual(self.child(create_args("t1")).returncode, 7)
        self.assertEqual(len(self.task_rows()), 1)


class TaskRunCrashTests(ChildCase):
    """X-06 (C2) for `task run`, the transition RUNNING -> COMPLETED_UNVERIFIED.

    Killed at either side of the COMMIT, the task is either still RUNNING with no
    completion record (so `task run` can simply be run again), or completed once with a
    lagging HEAD that the next run repairs. Never half-completed, never completed twice."""

    def setUp(self):
        super().setUp()
        os.makedirs(self.gov, exist_ok=True)
        self.guarded(["init"])
        with open(os.path.join(self.gov, "revocations.toml"), "w", encoding="utf-8", newline=BS_N) as fh:
            fh.write(REVOCATIONS_TEXT)
        self.guarded(["task", "create", "--id", "t1", "--project", "p", "--objective", "x",
                      "--request", "CREATE_REPORT"])
        self.assertIn("state: RUNNING", self.guarded(["task", "evaluate", "t1"]).stdout)
        self.report_file = os.path.join(self.data, "reports", "t1.txt")

    def guarded(self, args, code=0, **kw):
        marker = self.marker()
        result = harness.run_jarvis(args, self.cfg, marker=marker, **kw)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertGuardClean(marker)
        return result

    def report_text(self):
        with open(self.report_file, encoding="utf-8") as fh:
            return fh.read()

    def transitions_to(self):
        return [rec["detail"]["to"] for _, rec, _ in self.records() if rec["event"] == "TASK_TRANSITION"]

    def test_crash_before_commit_leaves_the_task_running_and_it_can_be_run_again(self):
        self.guarded(["task", "run", "t1"], code=CRASH_EXIT, crash="before_commit")
        self.assertEqual(self.transitions_to(), ["RUNNING"], "a completion record was committed")
        self.assertIn("state: RUNNING", self.guarded(["task", "show", "t1"]).stdout)
        self.assertIn("audit verify: OK", self.guarded(["audit", "verify"]).stdout)
        self.assertIn("task completed: t1", self.guarded(["task", "run", "t1"]).stdout)
        self.assertEqual(self.transitions_to(), ["RUNNING", "COMPLETED_UNVERIFIED"])
        self.assertIn("state: COMPLETED_UNVERIFIED", self.report_text())
        self.assertNotIn("state: RUNNING", self.report_text())
        self.assertIn("audit verify: OK", self.guarded(["audit", "verify"]).stdout)

    def test_crash_after_commit_leaves_the_task_completed_once(self):
        self.guarded(["task", "run", "t1"], code=CRASH_EXIT, crash="after_commit")
        self.assertEqual(self.transitions_to(), ["RUNNING", "COMPLETED_UNVERIFIED"])
        self.assertIn("state: COMPLETED_UNVERIFIED", self.guarded(["task", "show", "t1"]).stdout)
        # The kill came before the file was refreshed: it is stale, and says so by its
        # as_of_seq. Asking for the report repairs it from the committed state.
        stale = self.report_text()
        self.assertIn("state: RUNNING", stale)
        self.assertIn("as_of_seq: 2", stale)
        self.assertIn("state: COMPLETED_UNVERIFIED", self.guarded(["report", "t1"]).stdout)
        fresh = self.report_text()
        self.assertIn("state: COMPLETED_UNVERIFIED", fresh)
        self.assertNotIn("state: RUNNING", fresh)
        self.assertIn("as_of_seq: 3", fresh)
        self.assertIn("audit verify: OK", self.guarded(["audit", "verify"]).stdout)
        # Running it again is refused, not repeated.
        self.assertIn("TASK_NOT_RUNNING", self.guarded(["task", "run", "t1"], code=7).stdout)
        self.assertEqual(self.transitions_to(), ["RUNNING", "COMPLETED_UNVERIFIED"])
        self.assertEqual(len([e for _, rec, _ in self.records() if (e := rec["event"]) == "RECOVERY"]), 1)


class TaskRaceTests(ChildCase):
    """X-05 (C1) for task creation: children held at the write lock and released together."""

    CHILDREN = 4

    def race(self, ids):
        self.make_store()
        sync = os.path.join(self.tmp, "sync")
        os.mkdir(sync)
        procs = [harness.spawn_jarvis(create_args(task_id), self.cfg, marker=self.marker(), sync_dir=sync)
                 for task_id in ids]
        try:
            import time
            deadline = time.monotonic() + 30
            while len([n for n in os.listdir(sync) if n.startswith("ready.")]) < len(ids):
                self.assertLess(time.monotonic(), deadline, "children did not all reach the write lock")
                time.sleep(0.02)
            open(os.path.join(sync, "go"), "w").close()
            return [harness.finish(p) for p in procs]
        finally:
            for p in procs:
                if p.poll() is None:
                    p.kill()

    def assert_linear(self):
        records = self.records()
        self.assertEqual([seq for seq, _, _ in records], list(range(len(records))))
        prevs = [rec["prev_hash"] for _, rec, _ in records]
        self.assertEqual(len(prevs), len(set(prevs)), "two records share a predecessor")
        for (_, _, prev_digest), (_, rec, _) in zip(records, records[1:]):
            self.assertEqual(rec["prev_hash"], prev_digest)
        verify = harness.run_jarvis(["audit", "verify"], self.cfg, marker=self.marker())
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)

    def test_different_tasks_created_at_once_all_succeed_in_a_linear_chain(self):
        results = self.race(["t%d" % i for i in range(self.CHILDREN)])
        self.assertEqual([r.returncode for r in results], [0] * self.CHILDREN,
                         [r.stdout + r.stderr for r in results])
        events = [rec["event"] for _, rec, _ in self.records()]
        self.assertEqual(events.count("TASK_CREATED"), self.CHILDREN)
        self.assert_linear()

    def test_the_same_task_id_created_at_once_succeeds_exactly_once(self):
        results = self.race(["same"] * self.CHILDREN)
        codes = sorted(r.returncode for r in results)
        self.assertEqual(codes, [0] + [7] * (self.CHILDREN - 1), [r.stdout + r.stderr for r in results])
        for r in results:
            if r.returncode == 7:
                self.assertIn("TASK_EXISTS", r.stdout)
        events = [rec["event"] for _, rec, _ in self.records()]
        self.assertEqual(events.count("TASK_CREATED"), 1)
        conn = sqlite3.connect(Store.db_path(self.data))
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 1)
        finally:
            conn.close()
        self.assert_linear()


class GuardedCommandTests(ChildCase):
    """X-13b for the commands added after the first child-process tests: each runs as a
    real `python -m jarvis` child under the runtime guard and records no violation.
    Registry and contract loading are reached through `task evaluate`."""

    def setUp(self):
        super().setUp()
        self.proj = os.path.join(self.tmp, "proj")
        self.src = os.path.join(self.proj, "src")
        os.makedirs(self.src)
        self.write(os.path.join(self.gov, "revocations.toml"),
                   "schema_version = 1\ncapabilities = []\nprojects = []\ncontract_hashes = []\n")
        self.write(os.path.join(self.gov, "registry.toml"),
                   "schema_version = 1\n[[projects]]\nid = \"p\"\nname = \"P\"\nroot = '%s'\n" % self.proj)
        self.contract = os.path.join(self.gov, "contracts", "p.toml")
        self.write(self.contract,
                   "schema_version = 1\nproject_id = \"p\"\nscope_roots = ['%s']\n" % self.src)

    @staticmethod
    def write(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def run_guarded(self, args, code=0):
        marker = self.marker()
        result = harness.run_jarvis(args, self.cfg, marker=marker)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertGuardClean(marker)
        return result.stdout

    def create(self, task_id, *requests, project="p"):
        args = ["task", "create", "--id", task_id, "--project", project, "--objective", "x"]
        for request in requests:
            args += ["--request", request]
        self.run_guarded(args)

    def test_init_runs_under_the_guard(self):
        self.assertIn("init: OK", self.run_guarded(["init"]))
        self.assertIn("audit verify: OK", self.run_guarded(["audit", "verify"]))
        self.assertIn("init: store already exists", self.run_guarded(["init"], code=8))

    def test_doctor_runs_under_the_guard(self):
        self.assertIn("FAIL store: not initialized", self.run_guarded(["doctor"], code=9))
        self.run_guarded(["init"])
        self.assertIn("doctor: OK (0 warning(s))", self.run_guarded(["doctor"]))

    def test_project_list_and_show_run_under_the_guard(self):
        self.assertIn("p  P  [ok]", self.run_guarded(["project", "list"]))
        self.assertIn("status: ok", self.run_guarded(["project", "show", "p"]))
        self.assertIn("PROJECT_UNKNOWN", self.run_guarded(["project", "show", "nope"], code=10))

    def test_note_commands_run_under_the_guard(self):
        from .test_notes_cli import note_policy_text
        policy = os.path.join(self.tmp, "policy-note.toml")
        self.write(policy, note_policy_text())
        self.run_guarded(["init", "--policy", policy])
        added = self.run_guarded(["note", "add", "--project", "p", "--text", "guarded note",
                                  "--policy", policy])
        seq = [line for line in added.splitlines() if line.startswith("note recorded:")][0].split()[-1]
        self.assertIn("notes: 1", self.run_guarded(["note", "list", "--project", "p"]))
        self.assertIn("guarded note", self.run_guarded(["note", "show", seq]))
        self.assertIn("PASS notes: 1 recorded", self.run_guarded(["doctor", "--policy", policy]))
        self.assertIn("audit verify: OK", self.run_guarded(["audit", "verify"]))

    def test_resume_runs_under_the_guard(self):
        self.run_guarded(["init"])
        self.create("t1", "CREATE_TASK")
        text = self.run_guarded(["resume", "--project", "p"])
        self.assertIn("audit: OK", text)
        self.assertIn("t1  PENDING", text)

    def test_bounded_reading_runs_under_the_guard(self):
        from .test_read_cli import read_policy_text
        policy = os.path.join(self.tmp, "policy-read.toml")
        self.write(policy, read_policy_text())
        sample = os.path.join(self.src, "a.txt")
        self.write(sample, "guarded read")
        self.run_guarded(["init", "--policy", policy])
        self.create("t1", "READ_FILE=path:%s" % sample, "READ_PROJECT=path:%s" % self.src)
        self.assertIn("state: RUNNING", self.run_guarded(["task", "evaluate", "t1", "--policy", policy]))
        text = self.run_guarded(["task", "run", "t1", "--policy", policy, "--show-reads"])
        self.assertIn("guarded read", text)
        self.assertIn("task completed: t1", text)
        self.assertIn("audit verify: OK", self.run_guarded(["audit", "verify"]))

    def test_brief_generation_runs_under_the_guard(self):
        from .test_brief_cli import brief_policy_text
        policy = os.path.join(self.tmp, "policy-brief.toml")
        self.write(policy, brief_policy_text())
        sample = os.path.join(self.src, "a.txt")
        self.write(sample, "brief source")
        self.run_guarded(["init", "--policy", policy])
        self.create("t1", "READ_FILE=path:%s" % sample, "GENERATE_WORKER_BRIEF")
        self.run_guarded(["task", "evaluate", "t1", "--policy", policy])
        self.assertIn("brief: ", self.run_guarded(["task", "run", "t1", "--policy", policy]))
        self.assertIn("| brief source", self.run_guarded(["brief", "show", "t1"]))
        self.assertIn("PASS briefs: all match the chain", self.run_guarded(["doctor", "--policy", policy]))

    def test_task_evaluate_run_and_report_run_under_the_guard(self):
        self.run_guarded(["init"])
        self.create("t1", "CREATE_TASK", "CREATE_REPORT")
        self.assertIn("state: RUNNING", self.run_guarded(["task", "evaluate", "t1"]))
        self.assertIn("task completed: t1", self.run_guarded(["task", "run", "t1"]))
        self.assertIn("state: COMPLETED_UNVERIFIED", self.run_guarded(["report", "t1"]))
        self.assertIn("COMPLETED_UNVERIFIED=1", self.run_guarded(["report"]))
        self.assertTrue(os.path.isfile(os.path.join(self.data, "reports", "t1.txt")))
        self.assertIn("audit verify: OK", self.run_guarded(["audit", "verify"]))

    def test_registry_and_contract_loaders_run_under_the_guard(self):
        """READ_FILE inside the contract scope reaches PHASE_NOT_ENABLED only if the
        registry and the contract were both loaded and accepted in the child."""
        self.run_guarded(["init"])
        self.create("t2", "READ_FILE=path:%s" % self.src)
        self.assertIn("PHASE_NOT_ENABLED", self.run_guarded(["task", "evaluate", "t2"]))
        # An invalid contract and a missing registry are loaded, and denied, under the guard.
        self.write(self.contract, "not a contract [")
        self.create("t3", "READ_FILE=path:%s" % self.src)
        self.assertIn("CONTRACT_INVALID", self.run_guarded(["task", "evaluate", "t3"]))
        os.remove(os.path.join(self.gov, "registry.toml"))
        self.create("t4", "READ_FILE=path:%s" % self.src)
        self.assertNotIn("PHASE_NOT_ENABLED", self.run_guarded(["task", "evaluate", "t4"]))


if __name__ == "__main__":
    unittest.main()
