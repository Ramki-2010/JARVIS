"""scripts/free_memory.py: RK's own memory-freeing script (closes the programs on RK's list before JARVIS runs).

Like the other operator scripts it is loaded from its file. No test ever closes a real program: a stand-in for the
machine records what it is asked. Pinned here: it only acts on RK's list; the never-touch set cannot be overridden; a dry
run touches nothing; "force" is used only where the entry allows it; a program that will not close is left open and said
so; the freed memory is measured, never assumed; and JARVIS itself has no way to close anything.
"""

import importlib.util
import os
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("free_memory_script", os.path.join(REPO, "scripts", "free_memory.py"))
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)


class FakeSystem:
    """A machine that records every request. `stubborn` programs ignore a polite close; `immortal` ones ignore force too."""

    def __init__(self, procs, stubborn=(), immortal=(), freed_gb=0.0):
        self.procs = dict(procs)   # pid -> (image, mb)
        self.stubborn, self.immortal, self.freed_gb = set(stubborn), set(immortal), freed_gb
        self.asked, self.forced, self.slept, self.base = [], [], 0.0, 10.0

    def processes(self):
        return [fm.Proc(pid, image, mb) for pid, (image, mb) in self.procs.items()]

    def ask_close(self, pid):
        self.asked.append(pid)
        if pid in self.procs and self.procs[pid][0] not in self.stubborn and self.procs[pid][0] not in self.immortal:
            del self.procs[pid]

    def force_close(self, pid):
        self.forced.append(pid)
        if pid in self.procs and self.procs[pid][0] not in self.immortal:
            del self.procs[pid]

    def available_gb(self):
        closed = 0.0 if not self.asked else self.freed_gb
        return self.base + closed

    def sleep(self, seconds):
        self.slept += seconds


def entry(id="x", images=("x",), force=False, grace=2.0, last=False):
    return fm.Entry(id, id.title(), tuple(images), force, grace, last)


def write(text):
    handle = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False, encoding="utf-8")
    handle.write(text)
    handle.close()
    return handle.name


HEAD = 'schema_version = 1\n'
ONE = '[[program]]\nid = "a"\nname = "A"\nimages = ["%s"]\n'


class ListTests(unittest.TestCase):
    def load(self, text):
        path = write(text)
        try:
            return fm.load_list(path)
        finally:
            os.unlink(path)

    def test_the_example_in_the_repository_is_valid(self):
        entries = fm.load_list(os.path.join(REPO, "docs", "examples", "close_list.example.toml"))
        self.assertGreaterEqual(len(entries), 3)
        self.assertTrue(entries[-1].last)            # the VPN comes last
        self.assertFalse([e for e in entries if e.images[0] == "zen"][0].force)   # a browser is never ended by force
        for e in entries:
            self.assertFalse(set(e.images) & fm.PROTECTED)

    def test_defaults_names_and_the_exe_suffix(self):
        e = self.load(HEAD + ONE % "Spotify.exe")[0]
        self.assertEqual((e.images, e.force, e.grace, e.last), (("spotify",), False, 10.0, False))

    def test_last_programs_are_moved_to_the_end_and_the_rest_keep_their_order(self):
        text = HEAD + (ONE % "a").replace('id = "a"', 'id = "vpn"') + 'last = true\n' + (ONE % "b").replace('id = "a"', 'id = "one"') + (ONE % "c").replace('id = "a"', 'id = "two"')
        self.assertEqual([e.id for e in self.load(text)], ["one", "two", "vpn"])

    def test_anything_that_could_widen_what_is_closed_is_refused(self):
        bad = {
            "a path": ONE % "C:\\\\Windows\\\\x",
            "a wildcard": ONE % "*",
            "a parent folder": ONE % "..\\\\x",
            "a quote": ONE % 'x"y',
            "an empty name": ONE % "",
            "an unknown key": ONE % "x" + 'kill_children = true\n',
            "a bad id": (ONE % "x").replace('id = "a"', 'id = "A B"'),
            "force as text": ONE % "x" + 'force = "yes"\n',
            "grace too long": ONE % "x" + 'grace = 9999\n',
            "grace zero": ONE % "x" + 'grace = 0\n',
            "grace true": ONE % "x" + 'grace = true\n',
        }
        for name, body in bad.items():
            with self.subTest(name), self.assertRaises(fm.ListError):
                self.load(HEAD + body)
        for name, text in {"no schema": ONE % "x", "wrong schema": 'schema_version = 2\n' + ONE % "x", "unknown top key": HEAD + 'extra = 1\n',
                           "not toml": "[[[", "duplicate id": HEAD + ONE % "x" + ONE % "y"}.items():
            with self.subTest(name), self.assertRaises(fm.ListError):
                self.load(text)

    def test_at_most_thirty_two_programs(self):
        rows = "".join('[[program]]\nid = "p%d"\nname = "P"\nimages = ["p%d"]\n' % (i, i) for i in range(33))
        with self.assertRaises(fm.ListError):
            self.load(HEAD + rows)

    def test_a_byte_order_mark_from_an_editor_is_accepted(self):
        path = write("\ufeff" + HEAD + ONE % "x")
        try:
            self.assertEqual(fm.load_list(path)[0].images, ("x",))
        finally:
            os.unlink(path)

    def test_a_missing_file_is_a_plain_error(self):
        with self.assertRaises(fm.ListError):
            fm.load_list(os.path.join(tempfile.gettempdir(), "no-such-close-list.toml"))


