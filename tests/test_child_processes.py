"""Child-process tests: X-05, X-06, X-13b (ADR-0002 D5, ADR-0005 D2, D6, D12).

Every child is `python -m jarvis`, started by tests/harness.py under the runtime
guard. The parent test process builds fixtures in temporary directories and never
touches the real data root (ADR-0007 D7).

What the CLI can drive today. There is no task command yet, so the only write a
child can make through `python -m jarvis` is the RECOVERY record that start-up
appends when HEAD is missing or lagging (ADR-0005 D6). That is a real
BEGIN IMMEDIATE ... COMMIT write through the same code path as every later write.
X-06 is therefore covered for that write only; the task-creating variant of the
same crash needs the task command and is NOT covered here.
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
        procs = [harness.spawn_jarvis(["status"], self.cfg, sync_dir=sync) for _ in range(self.CHILDREN)]
        try:
            self._wait_until_all_ready(sync)
            open(os.path.join(sync, "go"), "w").close()
            for p in procs:
                harness.finish(p)
        finally:
            for p in procs:
                if p.poll() is None:
                    p.kill()
        verify = harness.run_jarvis(["audit", "verify"], self.cfg)
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)


class CrashRecoveryTests(ChildCase):
    """X-06 (C2): a child dies at a chosen side of the COMMIT; the next run recovers.

    Covers the RECOVERY write (an audit-only write). See the module docstring.
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

    @unittest.skip("X-06 NOT COVERED for task creation: the CLI has no task command yet, so a "
                   "crash inside a state-and-audit commit cannot be driven through "
                   "`python -m jarvis`. Only the audit-only RECOVERY write is crash-tested.")
    def test_crash_during_task_creation(self):
        """Placeholder that keeps the gap visible in every test run."""

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


if __name__ == "__main__":
    unittest.main()
