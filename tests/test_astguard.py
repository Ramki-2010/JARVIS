"""Regression fixtures for tests/astguard.py.

Each fixture is source text that is parsed and never executed. The flagged cases
are the bypasses found in the PR #17 review (aliased imports, `from ... import`,
assignment aliases, process executors, `_winapi`, and dynamic access). The clean
cases are ordinary code that the scanner must leave alone, so the rules stay
targeted. These guards catch mistakes; they are not a security boundary.
"""

import ast
import unittest

from tests import astguard

PROCESS_FLAGGED = [
    ("import os\nos.system('x')", "os.system"),
    ("import os as o\no.system('x')", "os.system"),
    ("from os import system\nsystem('x')", "os.system"),
    ("from os import popen as p\np('x')", "os.popen"),
    ("import os\ns = os.system\ns('x')", "os.system"),
    ("import os\no = os\no.system('x')", "os.system"),
    ("import os\nos.spawnl(0, 'x')", "os.spawnl"),
    ("import os\nos.execv('x', [])", "os.execv"),
    ("import os\nos.startfile('x')", "os.startfile"),
    ("import nt\nnt.system('x')", "nt.system"),
    ("import subprocess\nsubprocess.Popen(['x'])", "subprocess.Popen"),
    ("import subprocess as sp\nsp.run(['x'])", "subprocess.run"),
    ("from subprocess import run\nrun(['x'])", "subprocess.run"),
    ("from subprocess import Popen as P\nP(['x'])", "subprocess.Popen"),
    ("import subprocess\ncb = subprocess.check_output\ncb(['x'])", "subprocess.check_output"),
    ("import multiprocessing as mp\nmp.Process()", "multiprocessing.Process"),
    ("from concurrent.futures import ProcessPoolExecutor\nProcessPoolExecutor()",
     "concurrent.futures.ProcessPoolExecutor"),
    ("import concurrent.futures as cf\ncf.ProcessPoolExecutor()",
     "concurrent.futures.ProcessPoolExecutor"),
    ("import concurrent.futures\nconcurrent.futures.ProcessPoolExecutor()",
     "concurrent.futures.ProcessPoolExecutor"),
    ("from concurrent.futures import process\nprocess.ProcessPoolExecutor()",
     "concurrent.futures.process.ProcessPoolExecutor"),
    ("import _winapi\n_winapi.CreateProcess(1)", "_winapi.CreateProcess"),
    ("from _winapi import CreateProcess as cp\ncp(1)", "_winapi.CreateProcess"),
    ("import _posixsubprocess\n_posixsubprocess.fork_exec()", "_posixsubprocess.fork_exec"),
    ("import asyncio\nasyncio.create_subprocess_exec('x')", "asyncio.create_subprocess_exec"),
]

ENVIRONMENT_FLAGGED = [
    ("import os\nos.environ['X']", "os.environ"),
    ("import os as o\no.environ.get('X')", "os.environ"),
    ("from os import environ as e\ne['X']", "os.environ"),
    ("from os import environ\nenviron['X']", "os.environ"),
    ("import os\nos.getenv('X')", "os.getenv"),
    ("from os import getenv as g\ng('X')", "os.getenv"),
    ("import os\nos.putenv('X', '1')", "os.putenv"),
    ("import os\nos.environb", "os.environb"),
    ("import os\nf = os.getenv\nf('X')", "os.getenv"),
    ("import nt\nnt.environ", "nt.environ"),
]

DYNAMIC_FLAGGED = [
    ("import os\ngetattr(os, 'system')('x')", "getattr(os)"),
    ("import os as o\ngetattr(o, 'environ')", "getattr(os)"),
    ("import subprocess\ngetattr(subprocess, 'Popen')", "getattr(subprocess)"),
    ("import os\nvars(os)['system']", "vars(os)"),
    ("import subprocess\nvars(subprocess)", "vars(subprocess)"),
    ("import os\nos.__dict__['getenv']('X')", "os.__dict__"),
    ("__import__('subprocess').run(['x'])", "__import__"),
    ("getattr(__import__('os'), 'system')", "__import__"),
    ("import importlib\nimportlib.import_module('subprocess')", "importlib.import_module"),
    ("from importlib import import_module as im\nim('os')", "importlib.import_module"),
    ("import sys\nsys.modules['os']", "sys.modules"),
    ("from sys import modules\nmodules['subprocess']", "sys.modules"),
]

STAR_FLAGGED = [
    ("from os import *", "os"),
    ("from subprocess import *", "subprocess"),
    ("from concurrent.futures import *", "concurrent.futures"),
]

CLEAN = [
    "import os\nos.path.join('a', 'b')\nos.getlogin()\nos.replace('a', 'b')\nos.fsync(1)\nos.remove('x')",
    "import subprocess\nsubprocess.PIPE\nsubprocess.DEVNULL",
    "result = object()\ngetattr(result, 'reason', '')",
    "class A:\n    def f(self):\n        return vars(self), self.__dict__",
    "import sys\nsys.argv\nsys.stdlib_module_names",
    "import sqlite3\nsqlite3.connect('x')",
    "import ntpath\nntpath.isabs('C:\\\\x')",
    "from concurrent.futures import ThreadPoolExecutor\nThreadPoolExecutor()",
    "import importlib.util\nx = 1",
]


def findings(source):
    return astguard.scan(ast.parse(source))


class FlaggedCases(unittest.TestCase):
    def assert_flagged(self, cases, rule):
        for source, expected in cases:
            with self.subTest(source=source.replace("\n", "; ")):
                hits = [f for f in findings(source) if f.rule == rule and f.name == expected]
                self.assertTrue(hits, "not flagged as %s %s: %s" % (rule, expected, findings(source)))

    def test_process_creation_through_aliases_and_executors(self):
        self.assert_flagged(PROCESS_FLAGGED, "process")

    def test_environment_access_through_aliases(self):
        self.assert_flagged(ENVIRONMENT_FLAGGED, "environment")

    def test_dynamic_bypasses_on_guarded_modules(self):
        self.assert_flagged(DYNAMIC_FLAGGED, "dynamic")

    def test_star_imports_from_guarded_modules(self):
        self.assert_flagged(STAR_FLAGGED, "star-import")


class CleanCases(unittest.TestCase):
    def test_ordinary_code_is_not_flagged(self):
        for source in CLEAN:
            with self.subTest(source=source.replace("\n", "; ")):
                self.assertEqual(findings(source), [])


class KnownLimits(unittest.TestCase):
    """What a syntax scan cannot see. Listed so nobody mistakes it for a boundary."""

    def test_a_module_passed_through_a_function_argument_is_not_seen(self):
        source = "def call(mod):\n    return mod.system('x')\nimport os\ncall(os)"
        self.assertEqual([f for f in findings(source) if f.rule == "process"], [])

    def test_a_name_built_at_run_time_is_not_seen(self):
        source = "import os\nname = 'sys' + 'tem'\nf = getattr(os, name)"
        # The getattr on a guarded module IS flagged, whatever the name. The built
        # string itself is not what makes it visible.
        self.assertTrue([f for f in findings(source) if f.rule == "dynamic"])


if __name__ == "__main__":
    unittest.main()
