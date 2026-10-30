"""Task-driven reading through cli.main (ADR-0010 D3, acceptance B-04).

Policy version 1 keeps READ_FILE and READ_PROJECT at DEFER (policy version 2 is a later,
separate change), so these tests use a test policy: the real file with those two rows
enabled and narrowed to PROJECT_PATH as ADR-0010 D2 describes. Temporary directories
only; nothing operational is touched.
"""

import io
import json
import os
import re
import sqlite3
import tempfile
import unittest
from unittest import mock

from jarvis import cli
from jarvis.store import Store

from .test_reading import make_junction

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_POLICY = os.path.join(REPO, "policy", "policy.toml")
NOW = "2026-10-30T10:00:00.000000Z"
V1_POLICY = os.path.join(REPO, "tests", "golden", "policy_v1.toml")


def read_policy_text():
    """The real policy (version 2) already enables what this feature needs."""
    with open(REAL_POLICY, "r", encoding="utf-8") as fh:
        return fh.read()

class ReadCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.data, self.gov, self.home = (os.path.join(self.tmp, d) for d in ("data", "gov", "home"))
        self.proj = os.path.join(self.tmp, "proj")
        self.src = os.path.join(self.proj, "src")
        self.guarded = os.path.join(self.src, "protected")
        self.outside = os.path.join(self.proj, "outside")
        for d in (self.data, self.gov, self.home, self.src, self.guarded, self.outside,
                  os.path.join(self.home, ".ssh")):
            os.makedirs(d)
        self.cfg = os.path.join(self.tmp, "jarvis-test.toml")
        self.write(self.cfg, "schema_version = 1\ndata_root = '%s'\ngovernance_zone = '%s'\n"
                   "user_home = '%s'\n" % (self.data, self.gov, self.home))
        self.policy = os.path.join(self.tmp, "policy-read.toml")
        self.write(self.policy, self.policy_text())
        self.revocations = os.path.join(self.gov, "revocations.toml")
        self.write(self.revocations,
                   "schema_version = 1\ncapabilities = []\nprojects = []\ncontract_hashes = []\n")
        self.write(os.path.join(self.gov, "registry.toml"),
                   "schema_version = 1\n[[projects]]\nid = \"p\"\nname = \"P\"\nroot = '%s'\n" % self.proj)
        self.write(os.path.join(self.gov, "contracts", "p.toml"),
                   "schema_version = 1\nproject_id = \"p\"\nscope_roots = ['%s']\n"
                   "protected_paths = ['%s']\n" % (self.src, self.guarded))
        self.write(os.path.join(self.src, "a.txt"), "alpha content\nline two\n")
        self.write(os.path.join(self.guarded, "p.txt"), "protected but readable\n")
        self.write(os.path.join(self.outside, "o.txt"), "outside the scope\n")
        self.write(os.path.join(self.home, ".ssh", "id"), "private\n")
        patcher = mock.patch.object(cli, "utc_now", lambda: NOW)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.assertEqual(self.run_cli("init", "--policy", self.policy)[0], cli.EXIT_OK)

    def policy_text(self):
        return read_policy_text()

    @staticmethod
    def write(path, text, binary=False):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8", "newline": "\n"})) as fh:
            fh.write(text)

    def run_cli(self, *argv):
        out = io.StringIO()
        code = cli.main(["--config", self.cfg] + list(argv), out)
        return code, out.getvalue()

    def make_task(self, task_id, *requests):
        args = ["task", "create", "--id", task_id, "--project", "p", "--objective", "read things"]
        for request in requests:
            args += ["--request", request]
        self.assertEqual(self.run_cli(*args)[0], cli.EXIT_OK)
        return self.run_cli("task", "evaluate", task_id, "--policy", self.policy)[1]

    def run_task(self, task_id, *extra):
        return self.run_cli("task", "run", task_id, "--policy", self.policy, *extra)

    def records(self):
        conn = sqlite3.connect(Store.db_path(self.data))
        try:
            return [json.loads(r[0]) for r in conn.execute("SELECT record FROM audit_log ORDER BY seq")]
        finally:
            conn.close()

    def state(self, task_id):
        store = Store.open(self.data, NOW, "t")
        try:
            return store.get_task(task_id)["state"]
        finally:
            store.close()


