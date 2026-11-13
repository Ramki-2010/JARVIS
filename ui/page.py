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
#galaxy{grid-column:1/-1}#galaxy .wrap{display:grid;grid-template-columns:minmax(300px,2fr) minmax(220px,1fr);gap:14px}
#gview{position:relative;border:1px solid var(--line);border-radius:8px;background:#05080c;min-height:320px}
#gview:focus{outline:2px solid var(--cyan)}#gcanvas{display:block;width:100%;height:360px;cursor:grab;touch-action:none}
#glist{list-style:none;margin:0;padding:0;max-height:360px;overflow:auto}#glist button{width:100%;text-align:left;margin:0 0 4px;font-size:12px}
#glist button[aria-pressed=true]{border-color:var(--cyan)}.legend{display:flex;flex-wrap:wrap;gap:12px;margin:8px 0 0;color:var(--dim);font-size:12px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
@media (max-width:760px){#galaxy .wrap{grid-template-columns:1fr}}
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
const dh = document.createElement("h2"); dh.textContent = "Detail"; const dpre = document.createElement("pre");
dpre.textContent = "Choose a task above, or a node in the galaxy."; detail.append(dh, dpre); main.append(detail);
// ---- galaxy (read-only; ADR-0011 D5). Drawn from /api/galaxy; selecting a node opens the same detail as the lists.
const gsec = document.createElement("section"); gsec.id = "galaxy";
const gh = document.createElement("h2"); const gt = document.createElement("span"); gt.textContent = "Galaxy (read-only)";
const gb = document.createElement("span"); gb.className = "badge LOADING"; gb.textContent = "LOADING"; gh.append(gt, gb);
const gwrap = document.createElement("div"); gwrap.className = "wrap";
const gview = document.createElement("div"); gview.id = "gview"; gview.tabIndex = 0; gview.setAttribute("role", "group");
gview.setAttribute("aria-label", "Galaxy view. Arrow keys rotate. The list beside it holds the same nodes.");
const canvas = document.createElement("canvas"); canvas.id = "gcanvas"; canvas.setAttribute("aria-hidden", "true"); gview.append(canvas);
const glist = document.createElement("ul"); glist.id = "glist"; glist.setAttribute("aria-label", "Galaxy nodes");
gwrap.append(gview, glist);
const gcount = document.createElement("p"); gcount.className = "legend"; gcount.id = "gcount";
const gleg = document.createElement("p"); gleg.className = "legend";
const COLORS = {project:"#38d3e8", task:"#3ddc97", note:"#f2c14e", result:"#ff9f43", preview:"#7b93a6"};
for (const [k, label] of [["project","project"],["task","task"],["note","note"],["result","relayed result (untrusted)"],["preview","PREVIEW: later phase, not a record"]]) {
  const s = document.createElement("span"); const i = document.createElement("i"); i.style.background = COLORS[k]; s.append(i, label); gleg.append(s); }
gsec.append(gh, gwrap, gcount, gleg); main.prepend(gsec);
let G = {nodes: [], links: []}, yaw = 0.6, pitch = 0.35, picked = "", hovered = "";
const ctx = canvas.getContext("2d");
function size() { const r = canvas.getBoundingClientRect(), d = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(r.width * d)); canvas.height = Math.max(1, Math.round(r.height * d)); ctx.setTransform(d, 0, 0, d, 0, 0); }
function project3(n) { const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
  const x1 = n.x * cy - n.z * sy, z1 = n.x * sy + n.z * cy, y2 = n.y * cp - z1 * sp, z2 = n.y * sp + z1 * cp;
  const w = canvas.clientWidth, h = canvas.clientHeight, f = 2.6 / (2.6 + z2), s = Math.min(w, h) * 0.36;
  return {sx: w / 2 + x1 * s * f, sy: h / 2 + y2 * s * f, depth: z2, f}; }
