"""Static guards: X-13a, X-14 (ADR-0002 D5) and explicit text encoding (ADR-0006 3.4).

These catch mistakes. They are NOT a security boundary (ADR-0006 6.1). They read
parsed syntax only: tests/astguard.py resolves import aliases and a few dynamic
patterns, and cannot see code built at run time. The runtime guard (X-13b) backs
them up, but only on the code paths a test executes.
"""

import ast
import os
import sys
import unittest

from tests import astguard

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCT = os.path.join(REPO, "jarvis")
TESTS = os.path.join(REPO, "tests")

FORBIDDEN_MODULES = {
    "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "xmlrpc", "asyncio",
    "subprocess", "multiprocessing", "ctypes", "cffi", "importlib",
    "pickle", "marshal", "shelve",
}
FORBIDDEN_BUILTINS = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_OS_PREFIXES = ("system", "spawn", "exec", "popen", "startfile", "fork")


def python_files(root):
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def parse(path):
    with open(path, "r", encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def imported_roots(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node, node.module.split(".")[0]


class ProductCodeGuardTests(unittest.TestCase):
    """X-13a: no network, process, native-code or unsafe-eval facility in jarvis/."""

    def test_product_tree_exists(self):
        self.assertTrue(list(python_files(PRODUCT)))

    def test_no_forbidden_or_third_party_imports(self):
        stdlib = set(sys.stdlib_module_names)
        for path in python_files(PRODUCT):
            for node, root in imported_roots(parse(path)):
                with self.subTest(file=os.path.relpath(path, REPO), module=root, line=node.lineno):
                    self.assertNotIn(root, FORBIDDEN_MODULES)
                    self.assertTrue(root in stdlib or root == "jarvis",
                                    "import outside the standard library")

    def test_no_forbidden_calls(self):
        for path in python_files(PRODUCT):
            for node in ast.walk(parse(path)):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                with self.subTest(file=os.path.relpath(path, REPO), line=node.lineno):
                    if isinstance(f, ast.Name):
                        self.assertNotIn(f.id, FORBIDDEN_BUILTINS)
                    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "os":
                        self.assertFalse(f.attr.startswith(FORBIDDEN_OS_PREFIXES))

    def test_no_aliased_process_environment_or_dynamic_access(self):
        """Aliased imports, from-imports, assignment aliases, process executors,
        _winapi, os.environ and the targeted dynamic patterns (tests/astguard.py)."""
        for path in python_files(PRODUCT):
            for finding in astguard.scan(parse(path)):
                with self.subTest(file=os.path.relpath(path, REPO), line=finding.line):
                    self.fail("%s: %s" % (finding.rule, finding.name))

    def test_text_open_has_explicit_encoding(self):
        for path in python_files(PRODUCT):
            for node in ast.walk(parse(path)):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "open"):
                    continue
                mode = None
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = kw.value.value
                if mode and "b" in mode:
                    continue
                with self.subTest(file=os.path.relpath(path, REPO), line=node.lineno):
                    self.assertIn("encoding", [kw.arg for kw in node.keywords])


class DependencyTests(unittest.TestCase):
    """X-14: the dependency manifest is empty; standard library only."""

    def test_no_dependency_manifest(self):
        for name in ("requirements.txt", "requirements-dev.txt", "setup.py", "setup.cfg",
                     "Pipfile", "poetry.lock", "uv.lock"):
            with self.subTest(file=name):
                self.assertFalse(os.path.exists(os.path.join(REPO, name)))
        pyproject = os.path.join(REPO, "pyproject.toml")
        if os.path.exists(pyproject):
            import tomllib
            with open(pyproject, "rb") as fh:
                data = tomllib.load(fh)
            self.assertFalse(data.get("project", {}).get("dependencies"))


class HarnessGuardTests(unittest.TestCase):
    """ADR-0002 D5: tests/ may start processes only through the harness helper."""

    ALLOWED_FILE = "harness.py"

    def test_no_process_creation_outside_harness(self):
        for path in python_files(TESTS):
            if os.path.basename(path) in (self.ALLOWED_FILE, os.path.basename(__file__)):
                continue
            for node, root in imported_roots(parse(path)):
                with self.subTest(file=os.path.relpath(path, REPO), line=node.lineno):
                    self.assertNotIn(root, {"subprocess", "multiprocessing"})

    def test_exactly_one_process_creating_reference_in_tests(self):
        """The only one is subprocess.Popen in tests/harness.py. Aliases, from-imports,
        process executors and _winapi count (tests/astguard.py)."""
        sites = []
        for path in python_files(TESTS):
            for finding in astguard.scan(parse(path)):
                if finding.rule == "process":
                    sites.append((os.path.relpath(path, REPO), finding.name))
        self.assertEqual(sites, [(os.path.join("tests", "harness.py"), "subprocess.Popen")],
                         "process-creating references in tests/: %s" % sites)

    def test_no_dynamic_bypass_or_star_import_in_tests(self):
        for path in python_files(TESTS):
            for finding in astguard.scan(parse(path)):
                if finding.rule in ("dynamic", "star-import"):
                    with self.subTest(file=os.path.relpath(path, REPO), line=finding.line):
                        self.fail("%s: %s" % (finding.rule, finding.name))

    def test_harness_does_not_use_a_shell(self):
        tree = parse(os.path.join(TESTS, self.ALLOWED_FILE))
        resolve = astguard.resolver(tree)
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and astguard.is_process(resolve(n.func) or "")]
        self.assertEqual(len(calls), 1)
        for node in calls:
            self.assertNotIn("shell", [kw.arg for kw in node.keywords])

    def test_product_code_has_no_test_hook(self):
        """No test code, test hook or test-only branch is added to jarvis/ (ADR-0002 D5)."""
        for path in python_files(PRODUCT):
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            rel = os.path.relpath(path, REPO)
            for token in ("JARVIS_TEST", "sitecustomize", "childguard"):
                with self.subTest(file=rel, token=token):
                    self.assertNotIn(token, text)
            for finding in astguard.scan(parse(path)):
                if finding.rule == "environment":
                    with self.subTest(file=rel, line=finding.line):
                        self.fail("environment access in product code: %s" % finding.name)
            # Also any attribute or name spelled like an environment accessor, whatever
            # object it hangs off (the check that PR #17 had before alias resolution).
            for node in ast.walk(parse(path)):
                name = node.attr if isinstance(node, ast.Attribute) else (
                    node.id if isinstance(node, ast.Name) else None)
                with self.subTest(file=rel, line=getattr(node, "lineno", 0)):
                    self.assertNotIn(name, {"environ", "environb", "getenv", "putenv"})

if __name__ == "__main__":
    unittest.main()