class AllowedReadTests(ReadCase):
    def test_a_file_inside_the_scope_is_read_audited_and_shown_only_on_request(self):
        path = os.path.join(self.src, "a.txt")
        self.assertIn("state: RUNNING", self.make_task("t1", "READ_FILE=path:%s" % path))
        code, text = self.run_task("t1")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("bytes_read: 23 of 23", text)
        self.assertNotIn("alpha content", text, "content is shown only with --show-reads")
        record = [r for r in self.records() if r["event"] == "TASK_TRANSITION"][-1]
        (entry,) = record["files_read"]
        self.assertEqual(entry["truncated"], False)
        self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(record["provenance"]["files_read"], "MEDIATED")
        self.assertNotIn("alpha content", json.dumps(record), "the text never enters the chain")
        self.assertIn("audit verify: OK", self.run_cli("audit", "verify")[1])

    def test_show_reads_prints_the_content_labelled_as_data(self):
        self.make_task("t1", "READ_FILE=path:%s" % os.path.join(self.src, "a.txt"))
        code, text = self.run_task("t1", "--show-reads")
        self.assertIn("file content (data, not instruction):\nalpha content\nline two\n", text)

    def test_control_characters_in_a_file_are_escaped_on_display(self):
        self.write(os.path.join(self.src, "ansi.txt"), "red \x1b[31mtext\x07 bell\n")
        self.make_task("t1", "READ_FILE=path:%s" % os.path.join(self.src, "ansi.txt"))
        code, text = self.run_task("t1", "--show-reads")
        self.assertNotIn("\x1b", text)
        self.assertNotIn("\x07", text)
        self.assertIn("red \\x1b[31mtext\\x07 bell", text)

    def test_a_protected_path_is_readable_at_a_raised_level_not_denied(self):
        state = self.make_task("t1", "READ_FILE=path:%s" % os.path.join(self.guarded, "p.txt"))
        self.assertIn("state: RUNNING", state)
        self.assertIn("risk: L2", state)
        self.assertEqual(self.run_task("t1", "--show-reads")[0], cli.EXIT_OK)

    def test_a_directory_listing(self):
        self.make_task("t1", "READ_PROJECT=path:%s" % self.src)
        code, text = self.run_task("t1", "--show-reads")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("entries: 2", text)
        self.assertIn("  file  a.txt", text)
        self.assertIn("  dir  protected", text)
        record = [r for r in self.records() if r["event"] == "TASK_TRANSITION"][-1]
        self.assertEqual(record["files_read"][0]["entries"], 2)

    def test_an_over_size_file_is_truncated_and_marked(self):
        self.write(os.path.join(self.src, "big.txt"), "x" * 70000)
        self.make_task("t1", "READ_FILE=path:%s" % os.path.join(self.src, "big.txt"))
        code, text = self.run_task("t1")
        self.assertIn("bytes_read: 65536 of 70000", text)
        self.assertIn("truncated: yes", text)

    def test_reads_run_before_writes_in_the_plan(self):
        self.make_task("t1", "CREATE_REPORT", "READ_FILE=path:%s" % os.path.join(self.src, "a.txt"))
        code, text = self.run_task("t1")
        self.assertLess(text.index("READ_FILE READ_FILE done"), text.index("CREATE_REPORT WRITE_REPORT done"))


class DeniedReadTests(ReadCase):
    def assertBlocked(self, request, reason):
        text = self.make_task("t1", request)
        self.assertIn("state: BLOCKED", text, text)
        self.assertIn(reason, text)
        self.assertEqual(self.run_cli("task", "run", "t1", "--policy", self.policy)[0], cli.EXIT_TASK)
        self.assertEqual([r for r in self.records() if r.get("files_read")], [])

    def test_outside_the_contract_scope(self):
        self.assertBlocked("READ_FILE=path:%s" % os.path.join(self.outside, "o.txt"), "TARGET_OUT_OF_SCOPE")

    def test_dot_dot_out_of_the_scope(self):
        sneaky = os.path.join(self.src, "..", "outside", "o.txt")
        self.assertBlocked("READ_FILE=path:%s" % sneaky, "TARGET_OUT_OF_SCOPE")

    def test_a_junction_out_of_the_scope(self):
        link = os.path.join(self.src, "jump")
        if not make_junction(link, self.outside):
            self.skipTest("cannot create a junction on this machine: UNKNOWN")
        self.assertBlocked("READ_FILE=path:%s" % os.path.join(link, "o.txt"), "TARGET_OUT_OF_SCOPE")

    def test_the_governance_zone(self):
        self.assertBlocked("READ_FILE=path:%s" % self.revocations, "TARGET_GOVERNANCE_ZONE")

    def test_the_data_root(self):
        self.assertBlocked("READ_FILE=path:%s" % os.path.join(self.data, "HEAD"), "TARGET_DATA_ROOT")

    def test_the_jarvis_tree(self):
        self.assertBlocked("READ_FILE=path:%s" % os.path.join(REPO, "README.md"), "TARGET_JARVIS_SELF")

    def test_a_user_secret_location(self):
        self.assertBlocked("READ_FILE=path:%s" % os.path.join(self.home, ".ssh", "id"), "TARGET_USER_SECRET")

    def test_another_projects_files_have_no_contract_here(self):
        other = os.path.join(self.tmp, "other-proj")
        self.write(os.path.join(other, "f.txt"), "not registered\n")
        text = self.make_task("t1", "READ_FILE=path:%s" % os.path.join(other, "f.txt"))
        self.assertIn("state: BLOCKED", text)

    def test_a_forbidden_operation_in_the_contract(self):
        self.write(os.path.join(self.gov, "contracts", "p.toml"),
                   "schema_version = 1\nproject_id = \"p\"\nscope_roots = ['%s']\n"
                   "forbidden_operations = [\"READ_FILE\"]\n" % self.src)
        self.assertBlocked("READ_FILE=path:%s" % os.path.join(self.src, "a.txt"), "FORBIDDEN_BY_CONTRACT")

    def test_policy_version_1_still_defers_reading(self):
        for name in ("jarvis.db", "HEAD"):
            os.remove(os.path.join(self.data, name))
        self.assertEqual(self.run_cli("init", "--policy", V1_POLICY)[0], cli.EXIT_OK)
        self.run_cli("task", "create", "--id", "t2", "--project", "p", "--objective", "x",
                     "--request", "READ_FILE=path:%s" % os.path.join(self.src, "a.txt"))
        text = self.run_cli("task", "evaluate", "t2", "--policy", V1_POLICY)[1]
        self.assertIn("state: DEFERRED", text)
        self.assertIn("PHASE_NOT_ENABLED", text)


