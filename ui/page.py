"""The Stage A page: one HTML document, one nonced style block, one nonced script.

The page shows what the CLI prints, as text. It holds no logic that decides
anything. The ring animates only while a task is really RUNNING (ADR-0011 D4).
"""


def csp(nonce: str) -> str:
    src = "'nonce-%s'" % nonce if nonce else "'none'"
    return ("default-src 'none'; script-src %s; style-src %s; connect-src 'self'; img-src 'none'; "
            "font-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'" % (src, src))


_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JARVIS dashboard</title>
<style nonce="__NONCE__">
:root{--bg:#070b10;--panel:#0d141c;--line:#1b2a38;--text:#cfe3ef;--dim:#7b93a6;--cyan:#38d3e8;
--ok:#3ddc97;--warn:#f2c14e;--bad:#ff5d6c;--wait:#a78bfa}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.45 "Segoe UI",system-ui,sans-serif}
header{display:flex;align-items:center;gap:24px;padding:18px 24px;border-bottom:1px solid var(--line)}
.ring{width:132px;height:132px;flex:none}.ring text{fill:var(--cyan);font:600 13px "Segoe UI",sans-serif;letter-spacing:2px}
.ring .track{stroke:var(--line)}.ring .arc{stroke:var(--cyan);transform-origin:66px 66px;transition:stroke .4s}
.ring.RUNNING .arc{animation:spin 2.4s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.ring.WAITING .arc,.ring.DEFERRED .arc{stroke:var(--wait)}.ring.COMPLETED .arc{stroke:var(--ok)}
.ring.ERROR .arc,.ring.AUDIT_FAULT .arc{stroke:var(--bad)}.ring.CANCELLED .arc{stroke:var(--dim)}
.state h1{margin:0;font-size:22px;letter-spacing:1px}.state p{margin:4px 0 0;color:var(--dim)}
.tools{margin-left:auto;display:flex;gap:8px;align-items:center}
button,select,input{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:6px 10px;font:inherit}
button:focus,select:focus,input:focus{outline:2px solid var(--cyan);outline-offset:1px}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px;padding:18px 24px}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-height:120px}
section h2{margin:0 0 8px;font-size:13px;letter-spacing:1.5px;text-transform:uppercase;color:var(--dim);display:flex;justify-content:space-between}
.badge{font-size:11px;padding:1px 7px;border-radius:9px;border:1px solid var(--line)}
.LOADING{color:var(--dim)}.SUCCESS{color:var(--ok)}.WARNING{color:var(--warn)}.ERROR{color:var(--bad)}.EMPTY{color:var(--dim)}
pre{margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.5 Consolas,monospace;color:var(--text);max-height:340px;overflow:auto}
footer{padding:8px 24px 18px;color:var(--dim);font-size:12px}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
</style></head><body>
<header>
  <svg class="ring IDLE" id="ring" viewBox="0 0 132 132" role="img" aria-labelledby="ringstate">
    <circle class="track" cx="66" cy="66" r="56" fill="none" stroke-width="6"/>
    <circle class="arc" cx="66" cy="66" r="56" fill="none" stroke-width="6" stroke-dasharray="120 232" stroke-linecap="round"/>
    <circle class="track" cx="66" cy="66" r="44" fill="none" stroke-width="1"/>
    <text x="66" y="71" text-anchor="middle">J.A.R.V.I.S.</text>
  </svg>
  <div class="state"><h1 id="ringstate">LOADING</h1><p id="ringdetail">reading the records</p></div>
  <div class="tools">
    <label for="taskpick" class="sr">Task</label><select id="taskpick" aria-label="Show a task"><option value="">show a task</option></select>
    <button id="refresh" title="Refresh (R)">Refresh</button>
  </div>
