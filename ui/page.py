"""The dashboard page: one HTML document, one nonced style block, one nonced script (ADR-0011).

An immersive, read-only view: the galaxy fills the window and a floating HUD sits over it. The page
shows what the CLI printed and holds no logic that decides anything.

Truthfulness (ADR-0011 D4, D5). Two kinds of motion, kept apart:
  * Ambient motion (slow drift, a turning view, breathing glow, rotating ticks) is decoration. It means
    nothing, can be switched off, and is off by default when the system asks for reduced motion.
  * Reactions (a ring state, a new node growing in with ripples and its links drawing in) happen only for
    something real: a state derived from the records, or a record that was not there at the last poll.
The ring's LISTENING and SPEAKING looks exist in the stylesheet but are only used if the control plane
side ever reports those states from a real signal (ADR-0012); nothing here invents them.
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
:root{--bg:#02050a;--text:#d6e6f2;--dim:#9fb4c4;--cyan:#5ee7ff;--rc:#5ee7ff}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:radial-gradient(ellipse 60% 55% at 42% 50%,rgba(35,90,120,.30),rgba(10,28,44,.18) 45%,transparent 75%),
radial-gradient(ellipse 40% 35% at 78% 28%,rgba(70,40,120,.20),transparent 70%),
radial-gradient(ellipse 35% 30% at 20% 82%,rgba(20,100,90,.16),transparent 70%),var(--bg);
color:var(--text);font:14px/1.45 "Segoe UI",system-ui,sans-serif;overflow:hidden}
#gview{position:fixed;inset:0}#gview:focus{outline:none}#gview:focus-visible{box-shadow:inset 0 0 0 2px var(--cyan)}
#gcanvas{display:block;width:100%;height:100%;cursor:grab;touch-action:none}
.glass{background:rgba(8,15,24,.55);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);box-shadow:0 12px 44px rgba(0,0,0,.5);border-radius:16px}
.hud{position:fixed;pointer-events:none;z-index:5}.hud>*{pointer-events:auto}
.tl{left:28px;top:22px;width:min(310px,44vw);display:flex;flex-direction:column;gap:12px}
.tl h1{margin:0;font:600 22px "Segoe UI",sans-serif;letter-spacing:3px;color:#f2f9ff;text-shadow:0 0 22px var(--rc)}
.tl p{margin:2px 0 0;font-size:12px;color:var(--dim)}
.insp{padding:12px 14px;display:flex;flex-direction:column;gap:5px;min-height:110px}
.cap{font:500 10.5px Consolas,monospace;letter-spacing:2px;color:var(--dim)}
.insp h2{margin:0;font-size:15px;color:#f2f9ff;word-break:break-word}
#ist{font:500 11px Consolas,monospace;color:var(--cyan)}
#ibd{margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.55 Consolas,monospace;color:#c3d4e2;max-height:210px;overflow:auto}
.tc{left:50%;top:18px;transform:translateX(-50%);display:flex;gap:8px;flex-wrap:wrap;justify-content:center;max-width:56vw}
.pill{display:inline-flex;align-items:center;gap:8px;min-height:34px;padding:0 14px;border:0;border-radius:999px;color:var(--text);font:500 12px "Segoe UI",sans-serif;cursor:pointer;
background:rgba(8,15,24,.55);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);box-shadow:0 8px 28px rgba(0,0,0,.45)}
.pill:hover{background:rgba(20,34,48,.75)}.pill[aria-pressed=true]{background:rgba(94,231,255,.20);color:#f2f9ff}
.pill:focus-visible,.chip:focus-visible,.close:focus-visible,#glist button:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}
.tr{right:28px;top:22px;width:212px;padding:12px 12px 10px}
.chip{display:flex;align-items:center;gap:10px;width:100%;border:0;background:transparent;color:var(--text);font:500 12.5px "Segoe UI",sans-serif;padding:5px 4px;border-radius:8px;cursor:pointer;text-align:left}
.chip:hover{background:rgba(255,255,255,.05)}.chip[aria-pressed=false]{opacity:.38}
.dot{width:10px;height:10px;border-radius:50%;flex:none}.cnt{margin-left:auto;font:500 11px Consolas,monospace;color:var(--dim)}
.ringbox{right:48px;top:50%;transform:translateY(-46%);width:240px;display:flex;flex-direction:column;align-items:center;gap:12px}
.ringsvg{color:var(--rc);overflow:visible;filter:drop-shadow(0 0 12px currentColor);animation:breathe 4.6s ease-in-out infinite}
@keyframes breathe{0%,100%{filter:drop-shadow(0 0 8px currentColor)}50%{filter:drop-shadow(0 0 20px currentColor)}}
.ticks{transform-origin:120px 120px;animation:rot 60s linear infinite}.dots{transform-origin:120px 120px;animation:rot 45s linear infinite reverse}
@keyframes rot{to{transform:rotate(360deg)}}
.arcg{transform-origin:120px 120px}.RUNNING .arcg{animation:rot 2.6s linear infinite}
.rip{fill:none;stroke:currentColor;stroke-width:1.5;opacity:0;transform-origin:120px 120px}
.SPEAKING .rip{animation:out 2.4s ease-out infinite}.LISTENING .rip{animation:inn 2.4s ease-in infinite}
.rip:nth-of-type(2){animation-delay:.8s!important}.rip:nth-of-type(3){animation-delay:1.6s!important}
@keyframes out{0%{opacity:.55;transform:scale(1)}100%{opacity:0;transform:scale(2.2)}}
@keyframes inn{0%{opacity:0;transform:scale(2.2)}100%{opacity:.55;transform:scale(1)}}
body.calm .ringsvg,body.calm .ticks,body.calm .dots{animation:none}
@media (prefers-reduced-motion:reduce){.ringsvg,.ticks,.dots{animation:none}}
.pills{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tag{padding:4px 12px;border-radius:999px;background:rgba(8,15,24,.55);font:500 11px Consolas,monospace;letter-spacing:1.5px;color:var(--dim)}
#rstate{color:var(--rc)}#rdetail{font:500 11.5px Consolas,monospace;color:var(--dim);text-align:center;max-width:230px}
.note{left:28px;bottom:20px;max-width:380px;font-size:11px;color:#7f95a6;line-height:1.5}
.drawer{position:fixed;left:0;top:0;bottom:0;width:min(580px,96vw);z-index:20;overflow:auto;padding:18px 20px 28px;border-radius:0 16px 16px 0;
transform:translateX(-104%);visibility:hidden;transition:transform .25s ease,visibility 0s .25s}
.drawer.open{transform:none;visibility:visible;transition:transform .25s ease}
.drawer header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.drawer h2{margin:0;font-size:15px;letter-spacing:2px;text-transform:uppercase;color:var(--dim)}
.close{border:0;border-radius:8px;background:rgba(255,255,255,.07);color:var(--text);padding:6px 12px;font:inherit;cursor:pointer}
#glist{list-style:none;margin:0 0 14px;padding:0;max-height:250px;overflow:auto}
#glist button{width:100%;text-align:left;margin:0 0 3px;font:12px Consolas,monospace;color:var(--text);background:rgba(255,255,255,.04);border:0;border-radius:6px;padding:6px 10px;cursor:pointer}
#glist button[aria-pressed=true]{background:rgba(94,231,255,.18)}
.drawer section{background:rgba(255,255,255,.035);border-radius:10px;padding:10px 12px;margin-bottom:10px}
.drawer section h3{margin:0 0 6px;font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:var(--dim);display:flex;justify-content:space-between}
.badge{font-size:11px;padding:1px 8px;border-radius:9px;background:rgba(255,255,255,.07)}
.SUCCESS{color:#3ddc97}.WARNING{color:#f2c14e}.ERROR{color:#ff6b79}.EMPTY,.LOADING{color:var(--dim)}
pre.rec{margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.5 Consolas,monospace;color:var(--text);max-height:300px;overflow:auto}
@media (max-width:900px){.ringbox{transform:translateY(-46%) scale(.7);right:0}.tr{width:170px}.tc{max-width:90vw;top:auto;bottom:16px}}
</style></head><body>
<div id="gview" tabindex="0" role="group" aria-label="Galaxy view. Arrow keys rotate. The Records panel holds the same nodes as a list."><canvas id="gcanvas" aria-hidden="true"></canvas></div>

<div class="hud tl">
  <div><h1>J.A.R.V.I.S.</h1><p id="gcount">reading the records</p></div>
  <div class="glass insp"><span class="cap">INSPECTOR</span><h2 id="itl">Choose a node</h2><div id="ist"></div><pre id="ibd">Click a node, or open Records for the same list as text.</pre></div>
</div>

<div class="hud tc">
  <button class="pill" id="bleft" aria-label="Rotate left">&lsaquo;</button>
  <button class="pill" id="bfit">Fit</button>
  <button class="pill" id="bright" aria-label="Rotate right">&rsaquo;</button>
  <button class="pill" id="bmotion" aria-pressed="true">Ambient motion</button>
  <button class="pill" id="brec">Records</button>
  <button class="pill" id="brefresh" title="Refresh (R)">Refresh</button>
</div>

<div class="hud tr glass"><span class="cap">FILTER</span><div id="filters"></div></div>

<div class="hud ringbox" id="ringbox">
  <svg class="ringsvg" width="240" height="240" viewBox="0 0 240 240" role="img" aria-labelledby="rstate rdetail">
    <defs><radialGradient id="core" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="currentColor" stop-opacity=".34"/><stop offset="70%" stop-color="currentColor" stop-opacity=".10"/><stop offset="100%" stop-color="currentColor" stop-opacity="0"/></radialGradient></defs>
    <circle class="rip" cx="120" cy="120" r="62"/><circle class="rip" cx="120" cy="120" r="62"/><circle class="rip" cx="120" cy="120" r="62"/>
    <g class="ticks"><circle cx="120" cy="120" r="108" fill="none" stroke="currentColor" stroke-width="10" stroke-dasharray="1.4 6.9" opacity=".85"/></g>
    <circle cx="120" cy="120" r="97" fill="none" stroke="currentColor" stroke-opacity=".3"/>
    <g class="arcg"><circle id="arc" cx="120" cy="120" r="89" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-dasharray="170 395" transform="rotate(-90 120 120)"/></g>
    <g class="dots"><circle cx="120" cy="120" r="77" fill="none" stroke="currentColor" stroke-opacity=".5" stroke-width="2" stroke-dasharray="1 7" stroke-linecap="round"/></g>
    <circle cx="120" cy="120" r="62" fill="url(#core)" stroke="currentColor" stroke-opacity=".65" stroke-width="1.5"/>
    <text x="120" y="125" text-anchor="middle" fill="#f2f9ff" font-family="Consolas,monospace" font-weight="600" font-size="15" letter-spacing="3">J.A.R.V.I.S.</text>
  </svg>
  <div class="pills"><span class="tag" id="rstate">LOADING</span><span class="tag">LOCAL</span></div>
  <span id="rdetail">reading the records</span>
</div>

<span class="hud note">Read-only view of the JARVIS control plane. Dashed nodes are PREVIEW, not records. Drifting is decoration and means nothing; glow, ripples and new nodes appear only for real changes. Nothing is verified unless a record says so.</span>

<aside class="drawer glass" id="drawer" aria-label="Records">
  <header><h2>Records</h2><button class="close" id="dclose">Close</button></header>
  <ul id="glist"></ul>
  <div id="panels"></div>
</aside>

<script nonce="__NONCE__">
"use strict";
const token = new URLSearchParams(location.hash.slice(1)).get("t") || "";
history.replaceState(null, "", location.pathname);
const $ = (id) => document.getElementById(id);
const COLORS = {project: "#5ee7ff", task: "#3ddc97", failed: "#ff6b79", note: "#f2c14e", result: "#ff9f43", preview: "#9fb4c4"};
const STATE_COLORS = {IDLE: "#5ee7ff", RUNNING: "#5ee7ff", WAITING: "#a78bfa", DEFERRED: "#a78bfa", COMPLETED: "#3ddc97", CANCELLED: "#8aa0b2",
  ERROR: "#ff6b79", AUDIT_FAULT: "#ff6b79", LISTENING: "#f2c14e", SPEAKING: "#5eead4"};
const PARTIAL = {IDLE: 1, RUNNING: 1, WAITING: 1, DEFERRED: 1};
const KIND_NAMES = {project: "Projects", task: "Tasks", note: "Notes", result: "Relayed results", preview: "PREVIEW (not records)"};
let ambient = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

async function call(path) {
  const r = await fetch(path, {headers: {"X-JARVIS-Token": token}, cache: "no-store"});
  const body = await r.json();
  if (!r.ok) throw new Error(body.error || ("HTTP " + r.status));
  return body;
}

// ---------------------------------------------------------------- records drawer (the same data, as text)
const PANELS = [["status","Status"],["doctor","Health (doctor)"],["projects","Projects"],["tasks","Tasks"],
  ["notes","Notes"],["results","Relayed results (untrusted)"],["audit","Audit chain"],["resume","Resume"]];
const boxes = {};
for (const [key, title] of PANELS) {
  const s = document.createElement("section"), h = document.createElement("h3"), t = document.createElement("span"), b = document.createElement("span");
  t.textContent = title; b.className = "badge LOADING"; b.textContent = "LOADING"; h.append(t, b);
  const pre = document.createElement("pre"); pre.className = "rec"; s.append(h, pre); $("panels").append(s); boxes[key] = {b, pre};
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
  } catch (e) { b.className = "badge ERROR"; b.textContent = "ERROR"; pre.textContent = String(e.message); }
}
function openDrawer(open) { $("drawer").classList.toggle("open", open); if (open) $("dclose").focus(); else $("brec").focus(); }
$("brec").addEventListener("click", () => openDrawer(true));
$("dclose").addEventListener("click", () => openDrawer(false));

// ---------------------------------------------------------------- the ring (state comes only from real records)
async function ring() {
  try { const r = await call("/api/ring"); setRing(r.state, r.detail);
  } catch (e) { setRing("ERROR", String(e.message)); }
}
function setRing(state, detail) {
  const box = $("ringbox");
  box.className = "hud ringbox " + state;
  document.documentElement.style.setProperty("--rc", STATE_COLORS[state] || "#5ee7ff");
  $("arc").setAttribute("stroke-dasharray", PARTIAL[state] ? "170 395" : "565 0");
  $("rstate").textContent = state.replace("_", " "); $("rdetail").textContent = detail;
}

// ---------------------------------------------------------------- the galaxy
const canvas = $("gcanvas"), ctx = canvas.getContext("2d");
let G = {nodes: [], links: []}, born = {}, pos = {}, firstLoad = true, picked = "", hovered = "", hidden = {};
let yaw = 0.6, pitch = 0.3, drag = null, W = 0, H = 0, CX = 0, CY = 0, S = 1;
function size() {
  const r = canvas.getBoundingClientRect(), d = window.devicePixelRatio || 1;
  W = r.width; H = r.height; canvas.width = Math.max(1, Math.round(W * d)); canvas.height = Math.max(1, Math.round(H * d)); ctx.setTransform(d, 0, 0, d, 0, 0);
  CX = W * 0.43; CY = H * 0.5; S = Math.min(W * 0.25, H * 0.38);
}
function phase(id) { let h = 0; for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 997; return h / 997 * 6.2832; }
function colorOf(n) { return n.kind === "task" && n.status === "FAILED" ? COLORS.failed : (COLORS[n.kind] || "#ffffff"); }
function dim(n) { return n.status === "CANCELLED" || n.status === "COMPLETED_UNVERIFIED"; }
const sprites = {};
function sprite(c) {
  if (sprites[c]) return sprites[c];
  const s = document.createElement("canvas"); s.width = s.height = 96; const g = s.getContext("2d");
  const gr = g.createRadialGradient(48, 48, 0, 48, 48, 48);
  gr.addColorStop(0, "#ffffff"); gr.addColorStop(0.14, c); gr.addColorStop(0.32, c + "77"); gr.addColorStop(1, c + "00");
  g.fillStyle = gr; g.fillRect(0, 0, 96, 96); sprites[c] = s; return s;
}
function project3(n, t) {
  const ph = phase(n.id), a = ambient ? 0.022 : 0;
  const x = n.x + a * Math.sin(t / 1700 + ph), y = n.y + a * Math.sin(t / 2100 + ph * 1.3), z = n.z + a * Math.sin(t / 1900 + ph * 0.7);
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
  const x1 = x * cy - z * sy, z1 = x * sy + z * cy, y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp, f = 3.2 / (3.2 + z2);
  return {sx: CX + S * 1.24 * x1 * f, sy: CY + S * y2 * f, f, z: z2, ph};
}
function grow(id, t) { const b = born[id]; return b === undefined ? 1 : Math.max(0, Math.min(1, (t - b) / 700)); }
function draw(t) {
  ctx.clearRect(0, 0, W, H);
  ctx.save(); ctx.translate(CX, CY); ctx.rotate(-0.245); ctx.strokeStyle = "rgba(159,216,255,.07)"; ctx.lineWidth = 1;
  for (const k of [1, 0.77, 0.53]) { ctx.beginPath(); ctx.ellipse(0, 0, S * 1.38 * k, S * 0.44 * k, 0, 0, 6.2832); ctx.stroke(); }
  ctx.restore();
  const vis = G.nodes.filter((n) => !hidden[n.kind]); pos = {};
  for (const n of vis) pos[n.id] = project3(n, t);
  for (const l of G.links) {
    const a = pos[l.from], b = pos[l.to]; if (!a || !b) continue;
    const g = Math.max(grow(l.from, t), grow(l.to, t)), f = Math.max(0.12, Math.min(0.5, (a.f + b.f) * 0.25));
    ctx.strokeStyle = "rgba(125,211,252," + f.toFixed(2) + ")"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(a.sx + (b.sx - a.sx) * g, a.sy + (b.sy - a.sy) * g); ctx.stroke();
  }
  const order = vis.slice().sort((p, q) => pos[q.id].z - pos[p.id].z);
  for (const n of order) {
    const p = pos[n.id], breathe = ambient ? 1 + 0.07 * Math.sin(t / 900 + p.ph) : 1;
    const base = n.kind === "project" ? 10 : n.kind === "preview" ? 6 : n.kind === "result" ? 5 : 5.5;
    const r = Math.max(0.5, base * (0.55 + 0.85 * p.f) * breathe * grow(n.id, t)), c = colorOf(n);
    const alpha = Math.max(0.35, Math.min(1, 0.4 + 0.75 * p.f)) * (dim(n) ? 0.62 : 1);
    ctx.globalAlpha = alpha;
    if (n.kind === "preview") { ctx.setLineDash([3, 3]); ctx.strokeStyle = "#9fb4c4"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(p.sx, p.sy, r + 1, 0, 6.2832); ctx.stroke(); ctx.setLineDash([]); }
    else { const R = r * 3.3; ctx.drawImage(sprite(c), p.sx - R, p.sy - R, R * 2, R * 2); }
    ctx.globalAlpha = 1;
    if (n.id === picked || n.id === hovered) { ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(p.sx, p.sy, r + 5, 0, 6.2832); ctx.stroke(); }
    if (n.kind === "project" || n.kind === "preview" || n.id === picked || n.id === hovered) {
      const text = n.kind === "preview" ? n.label + " (PREVIEW)" : n.label; ctx.font = "12px Segoe UI, sans-serif"; const tw = ctx.measureText(text).width;
      const left = p.sx + r + 8 + tw > W - 4; ctx.fillStyle = "#d6e6f2"; ctx.shadowColor = "#000"; ctx.shadowBlur = 8;
      ctx.fillText(text, left ? p.sx - r - 8 - tw : p.sx + r + 8, p.sy + 4); ctx.shadowBlur = 0;
    }
  }
  for (const id of Object.keys(born)) {   // ripples for a record that really just appeared
    const age = (t - born[id]) / 1500, p = pos[id];
    if (age > 1.3) { delete born[id]; continue; }
    if (!p) continue;
    for (let k = 0; k < 2; k++) { const a = age - k * 0.25; if (a < 0 || a > 1) continue;
      ctx.strokeStyle = "rgba(242,193,78," + ((1 - a) * 0.8).toFixed(2) + ")"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(p.sx, p.sy, 8 + a * 60, 0, 6.2832); ctx.stroke(); }
  }
}
let prev = 0;
function frame(now) {
  const dt = Math.min(0.05, (now - prev) / 1000); prev = now;
  if (ambient && !drag) yaw += dt * 0.012;
  draw(now); requestAnimationFrame(frame);
}

function nodeAt(ev) {
  const r = canvas.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top; let best = null, bd = 14;
  for (const n of G.nodes) { const p = pos[n.id]; if (!p) continue; const d = Math.hypot(p.sx - mx, p.sy - my); if (d < bd) { bd = d; best = n; } }
  return best;
}
async function pick(n) {
  picked = n.id; $("itl").textContent = n.label; $("ist").textContent = n.kind.toUpperCase() + "  " + n.status;
  const fallback = n.note + (n.kind === "result" ? "\nThe relayed text is not shown here: it is untrusted data." : "");
  for (const b of $("glist").querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.id === n.id));
  if (!n.detail) { $("ibd").textContent = fallback; return; }
  const [kind, id] = n.detail.split("/"); $("ibd").textContent = "loading...";
  try { const r = await call("/api/" + kind + "/" + encodeURIComponent(id)); $("ibd").textContent = r.text.slice(0, 2400); }
  catch (e) { $("ibd").textContent = String(e.message); }
}
canvas.addEventListener("pointerdown", (ev) => { drag = {x: ev.clientX, y: ev.clientY, moved: false}; canvas.setPointerCapture(ev.pointerId); canvas.style.cursor = "grabbing"; });
canvas.addEventListener("pointermove", (ev) => {
  if (drag) { const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
    yaw += dx * 0.008; pitch = Math.max(-1.3, Math.min(1.3, pitch + dy * 0.008)); drag.x = ev.clientX; drag.y = ev.clientY; }
  else { const n = nodeAt(ev); hovered = n ? n.id : ""; canvas.style.cursor = n ? "pointer" : "grab"; } });
canvas.addEventListener("pointerup", (ev) => { const moved = drag && drag.moved; drag = null; canvas.style.cursor = "grab"; if (!moved) { const n = nodeAt(ev); if (n) pick(n); } });
$("gview").addEventListener("keydown", (ev) => { const k = ev.key; if (!k.startsWith("Arrow")) return; ev.preventDefault();
  if (k === "ArrowLeft") yaw -= 0.1; if (k === "ArrowRight") yaw += 0.1; if (k === "ArrowUp") pitch = Math.max(-1.3, pitch - 0.1); if (k === "ArrowDown") pitch = Math.min(1.3, pitch + 0.1); });
$("bleft").addEventListener("click", () => { yaw -= 0.26; });
$("bright").addEventListener("click", () => { yaw += 0.26; });
$("bfit").addEventListener("click", () => { yaw = 0.6; pitch = 0.3; hidden = {}; buildFilters(); });
$("bmotion").addEventListener("click", () => { ambient = !ambient; $("bmotion").setAttribute("aria-pressed", String(ambient)); document.body.classList.toggle("calm", !ambient); });
$("bmotion").setAttribute("aria-pressed", String(ambient)); document.body.classList.toggle("calm", !ambient);
window.addEventListener("resize", size);

function buildFilters() {
  const box = $("filters"); box.replaceChildren(); const counts = {};
  for (const n of G.nodes) counts[n.kind] = (counts[n.kind] || 0) + 1;
  for (const k of ["project", "task", "note", "result", "preview"]) {
    const b = document.createElement("button"); b.className = "chip"; b.setAttribute("aria-pressed", String(!hidden[k]));
    const d = document.createElement("span"); d.className = "dot";
    if (k === "preview") d.style.boxShadow = "inset 0 0 0 1.5px #9fb4c4"; else { d.style.background = COLORS[k]; d.style.boxShadow = "0 0 9px " + COLORS[k]; }
    const name = document.createElement("span"); name.textContent = KIND_NAMES[k]; const c = document.createElement("span"); c.className = "cnt"; c.textContent = counts[k] || 0;
    b.append(d, name, c); b.addEventListener("click", () => { hidden[k] = !hidden[k]; b.setAttribute("aria-pressed", String(!hidden[k])); }); box.append(b);
  }
}
function buildList() {
  const ul = $("glist"); ul.setAttribute("aria-label", "Galaxy nodes"); ul.replaceChildren();
  for (const n of G.nodes) { const li = document.createElement("li"), b = document.createElement("button");
    b.dataset.id = n.id; b.setAttribute("aria-pressed", String(n.id === picked)); b.textContent = n.kind.toUpperCase() + "  " + n.label + "  " + n.status;
    b.addEventListener("click", () => pick(n)); li.append(b); ul.append(li); }
}
async function loadGalaxy() {
  try { const g = await call("/api/galaxy");
    if (g.error) { $("gcount").textContent = g.error; return; }
    const known = new Set(G.nodes.map((n) => n.id)), now = performance.now();
    if (!firstLoad) for (const n of g.nodes) if (n.kind !== "preview" && !known.has(n.id)) born[n.id] = now;   // a record that was not there before
    firstLoad = false; G = g; const c = g.counts;
    $("gcount").textContent = c.projects + " project(s), " + c.tasks + " task(s), " + c.notes + " note(s), " + c.results + " relayed result(s)";
    buildFilters(); buildList();
  } catch (e) { $("gcount").textContent = String(e.message); } }

// ---------------------------------------------------------------- refresh: everything every 15 s, ring and galaxy every 5 s
let busy = false;
async function refreshAll() { if (busy) return; busy = true; try { await ring(); loadGalaxy(); for (const [key] of PANELS) panel(key); } finally { busy = false; } }
async function refreshLive() { if (busy || document.hidden) return; busy = true; try { await ring(); await loadGalaxy(); } finally { busy = false; } }
$("brefresh").addEventListener("click", refreshAll);
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") openDrawer(false);
  if ((ev.key === "r" || ev.key === "R") && ev.target.tagName !== "INPUT") refreshAll(); });
size(); requestAnimationFrame(frame); refreshAll();
setInterval(refreshLive, 5000); setInterval(() => { if (!document.hidden) for (const [key] of PANELS) panel(key); }, 15000);
</script></body></html>
"""


def html(nonce: str) -> str:
    return _HTML.replace("__NONCE__", nonce)
