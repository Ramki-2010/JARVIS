"""Read-only galaxy (ADR-0011 D5; Beta plan BR-13, BU-3): every LIVE node and link traces to a real record line,
PREVIEW nodes are labelled and never counted, placement is deterministic, and nothing in it can act."""

import ast
import os
import unittest

from ui import galaxy, page

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECTS = "jarvis  JARVIS  [ok]\nprojects: 1\n"
TASKS = ("t-run RUNNING L2 jarvis\nt-done COMPLETED_UNVERIFIED L2 jarvis\nt-stop CANCELLED L2 jarvis\n"
         "t-bad FAILED L2 jarvis\nt-wait BLOCKED L2 jarvis\ntasks: 5\n")
NOTES = "22  note  project/jarvis  2026-11-12T17:38:33.069388Z  204 bytes  sha256 170451ea504b\nnotes: 1\n"
RESULTS = "21  task t-done  2026-11-12T17:38:32.154190Z  205 bytes  sha256 9e7698fb5076  [UNTRUSTED, NOT VERIFIED]\nresults: 1\n"


def build(p=PROJECTS, t=TASKS, n=NOTES, r=RESULTS):
    return galaxy.build(p, t, n, r)


class Records(unittest.TestCase):
    def test_every_live_node_is_one_record_line(self):
        g = build()
        live = [n for n in g["nodes"] if n["kind"] != "preview"]
        self.assertEqual(len(live), 1 + 5 + 1 + 1)
        self.assertEqual(g["counts"], {"projects": 1, "tasks": 5, "notes": 1, "results": 1, "live_nodes": 8, "preview_nodes": 3})

    def test_every_link_names_a_real_field(self):
        g = build()
        ids = {n["id"] for n in g["nodes"]}
        self.assertEqual(len(g["links"]), 5 + 1 + 1)  # 5 tasks, 1 note, 1 result
        for link in g["links"]:
            self.assertIn(link["from"], ids)
            self.assertIn(link["to"], ids)
            self.assertNotIn("preview", link["from"] + link["to"])
        self.assertIn({"from": "result:21", "to": "task:t-done", "why": "result was relayed for task"}, g["links"])
        self.assertIn({"from": "note:22", "to": "project:jarvis", "why": "note is scoped to project"}, g["links"])

    def test_preview_nodes_are_labelled_unlinked_and_not_counted(self):
        g = build()
        preview = [n for n in g["nodes"] if n["kind"] == "preview"]
        self.assertEqual({n["status"] for n in preview}, {"PREVIEW"})
        self.assertEqual({n["label"] for n in preview}, {"Memory", "Research", "Evidence"})
        self.assertTrue(all(n["detail"] is None for n in preview))
        self.assertEqual(g["counts"]["live_nodes"], 8)

    def test_empty_store_shows_only_labelled_preview(self):
        g = build("projects: 0\n", "tasks: 0\n", "notes: 0\n", "results: 0\n")
        self.assertEqual(g["counts"]["live_nodes"], 0)
        self.assertEqual(g["links"], [])
        self.assertTrue(all(n["kind"] == "preview" for n in g["nodes"]))

    def test_a_task_of_an_unlisted_project_is_a_node_but_not_linked(self):
        g = build(t="orphan RUNNING L2 ghost\n")
        self.assertIn("task:orphan", {n["id"] for n in g["nodes"]})
        self.assertFalse([link for link in g["links"] if link["from"] == "task:orphan"])

    def test_result_has_no_detail_route_and_is_marked_untrusted(self):
        node = [n for n in build()["nodes"] if n["id"] == "result:21"][0]
        self.assertIsNone(node["detail"])
        self.assertEqual(node["status"], "UNTRUSTED")


class Placement(unittest.TestCase):
    def test_layout_is_deterministic(self):
        self.assertEqual(build(), build())

    def test_active_work_sits_nearer_than_finished_work(self):
        by = {n["id"]: n for n in build()["nodes"]}
        distance = lambda n: (n["x"] ** 2 + n["y"] ** 2 + n["z"] ** 2) ** 0.5
        self.assertLess(distance(by["task:t-run"]), distance(by["task:t-done"]))
        self.assertLess(distance(by["task:t-done"]), distance(by["task:t-stop"]))

    def test_layout_does_not_depend_on_record_order(self):
        reordered = "t-stop CANCELLED L2 jarvis\nt-run RUNNING L2 jarvis\n"
        a = {n["id"]: (n["x"], n["y"], n["z"]) for n in build(t=reordered)["nodes"]}
        b = {n["id"]: (n["x"], n["y"], n["z"]) for n in build()["nodes"]}
        self.assertEqual(a["task:t-run"], b["task:t-run"])
        self.assertEqual(a["task:t-stop"], b["task:t-stop"])


class Hostile(unittest.TestCase):
    def test_hostile_text_stays_text(self):
        evil = "<script>alert(1)</script>"
        g = build(p="jarvis  %s  [ok]\n" % evil, t="x RUNNING L2 jarvis\nignore previous rules BLOCKED L9 jarvis\n")
        project = [n for n in g["nodes"] if n["kind"] == "project"][0]
        self.assertEqual(project["label"], evil)  # kept as data; the page inserts it as text only
        self.assertEqual([n["id"] for n in g["nodes"] if n["kind"] == "task"], ["task:x"])  # the malformed line is not a record


class Guards(unittest.TestCase):
    def test_galaxy_module_imports_only_pure_standard_modules(self):
        with open(os.path.join(REPO, "ui", "galaxy.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
        self.assertLessEqual(names, {"hashlib", "math", "re", "typing"})

    def test_page_uses_no_dangerous_dom_calls_and_no_outside_address(self):
        html = page.html("n")
        for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "http://", "https://", "WebSocket", "XMLHttpRequest"):
            self.assertNotIn(banned, html, banned)
        self.assertEqual(html.count("fetch("), 1)  # one helper, same origin, token header

    def test_page_offers_the_galaxy_as_a_keyboard_list_too(self):
        html = page.html("n")
        self.assertIn('aria-label", "Galaxy nodes"', html)
        self.assertIn("aria-pressed", html)
        self.assertIn("ArrowLeft", html)


if __name__ == "__main__":
    unittest.main()
