/* The living detail sheet, interactive. Load after director.js and sheet.js.

   The sheet fills the window. Click a detail to fly to it. Its 3D pane is then live: drag to orbit,
   scroll to zoom, and the four chips under it switch the view (assembled, exploded, section, x-ray).
   Drag the paper to pan, scroll over the paper to zoom, double-click to see the whole sheet. */
(() => {
const SH = window.__sheet, cv = SH.comp, PROPS = ['tx', 'ty', 'tz', 'az', 'el', 'span', 'ex', 'xray', 'sp'];
cv.id = 'living-sheet'; cv.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;display:block;z-index:20;touch-action:none;cursor:grab;background:#cbd0d6';
const hud = document.createElement('div');
hud.style.cssText = 'position:fixed;left:max(16px,env(safe-area-inset-left,0px));bottom:14px;z-index:21;font:500 12.5px "IBM Plex Sans","Segoe UI",sans-serif;color:#18202a;background:rgba(251,251,247,.92);border:1px solid #c3c9d0;border-radius:3px;padding:6px 10px;pointer-events:none;max-width:calc(100vw - 32px)';
hud.textContent = 'Building the sheet from the models…';
document.body.append(cv, hud);

// where each box's section plane sits, and which side of it stays
const SEC = { A: { axis: 'y', keep: -1, sp: 0, out: 40 }, 1: { axis: 'x', keep: -1, sp: 8.0, out: 60 }, 2: { axis: 'y', keep: 1, sp: 0, out: -40 },
  3: { axis: 'x', keep: -1, sp: 3.17, out: 40 }, 4: { axis: 'x', keep: -1, sp: 4.875, out: 60 } };
const st = {}, goal = {}; let cam = null, camGoal = null, live = null, hot = null, dirty = true, drag = null, last = performance.now();
const dpr = () => Math.min(window.devicePixelRatio || 1, 2), W = () => Math.round(innerWidth * dpr()), H = () => Math.round(innerHeight * dpr());
const kpx = () => cam.ppi * H() / 1080;
const fitPpi = (w, h, pad) => Math.min(1080 / (h + pad), 1080 * (W() / H()) / (w + pad));
const whole = () => ({ cx: SH.SW / 2, cy: SH.SH / 2, ppi: fitPpi(SH.SW, SH.SH, 1.2) });
const onCell = c => ({ cx: c.rect[0] + c.rect[2] / 2, cy: c.rect[1] + c.rect[3] / 2, ppi: fitPpi(c.rect[2], c.rect[3], 0.8) });
const toSheet = e => { const r = cv.getBoundingClientRect(), k = kpx() / dpr(); return [cam.cx + (e.clientX - r.left - r.width / 2) / k, cam.cy + (e.clientY - r.top - r.height / 2) / k]; };
const inside = (p, q) => p[0] >= q[0] && p[0] <= q[0] + q[2] && p[1] >= q[1] && p[1] <= q[1] + q[3];
const pane3 = c => [c.rect[0] + c.p3[0], c.rect[1] + c.p3[1], c.p3[2], c.p3[3]];
function pick(p) { for (const c of SH.CELLS) { if (!inside(p, c.rect)) continue; const chip = SH.chipRects(c).find(r => inside(p, [r.x, r.y, r.w, r.h]));
    return { cell: c, chip: chip ? chip.name : null, pane: inside(p, pane3(c)) }; } return null; }

function setMode(c, name) { const g = goal[c.id], s = SEC[c.id]; g.chip = name; g.ex = name === 'EXPLODED' ? 1 : 0; g.xray = name === 'X-RAY' ? 1 : 0; g.sp = name === 'SECTION' ? s.sp : s.out; dirty = true; }
function goLive(c) { if (live === c) return; live = c; dirty = true; }
function tick(now) { requestAnimationFrame(tick); const dt = Math.min(0.05, (now - last) / 1000); last = now; const a = 1 - Math.exp(-dt * 7);
  if (camGoal) { cam.cx += (camGoal.cx - cam.cx) * a; cam.cy += (camGoal.cy - cam.cy) * a; cam.ppi *= Math.pow(camGoal.ppi / cam.ppi, a);
    if (Math.abs(camGoal.cx - cam.cx) + Math.abs(camGoal.cy - cam.cy) < 0.004 && Math.abs(Math.log(camGoal.ppi / cam.ppi)) < 0.002) camGoal = null; dirty = true; }
  if (live) { const s = st[live.id], g = goal[live.id]; for (const p of PROPS) { const d = g[p] - s[p]; if (Math.abs(d) > 1e-4) { s[p] += d * (p === 'sp' ? Math.min(1, a * 0.6) : a); dirty = true; } else s[p] = g[p]; } s.chip = g.chip; }
  if (!dirty) return; dirty = false;
  SH.draw(cam, W(), H(), live ? { cell: live, state: { ...st[live.id], draw: 0, xsteel: live.xsteel } } : null, hot); }

cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); const p = toSheet(e), h = pick(p);
  drag = { x: e.clientX, y: e.clientY, moved: 0, orbit: !!(h && h.pane && h.cell === live), h }; cv.style.cursor = 'grabbing'; });