class RunTests(unittest.TestCase):
    def go(self, entries, system, apply=True):
        lines = []
        results, before, after = fm.run(entries, system, apply, lines.append)
        return results, before, after, lines

    def test_a_dry_run_asks_for_nothing_and_reports_what_it_would_do(self):
        system = FakeSystem({1: ("zen", 100.0), 2: ("zen", 50.0)})
        results, before, after, lines = self.go([entry("zen", ("zen",))], system, apply=False)
        self.assertEqual((system.asked, system.forced, system.slept), ([], [], 0.0))
        self.assertEqual((results[0].status, results[0].count, results[0].mb), ("would close", 2, 150.0))
        self.assertIsNone(after)
        self.assertEqual(len(system.procs), 2)

    def test_a_program_that_closes_when_asked_is_never_forced(self):
        system = FakeSystem({1: ("spotify", 90.0)})
        results, *_ = self.go([entry("spotify", ("spotify",), force=True)], system)
        self.assertEqual(results[0].status, "closed")
        self.assertEqual((system.asked, system.forced), ([1], []))

    def test_a_stubborn_program_is_left_open_unless_the_entry_allows_force(self):
        system = FakeSystem({1: ("zen", 100.0)}, stubborn={"zen"})
        results, *_ = self.go([entry("zen", ("zen",), force=False, grace=3.0)], system)
        self.assertEqual(results[0].status, "left open (still running)")
        self.assertEqual(system.forced, [])
        self.assertEqual(len(system.procs), 1)
        self.assertGreaterEqual(system.slept, 3.0)      # it waited the grace period before giving up

    def test_force_is_used_only_after_the_grace_period_and_only_where_allowed(self):
        system = FakeSystem({1: ("teams", 200.0)}, stubborn={"teams"})
        results, *_ = self.go([entry("teams", ("teams",), force=True, grace=2.0)], system)
        self.assertEqual(results[0].status, "closed by force")
        self.assertEqual((system.asked, system.forced), ([1], [1]))
        self.assertGreaterEqual(system.slept, 2.0)

    def test_a_program_that_cannot_be_ended_is_reported_not_claimed(self):
        system = FakeSystem({1: ("odd", 10.0)}, immortal={"odd"})
        results, *_ = self.go([entry("odd", ("odd",), force=True, grace=1.0)], system)
        self.assertEqual(results[0].status, "left open (still running)")

    def test_programs_that_are_not_running_are_skipped_without_a_call(self):
        system = FakeSystem({1: ("other", 10.0)})
        results, *_ = self.go([entry("gone", ("gone",))], system)
        self.assertEqual(results[0].status, "not running")
        self.assertEqual((system.asked, system.forced), ([], []))
        self.assertEqual(len(system.procs), 1)

    def test_only_exactly_named_programs_are_touched(self):
        system = FakeSystem({1: ("zen", 10.0), 2: ("zenith", 10.0), 3: ("azen", 10.0), 4: ("windscribeservice", 10.0), 5: ("windscribe", 10.0)})
        self.go([entry("zen", ("zen",)), entry("vpn", ("windscribe",))], system)
        self.assertEqual(sorted(system.asked), [1, 5])
        self.assertEqual(sorted(system.procs), [2, 3, 4])       # similar names, and the background service, are untouched

    def test_the_never_touch_set_cannot_be_overridden_by_the_list(self):
        for name in ("claude", "ollama", "llama-server", "python", "py", "explorer", "msmpeng", "svchost", "powershell", "voice"):
            self.assertIn(name, fm.PROTECTED, name)
            system = FakeSystem({1: (name, 500.0)})
            results, *_ = self.go([entry("bad", (name,), force=True)], system)
            self.assertEqual(results[0].status, "refused (never touched)", name)
            self.assertEqual((system.asked, system.forced), ([], []), name)
            self.assertEqual(len(system.procs), 1, name)

    def test_a_protected_name_is_refused_even_inside_a_list_with_other_entries(self):
        system = FakeSystem({1: ("claude", 100.0), 2: ("spotify", 50.0)})
        results, *_ = self.go([entry("a", ("spotify", "claude"), force=True)], system)
        self.assertEqual(results[0].status, "refused (never touched)")
        self.assertEqual(len(system.procs), 2)                  # the whole entry is refused, nothing in it is closed

    def test_it_never_touches_its_own_process(self):
        system = FakeSystem({os.getpid(): ("zen", 10.0)})
        results, *_ = self.go([entry("zen", ("zen",))], system)
        self.assertEqual(results[0].status, "not running")
        self.assertEqual(system.asked, [])

    def test_the_vpn_is_closed_after_the_torrent_client(self):
        system = FakeSystem({1: ("windscribe", 66.0), 2: ("tixati", 90.0)})
        order = [entry("vpn", ("windscribe",), last=True), entry("tixati", ("tixati",))]
        ordered = sorted(order, key=lambda e: e.last)
        fm.run(ordered, system, True, lambda line: None)
        self.assertEqual(system.asked, [2, 1])                 # Tixati (pid 2) first, then the VPN (pid 1)

    def test_the_freed_memory_is_measured_from_the_machine_not_estimated(self):
        system = FakeSystem({1: ("zen", 2000.0)}, freed_gb=2.4)
        _, before, after, _ = self.go([entry("zen", ("zen",))], system)
        self.assertEqual((before, after), (10.0, 12.4))
        self.assertGreaterEqual(system.slept, fm.SETTLE_SECONDS)   # it waits for Windows to reclaim before measuring


