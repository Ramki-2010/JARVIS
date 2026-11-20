"""scripts/boundaries.py: RK's read-only report of what can leave, or reach into, this machine.

Loaded from its file like the other operator scripts. No test runs a real command: a stand-in for the machine returns recorded
text. Pinned here: it reads the lookup allowlist from the fetcher's source without importing it; a probe that fails or is not
understood is UNKNOWN, never OK; Tailscale absent is "not installed", never "Funnel off"; a listener beyond loopback by a
watched program, Funnel on, Smart App Control off and a firewall that is off are each flagged; the exit code follows.
"""

import importlib.util
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("boundaries_script", os.path.join(REPO, "scripts", "boundaries.py"))
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)

NETSTAT_LOCAL = """
Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       2172
  TCP    127.0.0.1:11434        0.0.0.0:0              LISTENING       500
  TCP    127.0.0.1:50321        0.0.0.0:0              LISTENING       600
"""
NETSTAT_OPEN_MODEL = NETSTAT_LOCAL.replace("127.0.0.1:11434", "0.0.0.0:11434")
NETSTAT_PY_OPEN = NETSTAT_LOCAL + "  TCP    0.0.0.0:8123           0.0.0.0:0              LISTENING       600\n"
TASKS = '"svchost.exe","2172","Services","0","9,000 K"\n"ollama.exe","500","Console","1","90,000 K"\n"python.exe","600","Console","1","30,000 K"\n'
FW_STATE_ON = "Domain Profile Settings:\nState                                 ON\nPrivate Profile Settings:\nState                                 ON\nPublic Profile Settings:\nState                                 ON\nOk.\n"
FW_STATE_OFF = FW_STATE_ON.replace("Public Profile Settings:\nState                                 ON", "Public Profile Settings:\nState                                 OFF")
FW_POLICY = "Domain Profile Settings:\nFirewall Policy                       BlockInbound,AllowOutbound\nPrivate Profile Settings:\nFirewall Policy                       BlockInbound,AllowOutbound\nPublic Profile Settings:\nFirewall Policy                       BlockInbound,AllowOutbound\nOk.\n"


def sac(value):
    return "\nHKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\CI\\Policy\n    VerifiedAndReputablePolicyState    REG_DWORD    0x%x\n" % value


class FakeSystem:
    def __init__(self, netstat=NETSTAT_LOCAL, tasks=TASKS, fw_state=FW_STATE_ON, sac_text=None, tailscale="", ts_out=None, fail=()):
        self.netstat, self.tasks, self.fw_state, self.sac_text = netstat, tasks, fw_state, sac(1) if sac_text is None else sac_text
        self.tailscale, self.ts_out, self.fail, self.asked = tailscale, ts_out or {}, set(fail), []

    def tailscale_path(self):
        return self.tailscale

    def run(self, args, timeout=20):
        self.asked.append(list(args))
        name = args[0].lower()
        if name in self.fail:
            return None, ""
        if name == "netstat":
            return 0, self.netstat
        if name == "tasklist":
            return 0, self.tasks
        if name == "reg":
            return (0, self.sac_text) if "VerifiedAndReputablePolicyState" in self.sac_text else (1, "ERROR")
        if name == "netsh":
            return 0, (self.fw_state if "state" in args else FW_POLICY)
        if self.tailscale and name == self.tailscale.lower():
            return self.ts_out.get(args[1], (0, "No serve config"))
        return None, ""


def flat(sections):
    return [(title, level, text) for title, rows in sections for level, text in rows]


def levels(sections, title_part):
    return [lvl for title, lvl, _t in flat(sections) if title_part in title]