cv.addEventListener('pointermove', e => { if (!cam) return;
  if (!drag) { const h = pick(toSheet(e)), n = h && h.chip ? { cell: h.cell, chip: h.chip } : null; if ((n && n.chip) !== (hot && hot.chip) || (n && n.cell) !== (hot && hot.cell)) { hot = n; dirty = true; }
    cv.style.cursor = h && (h.chip || h.cell !== live) ? 'pointer' : 'grab'; return; }
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy);
  if (drag.orbit) { const g = goal[live.id], s = st[live.id]; g.az = s.az = s.az - dx * 0.4; g.el = s.el = Math.max(-5, Math.min(85, s.el + dy * 0.3)); }
  else { const k = kpx() / dpr(); cam.cx -= dx / k; cam.cy -= dy / k; camGoal = null; } dirty = true; });
cv.addEventListener('pointerup', e => { const d = drag; drag = null; cv.style.cursor = 'grab'; if (!d || d.moved > 5 || !d.h) return; const c = d.h.cell;
  if (d.h.chip) { goLive(c); setMode(c, d.h.chip); if (!camGoal && cam.ppi < onCell(c).ppi * 0.7) camGoal = onCell(c); }
  else if (c !== live || cam.ppi < onCell(c).ppi * 0.7) { goLive(c); camGoal = onCell(c); } });
cv.addEventListener('dblclick', () => { camGoal = whole(); });
cv.addEventListener('wheel', e => { e.preventDefault(); if (!cam) return; const p = toSheet(e), h = pick(p), f = Math.exp(-e.deltaY * 0.0015);
  if (h && h.pane && h.cell === live) { const g = goal[live.id]; g.span = Math.max(4, Math.min(600, g.span / f)); }
  else { const n = Math.max(whole().ppi * 0.6, Math.min(420, cam.ppi * f)), r = n / cam.ppi; cam.cx = p[0] - (p[0] - cam.cx) / r; cam.cy = p[1] - (p[1] - cam.cy) / r; cam.ppi = n; camGoal = null; } dirty = true; }, { passive: false });
addEventListener('resize', () => { dirty = true; });
addEventListener('keydown', e => { if (e.key === 'Escape' || e.key === 'f') camGoal = whole(); });

SH.prep().then(() => { for (const c of SH.CELLS) { const s = { ...SH.live3(c, 0) }; s.sp = SEC[c.id].out; s.chip = c.keys[0].chip; st[c.id] = s; goal[c.id] = { ...s }; c.sec3 = { axis: SEC[c.id].axis, keep: SEC[c.id].keep };
    c.xsteel = !['concrete', 'grout', 'sheathing'].some(k => DATAHAS(c.case, k)); c.chip = s.chip; }
  cam = whole(); hud.textContent = 'Click a detail to open it. Drag its 3D view to turn it, and use the four buttons under it. Scroll to zoom, double-click for the whole sheet.';
  requestAnimationFrame(tick); }).catch(err => { hud.textContent = 'The sheet could not be built: ' + err; });
const ALL = JSON.parse(document.getElementById('dt-data').textContent), DATAHAS = (ci, cls) => ALL[ci].parts.some(p => p.cls === cls);
// for tests on a page that is not on screen, where frames do not tick by themselves
window.__sheetApp = { step(ms, n = 1) { for (let i = 0; i < n; i++) tick(last + ms); }, open(id, chip) { const c = SH.cell(id); goLive(c); camGoal = onCell(c); if (chip) setMode(c, chip); },
  get state() { return { live: live && live.id, cam, st: live && st[live.id] }; } };
})();
