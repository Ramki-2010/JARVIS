"""`py -3.14 scripts\\boundaries.py`: a read-only report of what can leave, or reach into, this machine. RK's own tool.

It changes nothing and sends nothing. It runs a few read-only Windows commands (netstat, tasklist, reg query, netsh
advfirewall show, and `tailscale ... status` if installed) and reads the lookup allowlist from the fetcher's source file as
text. A probe that fails or is not understood is printed as UNKNOWN, never as OK. Not installed is said as "not installed".

Sections: the outbound lookup allowlist; programs listening on a non-loopback address (with the program's name); whether the
model server is loopback only; Windows Firewall state and default direction policy; Smart App Control; and the private
network's serve and public (Funnel) status. Exit code 0 when nothing needs attention, 1 when something does (a non-loopback
listener by a JARVIS-related program, Funnel reported on, Smart App Control off, firewall off), 2 for a usage error.
It is not part of the control plane (`jarvis/` starts no process); it is an operator script like `free_memory.py`.
"""

import argparse
import ast
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PORT = 11434
WATCHED = ("python", "ollama", "tailscale", "jarvis")   # program names whose network listening is worth naming
TAILSCALE_PATHS = (r"C:\Program Files\Tailscale\tailscale.exe", r"C:\Program Files (x86)\Tailscale\tailscale.exe")

OK, ATTENTION, UNKNOWN, INFO = "ok", "ATTENTION", "UNKNOWN", "info"


class Windows:
    """The real machine, read-only. Tests replace it with a stand-in that returns recorded text."""

    def run(self, args, timeout=20):
        try:
            done = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
            return done.returncode, (done.stdout or "") + (done.stderr or "")
        except (OSError, subprocess.SubprocessError):
            return None, ""

    def tailscale_path(self):
        for path in TAILSCALE_PATHS:
            if os.path.isfile(path):
                return path
        return ""


