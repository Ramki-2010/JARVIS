"""Syntax-based guards for process creation, environment access and dynamic bypasses.

These catch mistakes. They are NOT a security boundary (ADR-0006 6.1). They read
the parsed code only, so they cannot see code built at run time, names passed in
as arguments, or anything that is not written out in the source. The runtime
audit-hook guard (X-13b) backs them up, but only on the code paths a test
actually executes.

What they resolve:
- `import a.b as x`, `from a import b as c`, and simple `name = <module or attribute>`
  assignments, so `o.system`, `from os import system` and `s = os.system; s(...)` are
  all seen as `os.system`.
- Any reference (not only a call) that names a process-creating or environment
  facility, so passing `subprocess.run` as an argument is also found.
- Targeted dynamic patterns, only when the object is a guarded module:
  `getattr(os, ...)`, `vars(os)`, `os.__dict__`, `__import__(...)`,
  `importlib.import_module`, `sys.modules`, and `from <guarded module> import *`.
  Ordinary `getattr(result, "reason", "")` or `vars(self)` is not flagged.

What they do not do: follow a module through a function argument, a container, a
class attribute, `globals()`, `eval`, or a string built at run time.
"""

import ast
from typing import Dict, List, NamedTuple, Optional

# Process creation. `subprocess.PIPE` and similar constants are not creation.
SUBPROCESS_CREATORS = frozenset({
    "Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput",
})
PROCESS_EXACT = frozenset({
    "os.system", "os.popen", "os.startfile", "os.fork", "os.forkpty",
    "os.posix_spawn", "os.posix_spawnp",
    "nt.system", "nt.startfile", "posix.system", "posix.fork", "posix.posix_spawn",
    "_winapi.CreateProcess", "_posixsubprocess.fork_exec",
    "concurrent.futures.ProcessPoolExecutor", "concurrent.futures.process.ProcessPoolExecutor",
})
PROCESS_PREFIXES = (
    "os.spawn", "os.exec", "nt.spawn", "nt.exec", "posix.exec",
    "multiprocessing.", "asyncio.create_subprocess_", "asyncio.subprocess.",
)

# Environment access. Only jarvis/ is held to this (ADR-0006 6.3, test C3).
ENV_EXACT = frozenset({
    "os.environ", "os.environb", "os.getenv", "os.getenvb", "os.putenv", "os.unsetenv",
    "nt.environ", "nt.putenv", "posix.environ", "posix.putenv",
})

# Modules whose attributes must not be reached dynamically.
GUARDED_MODULES = frozenset({
    "os", "nt", "posix", "subprocess", "multiprocessing", "_winapi", "_posixsubprocess",
    "concurrent.futures", "concurrent.futures.process", "asyncio", "pty",
})
DYNAMIC_REFERENCES = frozenset({
    "importlib.import_module", "importlib.__import__", "builtins.__import__", "sys.modules",
})
GUARDED_ROOTS = frozenset(name.split(".")[0] for name in GUARDED_MODULES)


class Finding(NamedTuple):
    line: int
    rule: str   # "process", "environment", "dynamic", "star-import"
    name: str


def _collect(tree) -> "tuple[Dict[str, str], list]":
    names: Dict[str, str] = {}
    stars: list = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    names[alias.asname] = alias.name
                else:
                    root = alias.name.split(".")[0]
                    names[root] = root
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                if alias.name == "*":
                    stars.append((node.lineno, node.module))
                else:
                    names[alias.asname or alias.name] = node.module + "." + alias.name
    for _ in range(2):  # simple `x = <resolvable>` aliases, two passes for chains
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                resolved = _resolve(node.value, names)
                if resolved:
                    names[node.targets[0].id] = resolved
    return names, stars


def _resolve(node, names: Dict[str, str]) -> Optional[str]:
    if isinstance(node, ast.Name):
        return names.get(node.id)
    if isinstance(node, ast.Attribute):
        base = _resolve(node.value, names)
        return base + "." + node.attr if base else None
    return None


def resolver(tree):
    """Return a function mapping an expression node to its qualified name or None."""
    names, _stars = _collect(tree)
    return lambda node: _resolve(node, names)


def is_process(qualified: str) -> bool:
    if qualified in PROCESS_EXACT or qualified.startswith(PROCESS_PREFIXES):
        return True
    parts = qualified.split(".")
    return len(parts) == 2 and parts[0] == "subprocess" and parts[1] in SUBPROCESS_CREATORS


def is_environment(qualified: str) -> bool:
    return qualified in ENV_EXACT


def _classify(qualified: str) -> Optional[str]:
    if is_process(qualified):
        return "process"
    if is_environment(qualified):
        return "environment"
    if qualified in DYNAMIC_REFERENCES:
        return "dynamic"
    return None


def scan(tree) -> List[Finding]:
    names, stars = _collect(tree)
    found: List[Finding] = []

    for line, module in stars:
        if module.split(".")[0] in GUARDED_ROOTS:
            found.append(Finding(line, "star-import", module))

    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)

        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                rule = _classify(node.module + "." + alias.name)
                if rule:
                    found.append(Finding(line, rule, node.module + "." + alias.name))

        elif isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load):
            qualified = _resolve(node, names)
            if qualified:
                rule = _classify(qualified)
                if rule:
                    found.append(Finding(line, rule, qualified))
            if isinstance(node, ast.Attribute) and node.attr == "__dict__":
                owner = _resolve(node.value, names)
                if owner in GUARDED_MODULES:
                    found.append(Finding(line, "dynamic", owner + ".__dict__"))

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func, args = node.func.id, node.args
            if func == "__import__" and "__import__" not in names:
                found.append(Finding(line, "dynamic", "__import__"))
            elif func in ("getattr", "vars") and args:
                owner = _resolve(args[0], names)
                if owner in GUARDED_MODULES:
                    found.append(Finding(line, "dynamic", "%s(%s)" % (func, owner)))
    return found
