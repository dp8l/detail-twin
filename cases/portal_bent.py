"""Sample 4. A 24 ft portal bent assembled from the footing and the shear-tab connection."""
from __future__ import annotations

from detailtwin.catalog import w_shape
from detailtwin.core import Assembly, fmt_in, frame, min_distance

from . import footing_pedestal as fp
from . import steel_shear_tab as st

SPAN = 288.0  # column centre to column centre
COL_LEN = 144.0  # top of base plate to top of steel


def build() -> Assembly:
    fs, cs = fp.SPEC, st.SPEC
    col, bm = w_shape(fs["col"]), w_shape(cs["beam"])
    a = Assembly("portal", "One-bay bent, footing to bolt",
                 f"{fmt_in(SPAN)} span, {cs['beam']} beam on {fs['col']} columns, each column on its own footing")
    info = None
    for k, x0 in enumerate((0.0, SPAN)):
        info = fp.add_footing(a, fs, x0, 0.0, tag=f".{k + 1}", col_len=COL_LEN, dims=(k == 0), col_top_explode=0.0)
    for it in a.items:  # in the bent only the beam and its fasteners move apart
        it.explode = (0.0, 0.0, 0.0)
    z_tos = info["z_plate_top"] + COL_LEN
    xf = col["d"] / 2
    L = SPAN - 2 * xf - 2 * cs["setback"]
    beam, _ = st.beam_with_holes(cs, L, ends=("start", "end"))
    a.add("BM1", f"{cs['beam']} beam", "steel", f"{cs['beam']}x{L}h2", beam,
          frame((xf + cs["setback"], 0, z_tos - bm["d"] / 2), (0, 1, 0), (1, 0, 0)),
          {"Section": cs["beam"], "Depth d": f"{bm['d']} in.", "Flange bf x tf": f"{bm['bf']} x {bm['tf']} in.",
           "Web tw": f"{bm['tw']} in.", "Length": fmt_in(L), "Web holes": f"({2 * cs['n_bolts']}) {fmt_in(cs['hole'])} dia."},
          bm["source"], explode=(0, -22, 0), ifc="IfcBeam", steel=True, length=L)
    n0 = len(a.items)
    st.add_connection(a, cs, xf, +1, z_tos, tag=".1", dims=False)
    st.add_connection(a, cs, SPAN - xf, -1, z_tos, tag=".2", dims=False)
    for it in a.items[n0:]:
        base = it.mark.split(".")[0]
        it.explode = {"B": (0.0, 6.0, 0.0), "WSH": (0.0, -28.0, 0.0), "N": (0.0, -31.0, 0.0)}.get(base, (0.0, 0.0, 0.0))

    a.dim((0, -fs["B"] / 2, -fs["T"]), (SPAN, -fs["B"] / 2, -fs["T"]), (0, -16, 0))
    a.dim((SPAN + fs["B"] / 2, 0, info["z_plate_top"]), (SPAN + fs["B"] / 2, 0, z_tos), (10, 0, 0))
    a.dim((xf + cs["setback"], 0, z_tos), (SPAN - xf - cs["setback"], 0, z_tos), (0, 0, 9))

    beam_it = a.items[n0 - 1]
    plf = beam_it.weight / beam_it.length * 12
    a.check(f"{cs['beam']} weight per foot of the solid", f"{plf:.1f} lb/ft", f"{bm['W']:.0f} lb/ft (nominal)",
            abs(plf - bm["W"]) / bm["W"] < 0.02, "the web holes are deducted")
    fit = L + 2 * cs["setback"] + col["d"]
    a.check("Beam length plus setbacks plus column depth", fmt_in(fit), f"{fmt_in(SPAN)} (span)", abs(fit - SPAN) < 1e-6)
    bolts = [i for i in a.items if i.mark.startswith("B.")]
    gap = min(min_distance(b.world, beam_it.world) for b in bolts)
    want = (cs["hole"] - 0.75) / 2
    a.check("Bolts through beam web holes at both ends, smallest gap", f"{gap:.4f} in.", f"{want:.4f} in.", abs(gap - want) < 1e-3)
    fp.cage_checks(a, fs, tag=".1")
    steel = sum(i.weight for i in a.items if i.cls in ("steel", "plate", "weld", "bolt"))
    bars = sum(i.weight for i in a.items if i.cls in ("rebar", "tie"))
    conc = 2 * (fs["B"] ** 2 * fs["T"] + fs["ped"] ** 2 * fs["ped_h"]) / 46656
    a.check("Take-off", f"steel {steel:.0f} lb, bars {bars:.0f} lb, concrete {conc:.2f} cu yd", "summed from the solids", True)
    tested, clashes = a.interference(allowed=fp.EMBEDDED)
    a.check("Interference between parts", f"{len(clashes)} clashes in {tested} overlapping pairs", "0 clashes", not clashes,
            "; ".join(f"{x.mark}/{y.mark} {v:.4f} in.3" for x, y, v in clashes[:4]))
    a.notes = ["Every part here is the same solid used in samples 1 and 2, placed at building scale.",
               "This is a geometry sample. Nothing was designed for load, and the bent has no lateral system as drawn.",
               "Fastener, bar and bend dimensions were typed by hand for this sample."]
    a.view = {"dir": [0.55, -1.3, 0.42], "xray": True, "section": {"axis": "y", "pos": 0.0}}
    return a