def lookup_hosts(repo=REPO):
    """The hosts the fetcher may contact, read from its source as text (the fetcher is never imported here)."""
    try:
        with open(os.path.join(repo, "fetcher", "net.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "ALLOWED_HOSTS" for t in node.targets):
                call = node.value
                return sorted(ast.literal_eval(call.args[0])) if isinstance(call, ast.Call) and call.args else None
    except (OSError, SyntaxError, ValueError):
        pass
    return None


def parse_listeners(netstat_text):
    """(address, port, pid) for each listening TCP socket."""
    found = []
    for line in netstat_text.splitlines():
        m = re.match(r"^\s*TCP\s+(\S+):(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$", line)
        if m:
            found.append((m.group(1).strip("[]"), int(m.group(2)), int(m.group(3))))
    return found


def parse_tasklist(text):
    names = {}
    for line in text.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[1].isdigit():
            names[int(parts[1])] = parts[0].strip('"').lower()
    return names


def is_loopback(address):
    return address in ("127.0.0.1", "::1") or address.startswith("127.")


def listeners_section(system):
    code, netstat = system.run(["netstat", "-ano", "-p", "tcp"])
    code2, tasks = system.run(["tasklist", "/FO", "CSV", "/NH"])
    if not netstat or code != 0 or code2 != 0:
        return [(UNKNOWN, "Could not read the list of listening ports.")], None
    names = parse_tasklist(tasks)
    rows, model_state = [], "not running"
    for address, port, pid in parse_listeners(netstat):
        who = names.get(pid, "pid %d" % pid)
        if port == MODEL_PORT:
            model_state = "loopback only" if is_loopback(address) else "OPEN to the network (%s)" % address
        if not is_loopback(address) and any(w in who for w in WATCHED):
            rows.append((ATTENTION, "%s listens on %s:%d, not loopback only." % (who, address, port)))
    if not rows:
        rows.append((OK, "No Python, model-server, Tailscale or JARVIS program listens beyond this machine."))
    return rows, model_state


def firewall_section(system):
    code, state = system.run(["netsh", "advfirewall", "show", "allprofiles", "state"])
    code2, policy = system.run(["netsh", "advfirewall", "show", "allprofiles", "firewallpolicy"])
    if code != 0 or code2 != 0 or not state or not policy:
        return [(UNKNOWN, "Could not read the Windows Firewall.")]
    states = re.findall(r"^State\s+(\w+)", state, re.M)
    policies = re.findall(r"^Firewall Policy\s+(\S+)", policy, re.M)
    rows = []
    if len(states) == 3 and all(s.upper() == "ON" for s in states):
        rows.append((OK, "Windows Firewall is on for the Domain, Private and Public profiles."))
    else:
        rows.append((ATTENTION, "Windows Firewall is not on for every profile (%s)." % ", ".join(states) or "unreadable"))
    if policies:
        rows.append((INFO, "Default direction policy: %s." % "; ".join(sorted(set(policies)))))
    return rows


def sac_section(system):
    code, out = system.run(["reg", "query", r"HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy", "/v", "VerifiedAndReputablePolicyState"])
    m = re.search(r"VerifiedAndReputablePolicyState\s+REG_DWORD\s+0x([0-9a-fA-F]+)", out or "")
    if code != 0 or not m:
        return [(UNKNOWN, "Could not read the Smart App Control setting.")]
    value = int(m.group(1), 16)
    if value == 1:
        return [(OK, "Smart App Control is on (enforcing).")]
    if value == 2:
        return [(INFO, "Smart App Control is in evaluation mode.")]
    return [(ATTENTION, "Smart App Control is OFF (it should stay on).")]


def tailscale_section(system):
    path = system.tailscale_path()
    if not path:
        return [(INFO, "Tailscale is not installed on this machine.")]
    rows = []
    for what, args in (("serve", [path, "serve", "status"]), ("funnel", [path, "funnel", "status"])):
        code, out = system.run(args)
        text = (out or "").strip()
        if code is None:
            rows.append((UNKNOWN, "Could not run `tailscale %s status`." % what))
        elif "funnel on" in text.lower():
            rows.append((ATTENTION, "Tailscale %s status reports Funnel ON: something here is reachable from the public internet." % what))
        elif code != 0:
            rows.append((UNKNOWN, "`tailscale %s status` failed: %s" % (what, text.splitlines()[0][:100] if text else "no output")))
        else:
            first = text.splitlines()[0][:100] if text else "no output"
            rows.append((INFO, "tailscale %s status: no 'Funnel on' marker (first line: %s)." % (what, first)))
    rows.append((INFO, "UNVERIFIED: this reads Tailscale's text for the words 'Funnel on'; its exact wording is confirmed on RK's machine after installing."))
    return rows


def report(system=None, repo=REPO):
    system = system or Windows()
    sections = []
    hosts = lookup_hosts(repo)
    sections.append(("Lookups (what may leave this machine)", [(OK, "Weather and news may contact only these hosts, over HTTPS, with no redirect: %s." % ", ".join(hosts))] if hosts else [(UNKNOWN, "Could not read the lookup allowlist.")]))
    rows, model_state = listeners_section(system)
    sections.append(("Listening on the network", rows))
    if model_state is None:
        model_rows = [(UNKNOWN, "Model server (port %d): could not be checked." % MODEL_PORT)]
    elif model_state.startswith("OPEN"):
        model_rows = [(ATTENTION, "Model server (port %d): %s." % (MODEL_PORT, model_state))]
    else:
        model_rows = [(OK if model_state == "loopback only" else INFO, "Model server (port %d): %s." % (MODEL_PORT, model_state))]
    sections.append(("Model server", model_rows))
    sections.append(("Windows Firewall", firewall_section(system)))
    sections.append(("Smart App Control", sac_section(system)))
    sections.append(("Private network (Tailscale)", tailscale_section(system)))
    return sections


def main(argv=None, system=None) -> int:
    ap = argparse.ArgumentParser(prog="boundaries", description="A read-only report of what can leave, or reach into, this machine.")
    ap.parse_args(argv)
    needs = False
    for title, rows in report(system):
        print(title)
        for level, text in rows:
            print("  [%s] %s" % (level, text))
            needs = needs or level == ATTENTION
        print()
    print("Needs attention." if needs else "Nothing here needs attention (anything marked UNKNOWN could not be checked).")
    return 1 if needs else 0


if __name__ == "__main__":
    sys.exit(main())
