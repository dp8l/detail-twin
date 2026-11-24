"""Sample 1. Single-plate shear connection, W16X40 beam to the flange of a W10X49 column."""
from __future__ import annotations

from detailtwin.catalog import BOLT, HAND, w_shape
from detailtwin.core import STEEL_PCI, Assembly, fmt_in, frame, min_distance
from detailtwin.parts import drill, fillet_weld, hex_bolt, hex_nut, plate, round_washer, w_section

from detailtwin.families.shear_tab import add_connection, beam_with_holes  # noqa: F401

SPEC = dict(col="W10X49", beam="W16X40", tab_t=0.375, tab_w=4.5, n_bolts=4, bolt="3/4", pitch=3.0,
            edge_v=1.5, edge_h=1.5, a=3.0, first_bolt=3.0, hole=13 / 16, setback=0.5, weld=0.25,
            bolt_len=2.0, col_len=48.0, beam_len=36.0)


def build() -> Assembly:
    s = SPEC
    col = w_shape(s["col"])
    a = Assembly("shear_tab", "Single-plate shear connection",
                 f"{s['beam']} beam to {s['col']} column flange, ({s['n_bolts']}) {s['bolt']} in. bolts")
    xf = col["d"] / 2
    z_tos = 0.0

    a.add("C1", f"{s['col']} column", "steel", f"{s['col']}x{s['col_len']}",
          w_section(col["d"], col["bf"], col["tf"], col["tw"], col["kdes"], s["col_len"]),
          frame((0, 0, -30), (0, 1, 0), (0, 0, 1)),
          {"Section": s["col"], "Depth d": f"{col['d']} in.", "Flange bf x tf": f"{col['bf']} x {col['tf']} in.",
           "Web tw": f"{col['tw']} in.", "k (design)": f"{col['kdes']} in.", "Length shown": fmt_in(s["col_len"])},
          col["source"], ifc="IfcColumn", steel=True, length=s["col_len"])

    beam, bm = beam_with_holes(s, s["beam_len"])
    a.add("BM1", f"{s['beam']} beam", "steel", f"{s['beam']}x{s['beam_len']}h", beam,
          frame((xf + s["setback"], 0, z_tos - bm["d"] / 2), (0, 1, 0), (1, 0, 0)),
          {"Section": s["beam"], "Depth d": f"{bm['d']} in.", "Flange bf x tf": f"{bm['bf']} x {bm['tf']} in.",
           "Web tw": f"{bm['tw']} in.", "k (design)": f"{bm['kdes']} in.", "Length shown": fmt_in(s["beam_len"]),
           "Web holes": f"({s['n_bolts']}) {fmt_in(s['hole'])} dia."},
          bm["source"], explode=(14, 0, 0), ifc="IfcBeam", steel=True, length=s["beam_len"])

    xb, zs, tab_len = add_connection(a, s, xf, +1, z_tos)
    a.dim((xf + s["setback"], bm["bf"] / 2 + 1.5, z_tos), (xf + s["setback"], bm["bf"] / 2 + 1.5, z_tos - bm["d"]),
          (0, 2.5, 0))

    # ---- checks, all measured on the solids ------------------------------------------------
    for it, sec in ((a.items[0], col), (a.items[1], bm)):
        plf_gross = sec["A"] * 12 * STEEL_PCI
        solid = w_section(sec["d"], sec["bf"], sec["tf"], sec["tw"], sec["kdes"], 12.0)
        plf = solid.volume * STEEL_PCI
        area = solid.volume / 12.0
        a.check(f"{sec['label']} area of the modelled section", f"{area:.2f} in.2", f"{sec['A']} in.2 (table)",
                abs(area - sec["A"]) / sec["A"] < 0.01)
        a.check(f"{sec['label']} weight per foot of the solid", f"{plf:.1f} lb/ft", f"{sec['W']:.0f} lb/ft (nominal)",
                abs(plf - sec["W"]) / sec["W"] < 0.02)
    tab_it = next(i for i in a.items if i.mark == "PL1")
    bolts = [i for i in a.items if i.mark == "B"]
    gaps = [min_distance(b.world, a.items[1].world) for b in bolts]
    want = (s["hole"] - BOLT[s["bolt"]]["d"]) / 2
    a.check("Bolt shank to web hole, smallest radial gap", f"{min(gaps):.4f} in.",
            f"{want:.4f} in. (hole minus bolt, halved)", abs(min(gaps) - want) < 1e-3)
    seat = max(min_distance(b.world, tab_it.world) for b in bolts)
    a.check("Bolt heads seated on the tab, largest gap", f"{seat:.4f} in.", "0", seat < 1e-6)
    nut = next(i for i in a.items if i.mark == "N")
    b0 = bolts[0].world.bounding_box()
    n0 = nut.world.bounding_box()
    stick = n0.min.Y - b0.min.Y
    a.check("Bolt end beyond the nut", f"{stick:.3f} in.", "0 or more", stick >= 0)
    weld = next(i for i in a.items if i.mark == "W1" and i.props["Side"] == "far")
    clr = min_distance(weld.world, a.items[1].world)
    a.check("Far-side weld to beam end, clear gap", f"{clr:.3f} in.", "more than 0", clr > 0)
    tested, clashes = a.interference()
    a.check("Interference between parts", f"{len(clashes)} clashes in {tested} overlapping pairs", "0 clashes",
            not clashes, "; ".join(f"{x.mark}/{y.mark} {v:.4f} in.3" for x, y, v in clashes[:4]))
    a.notes = ["This is a geometry sample. Sizes are typical values chosen for the sample and nothing was designed for load.",
               "Bolt, nut and washer dimensions were typed by hand for this sample.",
               "Threads are drawn as annular grooves at the true pitch and depth, not as a helix.",
               "The nut bore equals the bolt diameter, so thread engagement is not modelled."]
    a.view = {"dir": [1.0, 1.3, 0.5], "section": {"axis": "x", "pos": xb}}
    return a
