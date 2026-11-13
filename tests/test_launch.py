"""Governed local launch (ADR-0015, Beta acceptance BU-12): every limit in D2 to D5 has a test.

Temporary folders only. No test starts a real program: the launcher is a fake or Popen is mocked.
"""

import hashlib
import os
import re
import tempfile
import types
import unittest
from typing import NamedTuple
from unittest import mock

from advisor.controller import Controller
from interaction import intents, launch_catalog as lc, launch_child, launch_files as lf
from interaction.intents import recognise
from jarvis import cli

from tests.test_notes_cli import NotesCase

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V3_POLICY = os.path.join(REPO, "tests", "golden", "policy_v3.toml")


class Workspace(unittest.TestCase):
    """A temporary 'machine': fake programs and a media folder."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)
        self.bin = os.path.join(self.root, "bin")
        self.movies = os.path.join(self.root, "Movies")
        self.pics = os.path.join(self.root, "Pictures")
        for d in (self.bin, self.movies, self.pics):
            os.makedirs(d)
        for exe in ("vlc.exe", "tool.exe", "game.exe", "viewer.exe"):
            self.touch(os.path.join(self.bin, exe))
        self.env = {"USERPROFILE": self.root, "APPDATA": os.path.join(self.root, "AppData")}

    def touch(self, path, text=""):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def data(self, **extra):
        base = {"schema_version": 1,
                "app": [{"id": "vlc", "name": "VLC", "spoken": ["video player"], "exe": os.path.join(self.bin, "vlc.exe"),
                         "file_args": ["{file}"]},
                        {"id": "tool", "name": "Task Manager", "spoken": ["task manager", "processes"], "exe": os.path.join(self.bin, "tool.exe")},
                        {"id": "viewer", "name": "Viewer", "exe": os.path.join(self.bin, "viewer.exe"), "file_args": ["{file}"]}],
                "folder": [{"id": "movies", "name": "Movies", "path": self.movies},
                           {"id": "pictures", "name": "Pictures", "path": self.pics},
                           {"id": "home", "name": "Home", "path": "%USERPROFILE%"}],
                "game": [{"id": "chess", "name": "Chess Master", "spoken": ["chess"], "exe": os.path.join(self.bin, "game.exe"),
                          "args": ["-fullscreen"]}],
                "filetype": [{"program": "vlc", "extensions": [".mkv", ".mp4"], "folders": ["movies"]},
                             {"program": "viewer", "extensions": [".png"], "folders": ["pictures"]}]}
        base.update(extra)
        return base

    def catalog(self, **extra):
        return lc.parse(self.data(**extra), self.env)


class CatalogRules(Workspace):
    def test_a_good_catalog_loads_everything(self):
        cat = self.catalog()
        self.assertEqual(cat.notices, ())
        self.assertEqual((sorted(cat.apps), sorted(cat.folders), sorted(cat.games)), (["tool", "viewer", "vlc"], ["home", "movies", "pictures"], ["chess"]))
        self.assertEqual(cat.folders["home"].path, os.path.normpath(self.root))   # %USERPROFILE% expanded
        self.assertEqual(len(cat.rules), 2)
        self.assertEqual(cat.games["chess"].args, ("-fullscreen",))

    def test_only_the_allowed_variables_may_be_used(self):
        for raw in ("%PATH%\\x.exe", "%COMSPEC%", "%USERNAME%\\x.exe", "%NOSUCH%\\x.exe", "%USERPROFILE%%X%"):
            self.assertIsNone(lc.expand(raw, dict(self.env, PATH="p", COMSPEC="c", USERNAME="u")), raw)
        self.assertEqual(lc.expand("%USERPROFILE%\\a", self.env), self.root + "\\a")

    def test_bad_programs_and_folders_are_dropped_with_a_notice_that_names_only_the_id(self):
        bad_apps = [{"id": "rel", "name": "R", "exe": "tool.exe"}, {"id": "unc", "name": "U", "exe": "\\\\server\\share\\t.exe"},
                    {"id": "dots", "name": "D", "exe": self.bin + "\\..\\bin\\tool.exe"}, {"id": "nonexe", "name": "N", "exe": os.path.join(self.bin, "x.bat")},
                    {"id": "gone", "name": "G", "exe": os.path.join(self.bin, "gone.exe")}, {"id": "envx", "name": "E", "exe": "%PATH%\\tool.exe"},
                    {"id": "ctrl", "name": "C\x07", "exe": os.path.join(self.bin, "tool.exe")}, {"id": "Bad Id", "name": "B", "exe": os.path.join(self.bin, "tool.exe")}]
        cat = self.catalog(app=bad_apps, folder=[{"id": "nofolder", "name": "F", "path": os.path.join(self.root, "nope")},
                                                   {"id": "relf", "name": "F", "path": "Movies"}], game=[], filetype=[])
        self.assertEqual(cat.count(), 0)
        self.assertEqual(len(cat.notices), 10)
        joined = " ".join(cat.notices)
        self.assertNotIn(self.root, joined)
        self.assertNotIn("Bad Id", joined)

    def test_arguments_are_fixed_and_safe(self):
        def one(args, kind="app", key="args"):
            entry = {"id": "x", "name": "X", "exe": os.path.join(self.bin, "tool.exe"), key: args}
            return self.catalog(**{"app": [], "game": [], "folder": [], "filetype": [], kind: [entry]}).count()

        self.assertEqual(one(["ms-settings:"]), 1)
        self.assertEqual(one(["https://www.youtube.com/"]), 1)                     # a fixed address RK wrote
        self.assertEqual(one(["https://x.example/watch?v=1&t=2"]), 1)
        self.assertEqual(one(["http://x.example/"]), 0)                            # not https
        self.assertEqual(one(["ftp://x.example/"]), 0)
        self.assertEqual(one(["file:///C:/x"]), 0)
        self.assertEqual(one(["steam://rungameid/1"]), 0)                          # only for games
        self.assertEqual(one(["steam://rungameid/1"], kind="game"), 1)
        self.assertEqual(one(["steam://rungameid/1 && calc"], kind="game"), 0)
        self.assertEqual(one(["{file}"]), 0)                                       # the placeholder is for file_args only
        self.assertEqual(one(["{file}"], key="file_args"), 1)
        self.assertEqual(one(["--x={file}"], key="file_args"), 0)                  # only as a whole element
        self.assertEqual(one(["a\x00b"]), 0)
        self.assertEqual(one(["a\nb"]), 0)
        self.assertEqual(one(["x"] * 9), 0)
        self.assertEqual(one(["x" * 301]), 0)
        self.assertEqual(one("not a list"), 0)

    def test_the_entry_limit(self):
        many = [{"id": "f%d" % i, "name": "F%d" % i, "path": self.movies} for i in range(80)]
        cat = self.catalog(app=[], game=[], folder=many, filetype=[])
        self.assertEqual(cat.count(), lc.MAX_ENTRIES)
        self.assertTrue(any("more than 64" in n for n in cat.notices))

    def test_duplicates_and_a_wrong_schema(self):
        dup = self.catalog(game=[{"id": "tool", "name": "T", "exe": os.path.join(self.bin, "game.exe")}])
        self.assertEqual(len(dup.games), 0)
        self.assertEqual(lc.parse({"schema_version": 2}).count(), 0)
        self.assertTrue(lc.parse({}).notices)

    def test_file_type_rules_cannot_widen_the_allow_list_or_name_unknown_things(self):
        bad = [{"program": "vlc", "extensions": [".exe"], "folders": ["movies"]}, {"program": "vlc", "extensions": [".mkv", ".zip"], "folders": ["movies"]},
               {"program": "ghost", "extensions": [".mkv"], "folders": ["movies"]}, {"program": "vlc", "extensions": [".mkv"], "folders": ["ghost"]},
               {"program": "tool", "extensions": [".mkv"], "folders": ["movies"]},       # tool has no file_args
               {"program": "vlc", "extensions": [], "folders": ["movies"]}, {"program": "vlc", "extensions": [".mkv"], "folders": []}]
        cat = self.catalog(filetype=bad)
        self.assertEqual(cat.rules, ())
        self.assertEqual(len(cat.notices), 7)

    def test_lookup_by_id_name_and_spoken_name(self):
        cat = self.catalog()
        for said in ("task manager", "Task Manager", "the task manager", "processes", "tool"):
            self.assertEqual([e.id for e in lc.lookup(cat, said)], ["tool"], said)
        self.assertEqual([e.id for e in lc.lookup(cat, "chess")], ["chess"])
        self.assertEqual([e.id for e in lc.lookup(cat, "video player")], ["vlc"])
        self.assertEqual(lc.lookup(cat, "movies", "folder")[0].kind, "folder")
        self.assertEqual(lc.lookup(cat, "movies", "game"), [])
        for said in ("", "the", "task", "man", "nothing here", "tool; calc"):
            self.assertEqual(lc.lookup(cat, said), [], said)

    def test_load_reads_a_file_and_never_writes_it(self):
        path = os.path.join(self.root, "launch_catalog.toml")
        self.assertIsNone(lc.load(path))
        self.touch(path, "schema_version = 1\n[[folder]]\nid = 'movies'\nname = 'Movies'\npath = '%s'\n" % self.movies)
        before = os.stat(path).st_mtime_ns
        cat = lc.load(path, self.env)
        self.assertEqual(sorted(cat.folders), ["movies"])
        self.assertEqual(os.stat(path).st_mtime_ns, before)
        self.touch(path, "this is [not toml")
        self.assertEqual(lc.load(path).count(), 0)
        self.assertTrue(lc.load(path).notices)

    def test_recheck_notices_a_vanished_program(self):
        cat = self.catalog()
        self.assertTrue(lc.recheck(cat.apps["vlc"]))
        os.remove(cat.apps["vlc"].exe)
        self.assertFalse(lc.recheck(cat.apps["vlc"]))

    def test_the_never_open_list_and_the_allow_list_do_not_overlap(self):
        self.assertEqual(lc.FILE_EXTENSIONS & lc.NEVER_OPEN, frozenset())
        for ext in (".exe", ".msi", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".lnk", ".url", ".dll", ".zip", ".iso", ".hta", ".reg", ".scr"):
            self.assertIn(ext, lc.NEVER_OPEN, ext)


class ExampleCatalog(unittest.TestCase):
    def test_the_example_in_the_repository_is_valid_and_holds_no_personal_path(self):
        path = os.path.join(REPO, "docs", "examples", "launch_catalog.example.toml")
        env = {name: "C:\Sample\\" + name for name in lc.ALLOWED_VARS}
        import tomllib
        with open(path, "rb") as fh:
            raw = fh.read()
        cat = lc.parse(tomllib.loads(raw.decode("utf-8")), env, exists=lambda p: True, is_dir=lambda p: True)
        self.assertEqual(cat.notices, ())
        self.assertEqual((len(cat.apps), len(cat.folders), len(cat.games), len(cat.rules)), (10, 6, 1, 1))
        self.assertIsNone(re.search(rb"(?i)users[\/]+[a-z0-9._-]+|@[\w.-]+\.(com|net)", raw))


class FileFinding(Workspace):
    def setUp(self):
        super().setUp()
        self.touch(os.path.join(self.movies, "Dune.Part.Two.2024.mkv"))
        self.touch(os.path.join(self.movies, "Sub", "Deeper", "The Matrix (1999).mp4"))
        self.touch(os.path.join(self.movies, "dune.exe"))
        self.touch(os.path.join(self.movies, "dune.lnk"))
        self.touch(os.path.join(self.movies, "notes.txt"))
        self.roots = [("movies", self.movies)]
        self.exts = {".mkv", ".mp4", ".avi"}

    def names(self, query, **kw):
        return sorted(m.name for m in lf.find(self.roots, kw.pop("exts", self.exts), query, **kw).matches)

    def test_whole_word_case_and_punctuation_insensitive(self):
        self.assertEqual(self.names("dune"), ["Dune.Part.Two.2024.mkv"])
        self.assertEqual(self.names("DUNE part two"), ["Dune.Part.Two.2024.mkv"])
        self.assertEqual(self.names("the matrix"), ["The Matrix (1999).mp4"])
        self.assertEqual(self.names("matrix 1999"), ["The Matrix (1999).mp4"])
        self.assertEqual(self.names("dun"), [])            # not a whole word
        self.assertEqual(self.names("mat"), [])
        self.assertEqual(self.names("dune matrix"), [])    # every word must be present

    def test_forbidden_and_unlisted_extensions_are_never_found_whatever_the_caller_asks(self):
        self.assertEqual(self.names("dune", exts={".exe", ".lnk", ".mkv", ".txt"}), ["Dune.Part.Two.2024.mkv"] + [])  # .txt allowed by the list but no match
        self.assertEqual(self.names("dune", exts={".exe", ".lnk"}), [])
        self.assertEqual(self.names("notes", exts={".mkv"}), [])
        self.assertEqual(self.names("notes", exts={".txt"}), ["notes.txt"])
        self.assertEqual(self.names("dune", exts={".xyz"}), [])

    def test_query_tokens_are_validated(self):
        for bad in ("", "a", "x" * 61, "dune; calc", "..\\..\\x", "a/b", "dune|x", "<dune>", None, 5):
            self.assertEqual(lf.find(self.roots, self.exts, bad), lf.Found((), False), bad)

    def test_depth_entry_and_time_limits(self):
        deep = os.path.join(self.movies, "a", "b", "c", "d", "e")
        self.touch(os.path.join(deep, "Hidden Gem.mkv"))
        self.touch(os.path.join(self.movies, "a", "b", "c", "d", "Edge Case.mkv"))
        self.assertEqual(self.names("hidden gem"), [])        # depth 5: too deep
        self.assertEqual(self.names("edge case"), ["Edge Case.mkv"])   # depth 4
        self.assertTrue(lf.find(self.roots, self.exts, "dune", max_entries=2).truncated)
        ticks = iter([0.0] + [5.0] * 100)
        self.assertTrue(lf.find(self.roots, self.exts, "dune", clock=lambda: next(ticks)).truncated)

    def test_a_link_is_never_followed_or_opened(self):
        outside = os.path.join(self.root, "Outside")
        self.touch(os.path.join(outside, "Secret Film.mkv"))
        try:
            os.symlink(outside, os.path.join(self.movies, "linked"), target_is_directory=True)
            os.symlink(os.path.join(outside, "Secret Film.mkv"), os.path.join(self.movies, "Secret Link.mkv"))
        except (OSError, NotImplementedError):
            self.skipTest("this account may not create symbolic links")
        self.assertEqual(self.names("secret"), [])

    def test_containment_resolves_the_real_path(self):
        inside = os.path.join(self.movies, "ok.mkv")
        self.touch(inside)
        outside = self.touch(os.path.join(self.root, "Outside", "no.mkv"))
        self.assertTrue(lf.contained(inside, self.movies))
        self.assertFalse(lf.contained(outside, self.movies))
        self.assertFalse(lf.contained(os.path.join(self.movies, "..", "Outside", "no.mkv"), self.movies))
        self.assertFalse(lf.contained(os.path.join(self.movies, "missing.mkv"), self.movies))
        self.assertFalse(lf.contained(self.movies, self.movies))     # a folder is not a file

    def test_a_folder_that_does_not_exist_is_just_empty(self):
        self.assertEqual(lf.find([("x", os.path.join(self.root, "nope"))], self.exts, "dune"), lf.Found((), False))


class ChildRules(Workspace):
    def test_command_needs_an_absolute_local_exe_and_plain_arguments(self):
        exe = os.path.join(self.bin, "tool.exe")
        self.assertEqual(launch_child.command(exe, ["a", "b"]), [exe, "a", "b"])
        for bad in ("tool.exe", "\\\\server\\share\\tool.exe", os.path.join(self.bin, "x.bat"), os.path.join(self.bin, "x.exe\x07"), "", None, 5):
            with self.assertRaises(launch_child.LaunchRefused):
                launch_child.command(bad, [])
        for bad in (["a\x00"], [5], ["x"] * 9, ["x" * 601], "string"):
            with self.assertRaises(launch_child.LaunchRefused):
                launch_child.command(exe, bad)

    def test_the_environment_is_a_short_fixed_list_with_no_secrets(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "x", "ANTHROPIC_API_KEY": "y", "MY_SECRET": "z", "USERPROFILE": "C:\\u"}):
            env = launch_child.environment()
        self.assertTrue(set(env) <= set(launch_child._ENV_KEEP) | {"PATH"})
        self.assertEqual(env["USERPROFILE"], "C:\\u")
        for name in ("GITHUB_TOKEN", "ANTHROPIC_API_KEY", "MY_SECRET"):
            self.assertNotIn(name, env)
        self.assertEqual(env["PATH"].lower().endswith("system32"), True)

    def test_start_is_detached_with_no_shell_and_no_inherited_handles(self):
        exe = os.path.join(self.bin, "tool.exe")
        with mock.patch.object(launch_child.subprocess, "Popen") as popen:
            self.assertEqual(launch_child.start(exe, ["--x"]), launch_child.LaunchResult(True, ""))
        (cmd,), kw = popen.call_args
        self.assertEqual(cmd, [exe, "--x"])
        self.assertNotIn("shell", kw)
        self.assertEqual((kw["stdin"], kw["stdout"], kw["stderr"], kw["close_fds"]),
                         (launch_child.subprocess.DEVNULL, launch_child.subprocess.DEVNULL, launch_child.subprocess.DEVNULL, True))
        self.assertTrue(kw["creationflags"] & launch_child.subprocess.DETACHED_PROCESS)
        self.assertEqual(kw["cwd"], self.bin)

    def test_a_refusal_a_missing_program_and_a_failed_start_are_plain_results(self):
        exe = os.path.join(self.bin, "tool.exe")
        self.assertEqual(launch_child.start("relative.exe", []).error, "REFUSED")
        self.assertEqual(launch_child.start(os.path.join(self.bin, "gone.exe"), []).error, "MISSING")
        with mock.patch.object(launch_child.subprocess, "Popen", side_effect=OSError("blocked")):
            self.assertEqual(launch_child.start(exe, []), launch_child.LaunchResult(False, "FAILED"))


class LaunchCliTests(NotesCase):
    def launch(self, *argv, policy=None):
        extra = ["--policy", policy] if policy and argv and argv[0] == "authorize" else []
        return self.run_cli("launch", *argv, *extra)

    def events(self, name):
        return [r for r in self.records() if r["event"] == name]

    def test_every_kind_is_authorised_and_audited_under_the_real_policy(self):
        for kind in ("app", "folder", "file", "game"):
            self.assertEqual(self.launch("authorize", kind, "tool")[0], cli.EXIT_OK, kind)
        self.assertEqual(len(self.events("LAUNCH_AUTHORIZED")), 4)
        self.assertEqual(self.run_cli("audit", "verify")[0], cli.EXIT_OK)

    def test_unknown_kinds_and_ids_are_refused_before_anything_is_written(self):
        for kind, ident in (("shell", "x"), ("app", "Bad Id"), ("app", "../x"), ("app", ""), ("APP", "x"), ("app", "x" * 40)):
            code, text = self.launch("authorize", kind, ident)
            self.assertEqual(code, cli.EXIT_LAUNCH, (kind, ident))
        self.assertEqual(self.events("LAUNCH_AUTHORIZED") + self.events("LAUNCH_REFUSED"), [])

    def test_without_the_capability_the_open_is_refused_and_the_refusal_recorded(self):
        code, text = self.launch("authorize", "app", "tool", policy=V3_POLICY)
        self.assertEqual(code, cli.EXIT_LAUNCH, text)
        self.assertIn("LAUNCH_NOT_ALLOWED", text)
        self.assertEqual(len(self.events("LAUNCH_REFUSED")), 1)
        self.assertEqual(self.events("LAUNCH_AUTHORIZED"), [])

    def test_a_file_is_recorded_by_extension_and_path_hash_only(self):
        code, text = self.launch("record", "file", "vlc", "--result", "ok", "--ext", ".mkv", "--hash", "0a1b2c3d")
        self.assertEqual(code, cli.EXIT_OK, text)
        (rec,) = self.events("LAUNCH_RECORDED")
        self.assertEqual(rec["detail"], {"kind": "file", "id": "vlc", "result": "ok", "ext": ".mkv", "path_hash": "0a1b2c3d"})
        self.assertEqual(rec["provenance"]["detail"], "MEDIATED")
        self.assertEqual(self.run_cli("audit", "verify")[0], cli.EXIT_OK)

    def test_bad_records_are_refused(self):
        bad = [("app", "tool", "maybe", "", ""), ("app", "tool", "ok", ".mkv", ""), ("app", "tool", "ok", "", "0a1b2c3d"),
               ("file", "vlc", "ok", "mkv", "0a1b2c3d"), ("file", "vlc", "ok", ".mkv", "ZZZZZZZZ"), ("file", "vlc", "ok", ".mkv", "0a1b2c3d4"),
               ("file", "vlc", "ok", ".movie name", "0a1b2c3d"), ("bogus", "tool", "ok", "", "")]
        for kind, ident, result, ext, digest in bad:
            with self.subTest(kind=kind, result=result, ext=ext, digest=digest):
                code, _t = self.launch("record", kind, ident, "--result", result, "--ext", ext, "--hash", digest)
                self.assertNotEqual(code, cli.EXIT_OK)
        self.assertEqual(self.events("LAUNCH_RECORDED"), [])

    def test_no_file_name_can_reach_the_record(self):
        self.assertNotEqual(self.launch("record", "file", "vlc", "--result", "ok", "--name", "Dune.mkv")[0], cli.EXIT_OK)
        self.assertNotEqual(self.launch("record", "file", "vlc", "--result", "ok", "--path", "C:\\x\\Dune.mkv")[0], cli.EXIT_OK)


class FakeConversation:
    """Stands in for the model: reaching it is how a test notices a phrase was treated as ordinary conversation."""

    def __init__(self):
        self.heard = []

    def stream_reply(self, text):
        self.heard.append(text)
        return iter(["Conversation reply."])


class Result(NamedTuple):
    code: int
    text: str = ""
    truncated: bool = False


class Flow(Workspace):
    """The conversation, with a fake control plane, a fake launcher and the real catalog and file finder."""

    def setUp(self):
        super().setUp()
        self.touch(os.path.join(self.movies, "Dune.Part.Two.2024.mkv"))
        self.touch(os.path.join(self.movies, "Dune 1984.mkv"))
        self.touch(os.path.join(self.movies, "The Matrix (1999).mp4"))
        self.touch(os.path.join(self.pics, "Holiday.png"))
        self.cat = self.catalog()
        self.calls, self.started = [], []
        self.allow, self.start_ok = True, True

    def make(self, with_launch=True):
        def runner(args):
            self.calls.append(list(args))
            return Result(0 if (self.allow or args[:2] != ["launch", "authorize"]) else 15)

        def launcher(exe, args):
            self.started.append((exe, list(args)))
            return launch_child.LaunchResult(self.start_ok, "" if self.start_ok else "FAILED")

        self.conversation = FakeConversation()
        return Controller(self.conversation, runner, launcher=launcher if with_launch else None, catalog_source=(lambda: self.cat) if with_launch else None)

    def say(self, ctl, text):
        return [t for _k, t in ctl.respond(text)]

    def test_an_app_opens_at_once_and_is_audited_before_and_after(self):
        ctl = self.make()
        self.assertEqual(self.say(ctl, "open task manager"), ["Opening Task Manager, sir."])
        self.assertEqual(self.started, [(os.path.normpath(os.path.join(self.bin, "tool.exe")), [])])
        self.assertEqual(self.calls, [["launch", "authorize", "app", "tool"], ["launch", "record", "app", "tool", "--result", "ok"]])

    def test_spoken_aliases_and_polite_wording(self):
        ctl = self.make()
        for said in ("open the processes", "Launch task manager please", "Jarvis, could you start the task manager, sir", "bring up task manager"):
            self.started.clear()
            self.assertEqual(self.say(ctl, said), ["Opening Task Manager, sir."], said)
            self.assertEqual(len(self.started), 1)

    def test_a_folder_opens_in_explorer_with_the_catalog_path_as_the_only_argument(self):
        ctl = self.make()
        self.assertEqual(self.say(ctl, "open my movies folder"), ["Opening Movies, sir."])
        (exe, args), = self.started
        self.assertTrue(exe.lower().endswith("explorer.exe"))
        self.assertEqual(args, [os.path.normpath(self.movies)])
        self.assertEqual(self.calls[0], ["launch", "authorize", "folder", "movies"])

    def test_play_never_opens_a_folder_and_open_can(self):
        ctl = self.make()
        self.assertEqual(self.say(ctl, "play the movies folder"), ["I could not find that, sir."])
        self.assertEqual(self.started, [])

    def test_a_game_waits_for_a_yes(self):
        ctl = self.make()
        self.assertEqual(self.say(ctl, "play chess"), ["Shall I start Chess Master, sir?"])
        self.assertEqual((self.started, self.calls), ([], []))
        self.assertEqual(self.say(ctl, "yes"), ["Starting Chess Master, sir."])
        self.assertEqual(self.started, [(os.path.normpath(os.path.join(self.bin, "game.exe")), ["-fullscreen"])])
        self.assertEqual(self.calls[0], ["launch", "authorize", "game", "chess"])

    def test_a_no_or_an_unrelated_reply_abandons_the_proposal(self):
        for reply in ("no", "what is the status"):
            ctl = self.make()
            self.say(ctl, "play chess")
            self.say(ctl, reply)
            self.say(ctl, "yes")
            self.assertEqual(self.started, [], reply)

    def test_a_single_file_is_named_and_waits_for_a_yes(self):
        ctl = self.make()
        said = self.say(ctl, "play the matrix movie")
        self.assertEqual(said, ["I found The Matrix (1999). Shall I open it in VLC, sir?"])
        self.assertEqual((self.started, self.calls), ([], []))
        self.assertEqual(self.say(ctl, "yes please"), ["Opening The Matrix (1999), sir."])
        (exe, args), = self.started
        self.assertEqual(args, [os.path.join(self.movies, "The Matrix (1999).mp4")])
        self.assertTrue(exe.endswith("vlc.exe"))

    def test_the_audit_never_holds_the_file_name(self):
        ctl = self.make()
        self.say(ctl, "watch the matrix")
        self.say(ctl, "yes")
        record = next(c for c in self.calls if c[:2] == ["launch", "record"])
        self.assertEqual(record[:5], ["launch", "record", "file", "vlc", "--result"])
        self.assertEqual(record[5:7], ["ok", "--ext"])
        self.assertEqual(record[7], ".mp4")
        self.assertRegex(record[9], r"^[0-9a-f]{8}$")
        every_word = " ".join(" ".join(c) for c in self.calls).lower()
        self.assertNotIn("matrix", every_word)
        self.assertNotIn(self.movies.lower(), every_word)

    def test_several_files_ask_which_and_then_confirm(self):
        ctl = self.make()
        said = self.say(ctl, "play dune")
        self.assertIn("I found 2", said[-1])
        self.assertEqual(self.started, [])
        offer = self.say(ctl, "the second one")
        self.assertIn("Shall I open it in VLC", offer[0])
        self.assertEqual(self.started, [])
        self.say(ctl, "yes")
        self.assertEqual(len(self.started), 1)
        self.assertIn("Dune", os.path.basename(self.started[0][1][0]))

    def test_a_bad_choice_or_a_no_starts_nothing(self):
        for reply in ("seventh", "no", "9"):
            ctl = self.make()
            self.say(ctl, "play dune")
            self.say(ctl, reply)
            self.say(ctl, "yes")
            self.assertEqual(self.started, [], reply)

    def test_a_file_type_without_a_rule_is_not_found(self):
        self.touch(os.path.join(self.movies, "Evil.exe"))
        self.touch(os.path.join(self.movies, "Evil Doc.pdf"))
        ctl = self.make()
        for said in ("open evil", "play evil doc", "open evil exe"):
            self.assertNotIn("Shall I", " ".join(self.say(ctl, said)), said)
        self.assertEqual(self.started, [])

    def test_policy_denied_means_nothing_starts(self):
        self.allow = False
        ctl = self.make()
        self.assertEqual(self.say(ctl, "open task manager"), ["That is not permitted, sir."])
        self.assertEqual(self.started, [])
        self.assertEqual([c[:2] for c in self.calls], [["launch", "authorize"]])   # no 'ok' record for something that did not happen

    def test_a_failed_start_changes_nothing_and_is_recorded_as_failed(self):
        self.start_ok = False
        ctl = self.make()
        events = list(ctl.respond("open task manager"))
        self.assertEqual(events, [("error", "I could not start Task Manager, sir. Nothing has changed.")])
        self.assertEqual(self.calls[-1][-2:], ["--result", "failed"])

    def test_a_program_that_has_vanished_is_noticed_before_use(self):
        os.remove(self.cat.apps["tool"].exe)
        ctl = self.make()
        self.assertIn("cannot find it on this machine", self.say(ctl, "open task manager")[0])
        self.assertEqual((self.started, self.calls), ([], []))

    def test_an_unlisted_name_is_not_on_the_list(self):
        ctl = self.make()
        for said in ("open the browser", "open youtube", "launch calc", "open the pod bay doors"):
            self.assertEqual(self.say(ctl, said), ["That is not on my list, sir."], said)
        self.assertEqual((self.started, self.calls), ([], []))

    def test_things_that_are_not_requests_to_open_are_still_conversation(self):
        ctl = self.make()
        self.assertEqual(recognise("start over"), None)
        self.assertEqual(self.say(ctl, "play it by ear"), ["Conversation reply."])
        self.assertEqual(self.conversation.heard, ["play it by ear"])
        self.assertEqual(self.started, [])

    def test_when_launching_is_off_the_old_plain_answer_stands(self):
        ctl = self.make(with_launch=False)
        said = self.say(ctl, "open task manager")
        self.assertIn("no network, browser or phone access", said[0])
        self.assertEqual((self.started, self.calls), ([], []))
        self.assertEqual(ctl.pending, "open task manager")

    def test_the_catalog_is_read_afresh_for_each_request(self):
        ctl = self.make()
        self.say(ctl, "open task manager")
        self.cat = lc.EMPTY
        self.assertEqual(self.say(ctl, "open task manager"), ["That is not on my list, sir."])

    def test_hostile_names_are_only_ever_lookup_tokens(self):
        ctl = self.make()
        for said in ("open ..\\..\\windows\\system32\\cmd.exe", "open c:\\windows\\system32\\calc.exe", "open tool.exe && calc",
                     "open http://evil.example/x", "open " + "a" * 200, "open $(calc)", "launch %comspec%"):
            self.say(ctl, said)
        self.assertEqual(self.started, [])


class LaunchPhrases(unittest.TestCase):
    def test_phrases(self):
        cases = {"open task manager": ("open", "", "task manager"), "launch vlc": ("launch", "", "vlc"),
                 "play the dune movie": ("play", "file", "dune"), "open my downloads folder": ("open", "folder", "downloads"),
                 "show me the videos folder": ("show me", "folder", "videos"), "watch dune": ("watch", "", "dune"),
                 "listen to rahman songs": ("listen to", "file", "rahman"), "play minecraft game": ("play", "game", "minecraft"),
                 "open settings please, sir": ("open", "", "settings")}
        for text, (verb, hint, name) in cases.items():
            got = recognise(text)
            self.assertIsNotNone(got, text)
            self.assertEqual((got.kind, got.args, got.text), (intents.LAUNCH, (verb, hint), name), text)

    def test_other_intents_keep_their_phrases(self):
        self.assertEqual(recognise("show me my projects").kind, intents.READ)
        self.assertEqual(recognise("list notes").kind, intents.READ)
        self.assertEqual(recognise("show me the news").kind, intents.NEWS)
        self.assertEqual(recognise("start over"), None)

    def test_the_name_never_carries_more_than_plain_words(self):
        for text in ("open ../x", "open c:\\x.exe", "open x; calc", "open a|b", "open $(x)", "open " + "a" * 100):
            got = recognise(text)
            if got is not None and got.kind == intents.LAUNCH:
                self.assertRegex(got.text, r"^[a-z0-9][a-z0-9 .'-]{1,59}$")


if __name__ == "__main__":
    unittest.main()
