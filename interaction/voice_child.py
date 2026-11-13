"""Starts and talks to the voice worker (ADR-0012 D2). A second process-creating place, like `child.py`.

The worker is `<root>\\venv\\Scripts\\python.exe -E -s -m voice --root <root>` run from the
repository folder: the voice interpreter by absolute path under the data root, no shell, a minimal
environment (offline model settings only), pipes for stdin and stdout, and a log file for stderr.
Commands and events are single JSON lines. Nothing from an utterance becomes an argument.
"""

import json
import os
import queue
import subprocess
import threading
import time
from typing import Iterator, Optional

from interaction.child import REPO

_ENV_KEEP = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")


class VoiceRefused(ValueError):
    """A voice worker that must not be started."""


def interpreter(root: str) -> str:
    exe = os.path.join(root, "venv", "Scripts", "python.exe")
    if not os.path.isabs(root) or not os.path.isfile(exe):
        raise VoiceRefused("no voice interpreter at the voice folder")
    return exe


def environment(root: str) -> dict:
    env = {name: os.environ[name] for name in _ENV_KEEP if name in os.environ}
    system32 = os.path.join(env.get("SYSTEMROOT", r"C:\Windows"), "System32")
    env["PATH"] = system32  # the system folder only; nothing from the user's own PATH
    env.update(HF_HOME=os.path.join(root, "hf-cache"), HF_HUB_OFFLINE="1", HF_HUB_DISABLE_XET="1", PYTHONUTF8="1")
    return env


class VoiceWorker:
    def __init__(self, root: str):
        self.root = root
        self._next = 0
        self.events: "queue.Queue[dict]" = queue.Queue()
        self.proc = None  # the worker process (no annotation: the process guard counts every reference)
        self.error = ""

    def start(self, ready_timeout: float = 180.0) -> bool:
        cmd = [interpreter(self.root), "-E", "-s", "-m", "voice", "--root", self.root]
        log = open(os.path.join(self.root, "voice-worker.log"), "ab")
        self.proc = subprocess.Popen(cmd, cwd=REPO, env=environment(self.root), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=log)
        threading.Thread(target=self._pump, daemon=True).start()
        end = time.monotonic() + ready_timeout
        while time.monotonic() < end:
            try:
                ev = self.events.get(timeout=1.0)
            except queue.Empty:
                if self.proc.poll() is not None:
                    return False
                continue
            if ev.get("event") == "ready":
                return True
            if ev.get("event") == "error":
                self.error = str(ev.get("error", ""))
                return False
        return False

    def _pump(self) -> None:
        for raw in self.proc.stdout:
            try:
                ev = json.loads(raw.decode("utf-8", errors="replace"))
                if isinstance(ev, dict):
                    self.events.put(ev)
            except ValueError:
                pass

    def send(self, cmd: str, **fields) -> int:
        self._next += 1
        msg = dict(fields, cmd=cmd, id=self._next)
        self.proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
        self.proc.stdin.flush()
        return self._next

    def say(self, text: str) -> int:
        return self.send("say", text=text)

    def wait_event(self, name: str, job_id: Optional[int] = None, timeout: float = 120.0) -> Optional[dict]:
        end = time.monotonic() + timeout
        stash = []
        try:
            while time.monotonic() < end:
                try:
                    ev = self.events.get(timeout=0.5)
                except queue.Empty:
                    continue
                if ev.get("event") == name and (job_id is None or ev.get("id") == job_id):
                    return ev
                stash.append(ev)
        finally:
            for ev in stash:
                self.events.put(ev)
        return None

    def drain(self) -> None:
        while True:
            try:
                self.events.get_nowait()
            except queue.Empty:
                return

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.send("quit")
                self.proc.stdin.close()
                self.proc.wait(timeout=60)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()
