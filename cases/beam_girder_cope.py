"""Beam to girder web, single-plate shear connection, beam top flange coped to clear the girder flange.

W16X40 beam framing into the web of a W21X44 girder, tops of steel flush. Every size in SPEC is a
sample value chosen for a test run of the detail-twin skill. It is not a design and not from a job.
"""
from __future__ import annotations

from build123d import Box, GeomType, Pos

from detailtwin.catalog import BOLT, HAND, w_shape
from detailtwin.core import STEEL_PCI, Assembly, fmt_in, frame, min_distance
from detailtwin.families.shear_tab import add_connection, beam_with_holes
from detailtwin.parts import cope, w_section

SRC = "Sample value chosen for this test run, not a design and not from a job"

SPEC = dict(girder="W21X44", beam="W16X40", girder_len=48.0, beam_len=36.0, setback=0.5,
            cope_len=4.0, cope_depth=1.25, cope_r=0.5,
            tab_t=0.375, tab_w=4.5, tab_len=9.0, n_bolts=3, bolt="3/4", pitch=3.0, edge_v=1.5, edge_h=1.5,
            a=3.0, first_bolt=3.0, hole=13 / 16, weld=0.25, bolt_len=2.0)

BIG = 500.0
TOL = 1e-3  # in., every measured length is held to this


def _within(solid, x=(-BIG, BIG), y=(-BIG, BIG), z=(-BIG, BIG)):
    """The part of a placed solid inside a world box, or None when nothing is there."""
    box = Pos((x[0] + x[1]) / 2, (y[0] + y[1]) / 2, (z[0] + z[1]) / 2) * Box(x[1] - x[0], y[1] - y[0], z[1] - z[0])
    cut = solid & box
    return cut if cut is not None and cut.volume > 1e-9 else None


def _cyl_faces(solid):
    """(face, bounding box) of every cylindrical face of a placed solid."""
    return [(f, f.bounding_box()) for f in solid.faces() if f.geom_type == GeomType.CYLINDER]


def _item(a, mark):
    return next(i for i in a.items if i.mark == mark)


