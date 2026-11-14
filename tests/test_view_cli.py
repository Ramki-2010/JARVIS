"""`view`, the static read-only HTML snapshot (Beta plan BS-3).

The page must be inert (no script, no external load), must escape every string a person,
a file or a worker controls, must show result metadata only, must not depend on the
clock, and must write only its own derived file. Temporary directories only.
"""

import hashlib
import io
import os
from html.parser import HTMLParser
import re
import sqlite3

from jarvis import cli, view
from jarvis.store import Store

from .test_result_cli import ADVERSARIAL, ResultCase

EVIL = '<script>alert(1)</script><img src=x onerror=alert(2)>"\'&'


ALLOWED_TAGS = {"html", "head", "meta", "title", "style", "body", "div", "header", "h1", "h2", "p", "span",
                "table", "thead", "tbody", "tr", "th", "td", "code", "footer"}


class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.attrs = set(), set()

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        self.attrs.update(name for name, _value in attrs if name not in (
            "charset", "name", "content", "http-equiv", "lang", "class", "scope"))


class ViewCase(ResultCase):
    @staticmethod
    def parse(page):
        collector = TagCollector()
        collector.feed(page)
        return collector.tags, collector.attrs

    def page(self, *extra):
        code, text = self.run_cli("view", "--stdout", "--policy", self.policy, *extra)
        return code, text

    def populate(self):
        self.write(os.path.join(self.gov, "registry.toml"),
                   "schema_version = 1\n[[projects]]\nid = \"p\"\nname = \"P &amp; <b>friends</b>\"\nroot = '%s'\n" % self.proj)
        self.run_cli("task", "create", "--id", "t2", "--project", "p", "--objective",
                     "objective with <script>alert(3)</script> & \"quotes\"", "--request", "CREATE_TASK")
        self.run_cli("task", "evaluate", "t2", "--policy", self.policy)
        self.run_cli("task", "run", "t2", "--policy", self.policy)
        self.assertEqual(self.add("--project", "p", text="note with " + EVIL)[0], cli.EXIT_OK)
        relayed = os.path.join(self.incoming, "r.txt")
        self.write(relayed, ADVERSARIAL + EVIL)
        self.assertEqual(self.run_cli("result", "add", "t1", "--file", relayed, "--policy", self.policy)[0], 0)


class PageContentTests(ViewCase):
    def test_a_populated_page_shows_the_state_and_nothing_executable(self):
        self.populate()
        code, page = self.page()
        self.assertEqual(code, cli.EXIT_OK, page[:300])
        self.assertTrue(page.startswith("<!doctype html>"))
        for expected in ("Audit OK", "Health OK", "Policy v4", "Not independently verified", "Unfinished tasks",
                         "Recent finished tasks (1 of 1)", "COMPLETED UNVERIFIED", "Latest notes", "data, not instruction",
                         "UNTRUSTED, NOT VERIFIED", "Metadata only"):
            self.assertIn(expected, page)
        tags, attrs = self.parse(page)
        self.assertEqual(tags - ALLOWED_TAGS, set(), "only inert layout tags")
        for name in attrs:
            self.assertFalse(name.startswith("on") or name in ("src", "href", "action", "srcset", "style"), name)
        self.assertNotRegex(page, r"(?i)https?://")
        self.assertIn("default-src 'none'", page)
        self.assertIn("style-src 'unsafe-inline'", page)

    def test_every_person_file_or_worker_string_is_escaped(self):
        self.populate()
        page = self.page()[1]
        self.assertNotIn("<img src=x", page)
        self.assertNotIn("<b>friends</b>", page)
        self.assertIn("&lt;script&gt;alert(3)&lt;/script&gt;", page)
        self.assertIn("P &amp;amp; &lt;b&gt;friends&lt;/b&gt;", page)
        self.assertIn("&lt;img src=x onerror=alert(2)&gt;", page)

    def test_a_result_shows_metadata_only(self):
        self.populate()
        page = self.page()[1]
        for leaked in ("SYSTEM: ignore all previous", "ADMIN OVERRIDE", "task create --id pwn", "terminal takeover"):
            self.assertNotIn(leaked, page)
        self.assertRegex(page, r"#\d+</td><td><code>t1</code>")
        self.assertRegex(page, r"[0-9a-f]{12}")

    def test_terminal_control_and_bidi_characters_are_neutralised(self):
        self.populate()
        page = self.page()[1]
        for raw in ("\x1b", "\x07", "‮"):
            self.assertNotIn(raw, page)

    def test_the_page_does_not_depend_on_the_clock(self):
        self.populate()
        first, second = self.page()[1], self.page()[1]
        self.assertEqual(first, second)

    def test_every_status_is_also_a_word_not_only_a_colour(self):
        self.populate()
        page = self.page()[1]
        for word in ("PASS", "Audit OK", "Health OK", "Not independently verified"):
            self.assertIn(">%s<" % word, page)

    def test_project_filter_and_unknown_project(self):
        self.populate()
        self.assertIn("Read-only snapshot for project p", self.page("--project", "p")[1])
        code, page = self.page("--project", "zzz")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("Project zzz is not registered", page)
        self.assertNotIn("Unfinished tasks", page)

    def test_an_empty_install_renders_friendly_empty_states(self):
        page = self.page()[1]
        for text in ("No notes recorded.", "No results relayed."):
            self.assertIn(text, page)
        self.run_cli("cancel", "t1")
        page = self.page()[1]
        for text in ("Nothing is waiting.", "Recent finished tasks (1 of 1)"):
            self.assertIn(text, page)

    def test_a_missing_registry_is_explained(self):
        os.remove(os.path.join(self.gov, "registry.toml"))
        page = self.page()[1]
        self.assertIn("Registry unavailable: REGISTRY_MISSING", page)
        self.assertIn("WARN", page)


