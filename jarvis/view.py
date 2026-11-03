"""A static, read-only HTML snapshot of the installation (Beta plan BS-3).

One self-contained page built from the same `resume.Snapshot` as the text summary:
no script, no server, no network, no external font, image or stylesheet. It can be
opened from disk and printed. A Content-Security-Policy meta tag forbids everything
except its own inline style, so even a hostile string could not run or load anything.

Everything that came from a person, a file or a worker is HTML-escaped after
`display.safe`, and labelled as data. Relayed results show metadata only, never text.
Colour is never the only signal: every status is also written as a word. The page takes
no clock, so the same store gives the same page.
"""

import html

from . import display, doctor, results
from . import projects as projects_mod
from .resume import Snapshot

STYLE = """
:root{color-scheme:light dark;--bg:#f4f6fa;--card:#ffffff;--ink:#14213d;--muted:#5b6478;--line:#d9deea;
--accent:#1f6feb;--ok:#0f7b3f;--okbg:#dff5e8;--warn:#8a5a00;--warnbg:#fff1cc;--bad:#a4161a;--badbg:#fde0e0;
--info:#1f4fa3;--infobg:#e2ecfb;--data:#5a3d99;--databg:#ece4fa}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--card:#161b22;--ink:#e6edf3;--muted:#9aa4b2;--line:#2b3340;
--accent:#58a6ff;--ok:#56d364;--okbg:#12301c;--warn:#e3b341;--warnbg:#38290b;--bad:#ff7b72;--badbg:#3d1416;
--info:#79b8ff;--infobg:#142a4a;--data:#c4a7ff;--databg:#2a2145}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:24px 16px 48px}
header{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:18px}
h1{margin:0;font-size:28px;letter-spacing:.18em}
.sub{margin:2px 0 0;color:var(--muted);font-size:13px}
h2{margin:30px 0 10px;font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;letter-spacing:.03em;
border:1px solid transparent;white-space:nowrap}
.ok{color:var(--ok);background:var(--okbg)}.warn{color:var(--warn);background:var(--warnbg)}
.bad{color:var(--bad);background:var(--badbg)}.info{color:var(--info);background:var(--infobg)}
.data{color:var(--data);background:var(--databg)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.num{font-size:28px;font-weight:700;line-height:1.1}.lbl{color:var(--muted);font-size:12px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top;font-size:14px}
th{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);background:var(--bg)}
tr:last-child td{border-bottom:0}
.empty{background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:14px 16px;color:var(--muted)}
.note{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--data);border-radius:10px;
padding:10px 14px;margin-bottom:8px}.meta{color:var(--muted);font-size:12px}
code{font:12px ui-monospace,Consolas,monospace;color:var(--muted)}
footer{margin-top:34px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:12px}
@media print{body{background:#fff;color:#000}.card,table,.note{break-inside:avoid}}
"""

CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; base-uri 'none'; form-action 'none'"


def esc(value) -> str:
    return html.escape(display.safe(str(value)), quote=True)


def pill(text: str, kind: str) -> str:
    return '<span class="pill %s">%s</span>' % (kind, esc(text))


STATE_KIND = {"RUNNING": "info", "PENDING": "info", "BLOCKED": "bad", "DEFERRED": "warn",
              "COMPLETED_UNVERIFIED": "warn", "FAILED": "bad", "CANCELLED": "warn", "VERIFIED": "ok"}
CHECK_KIND = {doctor.PASS: "ok", doctor.WARN: "warn", doctor.FAIL: "bad"}


def _card(number, label) -> str:
    return '<div class="card"><div class="num">%s</div><div class="lbl">%s</div></div>' % (esc(number), esc(label))


def _task_rows(pairs) -> str:
    out = []
    for row, task in pairs:
        out.append("<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            esc(row["task_id"]), pill(row["state"].replace("_", " "), STATE_KIND.get(row["state"], "info")),
            esc(row["risk_level"]), esc(row["project"]), esc(task["updated_utc"]),
            esc(task["objective"].replace("\n", " "))))
    return "".join(out)


def _table(head, body) -> str:
    cells = "".join("<th scope=\"col\">%s</th>" % esc(h) for h in head)
    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (cells, body)


