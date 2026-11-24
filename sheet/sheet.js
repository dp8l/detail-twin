/* The living detail sheet. Load after director.js on a page that carries the viewer.

   A structural detail sheet (ARCH E1, 42 x 30 in.) drawn on a 2D canvas at true drawing scales:
   border, title block with a revision table, sheet notes, boxed details with number bubbles and
   scales, and a frame elevation with grid bubbles, elevation tags and detail markers. Each box holds
   the 2D detail (the model rendered as line work, with dimensions, callouts, weld symbols and bolt
   centre marks taken from the model) beside a 3D pane with four views: assembled, exploded, section,
   x-ray. The 3D pane of the box in use is the live viewer; the others hold their last frame.

   Video:        await __sheet.prep();  __sheet.run('sheet_full', 1920, 1080, 30)
   Interactive:  app.js drives __sheet.draw(...)

   Sheet units are inches of paper, model units are inches. Typed by hand: detail titles, the sheet
   number and title, the sheet notes, and where each label sits. Everything else is read from the
   model: every dimension is measured from the parts, every callout is a part's own name and count,
   every weld size is the weld part's own leg. */
(() => {
const D = window.__dt, X = D.x, S = D.S, T = THREE, DIR = window.__dir;
const DATA = JSON.parse(document.getElementById('dt-data').textContent);
const INK = '#161b22', PAPER = '#fbfbf7', ACC = '#1c5bc9', MUTE = '#8b95a1', SHEETNO = 'S-501', ISSUED = '2026-11-24', NAME = 'detail-twin', REPO = 'github.com/dp8l/detail-twin';
const FONT = '"IBM Plex Sans", "Segoe UI", sans-serif';
const SW = 42, SH = 30, M = 0.5, TB = 4.5, DW = SW - 2 * M - TB, AH = 9.4, CW = DW / 2, CH = (SH - 2 * M - AH) / 2;
const SCALES = [[1 / 4, '3" = 1\'-0"'], [1 / 8, '1 1/2" = 1\'-0"'], [1 / 12, '1" = 1\'-0"'], [1 / 16, '3/4" = 1\'-0"'], [1 / 32, '3/8" = 1\'-0"'], [1 / 48, '1/4" = 1\'-0"']];
const lerp = (a, b, u) => a + (b - a) * u, ease = u => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
const V = (x, y, z) => new T.Vector3(x, y, z);

function fmtIn(x, den = 16) { let n = Math.round(Math.abs(x) * den); const whole = Math.floor(n / den); let rem = n - whole * den, d = den;
  while (rem && rem % 2 === 0) { rem /= 2; d /= 2; } const ft = Math.floor(whole / 12), inch = whole - ft * 12, fr = rem ? rem + '/' + d : '';
  return ft ? `${ft}'-${inch}${fr ? ' ' + fr : ''}"` : (fr && inch ? `${inch} ${fr}"` : fr ? `${fr}"` : `${inch}"`); }

// ---- reading the loaded case ---------------------------------------------------------------
const hit = (p, mark) => p.d.mark === mark || p.d.mark.startsWith(mark + '.');
function bb(mark, nth) { const box = new T.Box3(); let n = 0;
  for (const p of S.parts) if (hit(p, mark)) { if (nth === undefined || n === nth) box.union(p.mesh.geometry.boundingBox.clone().applyMatrix4(p.base)); n++; } return box; }
const ctr = (mark, nth = 0) => bb(mark, nth).getCenter(V(0, 0, 0));
const all = mark => S.parts.filter(p => hit(p, mark)).map((p, i) => ctr(mark, i));
function nm(ci, mark) { const r = DATA[ci].bom.find(q => q.mark === mark); return ((r.qty > 1 ? `(${r.qty}) ` : '') + r.name).toUpperCase(); }
const leg = (ci, mark) => DATA[ci].parts.find(p => p.mark === mark).props.Leg.replace('"', '');
const inPlane = d => Math.abs(d.a[1] - d.b[1]) < 1e-6 && Math.abs(d.off[1]) < 1e-6;
const caseDims = (ci, pick) => DATA[ci].dims.filter(inPlane).filter((d, i) => !pick || pick.includes(i)).map(d => ({ a: V(...d.a), b: V(...d.b), off: V(...d.off), text: d.text }));
const dimOf = (a, b, off) => ({ a, b, off, text: fmtIn(a.distanceTo(b)) });
const moved = (d, off) => ({ ...d, off: V(...off) });

// ---- the sheet -----------------------------------------------------------------------------
// p2, p3: the 2D and 3D panes inside a box. scale: paper inches per model inch. keys[0]: first 3D state.
const std = { p2: [0.35, 0.35, 8.8, 7.6], p3: [9.5, 0.35, 8.4, 7.6] };
const CELLS = [
  { id: 'A', n: 'A', title: 'FRAME ELEVATION', case: 3, rect: [M, M, DW, AH], p2: [0.35, 0.35, 19.6, 7.5], p3: [20.3, 0.35, 9.9, 7.5], notes: [30.55, 0.35, 5.6, 7.5], ts: 1.75, scale: 1 / 32,
    v2: { tx: 144, ty: 0, tz: 88, az: -90, el: 0, xray: 1 },
    annot() { const c1 = bb('C1.1'), c2 = bb('C1.2'), f = bb('F1.1'), bm = bb('BM1'), x1 = c1.getCenter(V(0, 0, 0)).x, x2 = c2.getCenter(V(0, 0, 0)).x, xr = bb('F1.2').max.x;
      return { dims: [dimOf(V(x1, 0, f.min.z), V(x2, 0, f.min.z), V(0, 0, -9))],
        notes: [{ text: nm(3, 'BM1'), anchor: V(150, 0, bm.max.z - 8), at: [0.42, 0.145] }, { text: nm(3, 'C1.1'), anchor: V(x1 + 5, 0, 96), at: [0.31, 0.52] },
          { text: nm(3, 'F1.2'), anchor: V(x2 - 30, 0, f.min.z + 9), at: [0.415, 0.80] }],
        grids: [{ x: x1, n: '1', z0: f.min.z - 6, z1: 190 }, { x: x2, n: '2', z0: f.min.z - 6, z1: 190 }],
        levels: [{ p: V(xr + 14, 0, bm.max.z), label: 'T.O. STEEL', z: bm.max.z - f.max.z }, { p: V(xr + 14, 0, c2.min.z), label: 'T.O. BASE PLATE', z: c2.min.z - f.max.z },
          { p: V(xr + 14, 0, f.max.z), label: 'T.O. FOOTING', z: 0 }],
        markers: [{ n: '1', c: ctr('PL1.1'), r: 19, at: [0.085, 0.24] }, { n: '2', c: V(x1, 0, 6), r: 44, at: [0.05, 0.60] }] }; },
    keys: [{ t: 0, tx: 144, ty: 0, tz: 74, az: 62, el: 18, span: 300, ex: 0, xray: 1, sp: 0, chip: 'X-RAY' }, { t: 3.0, az: 44 }] },
  { id: '1', n: '1', title: 'BEAM TO COLUMN, SINGLE-PLATE SHEAR CONNECTION', case: 0, rect: [M, M + AH, CW, CH], ...std, ts: 1, scale: 1 / 4,
    v2: { tx: 11.5, ty: 0, tz: -7.6, az: 90, el: 0, xray: 0 }, sec3: { axis: 'x', keep: -1 },
    annot() { const d = caseDims(0); d[3] = moved(d[3], [0, 0, -5.0]); d[4] = moved(d[4], [0, 0, -5.0]);
      return { dims: d, cmarks: all('B'), breaks: [{ a: V(26.4, 0, 1.2), b: V(26.4, 0, -17.2), to: [-1, 0] }, { a: V(-5.6, 0, 5.9), b: V(5.6, 0, 5.9), to: [0, -1] }, { a: V(-5.6, 0, -20.6), b: V(5.6, 0, -20.6), to: [0, 1] }],
        welds: [{ anchor: V(5.12, 0, -2.2), at: [0.75, 0.115], size: leg(0, 'W1'), both: 1 }],
        notes: [{ text: nm(0, 'PL1'), anchor: V(6.6, 0, -4.6), at: [0.52, 0.06], right: 1 }, { text: nm(0, 'B'), anchor: ctr('B', 1), at: [0.52, 0.115], right: 1 },
          { text: nm(0, 'BM1'), anchor: V(17, 0, -11), at: [0.04, 0.62] }, { text: nm(0, 'C1'), anchor: V(1.5, 0, -19.2), at: [0.50, 0.975] }] }; },
    keys: [{ t: 0, tx: 11, ty: 0, tz: -7.5, az: 50, el: 24, span: 40, ex: 0, xray: 0, sp: 60, chip: 'ASSEMBLED' }, { t: 0.8, az: 46 }, { t: 0.9, chip: 'EXPLODED' },
      { t: 2.5, tx: 15, az: 40, span: 50, ex: 1 }, { t: 3.9, az: 30 }, { t: 5.2, tx: 10, az: 38, span: 38, ex: 0 }, { t: 5.3, chip: 'SECTION' },
      { t: 7.4, tx: 8, az: 30, el: 14, span: 18, sp: 8.0 }, { t: 8.3, az: 24 }] },
  { id: '2', n: '2', title: 'COLUMN BASE, SPREAD FOOTING AND PEDESTAL', case: 1, rect: [M + CW, M + AH, CW, CH], ...std, ts: 1, scale: 1 / 12,
    v2: { tx: 0, ty: 0, tz: 13, az: -90, el: 0, xray: 0, sec: { axis: 'y', keep: 1, sp: 0 } }, sec3: { axis: 'y', keep: 1 },
    annot() { const f = bb('F1'), p = bb('P1'), m = bb('M1'), c = bb('C1');
      return { dims: [dimOf(V(f.min.x, 0, f.min.z), V(f.max.x, 0, f.min.z), V(0, 0, -7)), dimOf(V(f.max.x, 0, f.min.z), V(f.max.x, 0, f.max.z), V(6, 0, 0)),
          dimOf(V(p.max.x + 9, 0, p.min.z), V(p.max.x + 9, 0, p.max.z), V(5, 0, 0)), dimOf(V(f.min.x, 0, f.min.z), V(f.min.x, 0, m.min.z), V(-5, 0, 0))],
        welds: [{ anchor: V(c.max.x, 0, c.min.z + 0.15), at: [0.64, 0.15], size: leg(1, 'W2'), both: 0 }],
        notes: [{ text: nm(1, 'C1'), anchor: V(2, 0, 48), at: [0.62, 0.06] }, { text: nm(1, 'BP1'), anchor: V(6.5, 0, 25.5), at: [0.64, 0.26] },
          { text: nm(1, 'AR'), anchor: V(2.5, 0, 17), at: [0.64, 0.32] }, { text: nm(1, 'V1'), anchor: V(-7.75, 0, 15.5), at: [0.02, 0.30] },
          { text: nm(1, 'T1'), anchor: V(-8.3, 0, 9), at: [0.02, 0.37] }, { text: nm(1, 'M1'), anchor: V(-22, 0, m.min.z + 0.3), at: [0.02, 0.58] }] }; },
    keys: [{ t: 0, tx: 0, ty: 0, tz: 12, az: -52, el: 26, span: 104, ex: 0, xray: 0, sp: -40, chip: 'ASSEMBLED' }, { t: 0.5, chip: 'X-RAY' }, { t: 1.8, xray: 1 },
      { t: 4.2, tz: 10, az: 30, el: 30, span: 84 }, { t: 4.3, chip: 'EXPLODED' }, { t: 5.4, ex: 1, tz: 22, span: 92 }, { t: 6.0 }, { t: 7.0, ex: 0, tz: 12 },
      { t: 7.1, chip: 'SECTION' }, { t: 9.3, tz: 6, az: -74, el: 12, span: 90, sp: 0 }, { t: 10.0, az: -78 }] },
  { id: '3', n: '3', title: 'BEAM TO GIRDER, COPED TOP FLANGE', case: 4, rect: [M, M + AH + CH, CW, CH], ...std, ts: 1, scale: 1 / 4,
    v2: { tx: 7.5, ty: 0, tz: -9.5, az: 90, el: 0, xray: 0 },
    annot() { return { dims: caseDims(4, [0, 1, 2, 6, 7]), cmarks: all('B'), breaks: [{ a: V(22.4, 0, 1.2), b: V(22.4, 0, -17.2), to: [-1, 0] }],
        welds: [{ anchor: V(0.3, 0, -10.0), at: [0.385, 0.915], size: leg(4, 'W1'), both: 1 }],
        notes: [{ text: nm(4, 'PL1'), anchor: V(4.0, 0, -10.2), at: [0.50, 0.80], right: 1 }, { text: nm(4, 'B'), anchor: ctr('B', 2), at: [0.50, 0.855], right: 1 },
          { text: nm(4, 'BM1'), anchor: V(12, 0, -12.5), at: [0.04, 0.60] }, { text: nm(4, 'G1'), anchor: V(-2.7, 0, -0.22), at: [0.82, 0.10] }] }; },
    keys: [{ t: 0, tx: 8, ty: 0, tz: -7, az: 58, el: 24, span: 46, ex: 0, xray: 0, sp: 0, chip: 'ASSEMBLED' }, { t: 0.6, chip: 'EXPLODED' },
      { t: 2.1, tx: 12, az: 50, span: 54, ex: 1 }, { t: 3.5, az: 40 }, { t: 4.8, tx: 8, az: 48, span: 44, ex: 0 }, { t: 4.9, chip: 'ASSEMBLED' }, { t: 5.8, az: 44 }] },
  { id: '4', n: '4', title: 'SHEAR WALL HOLD-DOWN AT FOUNDATION', case: 2, rect: [M + CW, M + AH + CH, CW, CH], ...std, ts: 1, scale: 1 / 4,
    v2: { tx: 9, ty: 0, tz: 1.6, az: 90, el: 0, xray: 1 },
    annot() { const ep = bb('EP'), st = bb('ST', 0), hr = bb('HR'), fw = bb('FW'), xs = st.getCenter(V(0, 0, 0)).x, xr = hr.getCenter(V(0, 0, 0)).x;
      return { dims: [dimOf(V(ep.max.x, 0, fw.max.z), V(xr, 0, fw.max.z), V(0, 0, -2.6)), dimOf(V(xr, 0, fw.max.z), V(xr, 0, hr.min.z), V(-8.5, 0, 0))],
        notes: [{ text: nm(2, 'EP'), anchor: V(1.75, 0, 10), at: [0.82, 0.28] }, { text: nm(2, 'ST'), anchor: V(xs, 0, 11), at: [0.03, 0.20] },
          { text: nm(2, 'SC'), anchor: ctr('SC', 6), at: [0.03, 0.30] }, { text: nm(2, 'HD'), anchor: V(5.6, 0, 5), at: [0.03, 0.40] },
          { text: nm(2, 'SP'), anchor: V(13, 0, 0.75), at: [0.03, 0.66] }, { text: nm(2, 'AB'), anchor: V(10, 0, -4.5), at: [0.03, 0.80] },
          { text: nm(2, 'HR'), anchor: V(xr, 0, -8), at: [0.03, 0.90] }] }; },
    keys: [{ t: 0, tx: 7, ty: 3, tz: 9, az: 66, el: 20, span: 32, ex: 0, xray: 0, sp: 0, chip: 'ASSEMBLED' }, { t: 0.6, chip: 'EXPLODED' },
      { t: 2.1, tx: 11, az: 74, el: 18, span: 40, ex: 1 }, { t: 3.5, az: 80 }, { t: 4.8, tx: 8, az: 70, span: 34, ex: 0 }, { t: 4.9, chip: 'ASSEMBLED' }, { t: 6.2, az: 66 }] },
];
const SHEET_NOTES = ['DIMENSIONS, CALLOUTS AND WELD SIZES ON THIS SHEET ARE READ FROM THE 3D MODEL OF EACH DETAIL.',
  'EACH DETAIL CARRIES A 3D VIEW: ASSEMBLED, EXPLODED, SECTION AND X-RAY.',
  'DETAILS ARE DRAWN AT THE SCALES NOTED ON A 42 X 30 IN. SHEET.',
  'DETAILS ARE GEOMETRY SAMPLES. MEMBERS AND CONNECTIONS WERE NOT DESIGNED FOR LOAD.',
  'FASTENER, BAR AND LUMBER SIZES IN THE SAMPLES WERE ENTERED BY HAND.'];
const PROPS = ['tx', 'ty', 'tz', 'az', 'el', 'span', 'ex', 'xray', 'sp'];
for (const c of CELLS) { let prev = {}; for (const q of c.keys) { for (const p of PROPS.concat('chip')) if (q[p] === undefined) q[p] = prev[p]; prev = q; }
  c.dur = c.keys[c.keys.length - 1].t; c.chip = c.keys[0].chip; c.v2.span = c.p2[3] / c.scale; c.scaleText = SCALES.find(q => Math.abs(q[0] - c.scale) < 1e-9)[1]; }
const cell = id => CELLS.find(c => c.id === id);

// ---- the timeline: where the sheet camera looks, and which box is live --------------------
const FOCUS = { sheet: { cx: SW / 2, cy: SH / 2, ppi: 1080 / (SH + 1.2) } };
for (const c of CELLS) FOCUS[c.id] = { cx: c.rect[0] + c.rect[2] / 2, cy: c.rect[1] + c.rect[3] / 2, ppi: 1920 / (c.rect[2] + (c.id === 'A' ? 1.0 : 0.8)) };
FOCUS.A.cy = 540 / FOCUS.A.ppi - 0.4;
const CAM = [], LIVE = []; let tt = 0;
const hold = (f, d) => { CAM.push({ t: tt, f }); tt += d; CAM.push({ t: tt, f }); };
hold('sheet', 1.5); tt += 1.6;
for (const id of ['A', '1', '2', '3', '4']) { const c = cell(id); LIVE.push({ cell: id, t0: tt, t1: tt + c.dur }); hold(id, c.dur); tt += id === '4' ? 2.2 : 1.25; }
hold('sheet', 1.4);
const TOTAL = tt, CARD = 3.0;
function camAt(t) { let i = 0; while (i < CAM.length - 2 && t >= CAM[i + 1].t) i++; const a = FOCUS[CAM[i].f], b = FOCUS[CAM[i + 1].f];
  const u = ease(Math.min(1, Math.max(0, (t - CAM[i].t) / Math.max(1e-6, CAM[i + 1].t - CAM[i].t))));
  return { cx: lerp(a.cx, b.cx, u), cy: lerp(a.cy, b.cy, u), ppi: Math.exp(lerp(Math.log(a.ppi), Math.log(b.ppi), u)) }; }
function live3(c, t) { const ks = c.keys; let i = 0; while (i < ks.length - 2 && t >= ks[i + 1].t) i++; const a = ks[i], b = ks[i + 1];
  const u = ease(Math.min(1, Math.max(0, (t - a.t) / Math.max(1e-6, b.t - a.t)))), s = { draw: 0 };
  for (const p of PROPS) s[p] = p === 'span' ? Math.exp(lerp(Math.log(a.span), Math.log(b.span), u)) : lerp(a[p], b[p], u);
  s.chip = t >= b.t ? b.chip : a.chip; return s; }

// ---- 2D drawing primitives, in sheet inches ----------------------------------------------
const comp = document.createElement('canvas'), ctx = comp.getContext('2d');
let k = 1, ox = 0, oy = 0;
const px = (x, y) => [ox + x * k, oy + y * k];
function line(pts, w, color, dash) { ctx.beginPath(); pts.forEach((p, i) => { const q = px(p[0], p[1]); i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]); });
  ctx.lineWidth = Math.max(0.7, w * k); ctx.strokeStyle = color || INK; ctx.setLineDash((dash || []).map(d => d * k)); ctx.lineJoin = 'round'; ctx.stroke(); ctx.setLineDash([]); }