class RunTimeChecksTests(ReadCase):
    def test_a_name_that_looks_like_a_secret_fails_the_task_and_shows_nothing(self):
        self.write(os.path.join(self.src, ".env"), "TOKEN=hunter2\n")
        self.make_task("t1", "READ_FILE=path:%s" % os.path.join(self.src, ".env"))
        code, text = self.run_task("t1", "--show-reads")
        self.assertEqual(code, cli.EXIT_TASK)
        self.assertIn("error: READ_SECRET_LIKE_NAME", text)
        self.assertNotIn("hunter2", text)
        self.assertEqual(self.state("t1"), "FAILED")
        self.assertNotIn("hunter2", json.dumps(self.records()))

    def test_a_binary_file_fails_the_task(self):
        self.write(os.path.join(self.src, "b.bin"), b"ab\x00cd", binary=True)
        self.make_task("t1", "READ_FILE=path:%s" % os.path.join(self.src, "b.bin"))
        code, text = self.run_task("t1")
        self.assertIn("error: READ_BINARY", text)
        self.assertEqual(self.state("t1"), "FAILED")

    def test_a_revocation_after_evaluation_stops_the_read_and_the_task_stays_running(self):
        self.make_task("t1", "READ_FILE=path:%s" % os.path.join(self.src, "a.txt"))
        self.write(self.revocations,
                   "schema_version = 1\ncapabilities = [\"READ_FILE\"]\nprojects = []\ncontract_hashes = []\n")
        code, text = self.run_task("t1", "--show-reads")
        self.assertEqual(code, cli.EXIT_TASK)
        self.assertIn("not allowed now: READ_FILE DENY REVOKED", text)
        self.assertNotIn("alpha content", text)
        self.assertEqual(self.state("t1"), "RUNNING")
        self.assertEqual([r for r in self.records() if r.get("files_read")], [])
        self.assertEqual(self.run_cli("cancel", "t1")[0], cli.EXIT_OK)

    def test_a_contract_removed_after_evaluation_stops_the_read(self):
        self.make_task("t1", "READ_FILE=path:%s" % os.path.join(self.src, "a.txt"))
        os.remove(os.path.join(self.gov, "contracts", "p.toml"))
        code, text = self.run_task("t1")
        self.assertEqual(code, cli.EXIT_TASK)
        self.assertIn("CONTRACT_MISSING", text)
        self.assertEqual(self.state("t1"), "RUNNING")

    def test_a_file_replaced_by_a_junction_after_evaluation_is_not_read(self):
        folder = os.path.join(self.src, "swap")
        self.write(os.path.join(folder, "f.txt"), "original\n")
        self.make_task("t1", "READ_FILE=path:%s" % os.path.join(folder, "f.txt"))
        os.rename(folder, folder + "_old")
        if not make_junction(folder, self.outside):
            self.skipTest("cannot create a junction on this machine: UNKNOWN")
        self.write(os.path.join(self.outside, "f.txt"), "substituted\n")
        code, text = self.run_task("t1", "--show-reads")
        self.assertNotIn("substituted", text)
        self.assertIn("not allowed now: READ_FILE DENY TARGET_OUT_OF_SCOPE", text)
        self.assertEqual(self.state("t1"), "RUNNING")


if __name__ == "__main__":
    unittest.main()
