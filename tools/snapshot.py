"""Off-screen picture of a built case, for checking work. Not the page a person looks at.

    python tools/snapshot.py shear_tab out/shots/tab.png --dir 1,1.3,0.5 --focus 8,0,-7.5 --span 14
    python tools/snapshot.py footing out/shots/cage.png --xray --hide concrete
    python tools/snapshot.py footing out/shots/sec.png --cut y:0 --dir 0,-1,0.15

Reads out/<case>.json, the same payload the viewer page reads, so the picture shows what the page shows.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import numpy as np
import pyvista as pv

ROOT = Path(__file__).resolve().parents[1]
RGB = {"concrete": "#bdbab3", "grout": "#8f948e", "sheathing": "#bd9a60", "wood": "#d2ae76", "sill": "#8d8a5c",
       "steel": "#4d5a68", "plate": "#6f8296", "weld": "#d08a2e", "rebar": "#7a4433", "tie": "#a2633f",
       "anchor": "#b4b8bc", "bolt": "#bcc0c4", "connector": "#aab1b7", "nail": "#9299a0"}
GHOST = {"concrete", "grout", "sheathing"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("png")
    ap.add_argument("--dir", default=None, help="camera direction from the focus, x,y,z")
    ap.add_argument("--focus", default=None, help="point to look at, x,y,z in inches")
    ap.add_argument("--span", type=float, default=None, help="height of the view in inches")
    ap.add_argument("--xray", action="store_true", help="see through concrete, grout and sheathing")
    ap.add_argument("--hide", default="", help="classes or marks to leave out, comma separated")
    ap.add_argument("--only", default="", help="classes or marks to keep, comma separated")
    ap.add_argument("--explode", type=float, default=0.0)
    ap.add_argument("--cut", default=None, help="axis:position, keeps the side away from the camera")
    ap.add_argument("--size", default="1600,1100")
    a = ap.parse_args()

    c = json.loads((ROOT / "out" / f"{a.case}.json").read_text())
    hide = {s for s in a.hide.split(",") if s}
    only = {s for s in a.only.split(",") if s}
    view = np.array([float(v) for v in (a.dir or ",".join(map(str, c["view"].get("dir", [1, -1.2, 0.6])))).split(",")])
    view /= np.linalg.norm(view)
    geoms = {}
    for k, g in c["geoms"].items():
        pos = np.frombuffer(base64.b64decode(g["pos"]), dtype=np.float32).reshape(-1, 3)
        idx = np.frombuffer(base64.b64decode(g["idx"]), dtype=np.uint32).reshape(-1, 3)
        geoms[k] = pv.PolyData(pos.astype(float), np.hstack([np.full((len(idx), 1), 3), idx]).astype(np.int64).ravel())

    w, h = (int(v) for v in a.size.split(","))
    pl = pv.Plotter(off_screen=True, window_size=(w, h))
    pl.set_background("#f6f8fa", top="#d9e0e8")
    shown = 0
    for p in c["parts"]:
        if p["cls"] in hide or p["mark"] in hide or (only and p["cls"] not in only and p["mark"] not in only):
            continue
        m = np.array(p["m"]).reshape(4, 4).copy()
        m[:3, 3] += np.array(p["ex"]) * a.explode
        mesh = geoms[p["geom"]].transform(m, inplace=False)
        edges = mesh.extract_feature_edges(feature_angle=30, boundary_edges=True, non_manifold_edges=False, manifold_edges=False)
        if a.cut:
            ax, at = a.cut.split(":")
            k = "xyz".index(ax)
            n = np.zeros(3)
            n[k] = 1.0 if view[k] >= 0 else -1.0  # points at the camera side, which is removed
            org = np.zeros(3)
            org[k] = float(at)
            mesh = mesh.clip(normal=n, origin=org, invert=True)
            edges = edges.clip(normal=n, origin=org, invert=True) if edges.n_points else edges
            if mesh.n_points == 0:
                continue
        ghost = a.xray and p["cls"] in GHOST
        pl.add_mesh(mesh, color=RGB.get(p["cls"], "#888888"), opacity=0.15 if ghost else 1.0, smooth_shading=True,
                    split_sharp_edges=True, feature_angle=30, specular=0.15, ambient=0.25, diffuse=0.8)
        if edges.n_points:
            pl.add_mesh(edges, color="#10151b", line_width=1.2, opacity=0.7)
        shown += 1
    pl.enable_parallel_projection()
    b = np.array(pl.bounds).reshape(3, 2)
    focus = np.array([float(v) for v in a.focus.split(",")]) if a.focus else b.mean(axis=1)
    radius = np.linalg.norm(b[:, 1] - b[:, 0])
    pl.camera.focal_point = focus.tolist()
    pl.camera.position = (focus + view * radius * 3).tolist()
    pl.camera.up = (0, 0, 1) if abs(view[2]) < 0.99 else (0, 1, 0)
    pl.camera.parallel_scale = (a.span or radius * 0.62) / 2
    pl.camera.clipping_range = (radius * 0.1, radius * 8)
    Path(a.png).parent.mkdir(parents=True, exist_ok=True)
    pl.screenshot(a.png)
    print(f"{a.png}: {shown} parts drawn")


if __name__ == "__main__":
    main()
