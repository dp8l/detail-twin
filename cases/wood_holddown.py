"""Sample 3. Wood shear wall end at the foundation: end post, hold-down, sill anchors, sheathing nails."""
from __future__ import annotations

from build123d import Polygon, extrude, Plane, Pos

from detailtwin.catalog import BOLT, HAND, LUMBER
from detailtwin.core import Assembly, fmt_in, frame, min_distance
from detailtwin.parts import drill, hex_nut, hex_screw, nail, plate, plate_washer, round_rod, round_washer

SPEC = dict(L=48.0, H=36.0, stem_t=8.0, stem_h=16.0, stud="2x6", post="4x6", stud_oc=16.0, sheath=15 / 32,
            nail=(0.131, 2.5, 0.281), edge_oc=4.0, field_oc=12.0, edge_dist=0.75,
            ab="5/8", ab_x=(10.0, 40.0), ab_embed=7.0, ab_hole=11 / 16, ab_pw=3.0, ab_pw_t=0.229,
            hd_rod="5/8", hd_cl=1.375, hd_embed=12.0, hd_t=0.125, hd_w=2.5, hd_h=14.0, hd_seat=2.5, hd_seat_t=0.375,
            hd_lift=0.5, screw=(0.25, 2.5, 0.5), screw_z=(5.0, 7.0, 9.0, 11.0, 13.0), screw_y=(0.625, 1.875))
SPEC_SRC = "Detail spec of this sample"


def holddown(s):
    """Generic fabricated hold-down: back plate, seat plate and two gussets, as one solid.
    Local frame: back of the plate on x = 0, width along Y from 0, bottom at z = 0."""
    t, w, h, d, st = s["hd_t"], s["hd_w"], s["hd_h"], s["hd_seat"], s["hd_seat_t"]
    body = plate(t, w, h) + Pos(t, 0, 0) * plate(d, w, st)
    tri = Plane.XZ * Polygon((t, st), (t + d, st), (t, st + 7.0), align=None)
    body = body + Pos(0, t, 0) * extrude(tri, -t) + Pos(0, w, 0) * extrude(tri, -t)
    body = drill(body, s["ab_hole"], (s["hd_cl"], w / 2, 0), "Z")
    for z in s["screw_z"]:
        for y in s["screw_y"]:
            body = drill(body, s["screw"][0] + 1 / 64, (0, y, z), "X", depth=1.0)
    return body


