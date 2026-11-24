/* Scripted camera for the Detail Twin viewer. Loaded into the local preview page only.
   It drives the live viewer through keyframed shots and posts each rendered frame to tools/serve.py.

   __dir.run('low', 960, 540, 30)        every block
   __dir.run('low', 960, 540, 30, ['tab'])   one block
   __dir.still('tab', 6.8, 960, 540)     render one moment and leave it on the canvas
   __dir.status                          progress

   Units are inches, angles degrees. az is measured from +X toward +Y, el above the horizon,
   span is the height of the view. sp is the section position on the block's section axis. */
(() => {
const D = window.__dt, X = D.x, S = D.S, T = THREE;
const lerp = (a, b, u) => a + (b - a) * u;
const ease = u => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
const PAPER = '#fbfbf7', BG1 = '#f6f8fa', BG2 = '#d9e0e8';
const paperLin = new T.Color(PAPER).convertSRGBToLinear();
const bgc = document.createElement('canvas'); bgc.width = 2; bgc.height = 256;
const bgx = bgc.getContext('2d'), bgt = new T.CanvasTexture(bgc); bgt.encoding = T.sRGBEncoding;
const mix = (a, b, u) => '#' + new T.Color(a).lerp(new T.Color(b), u).getHexString();
function setBg(d) { const g = bgx.createLinearGradient(0, 0, 0, 256); g.addColorStop(0, mix(BG1, PAPER, d)); g.addColorStop(1, mix(BG2, PAPER, d));
  bgx.fillStyle = g; bgx.fillRect(0, 0, 2, 256); bgt.needsUpdate = true; }

// ---- the shots ---------------------------------------------------------------------------
// Each key gives the values that change. Missing values carry over from the key before.
const BLOCKS = [
  { id: 'tab', case: 0, sec: { axis: 'x', keep: -1 }, keys: [
    { t: 0.0, tx: 16, ty: 0, tz: -6, az: 90, el: 0, span: 58, ex: 0, draw: 1, xray: 0, sp: 60 },
    { t: 1.4 },
    { t: 3.4, tx: 11, tz: -7.5, az: 50, el: 24, span: 36, draw: 0 },
    { t: 4.0 },
    { t: 5.6, tx: 15, az: 42, el: 22, span: 46, ex: 1 },
    { t: 7.4, az: 28 },
    { t: 8.8, tx: 10, az: 38, span: 34, ex: 0 },
    { t: 9.2 },
    { t: 11.4, tx: 8, az: 30, el: 14, span: 15, sp: 8.0 },
    { t: 12.8, az: 22 } ] },
  { id: 'footing', case: 1, sec: { axis: 'y', keep: 1 }, keys: [
    { t: 0.0, tx: 0, ty: 0, tz: 12, az: -52, el: 26, span: 100, ex: 0, draw: 0, xray: 0, sp: -40 },
    { t: 0.8 },
    { t: 2.1, xray: 1 },
    { t: 5.0, tz: 10, az: 30, el: 30, span: 78 },
    { t: 6.3, ex: 1, tz: 22, span: 86 },
    { t: 7.1 },
    { t: 8.2, ex: 0, tz: 12 },
    { t: 10.0, tx: 7.6, ty: 7.6, tz: 16, az: 42, el: 48, span: 22 },
    { t: 10.8 },
    { t: 12.2, tx: 0, ty: 0, tz: 6, az: -72, el: 12, span: 86 },
    { t: 14.2, sp: 0, az: -78 },
    { t: 15.0, az: -82 } ] },
  { id: 'holddown', case: 2, keys: [
    { t: 0.0, tx: 20, ty: 3, tz: 12, az: 60, el: 22, span: 62, ex: 0, draw: 0, xray: 0, sp: 0 },
    { t: 0.9, az: 62 },
    { t: 2.6, tx: 7, tz: 9, az: 66, el: 20, span: 27 },
    { t: 3.0 },
    { t: 4.5, tx: 11, az: 74, el: 18, span: 36, ex: 1 },
    { t: 5.8, az: 80 },
    { t: 7.1, tx: 8, az: 70, span: 30, ex: 0 },
    { t: 7.6 } ] },
  { id: 'bent', case: 3, keys: [
    { t: 0.0, tx: 144, ty: 0, tz: 76, az: 68, el: 18, span: 255, ex: 0, draw: 0, xray: 1, sp: 0 },
    { t: 2.4, az: 46 },
    { t: 6.4, tx: 8, tz: 163, az: 58, el: 16, span: 19, zl: 1.8, pl: 0.6 },
    { t: 7.2, az: 54 },
    { t: 8.8, ex: 1, span: 46, ty: -6 },
    { t: 9.6 },
    { t: 10.9, ex: 0, span: 30, ty: 0 },
    { t: 13.8, tx: 0, tz: 16, az: 36, el: 28, span: 82 },
    { t: 14.6, az: 30 } ] },
  { id: 'cope', case: 4, keys: [
    { t: 0.0, tx: 8, ty: 0, tz: -7, az: 60, el: 24, span: 42, ex: 0, draw: 0, xray: 0, sp: 0 },
    { t: 0.8 },
    { t: 2.3, tx: 12, az: 52, span: 50, ex: 1 },
    { t: 3.9, az: 40 },
    { t: 5.2, tx: 8, az: 48, span: 38, ex: 0 },
    { t: 6.4, az: 44 } ] },
];
const PROPS = ['tx', 'ty', 'tz', 'az', 'el', 'span', 'ex', 'draw', 'xray', 'sp'];
for (const b of BLOCKS) { let prev = {}; for (const k of b.keys) { for (const p of PROPS) if (k[p] === undefined) k[p] = prev[p]; prev = k; } b.dur = b.keys[b.keys.length - 1].t; }

function stateAt(b, t) { const ks = b.keys; let i = 0; while (i < ks.length - 2 && t >= ks[i + 1].t) i++;
  const a = ks[i], c = ks[i + 1], u = ease(Math.min(1, Math.max(0, (t - a.t) / (c.t - a.t)))), s = {};
  // zl on the arriving key makes the zoom trail the pan, so the subject stays in frame during a dive
  const up = Math.pow(u, c.pl || 1);  // pl below 1 on the arriving key makes the pan lead
  for (const p of PROPS) s[p] = p === 'span' ? Math.exp(lerp(Math.log(a.span), Math.log(c.span), Math.pow(u, c.zl || 1)))
    : lerp(a[p], c[p], (p === 'tx' || p === 'ty' || p === 'tz') ? up : u);
  return s; }

// ---- applying one state ------------------------------------------------------------------
const base = {}; let ground = null;
function begin(b) {
  D.loadCase(b.case); S.tw = null; S.dims = false; S.xray = false; S.sec = !!b.sec;
  if (b.sec) { S.axis = b.sec.axis; document.getElementById('s-axis').value = b.sec.axis; X.updateSection(); } else X.refreshMats();
  if (S.dimObj) S.dimObj.visible = false;
  ground = S.root.children.find(o => o.material && o.material.isShadowMaterial);
  for (const cls in X.mats) if (!base[cls]) base[cls] = { c: new T.Color(X.CLS[cls].c).convertSRGBToLinear(), m: X.CLS[cls].m, e: 0.9 };
  X.scene.background = bgt;
}
function apply(b, st, W, H) {
  const cv = X.renderer.domElement;
  if (cv.width !== W || cv.height !== H) { X.renderer.setPixelRatio(1); X.renderer.setSize(W, H, false); }
  D.setExplode(st.ex); if (S.dimObj) S.dimObj.visible = false;
  const d = st.draw;
  for (const cls in X.mats) { const m = X.mats[cls], q = base[cls], gx = (X.GHOST.has(cls) || (st.xsteel && cls === 'steel')) ? st.xray : 0;   // xsteel: see through the members where there is no concrete
    m.color.copy(q.c).multiplyScalar(1 - d); m.emissive.copy(paperLin).multiplyScalar(d); m.emissiveIntensity = st.ei || 1.6;
    m.metalness = q.m * (1 - d); m.envMapIntensity = q.e * (1 - d);
    const tr = gx > 0.002; if (m.transparent !== tr) { m.transparent = tr; m.needsUpdate = true; }  // the shader is compiled per state
    m.opacity = 1 + (0.16 - 1) * gx; m.depthWrite = gx < 0.5; }
  for (const p of S.parts) if (X.GHOST.has(p.d.cls) || (st.xsteel && p.d.cls === 'steel')) p.mesh.castShadow = p.mesh.receiveShadow = st.xray < 0.5;
  const em = X.edgeMat(); em.opacity = lerp(0.62, 1, d);
  if (ground) ground.material.opacity = 0.2 * (1 - d);
  if (S.grid) S.grid.material.opacity = 0.22 * (1 - d);
  setBg(d);
  if (b.sec) { const k = { x: 0, y: 1, z: 2 }[b.sec.axis]; X.clip.normal.set(0, 0, 0).setComponent(k, b.sec.keep); X.clip.constant = -b.sec.keep * st.sp;
    for (const cap of S.caps || []) { cap.visible = true; cap.position.copy(S.C).setComponent(k, st.sp); cap.quaternion.setFromUnitVectors(new T.Vector3(0, 0, 1), X.clip.normal); } }
  const az = st.az * Math.PI / 180, el = st.el * Math.PI / 180, o = X.ortho, tg = new T.Vector3(st.tx, st.ty, st.tz);
  o.position.copy(tg).add(new T.Vector3(Math.cos(el) * Math.cos(az), Math.cos(el) * Math.sin(az), Math.sin(el)).multiplyScalar(S.R * 6));
  o.up.set(0, 0, 1); o.lookAt(tg); const h = st.span / 2, a = W / H; o.left = -h * a; o.right = h * a; o.top = h; o.bottom = -h; o.zoom = 1; o.updateProjectionMatrix();
  X.renderer.render(X.scene, o);
}
// toDataURL encodes at once. toBlob waits for an idle slot, which a pane that is not on screen gives once a second.
const grab = q => { const u = X.renderer.domElement.toDataURL('image/jpeg', q), s = atob(u.slice(u.indexOf(',') + 1)), a = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) a[i] = s.charCodeAt(i); return a; };

const api = { BLOCKS, begin, apply, status: { state: 'idle' },
  async run(tag, W, H, fps, only) { const st = api.status = { state: 'running', block: '', frame: 0, of: 0, done: [], t0: performance.now() };
    try { for (const b of BLOCKS) { if (only && !only.includes(b.id)) continue; begin(b); const n = Math.round(b.dur * fps); st.block = b.id; st.of = n;
        for (let i = 0; i < n; i++) { apply(b, stateAt(b, i / fps), W, H); const blob = grab(0.93);
          const r = await fetch(`/frame/${tag}/${b.id}/${i}`, { method: 'POST', body: blob }); if (r.status !== 204) throw new Error('post ' + r.status); st.frame = i + 1; }
        st.done.push(b.id + ':' + n); }
      st.state = 'done'; st.secs = Math.round((performance.now() - st.t0) / 1000); } catch (e) { st.state = 'error'; st.error = String(e); } },
  async still(id, t, W, H, name) { const b = BLOCKS.find(q => q.id === id); if (api._cur !== id) { begin(b); api._cur = id; } apply(b, stateAt(b, t), W, H);
    const blob = grab(0.93); const r = await fetch(`/shot/${name || (id + '_' + String(t).replace('.', 'p'))}`, { method: 'POST', body: blob }); return r.status; } };
window.__dir = api;
})();