class Report(unittest.TestCase):
    def test_a_quiet_machine_needs_no_attention_and_exits_zero(self):
        fake = FakeSystem()
        self.assertEqual(bd.main([], fake), 0)
        self.assertNotIn(bd.ATTENTION, [lvl for _t, lvl, _x in flat(bd.report(FakeSystem()))])

    def test_the_lookup_allowlist_is_read_from_the_source_text(self):
        hosts = bd.lookup_hosts(REPO)
        self.assertIn("api.open-meteo.com", hosts)
        self.assertEqual(hosts, sorted(hosts))
        self.assertIsNone(bd.lookup_hosts(os.path.join(REPO, "no-such-folder")))

    def test_the_model_server_is_loopback_open_or_not_running(self):
        text = lambda sections: " ".join(t for title, _l, t in flat(sections) if "Model server" in title)
        self.assertIn("loopback only", text(bd.report(FakeSystem())))
        self.assertIn("not running", text(bd.report(FakeSystem(netstat="  Proto\n"))))
        open_report = bd.report(FakeSystem(netstat=NETSTAT_OPEN_MODEL))
        self.assertIn(bd.ATTENTION, levels(open_report, "Model server"))
        self.assertEqual(bd.main([], FakeSystem(netstat=NETSTAT_OPEN_MODEL)), 1)

    def test_a_watched_program_listening_beyond_loopback_is_named_and_flagged(self):
        report = bd.report(FakeSystem(netstat=NETSTAT_PY_OPEN))
        rows = [t for title, lvl, t in flat(report) if lvl == bd.ATTENTION and "Listening" in title]
        self.assertEqual(len(rows), 1)
        self.assertIn("python.exe", rows[0])
        self.assertIn("8123", rows[0])
        # an unrelated system program on 0.0.0.0 is not flagged
        self.assertEqual(levels(bd.report(FakeSystem()), "Listening"), [bd.OK])

    def test_a_failed_probe_is_unknown_never_ok(self):
        report = bd.report(FakeSystem(fail=("netstat", "netsh")))
        self.assertEqual(levels(report, "Listening"), [bd.UNKNOWN])
        self.assertEqual(levels(report, "Firewall"), [bd.UNKNOWN])
        self.assertEqual(levels(report, "Model server"), [bd.UNKNOWN])
        self.assertEqual(levels(bd.report(FakeSystem(fail=("reg",))), "Smart App Control"), [bd.UNKNOWN])
        self.assertEqual(levels(bd.report(FakeSystem(sac_text="garbage")), "Smart App Control"), [bd.UNKNOWN])

    def test_the_firewall_and_smart_app_control(self):
        self.assertEqual(levels(bd.report(FakeSystem()), "Firewall")[0], bd.OK)
        self.assertEqual(levels(bd.report(FakeSystem(fw_state=FW_STATE_OFF)), "Firewall")[0], bd.ATTENTION)
        self.assertEqual(levels(bd.report(FakeSystem(sac_text=sac(1))), "Smart App Control"), [bd.OK])
        self.assertEqual(levels(bd.report(FakeSystem(sac_text=sac(0))), "Smart App Control"), [bd.ATTENTION])
        self.assertEqual(levels(bd.report(FakeSystem(sac_text=sac(2))), "Smart App Control"), [bd.INFO])

    def test_tailscale_absent_is_not_installed_and_never_says_funnel_off(self):
        rows = [t for title, _l, t in flat(bd.report(FakeSystem())) if "Tailscale" in title]
        self.assertEqual(len(rows), 1)
        self.assertIn("not installed", rows[0])
        self.assertNotIn("Funnel", rows[0])

    def test_funnel_on_is_flagged_and_other_output_is_not_called_safe(self):
        ts = r"C:\Program Files\Tailscale\tailscale.exe"
        on = FakeSystem(tailscale=ts, ts_out={"funnel": (0, "https://host.example.ts.net (Funnel on)\n|-- / proxy http://127.0.0.1:8123")})
        self.assertIn(bd.ATTENTION, levels(bd.report(on), "Tailscale"))
        self.assertEqual(bd.main([], on), 1)
        quiet = FakeSystem(tailscale=ts)
        self.assertNotIn(bd.ATTENTION, levels(bd.report(quiet), "Tailscale"))
        texts = " ".join(t for title, _l, t in flat(bd.report(quiet)) if "Tailscale" in title)
        self.assertIn("UNVERIFIED", texts)          # the wording of its output is confirmed on RK's machine
        broken = FakeSystem(tailscale=ts, ts_out={"funnel": (1, "error: not logged in")})
        self.assertIn(bd.UNKNOWN, levels(bd.report(broken), "Tailscale"))

    def test_only_read_only_commands_are_ever_asked(self):
        fake = FakeSystem(tailscale=r"C:\Program Files\Tailscale\tailscale.exe")
        bd.report(fake)
        for args in fake.asked:
            head = args[0].lower().rsplit("\\", 1)[-1]
            self.assertIn(head, ("netstat", "tasklist", "reg", "netsh", "tailscale.exe"), args)
            if head == "reg":
                self.assertEqual(args[1], "query")
            if head == "netsh":
                self.assertIn("show", args)
            if head == "tailscale.exe":
                self.assertEqual(args[2], "status")
                self.assertIn(args[1], ("serve", "funnel"))

    def test_parsers_handle_the_real_formats(self):
        self.assertEqual(bd.parse_listeners(NETSTAT_LOCAL)[0], ("0.0.0.0", 135, 2172))
        self.assertEqual(bd.parse_listeners("  TCP    [::]:445   [::]:0   LISTENING   4")[0], ("::", 445, 4))
        self.assertEqual(bd.parse_tasklist(TASKS)[500], "ollama.exe")


class TailnetAddress(unittest.TestCase):
    """Tailscale listens on its own private-network address by design; that is information, not an alarm. Any other program
    on that address, or Tailscale on an ordinary network address, is still flagged."""

    TASKS = TASKS + '"tailscaled.exe","700","Services","0","20,000 K"\n'

    def test_tailscale_on_its_own_private_address_is_information_only(self):
        net = NETSTAT_LOCAL + "  TCP    100.79.68.118:52711    0.0.0.0:0              LISTENING       700\n"
        fake = FakeSystem(netstat=net, tasks=self.TASKS)
        rows = [(lvl, t) for title, lvl, t in flat(bd.report(fake)) if "Listening" in title]
        self.assertEqual([lvl for lvl, _t in rows], [bd.INFO, bd.OK])
        self.assertIn("private-network", rows[0][1])
        self.assertEqual(bd.main([], fake), 0)

    def test_python_on_a_private_network_address_is_still_flagged(self):
        net = NETSTAT_LOCAL + "  TCP    100.79.68.118:8123     0.0.0.0:0              LISTENING       600\n"
        self.assertIn(bd.ATTENTION, levels(bd.report(FakeSystem(netstat=net)), "Listening"))

    def test_tailscale_on_an_ordinary_network_address_is_still_flagged(self):
        net = NETSTAT_LOCAL + "  TCP    192.168.1.5:41641      0.0.0.0:0              LISTENING       700\n"
        self.assertIn(bd.ATTENTION, levels(bd.report(FakeSystem(netstat=net, tasks=self.TASKS)), "Listening"))

    def test_the_real_wording_of_a_quiet_tailscale_is_read_as_not_published(self):
        ts = r"C:\Program Files\Tailscale\tailscale.exe"
        rows = [t for title, _l, t in flat(bd.report(FakeSystem(tailscale=ts, ts_out={"serve": (0, "No serve config"), "funnel": (0, "No serve config")}))) if "Tailscale" in title]
        self.assertTrue(any("No serve config" in t for t in rows))


if __name__ == "__main__":
    unittest.main()
