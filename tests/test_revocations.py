"""Revocation-list loader (ADR-0003 D7). Temporary files only."""

import os
import tempfile
import unittest

from jarvis import revocations as rev
from jarvis.model import RevocationFailure, RevocationSnapshot

H1 = "a" * 64


def doc(**over):
    values = {"schema_version": "1", "capabilities": "[]", "projects": "[]",
              "contract_hashes": "[]"}
    values.update(over)
    return "\n".join("%s = %s" % kv for kv in values.items()).encode("utf-8") + b"\n"


class ParseTests(unittest.TestCase):
    def test_an_empty_list_is_valid_and_revokes_nothing(self):
        snap = rev.parse(doc())
        self.assertEqual(snap, RevocationSnapshot())

    def test_entries(self):
        snap = rev.parse(doc(capabilities='["SEARCH_WEB", "PUSH"]', projects='["swarag"]',
                             contract_hashes='["%s"]' % H1))
        self.assertEqual(snap.capabilities, frozenset({"SEARCH_WEB", "PUSH"}))
        self.assertEqual(snap.projects, frozenset({"swarag"}))
        self.assertEqual(snap.contract_hashes, frozenset({H1}))

    def test_crlf_gives_the_same_snapshot(self):
        body = doc(capabilities='["PUSH"]')
        self.assertEqual(rev.parse(body), rev.parse(body.replace(b"\n", b"\r\n")))

    def test_anything_malformed_is_a_failure(self):
        bad = {
            "not toml": b"this is = = not toml",
            "lone CR": doc().replace(b"\n", b"\r", 1),
            "unknown key": doc() + b"extra = 1\n",
            "missing key": b"schema_version = 1\ncapabilities = []\nprojects = []\n",
            "unknown schema": doc(schema_version="2"),
            "bool schema": doc(schema_version="true"),
            "lower-case capability": doc(capabilities='["push"]'),
            "capability not a string": doc(capabilities="[1]"),
            "capabilities not a list": doc(capabilities='"PUSH"'),
            "bad project id": doc(projects='["Not Valid"]'),
            "short hash": doc(contract_hashes='["abc"]'),
            "upper-case hash": doc(contract_hashes='["%s"]' % ("A" * 64)),
            "not utf-8": b"\xff\xfe",
        }
        for label, raw in bad.items():
            with self.subTest(label=label):
                self.assertIsInstance(rev.parse(raw), RevocationFailure)


class LoadTests(unittest.TestCase):
    def test_missing_file_is_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsInstance(rev.load(rev.path_in(tmp)), RevocationFailure)

    def test_read_from_the_governance_zone_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(rev.path_in(tmp), "wb") as fh:
                fh.write(doc(capabilities='["PUSH"]'))
            self.assertEqual(rev.load(rev.path_in(tmp)).capabilities, frozenset({"PUSH"}))
            self.assertEqual(os.path.basename(rev.path_in(tmp)), "revocations.toml")

    def test_a_directory_in_place_of_the_file_is_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(rev.path_in(tmp))
            self.assertIsInstance(rev.load(rev.path_in(tmp)), RevocationFailure)


if __name__ == "__main__":
    unittest.main()
