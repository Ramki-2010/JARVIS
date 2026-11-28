"""The phone's operator scripts: make_remote_token.py (the token and its hash) and remote_gate.py (the public-feature check).

Loaded from their files like the other operator scripts. Temporary files only, never RK's real settings; no real command is run.
Pinned: the token is shown once and only its SHA-256 is written; rotating changes the hash; revoking clears it; a bad file is
never changed; the gate allows only a quiet or tailnet-only status that proxies to exactly the fixed port, and refuses everything
else, including wording it does not recognise.
"""

import hashlib
import importlib.util
import io
import os
import re
import tempfile
import unittest

from advisor import remote_config

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    spec = importlib.util.spec_from_file_location(name + "_script", os.path.join(REPO, "scripts", name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mk = load("make_remote_token")
gate = load("remote_gate")

HOST = "laptop.example.ts.net"
TEMPLATE = '# private settings\n[remote]\nhostname = "%s"\nlogin = "someone@example"\nport = 47000\ntoken_sha256 = ""   # filled in by the script\n' % HOST


class Token(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "remote.toml")
        with open(self.path, "w", encoding="utf-8", newline="") as fh:
            fh.write(TEMPLATE)

    def run_script(self, *args):
        out = io.StringIO()
        code = mk.main(["--file", self.path, *args], out=out)
        return code, out.getvalue()

    def text(self):
        with open(self.path, encoding="utf-8") as fh:
            return fh.read()

    def test_a_new_token_is_shown_once_and_only_its_hash_is_written(self):
        code, out = self.run_script()
        self.assertEqual(code, 0)
        link = re.search(r"https://%s/#t=(\S+)" % re.escape(HOST), out)
        self.assertTrue(link, out)
        token = link.group(1)
        self.assertGreaterEqual(len(token), 43)                       # 32 random bytes, 256 bits
        content = self.text()
        self.assertNotIn(token, content)                              # the token is never stored
        digest = hashlib.sha256(token.encode()).hexdigest()
        self.assertIn('token_sha256 = "%s"   # filled in by the script' % digest, content)   # the comment survives
        self.assertTrue(content.startswith("# private settings\n"))
        cfg = remote_config.load(self.path)                           # and the file is now valid for the advisor
        self.assertEqual(cfg.token_sha256, digest)

    def test_rotating_changes_the_hash_and_the_old_link_no_longer_matches(self):
        _c, out1 = self.run_script()
        first = remote_config.load(self.path).token_sha256
        _c, out2 = self.run_script()
        second = remote_config.load(self.path).token_sha256
        self.assertNotEqual(first, second)
        old = re.search(r"#t=(\S+)", out1).group(1)
        self.assertNotEqual(hashlib.sha256(old.encode()).hexdigest(), second)

    def test_revoking_clears_the_hash_so_phone_access_cannot_start(self):
        self.run_script()
        code, out = self.run_script("--revoke")
        self.assertEqual(code, 0)
        self.assertNotIn("#t=", out)
        with self.assertRaises(remote_config.RemoteConfigError) as cm:
            remote_config.load(self.path)
        self.assertIn("no remote token", str(cm.exception))

    def test_a_bad_file_is_refused_and_left_untouched(self):
        for name, text in {"no hostname": '[remote]\nlogin = "x"\ntoken_sha256 = ""\n', "bad hostname": TEMPLATE.replace(HOST, "localhost"),
                           "two hash lines": TEMPLATE + 'token_sha256 = ""\n', "no hash line": TEMPLATE.replace('token_sha256 = ""', "")}.items():
            with self.subTest(case=name):
                with open(self.path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(text)
                code, out = self.run_script()
                self.assertEqual(code, 2)
                self.assertNotIn("#t=", out)
                self.assertEqual(self.text(), text)

    def test_a_relative_or_missing_path_is_refused(self):
        for path in ("remote.toml", os.path.join(self.tmp.name, "missing.toml")):
            out = io.StringIO()
            self.assertEqual(mk.main(["--file", path], out=out), 2)
            self.assertNotIn("#t=", out.getvalue())

    def test_no_temporary_file_is_left_behind(self):
        self.run_script()
        self.assertEqual(sorted(os.listdir(self.tmp.name)), ["remote.toml"])


QUIET = "No serve config"
TAILNET_ONLY = "https://laptop.example.ts.net (tailnet only)\n|-- / proxy http://127.0.0.1:47000\n"


class FakeSystem:
    def __init__(self, serve=QUIET, funnel=QUIET, installed=True, fail=()):
        self.outputs, self.installed, self.fail, self.asked = {"serve": serve, "funnel": funnel}, installed, set(fail), []

    def tailscale_path(self):
        return r"C:\Tailscale\tailscale.exe" if self.installed else ""

    def run(self, args, timeout=20):
        self.asked.append(list(args))
        what = args[1]
        if what in self.fail:
            return 1, "error: not logged in"
        return 0, self.outputs[what]


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "remote.toml")
        with open(self.path, "w", encoding="utf-8", newline="") as fh:
            fh.write(TEMPLATE.replace('token_sha256 = ""', 'token_sha256 = "%s"' % ("a" * 64)))

    def check(self, **kw):
        return gate.check(self.path, FakeSystem(**kw))

    def test_nothing_published_or_tailnet_only_to_the_fixed_port_is_allowed(self):
        self.assertTrue(self.check()[0])
        self.assertTrue(self.check(serve=TAILNET_ONLY, funnel=TAILNET_ONLY)[0])

    def test_funnel_on_is_refused_whatever_else_it_says(self):
        for text in ("https://laptop.example.ts.net (Funnel on)\n|-- / proxy http://127.0.0.1:47000", TAILNET_ONLY + "Funnel on: yes\n"):
            for which in ("serve", "funnel"):
                with self.subTest(text=text[:30], which=which):
                    ok, reason = self.check(**{which: text})
                    self.assertFalse(ok)
                    self.assertTrue(reason)

    def test_anything_else_is_refused(self):
        cases = {
            "another target": "https://laptop.example.ts.net (tailnet only)\n|-- / proxy http://127.0.0.1:9999\n",
            "a remote target": "https://laptop.example.ts.net (tailnet only)\n|-- / proxy http://10.0.0.5:47000\n",
            "not marked": "https://laptop.example.ts.net\n|-- / proxy http://127.0.0.1:47000\n",
            "unknown wording": "something new in a later version",
            "empty": "",
            "only a proxy line": "|-- / proxy http://127.0.0.1:47000\n",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                self.assertFalse(self.check(serve=text)[0], name)
                self.assertFalse(self.check(funnel=text)[0], name)

    def test_not_installed_unreadable_or_a_bad_file_is_refused(self):
        self.assertFalse(self.check(installed=False)[0])
        self.assertFalse(self.check(fail=("funnel",))[0])
        self.assertFalse(self.check(fail=("serve",))[0])
        with open(self.path, "w", encoding="utf-8", newline="") as fh:
            fh.write(TEMPLATE)   # empty token hash
        ok, reason = self.check()
        self.assertFalse(ok)
        self.assertIn("no remote token", reason)
        self.assertFalse(gate.check(os.path.join(self.tmp.name, "missing.toml"), FakeSystem())[0])

    def test_only_two_read_only_status_commands_are_asked_and_the_exit_code_follows(self):
        fake = FakeSystem()
        out = io.StringIO()
        self.assertEqual(gate.main(["--file", self.path], fake, out), 0)
        self.assertEqual([a[1:] for a in fake.asked], [["serve", "status"], ["funnel", "status"]])
        self.assertIn("may be switched on", out.getvalue())
        out = io.StringIO()
        self.assertEqual(gate.main(["--file", self.path], FakeSystem(funnel="https://x (Funnel on)"), out), 1)
        self.assertIn("stays OFF", out.getvalue())

    def test_the_start_script_runs_the_gate_only_when_asked_and_passes_the_option_only_on_success(self):
        with open(os.path.join(REPO, "scripts", "start-jarvis.cmd"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("if defined JARVIS_REMOTE", text)
        self.assertIn("remote_gate.py", text)
        self.assertIn('if errorlevel 1 (echo phone access stays off this time.) else set "REMOTE_ARG=--remote-file', text)
        self.assertIn("%REMOTE_ARG% %*", text)


if __name__ == "__main__":
    unittest.main()
