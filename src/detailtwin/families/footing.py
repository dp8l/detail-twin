"""Spread footing, pedestal, bar cage, anchor rods and base plate family."""
from __future__ import annotations

import math

from detailtwin.catalog import BOLT, HAND, REBAR, w_shape
from detailtwin.core import STEEL_PCI, Assembly, fmt_in, frame, min_distance
from detailtwin.parts import (bar, drill, fillet_weld, hex_nut, plate, plate_washer, round_rod,
                              w_section)


SPEC_SRC = "Detail spec of this sample"


def add_footing(a: Assembly, s: dict, x0: float, y0: float, tag: str = "", col_len: float | None = None,
                dims: bool = True, col_top_explode: float = 16.0):
    """Footing, pedestal, cage, anchor rods, grout, base plate and column, centred at (x0, y0).
    Top of footing is z = 0. Returns the z of the top of the base plate."""
    B, T, P, H = s["B"], s["T"], s["ped"], s["ped_h"]
    col = w_shape(s["col"])
    col_len = col_len or s["col_len"]
    o = lambda x, y, z: (x0 + x, y0 + y, z)  # noqa: E731

    a.add(f"F1{tag}", f"Footing {fmt_in(B)} x {fmt_in(B)} x {fmt_in(T)}", "concrete", f"ftg{B}x{T}", plate(B, B, T),
          frame(o(-B / 2, -B / 2, -T), (1, 0, 0), (0, 0, 1)),
          {"Plan": f"{fmt_in(B)} x {fmt_in(B)}", "Thickness": fmt_in(T), "Volume": f"{B * B * T / 46656:.2f} cu yd"},
          SPEC_SRC, ifc="IfcFooting")
    a.add(f"P1{tag}", f"Pedestal {fmt_in(P)} x {fmt_in(P)} x {fmt_in(H)}", "concrete", f"ped{P}x{H}", plate(P, P, H),
          frame(o(-P / 2, -P / 2, 0), (1, 0, 0), (0, 0, 1)),
          {"Plan": f"{fmt_in(P)} x {fmt_in(P)}", "Height": fmt_in(H), "Volume": f"{P * P * H / 46656:.2f} cu yd"},
          SPEC_SRC, ifc="IfcFooting")

    # bottom mat, two layers of straight bars
    db, _ = REBAR[s["mat"]]
    L = B - 2 * s["cover"]
    mat_bar, _ = bar([(0, 0, 0), (L, 0, 0)], db, 1.0)
    e0 = -B / 2 + s["cover"] + db / 2
    sp = (B - 2 * (s["cover"] + db / 2)) / (s["n_mat"] - 1)
    z_lo = -T + s["cover"] + db / 2
    z_hi = z_lo + db
    pr = {"Size": s["mat"], "Diameter": f"{db} in.", "Shape": "straight", "Cut length": fmt_in(L)}
    for i in range(s["n_mat"]):
        a.add(f"M1{tag}", f"{s['mat']} bottom bar, {fmt_in(L)}", "rebar", f"mat{s['mat']}x{L}", mat_bar,
              frame(o(-L / 2, e0 + i * sp, z_lo), (1, 0, 0), (0, 0, 1)), {**pr, "Layer": "lower, along X"}, HAND,
              ifc="IfcReinforcingBar", steel=True, length=L)
        a.add(f"M1{tag}", f"{s['mat']} bottom bar, {fmt_in(L)}", "rebar", f"mat{s['mat']}x{L}", mat_bar,
              frame(o(e0 + i * sp, -L / 2, z_hi), (0, 1, 0), (0, 0, 1)), {**pr, "Layer": "upper, along Y"}, HAND,
              ifc="IfcReinforcingBar", steel=True, length=L)

    # ties, closed with 135 degree hooks lapped at one corner
    dt, _ = REBAR[s["tie"]]
    rt = (s["tie_id"] / 2 + 0.5) * dt
    h = P / 2 - s["tie_cover"] - dt / 2
    c = h - rt
    t = rt * math.tan(math.radians(67.5))
    Lh = t + max(6 * dt, s["tie_ext"])
    q = 1 / math.sqrt(2)
    v2, v1 = (h, c + t, 0.0), (c + t, h, dt)
    tie_pts = [(v2[0] - Lh * q, v2[1] - Lh * q, 0.0), v2, (h, -h, 0.0), (-h, -h, 0.0), (-h, h, dt), v1,
               (v1[0] - Lh * q, v1[1] - Lh * q, dt)]
    tie, tie_len = bar(tie_pts, dt, rt)
    for z in s["tie_z"]:
        a.add(f"T1{tag}", f"{s['tie']} closed tie, 135 deg hooks", "tie", f"tie{s['tie']}x{P}", tie,
              frame(o(0, 0, z), (1, 0, 0), (0, 0, 1)),
              {"Size": s["tie"], "Out to out": f"{fmt_in(2 * h + dt)} x {fmt_in(2 * h + dt)}",
               "Inside bend diameter": f"{s['tie_id']:g} bar diameters", "Hook": "135 deg, 3 in. extension",
               "Cut length": fmt_in(tie_len)}, HAND, ifc="IfcReinforcingBar", steel=True, length=tie_len)

    # pedestal verticals with 90 degree hooks resting on the mat
    dv, _ = REBAR[s["vert"]]
    rv = (s["hook_id"] / 2 + 0.5) * dv
    inner = P / 2 - s["tie_cover"] - dt  # inside face of the tie
    r_in = s["tie_id"] / 2 * dt  # inside bend radius of the tie
    nest = inner - r_in + (r_in - dv / 2) / math.sqrt(2)  # corner bar seated in the tie bend
    side = inner - dv / 2
    z_hook = z_hi + db / 2 + dv / 2
    z_top = H - s["vert_top_clear"]
    leg = rv + s["hook_ext"] * dv
    dowel, dow_len = bar([(0, 0, z_top - z_hook), (0, 0, 0), (leg, 0, 0)], dv, rv)
    spots = [(nest, nest, 1, 0), (nest, -nest, 1, 0), (-nest, nest, -1, 0), (-nest, -nest, -1, 0),
             (side, 0, 1, 0), (-side, 0, -1, 0), (0, side, 0, 1), (0, -side, 0, -1)]
    for x, y, hx, hy in spots:
        a.add(f"V1{tag}", f"{s['vert']} vertical with 90 deg hook", "rebar", f"dowel{s['vert']}", dowel,
              frame(o(x, y, z_hook), (hx, hy, 0), (0, 0, 1)),
              {"Size": s["vert"], "Diameter": f"{dv} in.", "Inside bend diameter": f"{s['hook_id']:g} bar diameters",
               "Hook extension": f"{s['hook_ext']:g} bar diameters", "Cut length": fmt_in(dow_len)}, HAND,
              ifc="IfcReinforcingBar", steel=True, length=dow_len)

    # anchor rods with a nut at the embedded end
    bo = BOLT[s["rod"]]
    z_tc = H  # top of concrete
    z_bp = z_tc + s["grout"]
    rod_len = s["rod_embed"] + s["rod_proj"]
    rod = round_rod(bo["d"], rod_len)
    nut = hex_nut(s["rod"])
    pw = plate_washer(s["pw"], s["pw_t"], bo["d"] + 0.0625)
    g = s["rod_g"] / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * g, sy * g
            a.add(f"AR{tag}", f"{s['rod']} in. anchor rod x {fmt_in(rod_len)}", "anchor", f"rod{s['rod']}x{rod_len}", rod,
                  frame(o(x, y, z_tc + s["rod_proj"]), (1, 0, 0), (0, 0, 1)),
                  {"Diameter": s["rod"] + '"', "Length": fmt_in(rod_len), "Embedment": fmt_in(s["rod_embed"]),
                   "Projection": fmt_in(s["rod_proj"]), **({"Grade": s["rod_grade"]} if s.get("rod_grade") else {})}, HAND,
                  ifc="IfcMechanicalFastener", steel=True, length=rod_len)
            a.add(f"AN{tag}", f"Heavy hex nut, embedded end of {s['rod']} in. rod", "anchor", f"nut{s['rod']}", nut,
                  frame(o(x, y, z_tc - s["rod_embed"]), (1, 0, 0), (0, 0, 1)),
                  {"Across flats": fmt_in(bo["F"]), "Height": fmt_in(bo["Hn"], 64)}, HAND,
                  ifc="IfcMechanicalFastener", steel=True)
            a.add(f"PW{tag}", f"Plate washer {fmt_in(s['pw'])} x {fmt_in(s['pw'])} x {fmt_in(s['pw_t'])}", "bolt",
                  f"pw{s['pw']}", pw, frame(o(x, y, z_bp + s["bp_t"]), (1, 0, 0), (0, 0, 1)),
                  {"Size": f"{fmt_in(s['pw'])} square", "Thickness": fmt_in(s["pw_t"]),
                   "Hole": fmt_in(bo["d"] + 0.0625)}, SPEC_SRC, explode=(0, 0, 11), ifc="IfcMechanicalFastener", steel=True)
            a.add(f"N2{tag}", f"Heavy hex nut for {s['rod']} in. rod", "bolt", f"nut{s['rod']}", nut,
                  frame(o(x, y, z_bp + s["bp_t"] + s["pw_t"]), (1, 0, 0), (0, 0, 1)),
                  {"Across flats": fmt_in(bo["F"]), "Height": fmt_in(bo["Hn"], 64)}, HAND,
                  explode=(0, 0, 13.5), ifc="IfcMechanicalFastener", steel=True)

    # grout and base plate
    grout = plate(s["bp"] + 2, s["bp"] + 2, s["grout"])
    bp = plate(s["bp"], s["bp"], s["bp_t"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            grout = drill(grout, s["rod_hole"], ((s["bp"] + 2) / 2 + sx * g, (s["bp"] + 2) / 2 + sy * g, 0), "Z")
            bp = drill(bp, s["rod_hole"], (s["bp"] / 2 + sx * g, s["bp"] / 2 + sy * g, 0), "Z")
    a.add(f"G1{tag}", f"Non-shrink grout, {fmt_in(s['grout'])}", "grout", "grout", grout,
          frame(o(-(s["bp"] + 2) / 2, -(s["bp"] + 2) / 2, z_tc), (1, 0, 0), (0, 0, 1)),
          {"Thickness": fmt_in(s["grout"]), "Plan": f"{fmt_in(s['bp'] + 2)} square"}, SPEC_SRC, explode=(0, 0, 4))
    a.add(f"BP1{tag}", f"Base plate PL {fmt_in(s['bp_t'])} x {fmt_in(s['bp'])} x {fmt_in(s['bp'])}", "plate", "bp", bp,
          frame(o(-s["bp"] / 2, -s["bp"] / 2, z_bp), (1, 0, 0), (0, 0, 1)),
          {"Thickness": fmt_in(s["bp_t"]), "Plan": f"{fmt_in(s['bp'])} square",
           "Holes": f"(4) {fmt_in(s['rod_hole'])} dia. at {fmt_in(s['rod_g'])} x {fmt_in(s['rod_g'])}"}, SPEC_SRC,
          explode=(0, 0, 8), ifc="IfcPlate", steel=True)

    # column and its welds to the base plate
    z_c = z_bp + s["bp_t"]
    a.add(f"C1{tag}", f"{s['col']} column", "steel", f"{s['col']}x{col_len}",
          w_section(col["d"], col["bf"], col["tf"], col["tw"], col["kdes"], col_len),
          frame(o(0, 0, z_c), (0, 1, 0), (0, 0, 1)),
          {"Section": s["col"], "Depth d": f"{col['d']} in.", "Flange bf x tf": f"{col['bf']} x {col['tf']} in.",
           "Web tw": f"{col['tw']} in.", "Length shown": fmt_in(col_len)}, col["source"],
          explode=(0, 0, col_top_explode), ifc="IfcColumn", steel=True, length=col_len)
    w = s["weld"]
    hd, hb, hw = col["d"] / 2, col["bf"] / 2, col["tw"] / 2
    web_l = col["d"] - 2 * col["kdes"]
    welds = [((hd, hb, z_c), (1, 0, 0), (0, -1, 0), 2 * hb, "flange"), ((-hd, -hb, z_c), (-1, 0, 0), (0, 1, 0), 2 * hb, "flange"),
             ((-web_l / 2, hw, z_c), (0, 1, 0), (1, 0, 0), web_l, "web"), ((web_l / 2, -hw, z_c), (0, -1, 0), (-1, 0, 0), web_l, "web")]
    for org, xd, zd, wl, where in welds:
        a.add(f"W2{tag}", f"Fillet weld {fmt_in(w)}, column to base plate", "weld", f"weld{w}x{wl:.3f}", fillet_weld(w, wl),
              frame(o(*org[:2], org[2]), xd, zd), {"Leg": fmt_in(w), "Length": fmt_in(wl), "At": where}, SPEC_SRC,
              explode=(0, 0, col_top_explode), ifc="IfcFastener", steel=True)

    if dims:
        yf = y0 - B / 2
        a.dim(o(-B / 2, -B / 2, -T), o(B / 2, -B / 2, -T), (0, -7, 0))
        a.dim(o(B / 2, -B / 2, -T), o(B / 2, -B / 2, 0), (6, 0, 0))
        a.dim(o(-P / 2, -P / 2, H), o(P / 2, -P / 2, H), (0, -5, 0))
        a.dim(o(P / 2, -P / 2, 0), o(P / 2, -P / 2, H), (5, 0, 0))
        a.dim(o(B / 2, e0, -T), o(B / 2, e0 + sp, -T), (5, 0, 0))
        a.dim(o(-B / 2, -B / 2, -T), o(-B / 2, -B / 2, z_lo - db / 2), (-5, 0, 0))
        a.dim(o(-g, -s["bp"] / 2, z_c), o(g, -s["bp"] / 2, z_c), (0, -3.5, 0))
    return {"z_plate_top": z_c, "nest": nest, "side": side, "cover_bot": s["cover"], "sp": sp}


EMBEDDED = [("concrete", "rebar"), ("concrete", "tie"), ("concrete", "anchor"), ("grout", "anchor")]


def cage_checks(a: Assembly, s: dict, tag: str = ""):
    """Covers, seating and bar weights, all measured on the solids."""
    ftg = next(i for i in a.items if i.mark == f"F1{tag}")
    ped = next(i for i in a.items if i.mark == f"P1{tag}")
    mats = [i for i in a.items if i.mark == f"M1{tag}"]
    ties = [i for i in a.items if i.mark == f"T1{tag}"]
    verts = [i for i in a.items if i.mark == f"V1{tag}"]
    bottom = ftg.world.faces().sort_by(lambda f: f.center().Z)[0]
    cov = min(min_distance(m.world, bottom) for m in mats)
    a.check("Bottom mat to underside of footing, clear cover", f"{cov:.3f} in.", f"{s['cover']:.3f} in. (spec)",
            abs(cov - s["cover"]) < 1e-3)
    sides = [f for f in ftg.world.faces() if abs(f.normal_at().Z) < 0.5]
    cov_s = min(min_distance(m.world, f) for m in mats for f in sides)
    a.check("Bottom mat to side of footing, clear cover", f"{cov_s:.3f} in.", f"{s['cover']:.3f} in. (spec)",
            abs(cov_s - s["cover"]) < 1e-3)
    psides = [f for f in ped.world.faces() if abs(f.normal_at().Z) < 0.5]
    upper = [t for t in ties if t.world.bounding_box().min.Z > 0]
    cov_t = min(min_distance(t.world, f) for t in upper for f in psides)
    a.check("Ties to face of pedestal, clear cover", f"{cov_t:.3f} in.", f"{s['tie_cover']:.3f} in. (spec)",
            abs(cov_t - s["tie_cover"]) < 1e-3)
    seat = max(min(min_distance(v.world, t.world) for t in upper[:1]) for v in verts)
    a.check("Verticals seated against the tie, largest gap", f"{seat:.4f} in.", "0", seat < 2e-3)
    rest = max(min(min_distance(v.world, m.world) for m in mats) for v in verts)
    a.check("Vertical hooks resting on the mat, largest gap", f"{rest:.4f} in.", "0", rest < 2e-3)
    for mark, size in ((f"M1{tag}", s["mat"]), (f"V1{tag}", s["vert"]), (f"T1{tag}", s["tie"])):
        it = next(i for i in a.items if i.mark == mark)
        plf = it.weight / it.length * 12
        a.check(f"{size} bar weight per foot of the solid", f"{plf:.3f} lb/ft", f"{REBAR[size][1]} lb/ft (nominal)",
                abs(plf - REBAR[size][1]) / REBAR[size][1] < 0.01)