function poly(pts, fill) { ctx.beginPath(); pts.forEach((p, i) => { const q = px(p[0], p[1]); i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]); }); ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); }
function box(x, y, w, h, lw, color, fill) { const a = px(x, y); if (fill) { ctx.fillStyle = fill; ctx.fillRect(a[0], a[1], w * k, h * k); }
  if (lw) { ctx.lineWidth = Math.max(0.7, lw * k); ctx.strokeStyle = color || INK; ctx.strokeRect(a[0], a[1], w * k, h * k); } }
function circle(x, y, r, lw, fill, dash) { const a = px(x, y); ctx.beginPath(); ctx.arc(a[0], a[1], r * k, 0, 7); if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  ctx.lineWidth = Math.max(0.7, lw * k); ctx.strokeStyle = INK; ctx.setLineDash((dash || []).map(d => d * k)); ctx.stroke(); ctx.setLineDash([]); }
function text(str, x, y, size, o = {}) { const a = px(x, y); ctx.save(); ctx.translate(a[0], a[1]); if (o.rot) ctx.rotate(o.rot);
  ctx.font = `${o.weight || 500} ${size * k}px ${FONT}`; ctx.textAlign = o.align || 'left'; ctx.textBaseline = o.base || 'alphabetic';
  if (o.mask) { const w = ctx.measureText(str).width, x0 = o.align === 'center' ? -w / 2 : o.align === 'right' ? -w : 0, pad = size * k * 0.16; ctx.fillStyle = PAPER; ctx.fillRect(x0 - pad, -size * k * 0.86, w + 2 * pad, size * k * 1.08); }
  ctx.fillStyle = o.color || INK; ctx.fillText(str, 0, 0); ctx.restore(); }