def render_html(snap: Snapshot) -> str:
    failures = snap.failures
    policy = next((c.detail for c in snap.checks if c.name == "policy" and c.status == doctor.PASS), None)
    chips = [pill("Audit " + ("OK" if snap.audit_ok else "PROBLEMS"), "ok" if snap.audit_ok else "bad"),
             pill("Health " + ("OK" if not failures else "%d failure(s)" % len(failures)),
                  "ok" if not failures else "bad"),
             pill("Audit tail %s" % snap.tail_seq, "info"),
             pill("Policy " + (policy.split(",")[0].replace("version ", "v") if policy else "unavailable"),
                  "info" if policy else "bad"),
             pill("Not independently verified", "warn")]
    body = ["<header><div><h1>JARVIS</h1><p class=\"sub\">Read-only snapshot%s</p></div><div class=\"chips\">%s</div></header>" % (
        " for project " + esc(snap.project) if snap.project else "", "".join(chips))]

    if snap.project_unknown:
        body.append('<div class="empty">Project %s is not registered and has no tasks.</div>' % esc(snap.project))
    else:
        counts = snap.task_counts
        body.append('<div class="cards">%s</div>' % "".join((
            _card(len(snap.projects), "projects"), _card(len(snap.open_tasks), "unfinished tasks"),
            _card(snap.done_total, "finished tasks"), _card(snap.notes_total, "notes"),
            _card(snap.results_total, "relayed results"),
            _card(counts.get("BLOCKED", 0) + counts.get("DEFERRED", 0), "blocked or deferred"))))

    body.append("<h2>Health</h2>")
    body.append(_table(("Check", "Status", "Detail"), "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(c.name), pill(c.status, CHECK_KIND[c.status]), esc(c.detail))
        for c in snap.checks)))

    body.append("<h2>Projects</h2>")
    if snap.registry_failure:
        body.append('<div class="empty">Registry unavailable: %s. RK writes the registry.</div>' % esc(snap.registry_failure))
    elif not snap.projects:
        body.append('<div class="empty">No projects registered.</div>')
    else:
        rows = []
        for view in snap.projects:
            state = projects_mod.contract_state(view)
            rows.append("<tr><td><code>%s</code></td><td>%s</td><td>%s</td></tr>" % (
                esc(view.record.id), esc(view.record.name), pill(state, "ok" if state == "ok" else "warn")))
        body.append(_table(("Id", "Name", "Contract"), "".join(rows)))

    if not snap.project_unknown:
        head = ("Task", "State", "Risk", "Project", "Updated", "Objective")
        body.append("<h2>Unfinished tasks</h2>")
        body.append(_table(head, _task_rows(snap.open_tasks)) if snap.open_tasks
                    else '<div class="empty">Nothing is waiting.</div>')
        body.append("<h2>Recent finished tasks (%d of %d)</h2>" % (len(snap.done_recent), snap.done_total))
        body.append(_table(head, _task_rows(snap.done_recent)) if snap.done_recent
                    else '<div class="empty">No finished tasks yet.</div>')

        body.append("<h2>Latest notes %s</h2>" % pill("data, not instruction", "data"))
        if snap.notes:
            for ref, shown in snap.notes:
                body.append('<div class="note"><div class="meta">#%s &middot; %s &middot; %s &middot; %s</div>%s</div>' % (
                    esc(ref.seq), esc(ref.kind), esc(ref.scope), esc(ref.recorded), esc(shown)))
        else:
            body.append('<div class="empty">No notes recorded.</div>')

        body.append("<h2>Relayed results %s</h2>" % pill(results.LABEL, "data"))
        if snap.results:
            body.append(_table(("Result", "Task", "Recorded", "Size", "SHA-256"), "".join(
                "<tr><td>#%s</td><td><code>%s</code></td><td>%s</td><td>%s bytes</td><td><code>%s</code></td></tr>" % (
                    esc(r.seq), esc(r.task), esc(r.recorded), esc(r.size), esc(r.sha256[:12])) for r in snap.results)))
            body.append('<p class="meta">Metadata only. The text of a result is never shown on this page.</p>')
        else:
            body.append('<div class="empty">No results relayed.</div>')

    body.append("<footer>Snapshot of audit record %s%s. Static page: no script, no server, no network. "
                "COMPLETED_UNVERIFIED means finished and not independently verified; nothing is ever shown as verified.</footer>" % (
                    esc(snap.tail_seq), " (last record %s)" % esc(snap.last_recorded) if snap.last_recorded else ""))
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta http-equiv=\"Content-Security-Policy\" content=\"%s\">"
            "<meta name=\"referrer\" content=\"no-referrer\"><title>JARVIS snapshot</title>"
            "<style>%s</style></head><body><div class=\"wrap\">%s</div></body></html>\n") % (
                CSP, STYLE, "".join(body))