def assemble(s: dict) -> Assembly:
    """The parts, placed. No checks."""
    gd, bm = w_shape(s["girder"]), w_shape(s["beam"])
    a = Assembly("beam_girder_cope", "Coped beam to girder web, single-plate connection",
                 f"{s['beam']} beam to the web of a {s['girder']} girder, top flange coped {fmt_in(s['cope_len'])} x "
                 f"{fmt_in(s['cope_depth'])}, ({s['n_bolts']}) {s['bolt']} in. bolts")
    z_tos = 0.0
    x_web = gd["tw"] / 2  # face of the girder web on the beam side
    x_end = x_web + s["setback"]

    # girder along world Y: local Z -> +Y, local X -> -X, so local Y (depth) = z cross x = +Z
    a.add("G1", f"{s['girder']} girder", "steel", f"{s['girder']}x{s['girder_len']}",
          w_section(gd["d"], gd["bf"], gd["tf"], gd["tw"], gd["kdes"], s["girder_len"]),
          frame((0, -s["girder_len"] / 2, z_tos - gd["d"] / 2), (-1, 0, 0), (0, 1, 0)),
          {"Section": s["girder"], "Depth d": f"{gd['d']} in.", "Flange bf x tf": f"{gd['bf']} x {gd['tf']} in.",
           "Web tw": f"{gd['tw']} in.", "k (design)": f"{gd['kdes']} in.", "Length shown": fmt_in(s["girder_len"])},
          gd["source"], ifc="IfcBeam", steel=True, length=s["girder_len"])

    # beam along world +X: local Z -> +X, local X -> +Y, so local Y (depth) = z cross x = +Z
    beam, _ = beam_with_holes(s, s["beam_len"])
    beam = cope(beam, bm["d"], s["cope_len"], s["cope_depth"], s["cope_r"])
    a.add("BM1", f"{s['beam']} beam, top flange coped", "steel",
          f"{s['beam']}x{s['beam_len']}h-cope{s['cope_len']}x{s['cope_depth']}r{s['cope_r']}", beam,
          frame((x_end, 0, z_tos - bm["d"] / 2), (0, 1, 0), (1, 0, 0)),
          {"Section": s["beam"], "Depth d": f"{bm['d']} in.", "Flange bf x tf": f"{bm['bf']} x {bm['tf']} in.",
           "Web tw": f"{bm['tw']} in.", "k (design)": f"{bm['kdes']} in.", "Length shown": fmt_in(s["beam_len"]),
           "Cope, top flange": f"{fmt_in(s['cope_len'])} long x {fmt_in(s['cope_depth'])} deep, "
                               f"{fmt_in(s['cope_r'])} radius", "Setback": fmt_in(s["setback"]),
           "Web holes": f"({s['n_bolts']}) {fmt_in(s['hole'])} dia."},
          f"Section: {bm['source']}. Cope, setback and holes: {SRC}",
          explode=(14, 0, 0), ifc="IfcBeam", steel=True, length=s["beam_len"])

    # tab on the +Y side of the beam web, welded to the girder web, bolt heads on the tab side
    add_connection(a, s, x_web, +1, z_tos)
    for it in a.items:  # the family words its parts for a column flange and for a different sample
        if it.mark in ("PL1", "W1"):
            it.source = SRC
        if it.mark == "W1":
            it.name = f"Fillet weld {fmt_in(s['weld'])}, tab to girder web"
        if it.mark == "B":
            it.source = f"Diameter and length: {SRC}. Head and thread dimensions: {HAND}"

    yd = bm["tw"] / 2 + s["tab_t"] + 0.9
    a.dim((x_end, yd, z_tos), (x_end + s["cope_len"], yd, z_tos), (0, 0, 3.4))
    a.dim((x_end + s["cope_len"], yd, z_tos), (x_end + s["cope_len"], yd, z_tos - s["cope_depth"]), (3.0, 0, 0))
    # flange tip to the cope cut: not a sixteenth, so the label is given in decimals, not rounded to a fraction
    a.dim((gd["bf"] / 2, yd, z_tos), (x_end + s["cope_len"], yd, z_tos), (0, 0, 4.8),
          text=f"{x_end + s['cope_len'] - gd['bf'] / 2:.3f}\"")
    return a


