"""`py -3.14 scripts\\remote_gate.py --file D:\\JARVIS\\governance\\remote.toml`: may phone access be switched on this time?

Exit 0 only if the settings file is valid AND the private network's own status says nothing here is public: Tailscale is
installed, and both `tailscale serve status` and `tailscale funnel status` report either nothing published ("No serve config")
or only entries that end "(tailnet only)" and proxy to exactly http://127.0.0.1:<the fixed port>. Anything else, including a
status that cannot be read or wording not recognised, is a refusal (exit 1, with the reason). It never changes anything: it
runs two read-only status commands. `scripts\\start-jarvis.cmd` calls it when JARVIS_REMOTE is set (ADR-0011 A4.6.5); the
advisor itself starts no process.
"""

import argparse
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from advisor import remote_config  # noqa: E402

TAILSCALE_PATHS = (r"C:\Program Files\Tailscale\tailscale.exe", r"C:\Program Files (x86)\Tailscale\tailscale.exe")
QUIET = "No serve config"
SAFE_TAG = "(tailnet only)"


class Windows:
    def tailscale_path(self):
        for path in TAILSCALE_PATHS:
            if os.path.isfile(path):
                return path
        return ""

    def run(self, args, timeout=20):
        try:
            done = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
            return done.returncode, ((done.stdout or "") + (done.stderr or "")).strip()
        except (OSError, subprocess.SubprocessError):
            return None, ""


def judge(text: str, port: int):
    """None if this status text is safe, else the reason it is not."""
    if text.strip() == QUIET:
        return None
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return "the status was empty"
    published = 0
    for line in lines:
        low = line.lower()
        if "funnel on" in low:
            return "it reports Funnel ON (public)"
        if low.startswith(("http://", "https://")):
            if not line.endswith(SAFE_TAG):
                return "a published address is not marked tailnet only"
            published += 1
        elif line.startswith("|--"):
            target = line.split("proxy", 1)[1].strip() if "proxy" in line else ""
            if target != "http://127.0.0.1:%d" % port:
                return "an entry proxies somewhere other than 127.0.0.1:%d" % port
        else:
            return "wording not recognised"
    return None if published else "wording not recognised"


def check(path: str, system=None):
    """(ok, reason)."""
    system = system or Windows()
    try:
        cfg = remote_config.load(path)
    except remote_config.RemoteConfigError as exc:
        return False, str(exc)
    exe = system.tailscale_path()
    if not exe:
        return False, "Tailscale is not installed"
    for what in ("serve", "funnel"):
        code, text = system.run([exe, what, "status"])
        if code != 0:
            return False, "`tailscale %s status` could not be read" % what
        reason = judge(text, cfg.port)
        if reason:
            return False, "tailscale %s status: %s" % (what, reason)
    return True, "nothing is published publicly"


def main(argv=None, system=None, out=sys.stdout) -> int:
    ap = argparse.ArgumentParser(prog="remote_gate")
    ap.add_argument("--file", required=True)
    args = ap.parse_args(argv)
    ok, reason = check(args.file, system)
    print(("phone access may be switched on: %s" if ok else "phone access stays OFF: %s") % reason, file=out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