def build() -> Assembly:
    s = SPEC
    L, H = s["L"], s["H"]
    sw, sd = LUMBER[s["stud"]]
    pw_, pd = LUMBER[s["post"]]
    bo, hb = BOLT[s["ab"]], BOLT[s["hd_rod"]]
    a = Assembly("holddown", "Shear wall hold-down at the foundation",
                 f"{s['post']} end post, {s['stud']} studs at {fmt_in(s['stud_oc'])}, sheathing nailed at {fmt_in(s['edge_oc'])} on edges")
    Z = (0, 0, 1)
    yc = sd / 2
    x_hd = pw_ + s["hd_cl"]

    a.add("FW", f"Stem wall, {fmt_in(s['stem_t'])} thick", "concrete", "stem", plate(L, s["stem_t"], s["stem_h"]),
          frame((0, 0, -s["stem_h"]), (1, 0, 0), Z), {"Thickness": fmt_in(s["stem_t"]), "Height shown": fmt_in(s["stem_h"])},
          SPEC_SRC, ifc="IfcFooting")

    sill = plate(L, sd, sw)
    for x in s["ab_x"]:
        sill = drill(sill, s["ab_hole"], (x, yc, 0), "Z")
    sill = drill(sill, s["ab_hole"], (x_hd, yc, 0), "Z")
    a.add("SP", f"{s['stud']} treated sill plate", "sill", "sill", sill, frame((0, 0, 0), (1, 0, 0), Z),
          {"Nominal": s["stud"], "Actual": f"{sw} x {sd} in.", "Length shown": fmt_in(L),
           "Holes": f"(3) {fmt_in(s['ab_hole'])} dia."}, HAND, explode=(0, 0, 0), ifc="IfcMember")
    a.add("EP", f"{s['post']} end post", "wood", "post", plate(pw_, pd, H), frame((0, 0, sw), (1, 0, 0), Z),
          {"Nominal": s["post"], "Actual": f"{pw_} x {pd} in.", "Length shown": fmt_in(H)}, HAND,
          explode=(0, 0, 0), ifc="IfcMember")
    stud = plate(sw, sd, H)
    xs = [s["stud_oc"] * k for k in range(1, int(L // s["stud_oc"]) + 1) if s["stud_oc"] * k + sw / 2 <= L]
    for x in xs:
        a.add("ST", f"{s['stud']} stud", "wood", "stud", stud, frame((x - sw / 2, 0, sw), (1, 0, 0), Z),
              {"Nominal": s["stud"], "Actual": f"{sw} x {sd} in.", "Spacing": fmt_in(s["stud_oc"])}, HAND, ifc="IfcMember")
    a.add("SH", f"Sheathing panel, {fmt_in(s['sheath'], 32)}", "sheathing", "sheath", plate(L, s["sheath"], H + sw),
          frame((0, -s["sheath"], 0), (1, 0, 0), Z), {"Thickness": fmt_in(s["sheath"], 32), "Area shown": f"{L * (H + sw) / 144:.1f} sq ft"},
          SPEC_SRC, explode=(0, -9, 0), ifc="IfcPlate")

    # sheathing nails: edges along the sill and the end post, field on the studs
    nd, nl, nh = s["nail"]
    nl_s = nail(nd, nl, nh)
    spots = [(x, s["edge_dist"], "edge, sill") for x in _steps(2.0, L - 2.0, s["edge_oc"])]
    spots += [(s["edge_dist"], z, "edge, end post") for z in _steps(sw + 3.25, sw + H - 0.75, s["edge_oc"])]
    spots += [(x, z, "field") for x in xs for z in _steps(sw + 5.25, sw + H - 0.75, s["field_oc"])]
    for x, z, where in spots:
        a.add("NL", f"Sheathing nail {nd} x {fmt_in(nl)}", "nail", "nail", nl_s, frame((x, -s["sheath"], z), (1, 0, 0), (0, -1, 0)),
              {"Shank": f"{nd} in.", "Length": fmt_in(nl), "Head": f"{nh} in.", "Line": where}, HAND,
              explode=(0, -13, 0), ifc="IfcMechanicalFastener", steel=True)

    # sill anchor bolts
    ab_len = s["ab_embed"] + sw + s["ab_pw_t"] + bo["Hn"] + 0.5
    rod = round_rod(bo["d"], ab_len)
    for x in s["ab_x"]:
        top = sw + s["ab_pw_t"] + bo["Hn"] + 0.5
        a.add("AB", f"{s['ab']} in. sill anchor x {fmt_in(ab_len)}", "anchor", "ab", rod, frame((x, yc, top), (1, 0, 0), Z),
              {"Diameter": s["ab"] + '"', "Length": fmt_in(ab_len), "Embedment": fmt_in(s["ab_embed"])}, HAND,
              ifc="IfcMechanicalFastener", steel=True, length=ab_len)
        a.add("ABN", f"Heavy hex nut, embedded end of {s['ab']} in. anchor", "anchor", f"nut{s['ab']}", hex_nut(s["ab"]),
              frame((x, yc, -s["ab_embed"]), (1, 0, 0), Z), {"Across flats": fmt_in(bo["F"]), "Height": fmt_in(bo["Hn"], 64)},
              HAND, ifc="IfcMechanicalFastener", steel=True)
        a.add("PW", f"Plate washer {fmt_in(s['ab_pw'])} x {fmt_in(s['ab_pw'])} x {s['ab_pw_t']}", "bolt", "abpw",
              plate_washer(s["ab_pw"], s["ab_pw_t"], s["ab_hole"]), frame((x, yc, sw), (1, 0, 0), Z),
              {"Size": f"{fmt_in(s['ab_pw'])} square", "Thickness": f"{s['ab_pw_t']} in."}, SPEC_SRC,
              explode=(0, 0, 6), ifc="IfcMechanicalFastener", steel=True)
        a.add("NT", f"Heavy hex nut for {s['ab']} in. anchor", "bolt", f"nut{s['ab']}", hex_nut(s["ab"]),
              frame((x, yc, sw + s["ab_pw_t"]), (1, 0, 0), Z), {"Across flats": fmt_in(bo["F"]), "Height": fmt_in(bo["Hn"], 64)},
              HAND, explode=(0, 0, 8), ifc="IfcMechanicalFastener", steel=True)

    # hold-down, its rod, washer, nut and screws
    z_hd = sw + s["hd_lift"]
    y_hd = yc - s["hd_w"] / 2
    a.add("HD", "Hold-down, fabricated, screwed to post", "connector", "hd", holddown(s), frame((pw_, y_hd, z_hd), (1, 0, 0), Z),
          {"Back plate": f"{fmt_in(s['hd_t'])} x {fmt_in(s['hd_w'])} x {fmt_in(s['hd_h'])}",
           "Seat": f"{fmt_in(s['hd_seat_t'])} x {fmt_in(s['hd_seat'])}", "Rod centreline from post": fmt_in(s["hd_cl"]),
           "Screws": f"({len(s['screw_z']) * len(s['screw_y'])}) {s['screw'][0]} x {fmt_in(s['screw'][1])}"}, SPEC_SRC,
          explode=(7, 0, 0), ifc="IfcDiscreteAccessory", steel=True)
    z_seat = z_hd + s["hd_seat_t"]
    top = z_seat + hb["wt"] + hb["Hn"] + 0.5
    hd_len = top + s["hd_embed"]
    a.add("HR", f"{s['hd_rod']} in. hold-down rod x {fmt_in(hd_len)}", "anchor", "hdrod", round_rod(hb["d"], hd_len),
          frame((x_hd, yc, top), (1, 0, 0), Z), {"Diameter": s["hd_rod"] + '"', "Length": fmt_in(hd_len),
                                               "Embedment": fmt_in(s["hd_embed"])}, HAND,
          ifc="IfcMechanicalFastener", steel=True, length=hd_len)
    a.add("ABN", f"Heavy hex nut, embedded end of {s['ab']} in. anchor", "anchor", f"nut{s['hd_rod']}", hex_nut(s["hd_rod"]),
          frame((x_hd, yc, -s["hd_embed"]), (1, 0, 0), Z), {"Across flats": fmt_in(hb["F"]), "Height": fmt_in(hb["Hn"], 64)},
          HAND, ifc="IfcMechanicalFastener", steel=True)
    a.add("HW", f"Hardened washer for {s['hd_rod']} in. rod", "bolt", f"washer{s['hd_rod']}",
          round_washer(hb["wod"], hb["wid"], hb["wt"]), frame((x_hd, yc, z_seat), (1, 0, 0), Z),
          {"OD": fmt_in(hb["wod"]), "ID": fmt_in(hb["wid"]), "Thickness": f"{hb['wt']:.3f}\""}, HAND,
          explode=(7, 0, 5), ifc="IfcMechanicalFastener", steel=True)
    a.add("NT", f"Heavy hex nut for {s['ab']} in. anchor", "bolt", f"nut{s['hd_rod']}", hex_nut(s["hd_rod"]),
          frame((x_hd, yc, z_seat + hb["wt"]), (1, 0, 0), Z), {"Across flats": fmt_in(hb["F"]), "Height": fmt_in(hb["Hn"], 64)},
          HAND, explode=(7, 0, 7), ifc="IfcMechanicalFastener", steel=True)
    sd_, sl, sh = s["screw"]
    scr = hex_screw(sd_, sl)
    for z in s["screw_z"]:
        for y in s["screw_y"]:
            a.add("SC", f"Hold-down screw {sd_} x {fmt_in(sl)}", "nail", "screw", scr,
                  frame((pw_ + s["hd_t"], y_hd + y, z_hd + z), (0, 1, 0), (1, 0, 0)),
                  {"Diameter": f"{sd_} in.", "Length": fmt_in(sl)}, SPEC_SRC, explode=(12, 0, 0),
                  ifc="IfcMechanicalFastener", steel=True)

    # dimensions
    yo = -s["sheath"]
    a.dim((0, sd, sw + H), (xs[0], sd, sw + H), (0, 0, 4))
    a.dim((xs[0], sd, sw + H), (xs[1], sd, sw + H), (0, 0, 4))
    a.dim((2.0, yo, s["edge_dist"]), (6.0, yo, s["edge_dist"]), (0, -3, -4))
    a.dim((pw_, sd, z_seat), (x_hd, sd, z_seat), (0, 5, 0))
    a.dim((L, sd, 0), (L, sd, sw), (5, 0, 0))
    a.dim((L, 0, -s["stem_h"]), (L, s["stem_t"], -s["stem_h"]), (5, 0, 0))
    a.dim((L, s["stem_t"], 0), (L, s["stem_t"], -s["ab_embed"]), (0, 5, 0))

    # checks measured on the solids
    nails = [i for i in a.items if i.mark == "NL" and i.props["Line"] == "edge, sill"]
    xs_n = sorted(n.world.bounding_box().center().X for n in nails)
    gaps = [b - c for b, c in zip(xs_n[1:], xs_n[:-1])]
    a.check("Edge nail spacing along the sill, largest", f"{max(gaps):.3f} in.", f"{s['edge_oc']:.3f} in. (spec)",
            abs(max(gaps) - s["edge_oc"]) < 1e-3)
    sh = next(i for i in a.items if i.mark == "SH")
    ed = min(n.world.bounding_box().center().Z for n in nails) - sh.world.bounding_box().min.Z
    a.check("Edge nail centre to bottom edge of panel", f"{ed:.3f} in.", f"{s['edge_dist']:.3f} in. (spec)", abs(ed - s["edge_dist"]) < 1e-3)
    post = next(i for i in a.items if i.mark == "EP")
    hr = next(i for i in a.items if i.mark == "HR")
    cl = min_distance(hr.world, post.world) + hb["d"] / 2
    a.check("Hold-down rod centreline from post face", f"{cl:.3f} in.", f"{s['hd_cl']:.3f} in. (spec)", abs(cl - s["hd_cl"]) < 1e-3)
    sp = next(i for i in a.items if i.mark == "SP")
    gap = min(min_distance(r.world, sp.world) for r in a.items if r.mark in ("AB", "HR"))
    a.check("Rods through sill holes, smallest radial gap", f"{gap:.4f} in.", f"{(s['ab_hole'] - bo['d']) / 2:.4f} in.",
            abs(gap - (s["ab_hole"] - bo["d"]) / 2) < 1e-3)
    emb = -hr.world.bounding_box().min.Z
    a.check("Hold-down rod embedment below top of concrete", f"{emb:.2f} in.", f"{s['hd_embed']:.2f} in. (spec)", abs(emb - s["hd_embed"]) < 1e-3)
    pen = min(n.world.bounding_box().max.Y for n in nails)
    a.check("Nail penetration into framing", f"{pen:.3f} in.", f"{nl - s['sheath']:.3f} in. (length minus panel)", abs(pen - (nl - s["sheath"])) < 1e-3)
    driven = [("nail", c) for c in ("wood", "sill", "sheathing")]
    tested, clashes = a.interference(allowed=driven + [("anchor", "concrete")])
    a.check("Interference between parts", f"{len(clashes)} clashes in {tested} overlapping pairs", "0 clashes", not clashes,
            "; ".join(f"{x.mark}/{y.mark} {v:.4f} in.3" for x, y, v in clashes[:4]))
    bf = (2 * 6 * L + 4 * 6 * H + 2 * 6 * H * len(xs)) / 144
    a.check("Framing lumber in view", f"{bf:.1f} board ft", "take-off from nominal sizes", True)
    a.notes = ["This is a geometry sample. Sizes are typical values chosen for the sample and nothing was designed for load.",
               "The hold-down is a generic fabricated shape, not a catalogue product.",
               "Lumber sizes, nail and fastener dimensions were typed by hand for this sample.",
               "Nails and screws are driven fasteners, so they are embedded in the wood by design.",
               "The wall is cut 3 ft above the sill and 4 ft from its end."]
    a.view = {"dir": [0.9, 1.25, 0.55], "section": {"axis": "x", "pos": x_hd}}
    return a


def _steps(lo, hi, step):
    out, v = [], lo
    while v <= hi + 1e-9:
        out.append(round(v, 6))
        v += step
    return out
