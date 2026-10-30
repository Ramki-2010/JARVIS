"""Policy loader and the real policy/policy.toml (ADR-0003 D6, ADR-0008 D1)."""

import os
import re
import unittest

from jarvis import canonical_json
from jarvis import policy as pol
from jarvis.model import PolicyFailure
from jarvis.reasons import REASON_CODES

from . import policy_d12 as d12
from . import policy_v2 as v2
from . import test_evaluator as te

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY_PATH = os.path.join(REPO, "policy", "policy.toml")

# Independent transcription of the ADR-0008 D1 table (29 entries).
ADR_0008_ENTRIES = (
    ".ssh", ".gnupg",
    ".git-credentials", ".netrc", "_netrc",
    ".aws", ".azure", ".config\\gcloud", ".kube", ".docker", ".npmrc", ".pypirc",
    ".config\\gh", "AppData\\Roaming\\GitHub CLI",
    ".claude", ".claude.json", ".codex", "AppData\\Roaming\\Claude",
    "AppData\\Roaming\\Microsoft\\Credentials", "AppData\\Local\\Microsoft\\Credentials",
    "AppData\\Roaming\\Microsoft\\Protect", "AppData\\Roaming\\Microsoft\\Vault",
    "AppData\\Local\\Microsoft\\Vault", "AppData\\Roaming\\Microsoft\\Crypto",
    "AppData\\Local\\Google\\Chrome\\User Data", "AppData\\Local\\Microsoft\\Edge\\User Data",
    "AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data",
    "AppData\\Roaming\\Mozilla\\Firefox\\Profiles", "AppData\\Roaming\\Opera Software",
)

MINIMAL = (b'schema_version = 1\npolicy_version = 1\n'
           b'[[capability]]\nname = "CREATE_TASK"\nbase_level = "L2"\n'
           b'requires_isolation = false\nallowed_classes = ["CONTROL_PLANE_RECORD"]\n'
           b'phase_enabled = true\nmechanism_implemented = true\nforbidden_l5 = false\n'
           b'non_goal = false\n'
           b'[secret_locations]\nuser_home_relative = [".ssh"]\n')


class RealPolicyFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loaded = pol.load(POLICY_PATH)

    def test_loads(self):
        self.assertIsInstance(self.loaded, pol.LoadedPolicy, getattr(self.loaded, "reason", ""))

    def test_versions_and_hash(self):
        snap = self.loaded.snapshot
        self.assertEqual((snap.schema_version, snap.policy_version), (1, 2))
        self.assertRegex(snap.sha256, r"^[0-9a-f]{64}$")

    def test_rules_equal_the_adr_0003_d12_table_with_the_adr_0010_d2_changes(self):
        # Row order carries no meaning, so compare by capability name.
        loaded = {r.name: r for r in self.loaded.snapshot.rules}
        expected = {r.name: r for r in v2.policy().rules}
        self.assertEqual(len(self.loaded.snapshot.rules), len(loaded))
        self.assertEqual(loaded, expected)

    def test_secret_locations_equal_adr_0008_table(self):
        self.assertEqual(self.loaded.secret_locations, ADR_0008_ENTRIES)
        self.assertEqual(len(self.loaded.secret_locations), 29)

    def test_no_real_paths_or_identities_in_file(self):
        with open(POLICY_PATH, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertIsNone(re.search(r"[A-Za-z]:\\\\?Users|@[\w.-]+\.(com|net)", text))

    def test_loaded_policy_gives_the_golden_decisions(self):
        """X-03 with the real file: same decisions as the golden file."""
        policy = self.loaded.snapshot
        out = {}
        for key, (cap, target, contract_in, c) in te.golden_cases(v2.ROWS):
            out[key] = te.evaluate(cap, target, contract_in, policy,
                                   te.RevocationSnapshot(), c, te.NOW, te.EARLIER).as_record()
        with open(te.GOLDEN_V2, "rb") as fh:
            expected = fh.read()
        self.assertEqual(canonical_json.dumps(out), expected)


class FailureTests(unittest.TestCase):
    def assertFails(self, raw, code, known=None):
        result = pol.parse(raw, known)
        self.assertIsInstance(result, PolicyFailure)
        self.assertEqual(result.reason, code)
        self.assertIn(result.reason, REASON_CODES)

    def test_minimal_policy_is_valid(self):
        self.assertIsInstance(pol.parse(MINIMAL), pol.LoadedPolicy)

    def test_unavailable(self):
        result = pol.load(os.path.join(REPO, "policy", "does-not-exist.toml"))
        self.assertEqual(result, PolicyFailure("POLICY_UNAVAILABLE"))

    def test_format_errors(self):
        self.assertFails(b"this is not toml [", "POLICY_FORMAT_INVALID")
        self.assertFails(b"\xff\xfe", "POLICY_FORMAT_INVALID")
        self.assertFails(MINIMAL + b"\r", "POLICY_FORMAT_INVALID")  # lone CR
        self.assertFails(MINIMAL.replace(b"schema_version = 1", b"schema_version = 9"),
                         "POLICY_FORMAT_INVALID")
        self.assertFails(MINIMAL + b"extra = 1\n", "POLICY_FORMAT_INVALID")

    def test_unknown_version(self):
        for bad in (b"0", b"-3"):
            self.assertFails(MINIMAL.replace(b"policy_version = 1", b"policy_version = " + bad),
                             "POLICY_VERSION_UNKNOWN")

    def test_rule_errors(self):
        cases = (
            (b'base_level = "L2"', b'base_level = "L9"'),
            (b'name = "CREATE_TASK"', b'name = "create task"'),
            (b'requires_isolation = false', b'requires_isolation = "no"'),
            (b'["CONTROL_PLANE_RECORD"]', b'["NOT_A_CLASS"]'),
            (b'["CONTROL_PLANE_RECORD"]', b'["GOVERNANCE_ZONE"]'),
            (b'["CONTROL_PLANE_RECORD"]', b'["UNCLASSIFIED"]'),
            (b'["CONTROL_PLANE_RECORD"]', b'[]'),
            (b'non_goal = false', b'non_goal = false\nsurprise = true'),
        )
        for old, new in cases:
            with self.subTest(change=new):
                self.assertFails(MINIMAL.replace(old, new), "POLICY_FORMAT_INVALID")

    def test_missing_key_and_duplicate_name(self):
        self.assertFails(MINIMAL.replace(b"non_goal = false\n", b""), "POLICY_FORMAT_INVALID")
        row = MINIMAL[MINIMAL.index(b"[[capability]]"):MINIMAL.index(b"[secret_locations]")]
        self.assertFails(MINIMAL.replace(b"[secret_locations]", row + b"[secret_locations]"),
                         "POLICY_FORMAT_INVALID")

    def test_secret_location_errors(self):
        for bad in ('"C:\\\\Windows"', '"\\\\.ssh"', '"../x"', '".ssh", ".SSH"', '""', ''):
            with self.subTest(entry=bad):
                raw = MINIMAL.replace(b'[".ssh"]', ("[%s]" % bad).encode("utf-8"))
                self.assertFails(raw, "POLICY_FORMAT_INVALID")

    def test_hash_mismatch_same_version(self):
        good = pol.parse(MINIMAL)
        self.assertIsInstance(good, pol.LoadedPolicy)
        recorded = {1: good.snapshot.sha256}
        self.assertIsInstance(pol.parse(MINIMAL, recorded), pol.LoadedPolicy)
        changed = MINIMAL.replace(b'"L2"', b'"L3"')
        self.assertFails(changed, "POLICY_HASH_MISMATCH", recorded)
        # A new version with changed content is not a mismatch.
        newer = changed.replace(b"policy_version = 1", b"policy_version = 2")
        self.assertIsInstance(pol.parse(newer, recorded), pol.LoadedPolicy)

    def test_hash_ignores_line_endings(self):
        a = pol.parse(MINIMAL)
        b = pol.parse(MINIMAL.replace(b"\n", b"\r\n"))
        self.assertEqual(a.snapshot.sha256, b.snapshot.sha256)


if __name__ == "__main__":
    unittest.main()
