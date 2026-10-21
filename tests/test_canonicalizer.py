"""Canonicalizer: X-09 and X-16 (ADR-0002 D5), ADR-0003 D3, ADR-0008 D1.

Temporary directories only. Junction and symlink tests skip with an explicit
message when the machine cannot create them, never passing silently (ADR-0006 5.4).
"""

import ctypes
import os
import ntpath
import tempfile
import unittest

from jarvis import canonicalizer as cz
from jarvis.model import CanonicalTarget, TargetFailure
from jarvis.reasons import TargetClass

from .test_policy import ADR_0008_ENTRIES

try:
    import _winapi
except ImportError:  # not Windows
    _winapi = None


def make_junction(link: str, target: str) -> bool:
    try:
        _winapi.CreateJunction(target, link)
        return True
    except (OSError, AttributeError):
        return False


def make_symlink(link: str, target: str) -> bool:
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        return False


def short_path(path: str):
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.windll.kernel32.GetShortPathNameW(path, buf, 1024)
    return buf.value if n else None


class TreeCase(unittest.TestCase):
    """A throwaway tree: governance/, data/, repo/, home/ (with a few secret
    entries present) and projects/demo/."""

    HOME_NAME = "h\u00f6me"          # non-ASCII on purpose (X-16)
    PROJECT_NAME = "\u0434\u0435mo"   # Cyrillic, non-ASCII on purpose

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = os.path.realpath(tmp.name)
        self.gov = os.path.join(self.base, "governance")
        self.data = os.path.join(self.base, "data")
        self.repo = os.path.join(self.base, "repo")
        self.home = os.path.join(self.base, self.HOME_NAME)
        self.projects = os.path.join(self.base, "projects")
        self.demo = os.path.join(self.projects, self.PROJECT_NAME)
        self.sibling = os.path.join(self.projects, self.PROJECT_NAME + "-evil")
        for d in (self.gov, self.data, self.repo, self.home, self.demo, self.sibling,
                  os.path.join(self.home, ".ssh"), os.path.join(self.home, ".config", "gh"),
                  os.path.join(self.home, "AppData", "Roaming", "Claude"),
                  os.path.join(self.demo, "src")):
            os.makedirs(d, exist_ok=True)
        for f in (os.path.join(self.gov, "jarvis.toml"), os.path.join(self.data, "jarvis.db"),
                  os.path.join(self.repo, "a.py"), os.path.join(self.home, ".ssh", "id_ed25519"),
                  os.path.join(self.home, ".config", "gh", "hosts.yml"),
                  os.path.join(self.demo, "src", "main.py"), os.path.join(self.sibling, "x.py"),
                  os.path.join(self.base, "outside.txt"),
                  os.path.join(self.home, "notes.txt")):
            with open(f, "w", encoding="utf-8") as fh:
                fh.write("x")
        self.roots = cz.build_roots(self.gov, self.data, self.repo, self.home,
                                    ADR_0008_ENTRIES, {"demo": self.demo})

    def canon(self, raw, **kw):
        return cz.canonicalize_path(raw, self.roots, **kw)

    def assertClass(self, raw, cls, **kw):
        result = self.canon(raw, **kw)
        self.assertIsInstance(result, CanonicalTarget, getattr(result, "reason", ""))
        self.assertIs(result.target_class, cls)
        return result

    def assertFailure(self, raw, code, **kw):
        result = self.canon(raw, **kw)
        self.assertEqual(result, TargetFailure(code))


