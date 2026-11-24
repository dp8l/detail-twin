"""Single-plate (shear tab) connection family."""
from __future__ import annotations

from detailtwin.catalog import BOLT, HAND, w_shape
from detailtwin.core import STEEL_PCI, Assembly, fmt_in, frame, min_distance
from detailtwin.parts import drill, fillet_weld, hex_bolt, hex_nut, plate, round_washer, w_section


def _grade(s: dict, key: str) -> dict:
    """A grade is shown only when the spec gives one. The family never supplies it."""
    return {"Grade": s[key]} if s.get(key) else {}


def add_connection(a: Assembly, s: dict, x_face: float, sign: int, z_tos: float, tag: str = "",
                   ex_scale: float = 1.0, dims: bool = True, to: str = "column flange",
                   source: str = "Connection spec of this sample"):
    """Shear tab, bolts and welds at a column flange face. `sign` is +1 when the beam runs
    toward +X from the face and -1 when it runs toward -X. Returns the bolt positions."""
    bm, bo = w_shape(s["beam"]), BOLT[s["bolt"]]
    tw = bm["tw"]
    tab_len = (s["n_bolts"] - 1) * s["pitch"] + 2 * s["edge_v"]
    z_top = z_tos - (s["first_bolt"] - s["edge_v"])
    y0, y1 = tw / 2, tw / 2 + s["tab_t"]
    xb = x_face + sign * s["a"]
    zs = [z_tos - s["first_bolt"] - i * s["pitch"] for i in range(s["n_bolts"])]
    e = ex_scale

    tab = plate(s["tab_w"], s["tab_t"], tab_len)
    for i in range(s["n_bolts"]):
        tab = drill(tab, s["hole"], (s["a"], 0, tab_len - s["edge_v"] - i * s["pitch"]), "Y")
    a.add(f"PL1{tag}", f"Shear tab PL {fmt_in(s['tab_t'])} x {fmt_in(s['tab_w'])} x {fmt_in(tab_len)}", "plate",
          f"tab{s['n_bolts']}", tab, frame((x_face, y0 if sign > 0 else y1, z_top - tab_len), (sign, 0, 0), (0, 0, 1)),
          {"Thickness": fmt_in(s["tab_t"]), "Width": fmt_in(s["tab_w"]), "Length": fmt_in(tab_len),
           "Holes": f"({s['n_bolts']}) {fmt_in(s['hole'])} dia."}, source,
          explode=(sign * 4 * e, 0, 0), ifc="IfcPlate", steel=True)

    wl = fillet_weld(s["weld"], tab_len)
    for k, (yy, ysgn) in enumerate(((y1, 1), (y0, -1))):
        # legs run along (sign, 0, 0) and (0, ysgn, 0), so the length runs along z = x cross y
        zc = sign * ysgn
        z_o = z_top - tab_len if zc > 0 else z_top
        a.add(f"W1{tag}", f"Fillet weld {fmt_in(s['weld'])}, tab to {to}", "weld", f"weld{s['weld']}x{tab_len}",
              wl, frame((x_face, yy, z_o), (sign, 0, 0), (0, 0, zc)),
              {"Leg": fmt_in(s["weld"]), "Length": fmt_in(tab_len), "Side": "near" if k == 0 else "far"},
              source, explode=(sign * 2 * e, 0, 0), ifc="IfcFastener", steel=True)

    bolt = hex_bolt(s["bolt"], s["bolt_len"])
    nut = hex_nut(s["bolt"])
    wsh = round_washer(bo["wod"], bo["wid"], bo["wt"])
    for z in zs:
        a.add(f"B{tag}", f"{s['bolt']} in. dia. heavy hex bolt x {fmt_in(s['bolt_len'])}", "bolt",
              f"bolt{s['bolt']}x{s['bolt_len']}", bolt, frame((xb, y1, z), (1, 0, 0), (0, 1, 0)),
              {"Diameter": s["bolt"] + '"', "Length": fmt_in(s["bolt_len"]), **_grade(s, "bolt_grade"),
               "Thread": f"{bo['tpi']} per inch over {fmt_in(bo['Lt'])}"}, HAND,
              explode=(sign * 4 * e, 3.5 * e, 0), ifc="IfcMechanicalFastener", steel=True)
        a.add(f"WSH{tag}", f"Hardened washer for {s['bolt']} in. bolt", "bolt", f"washer{s['bolt']}", wsh,
              frame((xb, -tw / 2, z), (1, 0, 0), (0, -1, 0)),
              {"OD": fmt_in(bo["wod"], 64), "ID": fmt_in(bo["wid"]), "Thickness": f"{bo['wt']:.3f}\""}, HAND,
              explode=(sign * 4 * e, -2.2 * e, 0), ifc="IfcMechanicalFastener", steel=True)
        a.add(f"N{tag}", f"Heavy hex nut for {s['bolt']} in. bolt", "bolt", f"nut{s['bolt']}", nut,
              frame((xb, -tw / 2 - bo["wt"], z), (1, 0, 0), (0, -1, 0)),
              {"Across flats": fmt_in(bo["F"]), "Height": fmt_in(bo["Hn"], 64), **_grade(s, "nut_grade")}, HAND,
              explode=(sign * 4 * e, -3.6 * e, 0), ifc="IfcMechanicalFastener", steel=True)

    if dims:
        yd = y1 + 0.9
        xo = xb + sign * 3.2
        a.dim((xb, yd, zs[0]), (xb, yd, zs[1]), (sign * 3.2, 0, 0))
        a.dim((xb, yd, z_top), (xb, yd, zs[0]), (sign * 3.2, 0, 0))
        a.dim((xb, yd, z_top), (xb, yd, z_top - tab_len), (sign * 5.0, 0, 0))
        a.dim((x_face, yd, z_top - tab_len), (xb, yd, z_top - tab_len), (0, 0, -2.2))
        a.dim((xb, yd, z_top - tab_len), (x_face + sign * s["tab_w"], yd, z_top - tab_len), (0, 0, -2.2))
        a.dim((x_face, yd, z_tos), (x_face + sign * s["setback"], yd, z_tos), (0, 0, 2.0))
    return xb, zs, tab_len


def beam_with_holes(s, length, ends=("start",)):
    """Beam solid in its local frame (length along +Z) with bolt holes at the named ends."""
    bm = w_shape(s["beam"])
    sol = w_section(bm["d"], bm["bf"], bm["tf"], bm["tw"], bm["kdes"], length)
    off = s["a"] - s["setback"]
    for end in ends:
        zc = off if end == "start" else length - off
        for i in range(s["n_bolts"]):
            sol = drill(sol, s["hole"], (0, bm["d"] / 2 - s["first_bolt"] - i * s["pitch"], zc), "X")
    return sol, bm
