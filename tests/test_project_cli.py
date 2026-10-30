"""`project list` and `project show` through cli.main (Beta plan BR-1).

Temporary directories only. The real governance zone is never used.
"""

import io
import os
import tempfile
import unittest

from jarvis import cli

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_POLICY = os.path.join(REPO, "policy", "policy.toml")


class ProjectCliTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.data = os.path.join(self.tmp, "data")
        self.gov = os.path.join(self.tmp, "gov")
        self.home = os.path.join(self.tmp, "home")
        self.proj = os.path.join(self.tmp, "proj")
        self.src = os.path.join(self.proj, "src")
        self.docs = os.path.join(self.proj, "docs")
        for d in (self.data, self.gov, self.home, self.src, self.docs):
            os.makedirs(d)
        self.cfg = os.path.join(self.tmp, "jarvis-test.toml")
        self.write(self.cfg, "schema_version = 1\ndata_root = '%s'\ngovernance_zone = '%s'\n"
                   "user_home = '%s'\n" % (self.data, self.gov, self.home))
        self.registry = os.path.join(self.gov, "registry.toml")
        self.contract = os.path.join(self.gov, "contracts", "alpha.toml")

    @staticmethod
    def write(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def registry_text(self, root):
        return ("schema_version = 1\n[[projects]]\nid = \"alpha\"\nname = \"Alpha\"\n"
                "repository = \"example/alpha\"\ndescription = \"A test project\"\n"
                "root = '%s'\n[[projects]]\nid = \"beta\"\nname = \"Beta\"\n" % root)

    def contract_text(self):
        return ("schema_version = 1\nproject_id = \"alpha\"\nscope_roots = ['%s']\n"
                "protected_paths = ['%s']\nforbidden_operations = [\"RUN_TEST\", \"PUSH\"]\n"
                "valid_until = \"2027-01-01T00:00:00.000000Z\"\n" % (self.src, self.docs))

    def run_cli(self, *argv):
        out = io.StringIO()
        code = cli.main(["--config", self.cfg] + list(argv) + ["--policy", REAL_POLICY]
                        if argv[0] == "project" else ["--config", self.cfg] + list(argv), out)
        return code, out.getvalue()

    def test_list_shows_each_project_and_its_contract_state(self):
        self.write(self.registry, self.registry_text(self.proj))
        self.write(self.contract, self.contract_text())
        code, text = self.run_cli("project", "list")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("alpha  Alpha  [ok]", text)
        self.assertIn("beta  Beta  [no root registered]", text)
        self.assertIn("projects: 2", text)

    def test_show_prints_the_contract_fields(self):
        self.write(self.registry, self.registry_text(self.proj))
        self.write(self.contract, self.contract_text())
        code, text = self.run_cli("project", "show", "alpha")
        self.assertEqual(code, cli.EXIT_OK, text)
        for expected in ("project: alpha", "name: Alpha", "repository: example/alpha",
                         "status: ok", "valid_until: 2027-01-01T00:00:00.000000Z",
                         "forbidden_operation: PUSH", "forbidden_operation: RUN_TEST"):
            self.assertIn(expected, text)
        self.assertRegex(text, r"contract_sha256: [0-9a-f]{64}")
        self.assertRegex(text, r"scope_root: .*src")
        self.assertRegex(text, r"protected_path: .*docs")

    def test_show_of_a_project_without_a_contract_says_so(self):
        self.write(self.registry, self.registry_text(self.proj))
        code, text = self.run_cli("project", "show", "alpha")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("status: CONTRACT_MISSING", text)
        self.assertNotIn("contract_sha256", text)

    def test_an_invalid_contract_is_reported_not_hidden(self):
        self.write(self.registry, self.registry_text(self.proj))
        self.write(self.contract, "not a contract [")
        code, text = self.run_cli("project", "show", "alpha")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("status: CONTRACT_INVALID", text)

    def test_a_root_inside_the_data_root_is_reported_as_rejected(self):
        self.write(self.registry, self.registry_text(self.data))
        code, text = self.run_cli("project", "list")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("alpha  Alpha  [root rejected: ROOT_PROTECTED]", text)

    def test_unknown_project_and_missing_registry(self):
        code, text = self.run_cli("project", "list")
        self.assertEqual(code, cli.EXIT_PROJECT)
        self.assertIn("REGISTRY_MISSING", text)
        self.write(self.registry, self.registry_text(self.proj))
        code, text = self.run_cli("project", "show", "nope")
        self.assertEqual(code, cli.EXIT_PROJECT)
        self.assertIn("PROJECT_UNKNOWN", text)

    def test_commands_write_nothing(self):
        self.write(self.registry, self.registry_text(self.proj))
        self.write(self.contract, self.contract_text())
        before = sorted(os.listdir(self.data)), sorted(os.listdir(self.gov))
        self.run_cli("project", "list")
        self.run_cli("project", "show", "alpha")
        self.assertEqual((sorted(os.listdir(self.data)), sorted(os.listdir(self.gov))), before)


if __name__ == "__main__":
    unittest.main()
