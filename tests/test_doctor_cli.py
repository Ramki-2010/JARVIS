"""`doctor` command through cli.main (Beta plan BR-7, acceptance B-08).

Temporary directories only. The real data root and governance zone are never used.
"""

import io
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from jarvis import cli
from jarvis.store import Store

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_POLICY = os.path.join(REPO, "policy", "policy.toml")
NOW = "2026-10-30T10:00:00.000000Z"
REVOCATIONS = "schema_version = 1\ncapabilities = []\nprojects = []\ncontract_hashes = []\n"


class DoctorCliTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.data = os.path.join(self.tmp, "data")
        self.gov = os.path.join(self.tmp, "gov")
        self.home = os.path.join(self.tmp, "home")
        self.proj = os.path.join(self.tmp, "proj")
        self.src = os.path.join(self.proj, "src")
        for d in (self.data, self.gov, self.home, self.src):
            os.makedirs(d)
        self.cfg = os.path.join(self.tmp, "jarvis-test.toml")
        self.write(self.cfg, "schema_version = 1\ndata_root = '%s'\ngovernance_zone = '%s'\n"
                   "user_home = '%s'\n" % (self.data, self.gov, self.home))
        self.revocations = os.path.join(self.gov, "revocations.toml")
        self.registry = os.path.join(self.gov, "registry.toml")
        self.contract = os.path.join(self.gov, "contracts", "p.toml")
        patcher = mock.patch.object(cli, "utc_now", lambda: NOW)
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def write(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def healthy(self):
        self.assertEqual(self.run_cli("init", "--policy", REAL_POLICY)[0], cli.EXIT_OK)
        self.write(self.revocations, REVOCATIONS)
        self.write(self.registry, "schema_version = 1\n[[projects]]\nid = \"p\"\nname = \"P\"\n"
                   "root = '%s'\n" % self.proj)
        self.write(self.contract,
                   "schema_version = 1\nproject_id = \"p\"\nscope_roots = ['%s']\n" % self.src)

    def run_cli(self, *argv):
        out = io.StringIO()
        code = cli.main(["--config", self.cfg] + list(argv), out)
        return code, out.getvalue()

    def doctor(self):
        return self.run_cli("doctor", "--policy", REAL_POLICY)

    def test_a_healthy_installation_passes(self):
        self.healthy()
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("doctor: OK (0 warning(s))", text)
        self.assertIn("PASS audit chain: verified, tail seq 0", text)
        self.assertIn("PASS project p: root and contract load", text)
        self.assertNotIn("FAIL", text)

    def test_an_uninitialized_store_fails(self):
        self.write(self.revocations, REVOCATIONS)
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("FAIL store: not initialized", text)
        self.assertFalse(Store.exists(self.data), "doctor must not create the store")

    def test_a_missing_revocation_list_fails(self):
        self.healthy()
        os.remove(self.revocations)
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("FAIL revocations: REVOCATION_UNAVAILABLE", text)

    def test_a_broken_contract_fails_and_names_the_project(self):
        self.healthy()
        self.write(self.contract, "not a contract [")
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("FAIL project p: contract: CONTRACT_INVALID", text)

    def test_a_missing_contract_is_a_warning_not_a_failure(self):
        self.healthy()
        os.remove(self.contract)
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("WARN project p: contract: CONTRACT_MISSING", text)
        self.assertIn("doctor: OK (1 warning(s))", text)

    def test_a_missing_registry_is_a_warning_not_a_failure(self):
        self.healthy()
        os.remove(self.registry)
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("WARN registry: REGISTRY_MISSING", text)

    def test_an_invalid_registry_fails(self):
        self.healthy()
        self.write(self.registry, "not a registry [")
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("FAIL registry:", text)

    def test_a_project_root_inside_the_data_root_is_rejected(self):
        self.healthy()
        self.write(self.registry, "schema_version = 1\n[[projects]]\nid = \"p\"\nname = \"P\"\n"
                   "root = '%s'\n" % self.data)
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("FAIL project p: root rejected: ROOT_PROTECTED", text)

    def test_a_tampered_audit_chain_fails(self):
        self.healthy()
        conn = sqlite3.connect(Store.db_path(self.data))
        try:
            conn.execute("UPDATE audit_log SET record = CAST(record || x'20' AS BLOB) WHERE seq = 0")
            conn.commit()
        finally:
            conn.close()
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("FAIL audit chain:", text)

    def test_a_missing_data_root_fails(self):
        self.healthy()
        os.rename(self.data, self.data + "-gone")
        code, text = self.doctor()
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("FAIL data root: missing", text)

    def test_an_invalid_policy_fails(self):
        self.healthy()
        bad = os.path.join(self.tmp, "bad-policy.toml")
        self.write(bad, "not a policy\n")
        code, text = self.run_cli("doctor", "--policy", bad)
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("FAIL policy:", text)

    def test_output_carries_no_file_contents(self):
        self.healthy()
        self.write(self.contract, "schema_version = 1\nproject_id = \"p\"\nsecret_marker = 'ZZ-MARK'\n")
        code, text = self.doctor()
        self.assertNotIn("ZZ-MARK", text)


if __name__ == "__main__":
    unittest.main()