</header>
<main id="panels"></main>
<footer>Read-only view of the JARVIS control plane. Every panel is the exact output of one CLI command. Nothing is verified unless a record says so. Press R to refresh.</footer>
<script nonce="__NONCE__">
"use strict";
const token = new URLSearchParams(location.hash.slice(1)).get("t") || "";
history.replaceState(null, "", location.pathname);
const PANELS = [["status","Status"],["doctor","Health (doctor)"],["projects","Projects"],["tasks","Tasks"],
  ["notes","Notes"],["results","Relayed results (untrusted)"],["audit","Audit chain"],["resume","Resume"]];
const main = document.getElementById("panels");
const boxes = {};
for (const [key, title] of PANELS) {
  const s = document.createElement("section"); const h = document.createElement("h2");
  const t = document.createElement("span"); t.textContent = title; const b = document.createElement("span");
  b.className = "badge LOADING"; b.textContent = "LOADING"; h.append(t, b);
  const pre = document.createElement("pre"); s.append(h, pre); main.append(s); boxes[key] = {b, pre};
}
const detail = document.createElement("section");
const dh = document.createElement("h2"); dh.textContent = "Task detail"; const dpre = document.createElement("pre");
dpre.textContent = "Choose a task above."; detail.append(dh, dpre); main.append(detail);
async function call(path) {
  const r = await fetch(path, {headers: {"X-JARVIS-Token": token}, cache: "no-store"});
  const body = await r.json();
  if (!r.ok) throw new Error(body.error || ("HTTP " + r.status));
  return body;
}
function badge(key, res) {
  const text = res.text || "";
  if (res.exit !== 0) return "ERROR";
  if (key === "doctor" && /WARN/.test(text)) return "WARNING";
  if (/(^|\n)(tasks|notes|results|projects): (none|0)\b/.test(text)) return "EMPTY";
  return "SUCCESS";
}
async function panel(key) {
  const {b, pre} = boxes[key];
  try { const res = await call("/api/" + key); const st = badge(key, res);
    b.className = "badge " + st; b.textContent = st; pre.textContent = res.text + (res.truncated ? "\n[output truncated]" : "");
    if (key === "tasks") fillTasks(res.text);
  } catch (e) { b.className = "badge ERROR"; b.textContent = "ERROR"; pre.textContent = String(e.message); }
}
function fillTasks(text) {
  const pick = document.getElementById("taskpick"); const keep = pick.value;
  while (pick.options.length > 1) pick.remove(1);
  for (const line of text.split("\n")) { const m = line.trim().match(/^(\S+) ([A-Z_]+) (L\d) (\S+)$/);
    if (m) { const o = document.createElement("option"); o.value = m[1]; o.textContent = m[1] + "  " + m[2]; pick.append(o); } }
  pick.value = keep;
}
async function ring() {
  const el = document.getElementById("ring");
  try { const r = await call("/api/ring"); el.setAttribute("class", "ring " + r.state);
    document.getElementById("ringstate").textContent = r.state; document.getElementById("ringdetail").textContent = r.detail;
  } catch (e) { el.setAttribute("class", "ring ERROR"); document.getElementById("ringstate").textContent = "ERROR";
    document.getElementById("ringdetail").textContent = String(e.message); }
}
async function refresh() { await ring(); for (const [key] of PANELS) panel(key); }
document.getElementById("refresh").addEventListener("click", refresh);
document.getElementById("taskpick").addEventListener("change", async (ev) => {
  const id = ev.target.value; if (!id) return; dpre.textContent = "loading...";
  try { const r = await call("/api/task/" + encodeURIComponent(id)); dpre.textContent = r.text; }
  catch (e) { dpre.textContent = String(e.message); } });
document.addEventListener("keydown", (ev) => { if ((ev.key === "r" || ev.key === "R") && ev.target.tagName !== "INPUT") refresh(); });
refresh(); setInterval(refresh, 15000);
</script></body></html>
"""


def html(nonce: str) -> str:
    return _HTML.replace("__NONCE__", nonce)
