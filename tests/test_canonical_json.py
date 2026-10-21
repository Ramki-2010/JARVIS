"""Canonical serialization tests (ADR-0005 D4)."""

import unittest

from jarvis import canonical_json as cj


class CanonicalJsonTests(unittest.TestCase):
    def test_sorted_keys_no_whitespace(self):
        self.assertEqual(cj.dumps({"b": 1, "a": [1, "x"]}), b'{"a":[1,"x"],"b":1}')

    def test_utf8_not_escaped_and_not_normalised(self):
        composed, decomposed = "é", "é"
        self.assertEqual(cj.dumps({"k": composed}), '{"k":"é"}'.encode("utf-8"))
        self.assertNotEqual(cj.dumps({"k": composed}), cj.dumps({"k": decomposed}))

    def test_float_rejected(self):
        with self.assertRaises(cj.CanonicalError):
            cj.dumps({"x": 1.5})
        with self.assertRaises(cj.CanonicalError):
            cj.loads(b'{"x":1.5}')

    def test_nan_rejected_on_parse(self):
        with self.assertRaises(cj.CanonicalError):
            cj.loads(b'{"x":NaN}')

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(cj.CanonicalError):
            cj.loads(b'{"a":1,"a":2}')

    def test_lone_surrogate_rejected(self):
        with self.assertRaises(cj.CanonicalError):
            cj.dumps({"x": "\ud800"})

    def test_round_trip_is_byte_identical(self):
        data = cj.dumps({"seq": 3, "prev_hash": "0" * 64, "errors": [], "note": None, "ok": True})
        self.assertEqual(cj.dumps(cj.loads(data)), data)

    def test_sha256(self):
        self.assertEqual(cj.sha256_hex(b""),
                         "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


if __name__ == "__main__":
    unittest.main()
