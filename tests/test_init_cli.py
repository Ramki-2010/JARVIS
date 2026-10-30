"""`init` command through cli.main (ADR-0005 D6; ADR-0007 D7).

Temporary directories only. The real data root and governance zone are never used.
"""

import io
import os
import tempfile
import unittest
from unittest import mock

from jarvis import cli
from jarvis import policy as policy_mod
from jarvis.store import Store

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_POLICY = os.path.join(REPO, "policy", "policy.toml")
NOW = "2026-10-30T10:00:00.000000Z"


class InitCliTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.data = os.path.join(self.tmp, "data")
        self.gov = os.path.join(self.tmp, "gov")
        self.home = os.path.join(self.tmp, "home")
        for d in (self.data, self.gov, self.home):
            os.mkdir(d)
        self.cfg = os.path.join(self.tmp, "jarvis-test.toml")
        self.write_config(self.data)
        patcher = mock.patch.object(cli, "utc_now", lambda: NOW)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_config(self, data_root):
        lines = ["schema_version = 1", "data_root = '%s'" % data_root,
                 "governance_zone = '%s'" % self.gov, "user_home = '%s'" % self.home]
        with open(self.cfg, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")

    def run_cli(self, *argv):
        out = io.StringIO()
        code = cli.main(["--config", self.cfg] + list(argv), out)
        return code, out.getvalue()

    def test_init_creates_a_verifiable_store_with_genesis(self):
        code, text = self.run_cli("init", "--policy", REAL_POLICY)
        self.assertEqual(code, cli.EXIT_OK, text)
        loaded = policy_mod.load(REAL_POLICY)
        self.assertIn("init: OK", text)
        self.assertIn("audit_tail_seq: 0", text)
        self.assertIn("policy_sha256: %s" % loaded.snapshot.sha256, text)
        self.assertEqual(sorted(os.listdir(self.data)), ["HEAD", "jarvis.db"])
        code, text = self.run_cli("audit", "verify")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("audit verify: OK", text)
        code, text = self.run_cli("status")
        self.assertIn("store: initialized", text)

    def test_init_with_the_default_policy_uses_the_repository_policy(self):
        code, text = self.run_cli("init")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("policy_sha256: %s" % policy_mod.load(REAL_POLICY).snapshot.sha256, text)

    def test_init_refuses_an_existing_store_and_leaves_it_unchanged(self):
        self.assertEqual(self.run_cli("init", "--policy", REAL_POLICY)[0], cli.EXIT_OK)
        db = Store.db_path(self.data)
        with open(db, "rb") as fh:
            before = fh.read()
        code, text = self.run_cli("init", "--policy", REAL_POLICY)
        self.assertEqual(code, cli.EXIT_INIT)
        self.assertIn("store already exists", text)
        with open(db, "rb") as fh:
            self.assertEqual(fh.read(), before)

    def test_init_does_not_create_a_missing_data_root(self):
        missing = os.path.join(self.tmp, "no-such-data")
        self.write_config(missing)
        code, text = self.run_cli("init", "--policy", REAL_POLICY)
        self.assertEqual(code, cli.EXIT_INIT)
        self.assertIn("data root missing", text)
        self.assertFalse(os.path.exists(missing))

    def test_init_refuses_an_invalid_policy_and_creates_nothing(self):
        bad = os.path.join(self.tmp, "bad-policy.toml")
        with open(bad, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("not a policy\n")
        code, text = self.run_cli("init", "--policy", bad)
        self.assertEqual(code, cli.EXIT_INIT)
        self.assertIn("policy invalid", text)
        self.assertEqual(os.listdir(self.data), [])

    def test_init_with_a_missing_policy_file_creates_nothing(self):
        code, text = self.run_cli("init", "--policy", os.path.join(self.tmp, "absent.toml"))
        self.assertEqual(code, cli.EXIT_INIT)
        self.assertEqual(os.listdir(self.data), [])


if __name__ == "__main__":
    unittest.main()