class RawInputTests(TreeCase):
    """X-09 (C4): rejected on the raw string, before any normalising call."""

    def test_rejected_shapes(self):
        base = self.demo
        cases = {
            "trailing dot": base + "\\src\\main.py.",
            "trailing space": base + "\\src\\main.py ",
            "trailing dot on a directory": base + "\\src.\\main.py",
            "reserved CON": base + "\\CON",
            "reserved con with extension": base + "\\src\\con.txt",
            "reserved NUL": base + "\\NUL",
            "reserved COM1": base + "\\COM1",
            "reserved LPT9 dotted": base + "\\LPT9.tar.gz",
            "reserved AUX with space before dot": base + "\\AUX .txt",
            "reserved superscript COM": base + "\\COM\u00b9",
            "alternate data stream": base + "\\src\\main.py:stream",
            "stream after directory": base + ":hidden\\src",
            "device prefix": "\\\\?\\" + base,
            "device dot prefix": "\\\\.\\C:\\x",
            "UNC": "\\\\server\\share\\x",
            "UNC with forward slashes": "//server/share/x",
            "relative": "projects\\demo",
            "rooted without drive": "\\projects\\demo",
            "drive relative": "C:projects",
            "empty": "",
            "NUL character": base + "\\a\x00b",
            "wildcard": base + "\\*.py",
            "question mark": base + "\\a?.py",
            "not a string": None,
        }
        for label, raw in cases.items():
            with self.subTest(label):
                self.assertFailure(raw, "TARGET_RAW_INVALID")

    def test_trailing_dot_is_rejected_even_though_it_would_resolve(self):
        """abspath and realpath would strip the dot and find a real file; the raw
        check must reject first."""
        target = os.path.join(self.demo, "src", "main.py")
        self.assertIsInstance(self.canon(target), CanonicalTarget)
        self.assertFailure(target + ".", "TARGET_RAW_INVALID")
        self.assertFailure(target + " ", "TARGET_RAW_INVALID")

    def test_matches_python_isreserved_when_available(self):
        if not hasattr(os.path, "isreserved"):
            self.skipTest("os.path.isreserved needs Python 3.13+")
        for name in ("CON", "con", "nul.txt", "COM3", "lpt1.a.b", "AUX", "PRN", "COM\u00b2",
                     "CONIN$", "CONOUT$", "console", "com10", "lpt", "normal.txt", "com1x"):
            with self.subTest(name=name):
                self.assertEqual(cz.is_reserved_name(name), os.path.isreserved(name), name)

    def test_dot_components_are_not_trailing_dot_errors(self):
        self.assertClass(self.demo + "\\src\\..\\src\\main.py", TargetClass.PROJECT_PATH)

    def test_forward_slashes_are_accepted(self):
        self.assertClass(self.demo.replace("\\", "/") + "/src/main.py", TargetClass.PROJECT_PATH)


class ResolutionTests(TreeCase):
    def test_missing_path_is_unresolvable(self):
        self.assertFailure(self.demo + "\\src\\nope.py", "TARGET_UNRESOLVABLE")

    def test_new_leaf_in_existing_parent(self):
        result = self.assertClass(self.demo + "\\src\\new.py", TargetClass.PROJECT_PATH,
                                  must_exist=False)
        self.assertTrue(result.value.endswith("new.py"))

    def test_new_leaf_in_missing_parent_is_unresolvable(self):
        self.assertFailure(self.demo + "\\missing\\new.py", "TARGET_UNRESOLVABLE", must_exist=False)

    def test_new_leaf_still_gets_raw_checks(self):
        self.assertFailure(self.demo + "\\src\\new.py.", "TARGET_RAW_INVALID", must_exist=False)
        self.assertFailure(self.demo + "\\src\\CON", "TARGET_RAW_INVALID", must_exist=False)