def run_checks(a: Assembly, s: dict) -> None:
    """Every check, measured on the placed solids of `a` and held against the spec `s`."""
    gd, bm = w_shape(s["girder"]), w_shape(s["beam"])
    g, b = _item(a, "G1").world, _item(a, "BM1").world
    gb, bb = g.bounding_box(), b.bounding_box()

    # ---- the rolled sections, uncoped, against the table -------------------------------------
    for sec in (gd, bm):
        solid = w_section(sec["d"], sec["bf"], sec["tf"], sec["tw"], sec["kdes"], 12.0)
        area, plf = solid.volume / 12.0, solid.volume * STEEL_PCI
        a.check(f"{sec['label']} area of the modelled section", f"{area:.2f} in.2", f"{sec['A']} in.2 (table)",
                abs(area - sec["A"]) / sec["A"] < 0.01)
        a.check(f"{sec['label']} weight per foot of the solid", f"{plf:.1f} lb/ft", f"{sec['W']:.0f} lb/ft (nominal)",
                abs(plf - sec["W"]) / sec["W"] < 0.02)

    # ---- features of the girder, read off its solid ------------------------------------------
    z_mid = (gb.min.Z + gb.max.Z) / 2
    x_web = _within(g, x=(0, BIG), z=(z_mid - 1, z_mid + 1)).bounding_box().max.X  # web face, beam side
    x_tip = gb.max.X  # tip of the girder flange, beam side
    z_fl = _within(g, x=(x_tip - 0.1, BIG), z=(z_mid, BIG)).bounding_box().min.Z  # underside of the top flange
    z_k = min(fb.min.Z for _, fb in _cyl_faces(g) if fb.min.Z > z_mid)  # bottom of the top fillets

    flush = bb.max.Z - gb.max.Z
    a.check("Top of beam against top of girder", f"{flush:+.4f} in.", "0 (flush)", abs(flush) < TOL)
    gap = min_distance(b, g)
    a.check("Beam to girder, clear gap", f"{gap:.4f} in.", f"{s['setback']:.4f} in. (setback)",
            abs(gap - s["setback"]) < TOL)

    # ---- the cope as cut ---------------------------------------------------------------------
    top = _within(b, z=(bb.max.Z - 0.01, BIG))  # the top 0.01 in. of the beam
    cut_len = top.bounding_box().min.X - bb.min.X
    z_floor = _within(b, x=(-BIG, bb.min.X + 0.01)).bounding_box().max.Z  # top of the beam at its end
    cut_depth = bb.max.Z - z_floor
    # cylindrical faces short along the beam (so not the rolled fillets) and not a full round hole
    arcs = [f.radius for f, fb in _cyl_faces(b) if fb.size.X < 1.5 and abs(fb.size.X - 2 * f.radius) > TOL]
    radius = arcs[0] if len(arcs) == 1 else float("nan")
    ok = (abs(cut_len - s["cope_len"]) < TOL and abs(cut_depth - s["cope_depth"]) < TOL
          and abs(radius - s["cope_r"]) < TOL)
    a.check("Cope as cut: length from beam end, depth below top of steel, re-entrant radius",
            f"{cut_len:.4f}, {cut_depth:.4f}, {radius:.4f} in.",
            f"{s['cope_len']:.4f}, {s['cope_depth']:.4f}, {s['cope_r']:.4f} in. (spec)", ok)

    # ---- the coped beam clear of the girder top flange ---------------------------------------
    level = _within(b, z=(z_fl, BIG))  # beam steel at the level of the girder flange
    clr_h = level.bounding_box().min.X - x_tip
    a.check("Cope, horizontal clearance past the girder flange tip", f"{clr_h:+.4f} in.", "more than 0", clr_h > TOL)
    under = _within(b, x=(-BIG, x_tip))  # beam steel in plan under the girder flange
    z_under = under.bounding_box().max.Z
    clr_f = z_fl - z_under
    a.check("Cope, vertical clearance below the girder flange", f"{clr_f:+.4f} in.", "more than 0", clr_f > TOL)
    clr_k = z_k - z_under
    a.check("Cope, vertical clearance below the girder fillet (k)", f"{clr_k:+.4f} in.", "more than 0", clr_k > TOL)

    # ---- tab, holes, bolts and welds ---------------------------------------------------------
    bo = BOLT[s["bolt"]]
    tab = _item(a, "PL1").world
    tb = tab.bounding_box()
    bolts = sorted((i.world for i in a.items if i.mark == "B"), key=lambda w: -w.bounding_box().max.Z)
    washers = [i.world for i in a.items if i.mark == "WSH"]
    nuts = [i.world for i in a.items if i.mark == "N"]
    welds = [i.world for i in a.items if i.mark == "W1"]
    # +Y face of the beam web, read at mid-depth and clear of the cope
    y_web = _within(b, x=(bb.max.X - 1, BIG), z=(bb.min.Z + 4, bb.max.Z - 4)).bounding_box().max.Y

    seat, off = min_distance(tab, g), tb.min.X - x_web
    a.check("Tab seated on the girder web", f"gap {seat:.4f} in., tab edge {off:+.4f} in. from the web face", "0",
            seat < 1e-6 and abs(off) < TOL)
    bear, side = min_distance(tab, b), tb.min.Y - y_web
    a.check("Tab against the +Y face of the beam web", f"gap {bear:.4f} in., tab face {side:+.4f} in. from the web face",
            "0", bear < 1e-6 and abs(side) < TOL)
    a.check("Tab as built: thickness, width, length", f"{tb.size.Y:.4f}, {tb.size.X:.4f}, {tb.size.Z:.4f} in.",
            f"{s['tab_t']:.4f}, {s['tab_w']:.4f}, {s['tab_len']:.4f} in. (spec)",
            abs(tb.size.Y - s["tab_t"]) < TOL and abs(tb.size.X - s["tab_w"]) < TOL
            and abs(tb.size.Z - s["tab_len"]) < TOL)

    def centre(fb):
        return (fb.min.X + fb.max.X) / 2, (fb.min.Z + fb.max.Z) / 2

    t_holes = _cyl_faces(tab)
    b_holes = [(f, fb) for f, fb in _cyl_faces(b) if fb.size.X < 1.5 and abs(fb.size.X - 2 * f.radius) < TOL]
    dias = [2 * f.radius for f, _ in t_holes + b_holes]
    a.check("Hole diameters, tab and beam web",
            f"({len(t_holes)}) in the tab, ({len(b_holes)}) in the web, {min(dias):.4f} to {max(dias):.4f} in.",
            f"({s['n_bolts']}) and ({s['n_bolts']}), {s['hole']:.4f} in. (spec)",
            len(t_holes) == len(b_holes) == s["n_bolts"] and all(abs(d - s["hole"]) < TOL for d in dias))

    axes = [centre(w.bounding_box()) for w in bolts]  # bolt axis, from the box of the bolt (the head is symmetric)
    line = [x - x_web for x, _ in axes]
    first = gb.max.Z - axes[0][1]
    pitch = [axes[i][1] - axes[i + 1][1] for i in range(len(axes) - 1)]
    a.check("Bolt line from the girder web face, first bolt below top of steel, pitch",
            f"{min(line):.4f} to {max(line):.4f}, {first:.4f}, {min(pitch):.4f} to {max(pitch):.4f} in.",
            f"{s['a']:.4f}, {s['first_bolt']:.4f}, {s['pitch']:.4f} in. (spec)",
            all(abs(v - s["a"]) < TOL for v in line) and abs(first - s["first_bolt"]) < TOL
            and all(abs(v - s["pitch"]) < TOL for v in pitch))

    tc = [centre(fb) for _, fb in t_holes]
    e_top, e_bot = tb.max.Z - max(z for _, z in tc), min(z for _, z in tc) - tb.min.Z
    e_free = tb.max.X - max(x for x, _ in tc)
    a.check("Tab, hole centre to edge: top, bottom, free edge", f"{e_top:.4f}, {e_bot:.4f}, {e_free:.4f} in.",
            f"{s['edge_v']:.4f}, {s['edge_v']:.4f}, {s['edge_h']:.4f} in. (spec)",
            abs(e_top - s["edge_v"]) < TOL and abs(e_bot - s["edge_v"]) < TOL and abs(e_free - s["edge_h"]) < TOL)
    bc = [centre(fb) for _, fb in b_holes]
    e_end, e_cope = min(x for x, _ in bc) - bb.min.X, z_floor - max(z for _, z in bc)
    e_min = min(s["edge_v"], s["edge_h"])
    a.check("Beam web, hole centre to beam end and top hole centre to the coped edge",
            f"{e_end:.4f}, {e_cope:.4f} in.", f"{e_min:.4f} in. or more (the edge distance of the spec)",
            e_end > e_min - TOL and e_cope > e_min - TOL)

    want = (s["hole"] - bo["d"]) / 2
    g_web = [min_distance(w, b) for w in bolts]
    a.check("Bolt shank to web hole, radial gap, least and greatest", f"{min(g_web):.4f}, {max(g_web):.4f} in.",
            f"{want:.4f} in. (hole minus bolt, halved)", all(abs(v - want) < TOL for v in g_web))
    # inside the tab the head bears on the plate, so the shank is measured alone, away from the head
    shanks = [_within(w, y=(tb.min.Y + 0.05, tb.max.Y - 0.05)) for w in bolts]
    g_tab = [min_distance(sh, tab) if sh is not None else float("nan") for sh in shanks]
    a.check("Bolt shank to tab hole, radial gap, least and greatest", f"{min(g_tab):.4f}, {max(g_tab):.4f} in.",
            f"{want:.4f} in. (hole minus bolt, halved)", all(abs(v - want) < TOL for v in g_tab))
    head = max(min_distance(w, tab) for w in bolts)
    a.check("Bolt heads seated on the tab, largest gap", f"{head:.4f} in.", "0", head < 1e-6)
    w_gap = max(min_distance(w, b) for w in washers)
    n_gap = max(min(min_distance(n, w) for w in washers) for n in nuts)
    a.check("Washer on the beam web and nut on the washer, largest gaps",
            f"{w_gap:.4f}, {n_gap:.4f} in., ({len(washers)}) washers and ({len(nuts)}) nuts", "0, 0",
            w_gap < 1e-6 and n_gap < 1e-6 and len(washers) == len(nuts) == s["n_bolts"])
    stick = min(n.bounding_box().min.Y for n in nuts) - max(w.bounding_box().min.Y for w in bolts)
    a.check("Bolt end beyond the nut, least", f"{stick:.3f} in.", "0 or more", stick >= 0)

    wbs = [w.bounding_box() for w in welds]
    legs = [v for wb in wbs for v in (wb.size.X, wb.size.Y)]
    w_len = [wb.size.Z for wb in wbs]
    w_seat = max(max(min_distance(w, g), min_distance(w, tab)) for w in welds)
    near = sum(1 for wb in wbs if wb.min.Y > tb.max.Y - TOL)  # on the outer face of the tab
    far = [w for w, wb in zip(welds, wbs) if wb.max.Y < tb.min.Y + TOL]  # on the beam-web side of the tab
    a.check("Fillet welds, tab to girder web: number, legs, length, largest gap to web or tab",
            f"({len(welds)}), {min(legs):.4f} to {max(legs):.4f}, {min(w_len):.4f} in., {w_seat:.4f} in.",
            f"(2) one each side, {s['weld']:.4f}, {s['tab_len']:.4f} in., 0",
            len(welds) == 2 and near == 1 and len(far) == 1 and all(abs(v - s["weld"]) < TOL for v in legs)
            and all(abs(v - s["tab_len"]) < TOL for v in w_len) and w_seat < 1e-6)
    clr_w = min(min_distance(w, b) for w in far) if far else float("nan")
    a.check("Weld on the beam-web side of the tab to the beam end, clear gap", f"{clr_w:.4f} in.", "more than 0",
            clr_w > TOL)

    tested, clashes = a.interference()
    a.check("Interference between parts", f"{len(clashes)} clashes in {tested} overlapping pairs", "0 clashes",
            not clashes, "; ".join(f"{x.mark}/{y.mark} {v:.4f} in.3" for x, y, v in clashes[:4]))


def build(spec: dict | None = None) -> Assembly:
    s = dict(SPEC, **(spec or {}))
    a = assemble(s)
    run_checks(a, s)
    a.notes = ["This is a geometry sample. Every size is a sample value chosen for a test run of the skill, not a "
               "design and not from a job. Nothing was designed for load and no code limit was checked.",
               "W shape dimensions were read from the AISC shapes table file. Bolt, nut and washer dimensions were "
               "typed by hand in the catalog and are not yet from a sourced table.",
               "The 1 1/2 in. edge distance of the spec is held exactly on the tab and as a least value in the beam "
               "web. That reading of the spec for the beam web is an assumption.",
               "The cope is a square cut with the re-entrant radius tangent to both cuts. Rolling tolerances, camber "
               "and cut roughness are not modelled.",
               "Welds are triangular prisms of the stated leg. Threads are annular grooves at the true pitch and "
               "depth, not a helix. The nut bore equals the bolt diameter, so thread engagement is not modelled.",
               "Not checked: room to enter and tighten the bolts, room to swing the beam into place, and anything "
               "framing into the far side of the girder."]
    a.view = {"dir": [1.0, 1.3, 0.5], "section": {"axis": "y", "pos": 0.0}}
    return a
