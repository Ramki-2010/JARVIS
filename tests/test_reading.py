"""Bounded reading (ADR-0010 D3) at the module level: caps, text only, regular files only,
secret-looking names, and the re-resolve checks. Temporary directories only."""

import hashlib
import os
import tempfile
import unittest
from unittest import mock

from jarvis import reading


def make_junction(link: str, target: str) -> bool:
    try:
        import _winapi
        _winapi.CreateJunction(target, link)
        return True
    except Exception:
        return False


class ReadingCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)

    def put(self, name, data: bytes) -> str:
        path = os.path.join(self.root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return os.path.realpath(path)


class FileReadTests(ReadingCase):
    def test_a_text_file_is_returned_with_the_hash_of_the_bytes_returned(self):
        path = self.put("a.txt", "hello\nwörld\n".encode("utf-8"))
        got = reading.read_file(path)
        self.assertEqual(got.text, "hello\nwörld\n")
        self.assertEqual(got.bytes_read, len("hello\nwörld\n".encode("utf-8")))
        self.assertEqual(got.sha256, hashlib.sha256("hello\nwörld\n".encode("utf-8")).hexdigest())
        self.assertFalse(got.truncated)
        self.assertEqual(got.size_on_disk, got.bytes_read)
        self.assertNotIn("text", got.as_audit())

    def test_a_long_file_is_cut_at_the_cap_on_a_character_boundary_and_marked(self):
        path = self.put("big.txt", ("é" * 40000).encode("utf-8"))   # 80000 bytes
        got = reading.read_file(path)
        self.assertTrue(got.truncated)
        self.assertEqual(got.size_on_disk, 80000)
        self.assertLessEqual(got.bytes_read, reading.MAX_FILE_BYTES)
        self.assertEqual(got.bytes_read, len(got.text.encode("utf-8")))
        self.assertEqual(set(got.text), {"é"})
        self.assertEqual(got.sha256, hashlib.sha256(got.text.encode("utf-8")).hexdigest())

    def test_a_file_exactly_at_the_cap_is_not_marked_truncated(self):
        got = reading.read_file(self.put("exact.txt", b"a" * reading.MAX_FILE_BYTES))
        self.assertFalse(got.truncated)
        self.assertEqual(got.bytes_read, reading.MAX_FILE_BYTES)

    def test_binary_and_non_utf8_are_refused(self):
        self.assertEqual(self.code(self.put("b.bin", b"abc\x00def")), "READ_BINARY")
        self.assertEqual(self.code(self.put("c.txt", b"\xff\xfe broken")), "READ_NOT_UTF8")

    def test_secret_looking_names_are_refused_even_though_the_file_is_text(self):
        for name in (".env", ".env.local", "server.pem", "api.KEY", "my_secret_notes.txt",
                     "id_rsa", "ID_ED25519.pub", "credentials.json", "vault.kdbx", "cert.pfx"):
            with self.subTest(name=name):
                self.assertEqual(self.code(self.put(name, b"harmless")), "READ_SECRET_LIKE_NAME")

    def test_ordinary_names_are_not_caught_by_the_name_rule(self):
        for name in ("readme.md", "environment.txt", "keyboard.py", "pem_notes.txt", "plan.txt"):
            with self.subTest(name=name):
                self.assertEqual(reading.read_file(self.put(name, b"ok")).text, "ok")

    def test_a_directory_is_not_a_file(self):
        folder = os.path.join(self.root, "d")
        os.mkdir(folder)
        self.assertEqual(self.code(folder), "READ_NOT_REGULAR")

    def test_a_path_that_resolves_elsewhere_now_is_refused(self):
        real = os.path.join(self.root, "d")
        os.makedirs(real)
        canonical = self.put("d/f.txt", b"original")
        other = os.path.join(self.root, "other")
        os.makedirs(other)
        self.put("other/f.txt", b"substituted")
        os.rename(real, real + "_old")
        if not make_junction(real, other):
            self.skipTest("cannot create a junction on this machine: UNKNOWN")
        self.assertEqual(self.code(canonical), "READ_PATH_CHANGED")

    def test_a_missing_file_is_refused(self):
        canonical = self.put("gone.txt", b"x")
        os.remove(canonical)
        self.assertEqual(self.code(canonical), "READ_PATH_CHANGED")

    def test_a_change_of_file_identity_during_the_read_is_discarded(self):
        path = self.put("f.txt", b"data")
        real = reading._identity
        calls = []

        def drifting(info):
            calls.append(1)
            return (0, len(calls)) if len(calls) >= 2 else real(info)
        with mock.patch.object(reading, "_identity", drifting):
            self.assertEqual(self.code(path), "READ_PATH_CHANGED")

    def test_a_change_after_the_read_is_discarded(self):
        path = self.put("f.txt", b"data")
        resolves = []
        real = reading._same_target

        def second_time_elsewhere(canonical):
            resolves.append(1)
            if len(resolves) == 2:
                raise reading.ReadError("READ_PATH_CHANGED")
            return real(canonical)
        with mock.patch.object(reading, "_same_target", second_time_elsewhere):
            self.assertEqual(self.code(path), "READ_PATH_CHANGED")

    def code(self, path):
        with self.assertRaises(reading.ReadError) as ctx:
            reading.read_file(path)
        return ctx.exception.code


class DirectoryTests(ReadingCase):
    def test_names_only_sorted_with_kinds_and_links_not_followed(self):
        self.put("sub/inner.txt", b"x")
        self.put("b.txt", b"x")
        self.put("A.txt", b"x")
        outside = os.path.join(self.root, "outside")
        os.makedirs(outside)
        self.put("outside/secret_data.txt", b"x")
        link = os.path.join(self.root, "sub", "jump")
        have_link = make_junction(link, outside)
        listing = reading.list_directory(self.root)
        names = [n for n, _ in listing.entries]
        self.assertEqual(names, sorted(names, key=lambda n: (n.casefold(), n)))
        kinds = dict(listing.entries)
        self.assertEqual((kinds["A.txt"], kinds["sub"]), ("file", "dir"))
        self.assertNotIn("inner.txt", names, "listing is not recursive")
        if have_link:
            sub = dict(reading.list_directory(os.path.join(self.root, "sub")).entries)
            self.assertEqual(sub["jump"], "link")
            self.assertNotIn("secret_data.txt", sub)

    def test_the_entry_cap(self):
        for i in range(reading.MAX_DIR_ENTRIES + 5):
            self.put("many/f%03d.txt" % i, b"")
        listing = reading.list_directory(os.path.join(self.root, "many"))
        self.assertEqual(len(listing.entries), reading.MAX_DIR_ENTRIES)
        self.assertTrue(listing.truncated)

    def test_a_file_is_not_a_directory(self):
        path = self.put("f.txt", b"x")
        with self.assertRaises(reading.ReadError) as ctx:
            reading.list_directory(path)
        self.assertEqual(ctx.exception.code, "READ_NOT_DIRECTORY")


class NameRuleTests(unittest.TestCase):
    def test_secret_like(self):
        self.assertTrue(reading.secret_like(".ENV"))
        self.assertFalse(reading.secret_like("main.py"))


if __name__ == "__main__":
    unittest.main()