class MainTests(unittest.TestCase):
    def test_a_bad_list_closes_nothing_and_says_so(self):
        system = FakeSystem({1: ("zen", 10.0)})
        path = write("not a list")
        try:
            self.assertEqual(fm.main(["--list", path, "--apply", "--log", os.devnull], system), 2)
        finally:
            os.unlink(path)
        self.assertEqual((system.asked, system.forced), ([], []))

    def test_the_default_is_a_dry_run_and_a_log_line_is_written(self):
        system = FakeSystem({1: ("spotify", 10.0)})
        folder = tempfile.mkdtemp()
        gov = os.path.join(folder, "governance")
        os.makedirs(gov)
        path = os.path.join(gov, "close_list.toml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(HEAD + ONE % "spotify")
        self.assertEqual(fm.main(["--list", path], system), 0)
        self.assertEqual((system.asked, system.forced), ([], []))      # without --apply nothing is closed
        with open(os.path.join(folder, "free_memory.log"), encoding="utf-8") as fh:
            record = fh.read()
        self.assertIn('"apply": false', record)
        self.assertEqual(fm.main(["--list", path, "--apply"], system), 0)
        self.assertEqual(system.asked, [1])


class BoundaryTests(unittest.TestCase):
    """JARVIS itself cannot close a program: only this operator script, run by RK's launcher, can."""

    def sources(self, folder):
        for dirpath, _d, names in os.walk(os.path.join(REPO, folder)):
            for name in names:
                if name.endswith(".py"):
                    path = os.path.join(dirpath, name)
                    with open(path, encoding="utf-8") as fh:
                        yield path, fh.read()

    def test_no_jarvis_package_can_end_a_program_or_runs_the_script(self):
        for folder in ("jarvis", "advisor", "ui", "interaction", "voice", "fetcher"):
            for path, text in self.sources(folder):
                for needle in ("taskkill", "TerminateProcess", "free_memory", "close_list"):
                    self.assertNotIn(needle, text, (path, needle))

    def test_the_launcher_runs_the_script_before_the_advisor_and_can_skip_it(self):
        with open(os.path.join(REPO, "scripts", "start-jarvis.cmd"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertLess(text.index("free_memory.py"), text.index("-m advisor"))
        self.assertIn("JARVIS_NO_FREE", text)
        self.assertIn("free_memory.py --apply", text)


if __name__ == "__main__":
    unittest.main()