class ClassificationTests(TreeCase):
    def test_protected_areas(self):
        self.assertClass(os.path.join(self.gov, "jarvis.toml"), TargetClass.GOVERNANCE_ZONE)
        self.assertClass(os.path.join(self.data, "jarvis.db"), TargetClass.DATA_ROOT)
        self.assertClass(os.path.join(self.repo, "a.py"), TargetClass.JARVIS_SELF)
        self.assertClass(self.gov, TargetClass.GOVERNANCE_ZONE)

    def test_user_secret_locations(self):
        self.assertClass(os.path.join(self.home, ".ssh", "id_ed25519"), TargetClass.USER_SECRET_LOCATION)
        self.assertClass(os.path.join(self.home, ".ssh"), TargetClass.USER_SECRET_LOCATION)
        self.assertClass(os.path.join(self.home, ".config", "gh", "hosts.yml"),
                         TargetClass.USER_SECRET_LOCATION)
        self.assertClass(os.path.join(self.home, "AppData", "Roaming", "Claude"),
                         TargetClass.USER_SECRET_LOCATION)

    def test_home_itself_and_ordinary_files_are_not_secret(self):
        self.assertClass(self.home, TargetClass.UNCLASSIFIED)
        self.assertClass(os.path.join(self.home, "notes.txt"), TargetClass.UNCLASSIFIED)
        self.assertClass(os.path.join(self.base, "outside.txt"), TargetClass.UNCLASSIFIED)

    def test_every_adr_0008_group_matches_even_when_absent_on_disk(self):
        """A missing entry still matches by its normalised absolute form."""
        for entry in ADR_0008_ENTRIES:
            with self.subTest(entry=entry):
                absent = ntpath.join(self.home, entry)
                if os.path.exists(absent):
                    continue
                self.assertTrue(
                    any(cz.inside(absent, f) for f in self.roots.protected[TargetClass.USER_SECRET_LOCATION]))
                # And a leaf created inside it, in an existing parent, is denied.
                parent = ntpath.dirname(absent)
                if os.path.isdir(parent):
                    result = self.canon(absent, must_exist=False)
                    self.assertIs(result.target_class, TargetClass.USER_SECRET_LOCATION)

    def test_sibling_sharing_a_name_prefix_is_not_inside(self):
        result = self.assertClass(os.path.join(self.sibling, "x.py"), TargetClass.UNCLASSIFIED)
        self.assertIsNone(result.project_id)

    def test_project_path_and_project_id(self):
        result = self.assertClass(os.path.join(self.demo, "src", "main.py"), TargetClass.PROJECT_PATH)
        self.assertEqual(result.project_id, "demo")

    def test_requested_project_outside_root_stays_project_path(self):
        """Scope is the evaluator's job (TARGET_OUT_OF_SCOPE), not the canonicalizer's."""
        result = self.assertClass(os.path.join(self.base, "outside.txt"), TargetClass.PROJECT_PATH,
                                  project_id="demo")
        self.assertEqual(result.project_id, "demo")

    def test_unknown_requested_project(self):
        self.assertClass(os.path.join(self.demo, "src", "main.py"), TargetClass.UNCLASSIFIED,
                         project_id="nope")

    def test_protected_area_beats_a_requested_project(self):
        self.assertClass(os.path.join(self.home, ".ssh", "id_ed25519"),
                         TargetClass.USER_SECRET_LOCATION, project_id="demo")

    def test_cross_drive_for_requested_project(self):
        roots = cz.build_roots(self.gov, self.data, self.repo, self.home, ADR_0008_ENTRIES,
                               {"far": "Z:\\far-away-project"})
        result = cz.canonicalize_path(os.path.join(self.demo, "src", "main.py"), roots,
                                      project_id="far")
        if ntpath.splitdrive(self.demo)[0].upper() == "Z:":
            self.skipTest("temp directory is on drive Z:")
        self.assertEqual(result, TargetFailure("TARGET_CROSS_DRIVE"))

    def test_precedence_when_areas_overlap(self):
        """GOVERNANCE_ZONE, then DATA_ROOT, then JARVIS_SELF, then USER_SECRET_LOCATION."""
        target = os.path.join(self.gov, "jarvis.toml")
        all_four = cz.build_roots(self.gov, self.gov, self.gov, self.base, (os.path.basename(self.gov),))
        self.assertIs(cz.canonicalize_path(target, all_four).target_class, TargetClass.GOVERNANCE_ZONE)
        no_gov = cz.build_roots(self.base + "\\nowhere-1", self.gov, self.gov, self.base,
                                (os.path.basename(self.gov),))
        self.assertIs(cz.canonicalize_path(target, no_gov).target_class, TargetClass.DATA_ROOT)
        no_gov_data = cz.build_roots(self.base + "\\nowhere-1", self.base + "\\nowhere-2", self.gov,
                                     self.base, (os.path.basename(self.gov),))
        self.assertIs(cz.canonicalize_path(target, no_gov_data).target_class, TargetClass.JARVIS_SELF)
        only_secret = cz.build_roots(self.base + "\\nowhere-1", self.base + "\\nowhere-2",
                                     self.base + "\\nowhere-3", self.base, (os.path.basename(self.gov),))
        self.assertIs(cz.canonicalize_path(target, only_secret).target_class,
                      TargetClass.USER_SECRET_LOCATION)

    def test_record_targets(self):
        ok = cz.canonicalize_record("task", "t-0001")
        self.assertEqual(ok, CanonicalTarget(TargetClass.CONTROL_PLANE_RECORD, "task/t-0001"))
        for bad in (("Task", "t-1"), ("task", ""), ("task", "../x"), ("task", "a b"), ("", "x"),
                    ("task", "x" * 65), (None, "x")):
            with self.subTest(bad=bad):
                self.assertEqual(cz.canonicalize_record(*bad), TargetFailure("TARGET_RAW_INVALID"))