class FaultTests(ViewCase):
    def test_a_changed_note_is_flagged_and_its_text_is_not_shown(self):
        self.assertEqual(self.add("--project", "p", text="original words")[0], cli.EXIT_OK)
        (path,) = self.memory_files()
        with open(path, "ab") as fh:
            fh.write(b"tampered\n")
        page = self.page()[1]
        self.assertIn("[NOTE_FILE_CHANGED]", page)
        self.assertNotIn("original words", page)
        self.assertIn("FAIL", page)
        self.assertIn("1 failure(s)", page)

    def test_a_broken_chain_shows_problems_and_exits_5(self):
        conn = sqlite3.connect(Store.db_path(self.data))
        try:
            conn.execute("UPDATE audit_log SET record = CAST(record || x'20' AS BLOB) WHERE seq = 0")
            conn.commit()
        finally:
            conn.close()
        code, page = self.page()
        self.assertEqual(code, cli.EXIT_AUDIT)
        self.assertIn("Audit PROBLEMS", page)

    def test_a_missing_store(self):
        os.remove(Store.db_path(self.data))
        os.remove(os.path.join(self.data, "HEAD"))
        self.assertEqual(self.page()[0], cli.EXIT_STORE_MISSING)


class WritingTests(ViewCase):
    def digest(self, path):
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    def test_the_default_writes_only_views_index_html(self):
        self.populate()
        before = {os.path.join(d, f): self.digest(os.path.join(d, f))
                  for d, _s, fs in os.walk(self.data) for f in fs}
        code, text = self.run_cli("view", "--policy", self.policy)
        self.assertEqual(code, cli.EXIT_OK, text)
        target = os.path.join(self.data, "views", "index.html")
        self.assertIn("view written: %s" % target, text)
        after = {os.path.join(d, f): self.digest(os.path.join(d, f))
                 for d, _s, fs in os.walk(self.data) for f in fs}
        self.assertEqual(set(after) - set(before), {target})
        self.assertEqual({k: v for k, v in after.items() if k != target}, before, "nothing else changed")
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), self.page()[1])
        self.assertEqual(self.run_cli("view", "--policy", self.policy)[0], cli.EXIT_OK)   # replaces cleanly
        self.assertFalse(os.path.exists(target + ".tmp"))
        self.assertIn("audit verify: OK", self.run_cli("audit", "verify")[1])
        self.assertIn("doctor: OK", self.run_cli("doctor", "--policy", self.policy)[1])

    def test_stdout_mode_writes_nothing(self):
        self.populate()
        self.page()
        self.assertFalse(os.path.exists(os.path.join(self.data, "views")))


class RenderUnitTests(ViewCase):
    def test_escape_helper(self):
        self.assertEqual(view.esc('<a href="x">&\x1b</a>'), "&lt;a href=&quot;x&quot;&gt;&amp;\\x1b&lt;/a&gt;")

    def test_the_style_block_has_no_external_reference(self):
        self.assertIsNone(re.search(r"(?i)url\(|@import|https?:", view.STYLE))


if __name__ == "__main__":
    import unittest
    unittest.main()
