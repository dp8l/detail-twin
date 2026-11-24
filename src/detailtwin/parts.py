"""Canonical solids, each built once in a local frame and placed many times."""
from __future__ import annotations

import math
from functools import lru_cache

from build123d import (Align, Axis, Box, Circle, Cylinder, FilletPolyline, Plane, Polygon, Pos,
                       RegularPolygon, chamfer, extrude, fillet, revolve, sweep)

from .catalog import BOLT

C = Align.CENTER
LO = Align.MIN


@lru_cache(maxsize=None)
def w_section(d, bf, tf, tw, k, length):
    """Rolled I shape. Depth along local Y, flange width along X, length along +Z.
    The web-to-flange fillet radius is k - tf."""
    y1 = d / 2 - tf
    pts = [(-bf / 2, -d / 2), (bf / 2, -d / 2), (bf / 2, -y1), (tw / 2, -y1), (tw / 2, y1), (bf / 2, y1),
           (bf / 2, d / 2), (-bf / 2, d / 2), (-bf / 2, y1), (-tw / 2, y1), (-tw / 2, -y1), (-bf / 2, -y1)]
    sk = Polygon(*pts, align=None)
    r = k - tf
    if r > 1e-6:
        inner = [v for v in sk.vertices() if abs(abs(v.X) - tw / 2) < 1e-6 and abs(abs(v.Y) - y1) < 1e-6]
        sk = fillet(inner, r)
    return extrude(sk, length)


def plate(lx, ly, lz):
    """Rectangular plate with its minimum corner at the local origin."""
    return Box(lx, ly, lz, align=(LO, LO, LO))


def drill(solid, dia, at, axis="Y", depth=100.0):
    """Cut a round through-hole of diameter `dia` centred at point `at`, along a local axis."""
    cyl = Cylinder(dia / 2, depth)
    if axis == "Z":
        return solid - Pos(*at) * cyl
    if axis == "Y":
        cyl = cyl.rotate(Axis.X, 90)
    elif axis == "X":
        cyl = cyl.rotate(Axis.Y, 90)
    return solid - Pos(*at) * cyl


def cope(solid, d, length, depth, radius=0.0, z_end=0.0, into=1, top=True, width=100.0):
    """Flange cope cut from a `w_section` solid (depth along local Y, length along local Z).
    The cut starts at the member end at z = `z_end` and runs `length` along the member, toward
    +Z when `into` is +1 and toward -Z when it is -1. It goes `depth` down from the top of steel
    (up from the bottom of steel when `top` is False) and takes the full flange width. The
    re-entrant corner is rounded to `radius`, with its axis across the web. Returns the cut solid."""
    sy = 1.0 if top else -1.0
    y_floor, y_out = sy * (d / 2 - depth), sy * (d / 2 + 1.0)
    z_out, z_cut = z_end - into * 1.0, z_end + into * length
    sk = Polygon((y_floor, z_out), (y_out, z_out), (y_out, z_cut), (y_floor, z_cut), align=None)
    if radius > 1e-6:
        corner = [v for v in sk.vertices() if abs(v.X - y_floor) < 1e-6 and abs(v.Y - z_cut) < 1e-6]
        sk = fillet(corner, radius)
    # the sketch is drawn as (local Y, local Z) and stood up on the YZ plane, then run across the flange
    return solid - extrude(Plane.YZ * sk, width / 2, both=True)


def _hex(F, H, both=False):
    """Hexagonal prism, across flats F, z from 0 to H, corners broken by a 30 degree chamfer."""
    body = extrude(RegularPolygon(F / 2, 6, major_radius=False), H)
    rc = F / 2 / math.cos(math.radians(30))
    c = rc - 0.47 * F
    cyl = Cylinder(rc, H, align=(C, C, LO))
    edges = cyl.edges().filter_by(lambda e: e.geom_type.name == "CIRCLE").sort_by(Axis.Z)
    pick = [edges[-1]] + ([edges[0]] if both else [])
    cyl = chamfer(pick, length=c * math.tan(math.radians(30)), length2=c)
    return body & cyl


@lru_cache(maxsize=None)
def hex_bolt(size, length):
    """Heavy hex bolt. Bearing face of the head at z = 0, shank toward -Z.
    The thread is drawn as annular grooves of the right pitch and depth, not as a helix."""
    b = BOLT[size]
    r, p = b["d"] / 2, 1.0 / b["tpi"]
    h = 0.61343 * p
    ls = max(length - b["Lt"], 0.0)
    head = _hex(b["F"], b["H"])
    n = int((length - ls) / p)
    pts = [(0, -ls), (r, -ls)]
    z = -ls
    for _ in range(n):
        pts += [(r - h, z - p / 2), (r, z - p)]
        z -= p
    pts[-1] = (r - h, -length)
    pts += [(0, -length)]
    thread = revolve(Plane.XZ * Polygon(*pts, align=None), Axis.Z)
    out = head + thread
    if ls > 0:
        out = out + Pos(0, 0, -ls) * Cylinder(r, ls, align=(C, C, LO))
    return out


@lru_cache(maxsize=None)
def hex_nut(size):
    b = BOLT[size]
    return _hex(b["F"], b["Hn"], both=True) - Cylinder(b["d"] / 2, b["Hn"], align=(C, C, LO))


@lru_cache(maxsize=None)
def round_washer(od, idia, t):
    return Cylinder(od / 2, t, align=(C, C, LO)) - Cylinder(idia / 2, t, align=(C, C, LO))


@lru_cache(maxsize=None)
def plate_washer(side, t, hole):
    return Box(side, side, t, align=(C, C, LO)) - Cylinder(hole / 2, t, align=(C, C, LO))


@lru_cache(maxsize=None)
def fillet_weld(leg, length):
    """Fillet weld as a triangular prism. Legs along local +X and +Y, length along +Z."""
    return extrude(Polygon((0, 0), (leg, 0), (0, leg), align=None), length)


def bar(points, db, bend_radius):
    """Reinforcing bar swept along its centreline. `bend_radius` is the centreline radius of
    each bend, the inside bend radius plus half a bar diameter. Returns solid and cut length."""
    pts = [tuple(p) for p in points]
    path = FilletPolyline(*pts, radius=bend_radius) if len(pts) > 2 else None
    if path is None:
        a, b = pts
        from build123d import Line
        path = Line(a, b)
    prof = Plane(origin=path @ 0, z_dir=path % 0) * Circle(db / 2)
    return sweep(prof, path), path.length


@lru_cache(maxsize=None)
def round_rod(dia, length):
    """Plain round rod, top at z = 0, running toward -Z."""
    return Cylinder(dia / 2, length, align=(C, C, Align.MAX))


@lru_cache(maxsize=None)
def hex_screw(shank, length, across_flats=0.375, head_h=0.16, flange=0.56, flange_t=0.05):
    """Hex washer-head screw. Underside of the washer flange at z = 0, shank toward -Z."""
    return (Cylinder(flange / 2, flange_t, align=(C, C, LO)) + Pos(0, 0, flange_t) * _hex(across_flats, head_h)
            + Cylinder(shank / 2, length, align=(C, C, Align.MAX)))


@lru_cache(maxsize=None)
def nail(shank, length, head, head_t=0.04):
    """Nail or screw as a shank with a flat head. Underside of the head at z = 0."""
    return Cylinder(head / 2, head_t, align=(C, C, LO)) + Cylinder(shank / 2, length, align=(C, C, Align.MAX))