class PathTrickTests(TreeCase):
    """X-16: dot-dot, junctions, symlinks, 8.3 names, case, non-ASCII roots."""

    def test_dotdot_into_a_secret_location(self):
        raw = os.path.join(self.demo, "src", "..", "..", "..", self.HOME_NAME, ".ssh", "id_ed25519")
        self.assertClass(raw, TargetClass.USER_SECRET_LOCATION)

    def test_dotdot_escaping_the_project(self):
        raw = os.path.join(self.demo, "src", "..", "..", "..", "outside.txt")
        result = self.assertClass(raw, TargetClass.UNCLASSIFIED)
        self.assertEqual(result.value, os.path.join(self.base, "outside.txt"))

    def test_case_differences(self):
        raw = os.path.join(self.home, ".SSH", "ID_ED25519").upper()
        # Upper-casing the whole path, drive and non-ASCII letters included.
        self.assertClass(raw, TargetClass.USER_SECRET_LOCATION)
        self.assertClass(os.path.join(self.demo, "SRC", "MAIN.PY"), TargetClass.PROJECT_PATH)

    def test_non_ascii_roots(self):
        self.assertIn("\u00f6", self.home)
        self.assertClass(os.path.join(self.home, ".ssh", "id_ed25519"), TargetClass.USER_SECRET_LOCATION)
        self.assertClass(os.path.join(self.demo, "src", "main.py"), TargetClass.PROJECT_PATH)

    def test_junction_into_a_secret_location(self):
        if _winapi is None:
            self.skipTest("junctions need Windows")
        link = os.path.join(self.demo, "innocent")
        if not make_junction(link, os.path.join(self.home, ".ssh")):
            self.skipTest("cannot create a junction on this machine: UNKNOWN")
        self.assertClass(os.path.join(link, "id_ed25519"), TargetClass.USER_SECRET_LOCATION)

    def test_junction_out_of_the_project(self):
        if _winapi is None:
            self.skipTest("junctions need Windows")
        link = os.path.join(self.demo, "escape")
        if not make_junction(link, self.data):
            self.skipTest("cannot create a junction on this machine: UNKNOWN")
        self.assertClass(os.path.join(link, "jarvis.db"), TargetClass.DATA_ROOT)

    def test_symlink_into_governance(self):
        link = os.path.join(self.demo, "sneaky")
        if not make_symlink(link, self.gov):
            self.skipTest("cannot create a symlink without elevation or Developer Mode: UNKNOWN")
        self.assertClass(os.path.join(link, "jarvis.toml"), TargetClass.GOVERNANCE_ZONE)

    def test_a_protected_root_that_is_itself_a_junction(self):
        """If a protected folder is a junction, the real folder is protected too."""
        if _winapi is None:
            self.skipTest("junctions need Windows")
        real = os.path.join(self.base, "real-secrets")
        os.makedirs(real)
        with open(os.path.join(real, "token"), "w", encoding="utf-8") as fh:
            fh.write("x")
        home2 = os.path.join(self.base, "home2")
        os.makedirs(home2)
        if not make_junction(os.path.join(home2, ".aws"), real):
            self.skipTest("cannot create a junction on this machine: UNKNOWN")
        roots = cz.build_roots(self.gov, self.data, self.repo, home2, (".aws",), None)
        result = cz.canonicalize_path(os.path.join(real, "token"), roots)
        self.assertIs(result.target_class, TargetClass.USER_SECRET_LOCATION)

    def test_short_8dot3_name(self):
        long_dir = os.path.join(self.data, "a long directory name for 8dot3")
        os.makedirs(long_dir)
        with open(os.path.join(long_dir, "f.txt"), "w", encoding="utf-8") as fh:
            fh.write("x")
        short = short_path(long_dir)
        if not short or short.lower() == long_dir.lower():
            self.skipTest("8.3 short names are not generated on this volume: UNKNOWN (LF-10)")
        self.assertNotEqual(short.lower(), long_dir.lower())
        self.assertClass(os.path.join(short, "f.txt"), TargetClass.DATA_ROOT)

    def test_short_8dot3_name_of_a_protected_root_itself(self):
        short = short_path(self.home)
        if not short or short.lower() == self.home.lower():
            self.skipTest("8.3 short names are not generated for this path: UNKNOWN (LF-10)")
        self.assertClass(os.path.join(short, ".ssh", "id_ed25519"), TargetClass.USER_SECRET_LOCATION)


if __name__ == "__main__":
    unittest.main()