function tw(str, size, weight) { ctx.font = `${weight || 500} ${size * 100}px ${FONT}`; return ctx.measureText(str).width / 100; }
function img(im, x, y, w, h) { const a = px(x, y); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high'; ctx.drawImage(im, a[0], a[1], w * k, h * k); }
function arrow(from, to, ts) { line([from, to], 0.011); const vx = to[0] - from[0], vy = to[1] - from[1], L = Math.hypot(vx, vy) || 1, u = [vx / L, vy / L], h = 0.11 * ts, b = [to[0] - u[0] * h, to[1] - u[1] * h];
  poly([to, [b[0] - u[1] * h * 0.3, b[1] + u[0] * h * 0.3], [b[0] + u[1] * h * 0.3, b[1] - u[0] * h * 0.3]], INK); }

function dim2(a0, b0, a1, b1, str, ts, cen, ends) { const sz = 0.15 * ts, dx = b1[0] - a1[0], dy = b1[1] - a1[1], L = Math.hypot(dx, dy) || 1, ux = dx / L, uy = dy / L;
  for (const [p, q] of [[a0, a1], [b0, b1]]) { const ex = q[0] - p[0], ey = q[1] - p[1], e = Math.hypot(ex, ey) || 1, g = Math.min(0.07 * ts, e * 0.3);
    line([[p[0] + ex / e * g, p[1] + ey / e * g], [q[0] + ex / e * 0.09 * ts, q[1] + ey / e * 0.09 * ts]], 0.011); }
  line([a1, b1], 0.011);
  for (const p of [a1, b1]) { const h = 0.075 * ts, sx = (ux - uy) * 0.7071, sy = (uy + ux) * 0.7071; line([[p[0] - sx * h, p[1] - sy * h], [p[0] + sx * h, p[1] + sy * h]], 0.024); }
  let ang = Math.atan2(dy, dx); if (ang > Math.PI / 2 + 1e-6 || ang <= -Math.PI / 2 + 1e-6) ang += Math.PI;
  const nx = Math.sin(ang), ny = -Math.cos(ang), w = tw(str, sz, 500); let mx = (a1[0] + b1[0]) / 2, my = (a1[1] + b1[1]) / 2;
  if (L < w + 0.1 * ts) { const near = q => ends.filter(e => Math.hypot(e[0] - q[0], e[1] - q[1]) < 0.02).length, na = near(a1), nb = near(b1);   // a short dimension reads outside, away from its neighbour
    const fa = na !== nb ? na < nb : Math.hypot(a1[0] - cen[0], a1[1] - cen[1]) >= Math.hypot(b1[0] - cen[0], b1[1] - cen[1]), e = fa ? a1 : b1, sg = fa ? -1 : 1, run = w + 0.2 * ts;
    line([e, [e[0] + ux * sg * run, e[1] + uy * sg * run]], 0.011); mx = e[0] + ux * sg * (run / 2 + 0.03 * ts); my = e[1] + uy * sg * (run / 2 + 0.03 * ts); }
  text(str, mx + nx * 0.055 * ts, my + ny * 0.055 * ts, sz, { align: 'center', rot: ang, mask: 1 }); }
function note2(anchor, at, str, ts, right) { const sz = 0.14 * ts, w = tw(str, sz, 500), x0 = right ? at[0] - w : at[0], left = x0 + w / 2 < anchor[0];
  const ex = left ? x0 + w + 0.07 * ts : x0 - 0.07 * ts, ey = at[1] - sz * 0.36, sh = (left ? 1 : -1) * 0.22 * ts;
  line([[ex, ey], [ex + sh, ey]], 0.011); arrow([ex + sh, ey], anchor, ts); text(str, x0, at[1], sz, { mask: 1 }); }
function bubble(x, y, r, n) { circle(x, y, r, 0.022, PAPER); line([[x - r, y], [x + r, y]], 0.016);
  text(n, x, y - r * 0.2, r * 0.74, { align: 'center', weight: 600 }); text(SHEETNO, x, y + r * 0.62, r * 0.36, { align: 'center' }); }
function marker2(c, r, at, n, ts) { const br = 0.3 * ts; circle(c[0], c[1], r, 0.016, null, [0.14, 0.09]);
  const vx = at[0] - c[0], vy = at[1] - c[1], L = Math.hypot(vx, vy) || 1; line([[c[0] + vx / L * r, c[1] + vy / L * r], [at[0] - vx / L * br, at[1] - vy / L * br]], 0.014); bubble(at[0], at[1], br, n); }
// fillet weld symbol: reference line, the triangle below it for the arrow side and above it for the other side, the leg to its left
function weld2(anchor, at, size, both, ts) { const L = 1.0 * ts, h = 0.17 * ts, y = at[1], x0 = at[0], x1 = x0 + L, m = x0 + L * 0.5;
  line([[x0, y], [x1, y]], 0.014); arrow([Math.abs(anchor[0] - x0) < Math.abs(anchor[0] - x1) ? x0 : x1, y], anchor, ts);
  for (const s of both ? [1, -1] : [1]) { line([[m, y], [m, y + s * h], [m + h, y], [m, y]], 0.014); text(size, m - 0.05 * ts, y + (s > 0 ? h * 0.92 : -h * 0.22), 0.125 * ts, { align: 'right' }); } }
function cmark2(c, ts) { const r = 0.2 * ts, d = [0.09, 0.03, 0.02, 0.03]; line([[c[0] - r, c[1]], [c[0] + r, c[1]]], 0.008, INK, d); line([[c[0], c[1] - r], [c[0], c[1] + r]], 0.008, INK, d); }
// a member that runs on past the view ends in a break line, and nothing is drawn beyond it
function break2(a, b, to, pane) { const ux = b[0] - a[0], uy = b[1] - a[1], L = Math.hypot(ux, uy) || 1, u = [ux / L, uy / L], n = [-u[1], u[0]], z = 0.13, far = 12, mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
  ctx.save(); const p0 = px(pane[0] - 0.04, pane[1] - 0.04); ctx.beginPath(); ctx.rect(p0[0], p0[1], (pane[2] + 0.08) * k, (pane[3] + 0.08) * k); ctx.clip();
  poly([a, b, [b[0] + to[0] * far, b[1] + to[1] * far], [a[0] + to[0] * far, a[1] + to[1] * far]], PAPER); ctx.restore();
  line([a, [mx - u[0] * z, my - u[1] * z], [mx - u[0] * z / 2 + n[0] * z, my - u[1] * z / 2 + n[1] * z], [mx + u[0] * z / 2 - n[0] * z, my + u[1] * z / 2 - n[1] * z], [mx + u[0] * z, my + u[1] * z], b], 0.016); }
function grid2(p0, p1, n, ts) { const r = 0.27 * ts; line([p0, p1], 0.012, INK, [0.5, 0.08, 0.06, 0.08]); circle(p1[0], p1[1] - r, r, 0.02, PAPER); text(n, p1[0], p1[1] - r + r * 0.36, r * 1.0, { align: 'center', weight: 600 }); }
function level2(p, label, el, ts) { const r = 0.1 * ts, str = label + '   EL. ' + el, L = tw(str, 0.14 * ts) + 0.45 * ts, a = px(p[0], p[1]); line([[p[0] - 0.5 * ts, p[1]], [p[0] + L, p[1]]], 0.012); circle(p[0], p[1], r, 0.014, PAPER);
  for (const [s, e] of [[0, Math.PI / 2], [Math.PI, 1.5 * Math.PI]]) { ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.arc(a[0], a[1], r * k, s, e); ctx.closePath(); ctx.fillStyle = INK; ctx.fill(); }
  text(str, p[0] + 0.24 * ts, p[1] - 0.07 * ts, 0.14 * ts); }

const CHIPS = ['ASSEMBLED', 'EXPLODED', 'SECTION', 'X-RAY'], CHW = 1.7, CHH = 0.4, CHG = 0.1;
const chipRects = c => { const b = [c.rect[0] + c.p3[0], c.rect[1] + c.p3[1], c.p3[2], c.p3[3]], y = b[1] + b[3] + 0.5; let x = b[0] + b[2] - CHIPS.length * CHW - (CHIPS.length - 1) * CHG;
  return CHIPS.map(name => { const r = { name, x, y, w: CHW, h: CHH }; x += CHW + CHG; return r; }); };
function drawCell(c, live, chip, hot) { const [x, y, w, h] = c.rect, ts = c.ts;
  box(x, y, w, h, 0.03);
  const a = [x + c.p2[0], y + c.p2[1], c.p2[2], c.p2[3]]; img(c.img2, ...a);
  const pr = P => { const v = P.clone().sub(c.proj.T); return [a[0] + a[2] / 2 + v.dot(c.proj.r) * c.proj.s, a[1] + a[3] / 2 - v.dot(c.proj.u) * c.proj.s]; }, at = f => [a[0] + f[0] * a[2], a[1] + f[1] * a[3]], an = c.an;
  for (const b of an.breaks || []) break2(pr(b.a), pr(b.b), b.to, a);
  for (const g of an.grids || []) grid2(pr(V(g.x, 0, g.z0)), pr(V(g.x, 0, g.z1)), g.n, ts);
  for (const m of an.cmarks || []) cmark2(pr(m), ts);
  const ends = an.dims.flatMap(d => [pr(d.a.clone().add(d.off)), pr(d.b.clone().add(d.off))]), cen = [0, 1].map(q => ends.reduce((t, e) => t + e[q], 0) / Math.max(1, ends.length));
  for (const d of an.dims) dim2(pr(d.a), pr(d.b), pr(d.a.clone().add(d.off)), pr(d.b.clone().add(d.off)), d.text, ts, cen, ends);
  for (const l of an.levels || []) level2(pr(l.p), l.label, Math.abs(l.z) < 1e-9 ? '0\'-0"' : (l.z > 0 ? '+' : '-') + fmtIn(l.z), ts);
  for (const wd of an.welds || []) weld2(pr(wd.anchor), at(wd.at), wd.size, wd.both, ts);
  for (const n of an.notes) note2(pr(n.anchor), at(n.at), n.text, ts, n.right);
  for (const m of an.markers || []) marker2(pr(m.c), m.r * c.proj.s, at(m.at), m.n, ts);
  const b = [x + c.p3[0], y + c.p3[1], c.p3[2], c.p3[3]];
  img(live ? X.renderer.domElement : c.img3, ...b); box(...b, live ? 0.04 : 0.022, ACC);
  box(b[0], b[1], 1.28, 0.36, 0, null, ACC); text('3D VIEW', b[0] + 0.64, b[1] + 0.262, 0.18, { align: 'center', weight: 600, color: PAPER });
  for (const r of chipRects(c)) { const on = r.name === chip, hv = hot && hot.cell === c && hot.chip === r.name;
    box(r.x, r.y, r.w, r.h, on ? 0 : 0.012, hv ? ACC : MUTE, on ? ACC : null); text(r.name, r.x + r.w / 2, r.y + 0.275, 0.155, { align: 'center', weight: 600, color: on ? PAPER : hv ? ACC : MUTE }); }
  const by = y + h - 0.86; bubble(x + 0.82, by, 0.44, c.n); text(c.title, x + 1.5, by - 0.02, 0.27, { weight: 600 });
  line([[x + 1.5, by + 0.1], [x + 1.5 + tw(c.title, 0.27, 600), by + 0.1]], 0.022); text('SCALE: ' + c.scaleText, x + 1.5, by + 0.38, 0.16);
  if (c.notes) { const q = [x + c.notes[0], y + c.notes[1], c.notes[2], c.notes[3]]; box(...q, 0.016); text('SHEET NOTES', q[0] + 0.25, q[1] + 0.5, 0.24, { weight: 600 });
    line([[q[0] + 0.25, q[1] + 0.6], [q[0] + 0.25 + tw('SHEET NOTES', 0.24, 600), q[1] + 0.6]], 0.018); let yy = q[1] + 1.05;
    SHEET_NOTES.forEach((s, i) => { text((i + 1) + '.', q[0] + 0.25, yy, 0.16); const words = s.split(' '); let ln = '';
      for (const wd of words) { if (tw(ln + wd, 0.16) > q[2] - 0.85) { text(ln, q[0] + 0.6, yy, 0.16); yy += 0.25; ln = ''; } ln += wd + ' '; } text(ln, q[0] + 0.6, yy, 0.16); yy += 0.4; }); } }

function titleBlock() { const x0 = M + DW, w = TB, yb = SH - M, c = x0 + w / 2; box(x0, M, w, SH - 2 * M, 0.03);
  const rows = [['NO.', 'REVISION', 'DATE'], ['0', 'ISSUED FOR REVIEW', ISSUED], ['', '', ''], ['', '', ''], ['', '', '']], rh = 0.5, cols = [0, 0.6, 3.25, w];
  rows.forEach((r, i) => { line([[x0, M + (i + 1) * rh], [x0 + w, M + (i + 1) * rh]], i === 0 ? 0.022 : 0.01);
    r.forEach((s, j) => text(s, x0 + cols[j] + 0.1, M + i * rh + 0.33, 0.145, { weight: i === 0 ? 600 : 500, color: i === 0 ? MUTE : INK })); });
  for (const cx of cols.slice(1, 3)) line([[x0 + cx, M], [x0 + cx, M + rows.length * rh]], 0.01);
  const sect = (y1, label) => { line([[x0, yb - y1], [x0 + w, yb - y1]], 0.03); text(label, x0 + 0.16, yb - y1 + 0.27, 0.14, { color: MUTE }); };
  sect(2.3, 'SHEET'); text(SHEETNO, c, yb - 0.62, 1.05, { align: 'center', weight: 700 });
  sect(3.5, 'DATE'); text(ISSUED, x0 + 0.3, yb - 2.62, 0.3, { weight: 600 }); line([[c + 0.2, yb - 3.5], [c + 0.2, yb - 2.3]], 0.016); text('SCALE', c + 0.36, yb - 3.23, 0.14, { color: MUTE }); text('AS NOTED', c + 0.4, yb - 2.62, 0.3, { weight: 600 });
  sect(6.4, 'SHEET TITLE'); ['TYPICAL', 'STRUCTURAL', 'DETAILS'].forEach((s, i) => text(s, x0 + 0.3, yb - 5.35 + i * 0.66, 0.5, { weight: 600 }));
  sect(8.3, 'DRAWN WITH'); text(NAME, x0 + 0.3, yb - 7.15, 0.5, { weight: 700 }); text('2D DETAILS AND 3D VIEWS FROM ONE MODEL', x0 + 0.3, yb - 6.72, 0.15, { color: MUTE });
  sect(10.4, ''); box(x0 + 0.3, yb - 10.05, w - 0.6, 1.4, 0.05); text('NOT FOR', c, yb - 9.42, 0.42, { align: 'center', weight: 700 }); text('CONSTRUCTION', c, yb - 8.9, 0.42, { align: 'center', weight: 700 }); }

function drawSheet(liveCell, chip, hot) {
  const g = ctx.createLinearGradient(0, 0, 0, comp.height); g.addColorStop(0, '#d7dbe0'); g.addColorStop(1, '#bfc5cc'); ctx.fillStyle = g; ctx.fillRect(0, 0, comp.width, comp.height);
  const s0 = px(0, 0); ctx.save(); ctx.shadowColor = 'rgba(20,28,38,.28)'; ctx.shadowBlur = 0.5 * k; ctx.shadowOffsetY = 0.14 * k; ctx.fillStyle = PAPER; ctx.fillRect(s0[0], s0[1], SW * k, SH * k); ctx.restore();
  box(M * 0.5, M * 0.5, SW - M, SH - M, 0.07);
  for (const c of CELLS) drawCell(c, c === liveCell, c === liveCell ? chip : c.chip, hot);
  titleBlock(); }
function endCard(u, W, H) { ctx.fillStyle = PAPER; ctx.globalAlpha = Math.min(1, u * 1.6); ctx.fillRect(0, 0, W, H); ctx.globalAlpha = Math.min(1, Math.max(0, u * 1.6 - 0.5));
  const r = H * 0.058, cx = W / 2, cy = H * 0.44; ctx.textAlign = 'center'; ctx.fillStyle = INK; ctx.strokeStyle = INK; ctx.lineWidth = Math.max(1.5, H * 0.0032);
  ctx.beginPath(); ctx.arc(cx, cy - H * 0.13, r, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.moveTo(cx - r, cy - H * 0.13); ctx.lineTo(cx + r, cy - H * 0.13); ctx.stroke();
  ctx.font = `600 ${r * 0.74}px ${FONT}`; ctx.fillText('3D', cx, cy - H * 0.13 - r * 0.2); ctx.font = `500 ${r * 0.34}px ${FONT}`; ctx.fillText(SHEETNO, cx, cy - H * 0.13 + r * 0.6);
  ctx.font = `700 ${H * 0.105}px ${FONT}`; ctx.fillText(NAME, cx, cy + H * 0.075);
  ctx.font = `500 ${H * 0.03}px ${FONT}`; ctx.fillStyle = MUTE; ctx.fillText('A SKILL FOR CLAUDE CODE', cx, cy + H * 0.15);
  ctx.font = `500 ${H * 0.036}px ${FONT}`; ctx.fillStyle = ACC; ctx.fillText(REPO, cx, cy + H * 0.245); ctx.globalAlpha = 1; }

// ---- preparing the 2D details and the first 3D frames -----------------------------------
const copyGL = () => { const s = X.renderer.domElement, c = document.createElement('canvas'); c.width = s.width; c.height = s.height; c.getContext('2d').drawImage(s, 0, 0); return c; };
function bolder(src) { const c = document.createElement('canvas'); c.width = src.width; c.height = src.height; const g = c.getContext('2d'); g.drawImage(src, 0, 0);
  g.globalCompositeOperation = 'darken'; for (const [dx, dy] of [[1, 0], [0, 1], [1, 1]]) g.drawImage(src, dx, dy); return c; }
const blk3 = c => ({ case: c.case, sec: c.sec3 || null });
let cur = null;
const api = { CELLS, CAM, LIVE, TOTAL, CARD, FOCUS, SW, SH, CHIPS, chipRects, cell, live3, blk3, comp, status: { state: 'idle' },
  async prep(R = 150) { await Promise.all(['500', '600', '700'].map(w => document.fonts.load(`${w} 20px "IBM Plex Sans"`)));
    for (const c of CELLS) { const b2 = { case: c.case, sec: c.v2.sec ? { axis: c.v2.sec.axis, keep: c.v2.sec.keep } : null };
      DIR.begin(b2); X.scene.background = null; X.renderer.setClearColor(0x000000, 0);
      DIR.apply(b2, { ...c.v2, ex: 0, draw: 1, ei: 2.6, sp: c.v2.sec ? c.v2.sec.sp : 0 }, Math.round(c.p2[2] * R), Math.round(c.p2[3] * R)); c.img2 = bolder(copyGL());
      const e = X.ortho.matrixWorld.elements; c.proj = { r: V(e[0], e[1], e[2]), u: V(e[4], e[5], e[6]), T: V(c.v2.tx, c.v2.ty, c.v2.tz), s: c.scale };
      c.an = c.annot(); c.w3 = Math.round(c.p3[2] * R * 0.82); c.h3 = Math.round(c.p3[3] * R * 0.82);
      DIR.begin(blk3(c)); DIR.apply(blk3(c), { ...live3(c, 0) }, c.w3, c.h3); c.img3 = copyGL(); c.chip = c.keys[0].chip; }
    cur = null; return CELLS.map(c => `${c.id} ${c.scaleText}`).join(' | ') + ` | ${TOTAL.toFixed(1)} + ${CARD} s`; },
  // draw the sheet for a camera {cx, cy, ppi at 1080 high}. live: {cell, state} renders that box's 3D pane now
  draw(cam, W, H, live, hot) { if (comp.width !== W || comp.height !== H) { comp.width = W; comp.height = H; } let chip = null, c = live ? live.cell : null;
    if (c) { if (cur !== c) { DIR.begin(blk3(c)); cur = c; } DIR.apply(blk3(c), live.state, c.w3, c.h3); chip = live.state.chip; c.chip = chip; }
    k = cam.ppi * H / 1080; ox = W / 2 - cam.cx * k; oy = H / 2 - cam.cy * k; drawSheet(c, chip, hot); if (c) c.img3 = copyGL(); return comp; },
  frame(t, W, H) { const lv = LIVE.find(l => t >= l.t0 && t < l.t1), c = lv ? cell(lv.cell) : null;
    api.draw(camAt(Math.min(t, TOTAL)), W, H, c ? { cell: c, state: live3(c, t - lv.t0) } : null); if (t > TOTAL) endCard((t - TOTAL) / 1.1, W, H); },
  grab(q = 0.93) { const u = comp.toDataURL('image/jpeg', q), s = atob(u.slice(u.indexOf(',') + 1)), a = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) a[i] = s.charCodeAt(i); return a; },
  async still(t, W, H, name) { api.frame(t, W, H); return (await fetch('/shot/' + name, { method: 'POST', body: api.grab() })).status; },
  // from: the first frame to save. Earlier frames are still drawn, so the 3D panes carry their state into the saved ones
  async run(tag, W, H, fps, from = 0) { const st = api.status = { state: 'running', frame: 0, of: Math.round((TOTAL + CARD) * fps), t0: performance.now() };
    try { await api.prep(); for (let i = 0; i < st.of; i++) { api.frame(i / fps, W, H);
        if (i < from) { st.frame = i + 1; if (i % 60 === 0) await new Promise(r => setTimeout(r)); continue; }
        const r = await fetch(`/frame/${tag}/sheet/${i}`, { method: 'POST', body: api.grab(0.95) });
        if (r.status !== 204) throw new Error('post ' + r.status); st.frame = i + 1; }
      st.state = 'done'; st.secs = Math.round((performance.now() - st.t0) / 1000); } catch (e) { st.state = 'error'; st.error = String(e && e.stack || e); } } };
window.__sheet = api;
})();