function draw() { const w = canvas.clientWidth, h = canvas.clientHeight; ctx.clearRect(0, 0, w, h);
  const pos = {}; for (const n of G.nodes) pos[n.id] = project3(n);
  ctx.lineWidth = 1; ctx.strokeStyle = "rgba(120,160,190,0.28)";
  for (const l of G.links) { const a = pos[l.from], b = pos[l.to]; if (!a || !b) continue; ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy); ctx.stroke(); }
  const order = G.nodes.slice().sort((p, q) => pos[q.id].depth - pos[p.id].depth);
  for (const n of order) { const p = pos[n.id], r = (n.kind === "project" ? 9 : n.kind === "preview" ? 6 : 5) * p.f;
    ctx.beginPath(); ctx.arc(p.sx, p.sy, r, 0, 6.2832); ctx.strokeStyle = COLORS[n.kind] || "#fff"; ctx.fillStyle = COLORS[n.kind] || "#fff";
    if (n.kind === "preview") { ctx.setLineDash([3, 3]); ctx.lineWidth = 1.5; ctx.stroke(); ctx.setLineDash([]); }
    else { ctx.globalAlpha = n.status === "CANCELLED" || n.status === "COMPLETED_UNVERIFIED" ? 0.55 : 1; ctx.fill(); ctx.globalAlpha = 1; }
    if (n.id === picked || n.id === hovered) { ctx.lineWidth = 2; ctx.strokeStyle = "#fff"; ctx.beginPath(); ctx.arc(p.sx, p.sy, r + 4, 0, 6.2832); ctx.stroke(); }
    if (n.kind === "project" || n.kind === "preview" || n.id === picked || n.id === hovered) { ctx.fillStyle = "#cfe3ef"; ctx.font = "12px Segoe UI, sans-serif";
      const text = n.kind === "preview" ? n.label + " (PREVIEW)" : n.label, tw = ctx.measureText(text).width;
      ctx.fillText(text, p.sx + r + 6 + tw > w - 4 ? p.sx - r - 6 - tw : p.sx + r + 6, p.sy + 4); } } }
async function pick(n) { picked = n.id; draw(); for (const b of glist.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.id === n.id));
  if (!n.detail) { dpre.textContent = n.label + "\n" + n.status + "\n" + n.note + (n.kind === "result" ? "\nThe relayed text is not shown here; it is untrusted data." : ""); return; }
  const [kind, id] = n.detail.split("/"); dpre.textContent = "loading...";
  try { const r = await call("/api/" + kind + "/" + encodeURIComponent(id)); dpre.textContent = r.text; } catch (e) { dpre.textContent = String(e.message); } }
function nearest(ev) { const r = canvas.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top; let best = null, bd = 14;
  for (const n of G.nodes) { const p = project3(n), d = Math.hypot(p.sx - mx, p.sy - my); if (d < bd) { bd = d; best = n; } } return best; }
let drag = null;
canvas.addEventListener("pointerdown", (ev) => { drag = {x: ev.clientX, y: ev.clientY, moved: false}; canvas.setPointerCapture(ev.pointerId); canvas.style.cursor = "grabbing"; });
canvas.addEventListener("pointermove", (ev) => { if (drag) { const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true; yaw += dx * 0.008; pitch = Math.max(-1.3, Math.min(1.3, pitch + dy * 0.008)); drag.x = ev.clientX; drag.y = ev.clientY; draw(); }
  else { const n = nearest(ev), id = n ? n.id : ""; if (id !== hovered) { hovered = id; draw(); } } });
canvas.addEventListener("pointerup", (ev) => { const moved = drag && drag.moved; drag = null; canvas.style.cursor = "grab"; if (!moved) { const n = nearest(ev); if (n) pick(n); } });
gview.addEventListener("keydown", (ev) => { const k = ev.key; if (!k.startsWith("Arrow")) return; ev.preventDefault();
  if (k === "ArrowLeft") yaw -= 0.1; if (k === "ArrowRight") yaw += 0.1; if (k === "ArrowUp") pitch = Math.max(-1.3, pitch - 0.1); if (k === "ArrowDown") pitch = Math.min(1.3, pitch + 0.1); draw(); });
window.addEventListener("resize", () => { size(); draw(); });
async function loadGalaxy() { try { const g = await call("/api/galaxy");
    if (g.error) { gb.className = "badge ERROR"; gb.textContent = "ERROR"; gcount.textContent = g.error; return; }
    G = g; const c = g.counts; gb.className = "badge " + (c.live_nodes ? "SUCCESS" : "EMPTY"); gb.textContent = c.live_nodes ? "SUCCESS" : "EMPTY";
    gcount.textContent = "Records: " + c.projects + " project(s), " + c.tasks + " task(s), " + c.notes + " note(s), " + c.results + " relayed result(s). PREVIEW nodes (" + c.preview_nodes + ") are not records.";
    glist.replaceChildren(); for (const n of g.nodes) { const li = document.createElement("li"); const b = document.createElement("button"); b.dataset.id = n.id; b.setAttribute("aria-pressed", "false");
      b.textContent = n.kind.toUpperCase() + "  " + n.label + "  " + n.status; b.addEventListener("click", () => pick(n)); li.append(b); glist.append(li); }
    size(); draw();
  } catch (e) { gb.className = "badge ERROR"; gb.textContent = "ERROR"; gcount.textContent = String(e.message); } }
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
async function refresh() { await ring(); for (const [key] of PANELS) panel(key); loadGalaxy(); }
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
