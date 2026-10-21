"""Configuration (X-08 / C3) and CLI tests. Temporary directories only."""

import io
import os
import sqlite3
import tempfile
import unittest

from jarvis import cli
from jarvis import config as cfg
from jarvis.store import Store

GOOD = (b"schema_version = 1\r\n"
        b"data_root = 'C:\\data'\r\n"
        b"governance_zone = 'C:\\gov'\r\n"
        b"user_home = 'C:\\home'\r\n")


def good(**over):
    lines = {"schema_version": "1", "data_root": "'C:\\data'", "governance_zone": "'C:\\gov'",
             "user_home": "'C:\\home'"}
    lines.update(over)
    return "\n".join("%s = %s" % kv for kv in lines.items()).encode("utf-8") + b"\n"


class ConfigTests(unittest.TestCase):
    def test_parse_and_hash_is_line_ending_independent(self):
        a = cfg.parse(GOOD)
        b = cfg.parse(GOOD.replace(b"\r\n", b"\n"))
        self.assertEqual(a, b)
        self.assertEqual(a.data_root, "C:\\data")
        self.assertEqual(a.busy_timeout_ms, 5000)

    def test_secret_like_environment_variable_does_not_change_config(self):
        """X-08 (C3): byte-identical configuration with and without it."""
        name = "JARVIS_TEST_API_TOKEN"
        before = cfg.parse(GOOD)
        os.environ[name] = "not-a-real-secret"
        try:
            after = cfg.parse(GOOD)
        finally:
            del os.environ[name]
        self.assertEqual(before, after)

    def test_secret_like_key_rejected(self):
        for key in ("api_key", "github_token", "password", "client_secret"):
            with self.subTest(key=key):
                with self.assertRaises(cfg.ConfigError) as ctx:
                    cfg.parse(good(**{key: "'x'"}))
                self.assertEqual(ctx.exception.code, "CONFIG_SECRET_LIKE_KEY")

    def test_unknown_or_missing_keys_rejected(self):
        with self.assertRaises(cfg.ConfigError):
            cfg.parse(good(colour="'blue'"))
        with self.assertRaises(cfg.ConfigError):
            cfg.parse(b"schema_version = 1\n")
        # user_home is required (ADR-0008 consequences) and must be an absolute path.
        without_home = good().replace(b"user_home = 'C:\\home'\n", b"")
        with self.assertRaises(cfg.ConfigError) as ctx:
            cfg.parse(without_home)
        self.assertEqual(ctx.exception.code, "CONFIG_KEYS_INVALID")
        with self.assertRaises(cfg.ConfigError) as ctx:
            cfg.parse(good(user_home="'relative\\home'"))
        self.assertEqual(ctx.exception.code, "CONFIG_PATH_INVALID")

    def test_user_home_comes_only_from_the_file(self):
        """ADR-0006 3.3: the environment never supplies it."""
        saved = os.environ.get("USERPROFILE")
        os.environ["USERPROFILE"] = "C:\\somebody-else"
        try:
            self.assertEqual(cfg.parse(GOOD).user_home, "C:\\home")
        finally:
            if saved is None:
                del os.environ["USERPROFILE"]
            else:
                os.environ["USERPROFILE"] = saved

    def test_schema_and_values(self):
        with self.assertRaises(cfg.ConfigError) as ctx:
            cfg.parse(good(schema_version="2"))
        self.assertEqual(ctx.exception.code, "CONFIG_SCHEMA_UNKNOWN")
        with self.assertRaises(cfg.ConfigError):
            cfg.parse(good(data_root="'relative\\path'"))
        with self.assertRaises(cfg.ConfigError):
            cfg.parse(good(busy_timeout_ms="0"))

    def test_lone_cr_and_bad_utf8_rejected(self):
        with self.assertRaises(cfg.ConfigError):
            cfg.parse(b"schema_version = 1\r")
        with self.assertRaises(cfg.ConfigError):
            cfg.parse(b"\xff\xfe")

    def test_missing_file(self):
        with self.assertRaises(cfg.ConfigError) as ctx:
            cfg.load(os.path.join(tempfile.gettempdir(), "no-such-jarvis-config.toml"))
        self.assertEqual(ctx.exception.code, "CONFIG_UNAVAILABLE")


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        self.data = os.path.join(root, "data")
        self.gov = os.path.join(root, "governance")
        os.makedirs(self.data)
        os.makedirs(self.gov)
        self.config_path = os.path.join(self.gov, "jarvis.toml")
        with open(self.config_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("schema_version = 1\ndata_root = '%s'\ngovernance_zone = '%s'\n"
                     "user_home = '%s'\n" % (self.data, self.gov, root))

    def run_cli(self, *args):
        out = io.StringIO()
        code = cli.main(["--config", self.config_path, *args], out=out)
        return code, out.getvalue()

    def test_missing_config(self):
        out = io.StringIO()
        code = cli.main(["--config", os.path.join(self.gov, "absent.toml"), "status"], out=out)
        self.assertEqual(code, cli.EXIT_CONFIG)
        self.assertIn("CONFIG_UNAVAILABLE", out.getvalue())

    def test_status_without_store(self):
        code, out = self.run_cli("status")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("store: not initialized", out)

    def test_status_and_verify_with_store(self):
        Store.create(self.data, "2026-10-21T10:00:00.000000Z", "tester", ((1, "a" * 64),)).close()
        code, out = self.run_cli("status")
        self.assertEqual(code, cli.EXIT_OK, out)
        self.assertIn("audit_tail_seq: 0", out)
        code, out = self.run_cli("audit", "verify")
        self.assertEqual(code, cli.EXIT_OK, out)
        self.assertIn("audit verify: OK", out)

    def test_verify_detects_tampering(self):
        store = Store.create(self.data, "2026-10-21T10:00:00.000000Z", "tester", ((1, "a" * 64),))
        store.create_task("t-1", "jarvis-cp", "x", "2026-10-21T10:00:01.000000Z", "tester")
        store.close()
        conn = sqlite3.connect(Store.db_path(self.data), isolation_level=None)
        data = conn.execute("SELECT record FROM audit_log WHERE seq = 1").fetchone()[0]
        conn.execute("UPDATE audit_log SET record = ? WHERE seq = 1", (data + b" ",))
        conn.close()
        code, out = self.run_cli("audit", "verify")
        self.assertEqual(code, cli.EXIT_AUDIT)
        self.assertIn("RECORD_HASH_MISMATCH", out)

    def test_verify_without_store(self):
        code, _ = self.run_cli("audit", "verify")
        self.assertEqual(code, cli.EXIT_STORE_MISSING)

    def test_usage_error(self):
        out = io.StringIO()
        self.assertEqual(cli.main(["frobnicate"], out=out), cli.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
