"""Sample 2. Spread footing, pedestal with its bar cage, anchor rods, grout and base plate."""
from __future__ import annotations

import math

from detailtwin.catalog import BOLT, HAND, REBAR, w_shape
from detailtwin.core import STEEL_PCI, Assembly, fmt_in, frame, min_distance
from detailtwin.parts import (bar, drill, fillet_weld, hex_nut, plate, plate_washer, round_rod,
                              w_section)

from detailtwin.families.footing import EMBEDDED, add_footing, cage_checks  # noqa: F401

SPEC = dict(B=72.0, T=18.0, cover=3.0, mat="#5", n_mat=9, ped=20.0, ped_h=24.0, vert="#6", tie="#3",
            tie_cover=1.5, tie_z=(-10.0, -4.0, 3.0, 9.0, 15.0, 21.0), vert_top_clear=2.0,
            hook_id=6.0, hook_ext=12.0, tie_id=4.0, tie_ext=3.0, grout=1.0, bp=14.0, bp_t=1.0,
            rod="3/4", rod_g=5.0, rod_embed=12.0, rod_proj=3.5, rod_hole=1.3125, pw=2.0, pw_t=0.25,
            col="W10X49", col_len=30.0, weld=0.3125)


def build() -> Assembly:
    s = SPEC
    a = Assembly("footing", "Spread footing and pedestal",
                 f"{fmt_in(s['B'])} footing, {fmt_in(s['ped'])} pedestal, {s['col']} column on a {fmt_in(s['bp'])} base plate")
    add_footing(a, s, 0.0, 0.0)
    cage_checks(a, s)
    col = w_shape(s["col"])
    it = next(i for i in a.items if i.mark == "C1")
    plf = it.weight / it.length * 12
    a.check(f"{s['col']} weight per foot of the solid", f"{plf:.1f} lb/ft", f"{col['W']:.0f} lb/ft (nominal)",
            abs(plf - col["W"]) / col["W"] < 0.02)
    rods = [i for i in a.items if i.mark == "AR"]
    bars = [i for i in a.items if i.cls in ("rebar", "tie")]
    clr = min(min_distance(r.world, b.world) for r in rods for b in bars)
    a.check("Anchor rods to nearest bar, clear distance", f"{clr:.3f} in.", "more than 0", clr > 0)
    tested, clashes = a.interference(allowed=EMBEDDED)
    a.check("Interference between parts", f"{len(clashes)} clashes in {tested} overlapping pairs", "0 clashes",
            not clashes, "; ".join(f"{x.mark}/{y.mark} {v:.4f} in.3" for x, y, v in clashes[:4]))
    a.notes = ["This is a geometry sample. Sizes are typical values chosen for the sample and nothing was designed for load.",
               "Bar diameters, bend diameters, hook extensions and fastener sizes were typed by hand for this sample.",
               "Bars are smooth rounds of the nominal diameter. Deformations are not modelled.",
               "Anchor rod threads are not modelled.",
               "Concrete is a plain solid. It is not cut around the bars, so the bars are embedded by design."]
    a.view = {"dir": [1.0, -1.3, 0.62], "xray": True, "section": {"axis": "y", "pos": 0.0}}
    return a
