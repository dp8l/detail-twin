"""Detail Twin core: an assembly of exact solids with marks, sources, checks and exports.

Units are inches and pounds throughout. Geometry is OpenCascade B-rep through build123d.
Every part keeps the source of its dimensions, and every check is measured on the solids.
"""
from __future__ import annotations

import base64
import math
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np
from build123d import Color, Compound, Location, Plane, Unit, Vector, export_step
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Vec

STEEL_PCF = 490.0  # lb/ft3, unit weight of steel used for take-off (input)
STEEL_PCI = STEEL_PCF / 1728.0
TESS_LIN = 0.004  # in, chord deflection of the display mesh
TESS_ANG = 0.22  # rad


def frame(origin, x_dir, z_dir) -> Location:
    """Placement that sends local X to x_dir and local Z to z_dir."""
    return Plane(origin=origin, x_dir=x_dir, z_dir=z_dir).location


def fmt_in(x: float, denom: int = 16) -> str:
    """Feet-inch-fraction text of a length in inches, to the nearest 1/denom."""
    neg = x < 0
    x = abs(x)
    n = round(x * denom)
    whole, rem = divmod(n, denom)
    ft, inch = divmod(whole, 12)
    frac = Fraction(rem, denom)
    if ft == 0:
        s = (f"{inch} {frac}" if frac and inch else f"{frac}" if frac else f"{inch}") + '"'
    else:
        s = f"{ft}'-{inch}" + (f" {frac}" if frac else "") + '"'
    return ("-" if neg else "") + s


def common_volume(a, b) -> float:
    op = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    op.Build()
    if not op.IsDone():
        return float("nan")
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(op.Shape(), g)
    return g.Mass()


def min_distance(a, b) -> float:
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


def loc_matrix(loc: Location) -> list[float]:
    t = loc.wrapped.Transformation()
    m = [[t.Value(r, c) for c in range(1, 5)] for r in range(1, 4)]
    m.append([0.0, 0.0, 0.0, 1.0])
    return [v for row in m for v in row]  # row-major 4x4


def _b64(arr: np.ndarray) -> str:
    return base64.b64encode(arr.tobytes()).decode("ascii")


@dataclass
class Item:
    mark: str
    name: str
    cls: str  # material class used for display and for the clash rules
    geom: str  # key of the canonical geometry (identical parts share one)
    shape: object  # canonical solid in its local frame
    loc: Location
    props: dict
    source: str
    explode: tuple = (0.0, 0.0, 0.0)
    ifc: str = "IfcBuildingElementProxy"
    weight: float | None = None
    length: float | None = None
    _world: object = None

    @property
    def world(self):
        if self._world is None:
            self._world = self.shape.moved(self.loc)
        return self._world


@dataclass
class Assembly:
    id: str
    title: str
    blurb: str
    items: list = field(default_factory=list)
    dims: list = field(default_factory=list)
    checks: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    view: dict = field(default_factory=dict)

    def add(self, mark, name, cls, geom, shape, loc, props, source, explode=(0, 0, 0),
            ifc="IfcBuildingElementProxy", steel=False, length=None) -> Item:
        w = shape.volume * STEEL_PCI if steel else None
        it = Item(mark, name, cls, geom, shape, loc, dict(props), source,
                  tuple(float(e) for e in explode), ifc, w, length)
        self.items.append(it)
        return it

    def dim(self, a, b, off, text=None):
        a, b = Vector(*a), Vector(*b)
        self.dims.append({"a": [a.X, a.Y, a.Z], "b": [b.X, b.Y, b.Z], "off": list(off),
                          "text": text or fmt_in((b - a).length)})

    def check(self, what, model, ref, ok, note=""):
        self.checks.append({"what": what, "model": model, "ref": ref, "ok": bool(ok), "note": note})

    # ---- measured checks ---------------------------------------------------------------
    def interference(self, allowed=(), tol=1e-5):
        """Common volume of every pair of parts whose boxes overlap. `allowed` lists class
        pairs that are embedded by design (a bar cast in concrete) and are not a clash."""
        allowed = {frozenset(p) for p in allowed}
        boxes = [it.world.bounding_box() for it in self.items]
        clashes, tested = [], 0
        for i in range(len(self.items)):
            for j in range(i + 1, len(self.items)):
                a, b = self.items[i], self.items[j]
                if frozenset((a.cls, b.cls)) in allowed:
                    continue
                A, B = boxes[i], boxes[j]
                if (A.min.X > B.max.X or B.min.X > A.max.X or A.min.Y > B.max.Y or
                        B.min.Y > A.max.Y or A.min.Z > B.max.Z or B.min.Z > A.max.Z):
                    continue
                tested += 1
                v = common_volume(a.world, b.world)
                if not (v <= tol):
                    clashes.append((a, b, v))
        return tested, clashes

    def mesh_fidelity(self):
        """Largest relative gap between display-mesh volume and exact solid volume."""
        worst = 0.0
        for key, (pos, idx, vol) in self._geoms().items():
            p = pos.reshape(-1, 3).astype(np.float64)
            t = idx.reshape(-1, 3)
            mv = abs(np.einsum("ij,ij->i", p[t[:, 0]], np.cross(p[t[:, 1]], p[t[:, 2]])).sum() / 6.0)
            worst = max(worst, abs(mv - vol) / vol)
        return worst

    # ---- exports ------------------------------------------------------------------------
    def _geoms(self):
        if not hasattr(self, "_gcache"):
            self._gcache = {}
            for it in self.items:
                if it.geom in self._gcache:
                    continue
                v, t = it.shape.tessellate(TESS_LIN, TESS_ANG)
                pos = np.array([c for p in v for c in (p.X, p.Y, p.Z)], dtype=np.float32)
                idx = np.array([c for tri in t for c in tri], dtype=np.uint32)
                self._gcache[it.geom] = (pos, idx, it.shape.volume)
        return self._gcache

    def bom(self):
        rows = {}
        for it in self.items:
            r = rows.setdefault(it.mark, {"mark": it.mark, "name": it.name, "cls": it.cls, "qty": 0,
                                          "unit_wt": it.weight, "total_wt": 0.0 if it.weight else None,
                                          "length": it.length})
            r["qty"] += 1
            if it.weight:
                r["total_wt"] += it.weight
        return list(rows.values())

    def payload(self):
        geoms = {k: {"pos": _b64(p), "idx": _b64(i)} for k, (p, i, _) in self._geoms().items()}
        parts = [{"mark": it.mark, "name": it.name, "cls": it.cls, "geom": it.geom,
                  "m": [round(v, 6) for v in loc_matrix(it.loc)], "ex": list(it.explode),
                  "props": it.props, "source": it.source,
                  "weight": None if it.weight is None else round(it.weight, 3),
                  "length": it.length, "ifc": it.ifc} for it in self.items]
        tri = sum(len(i) // 3 for _, i, _ in self._geoms().values())
        return {"id": self.id, "title": self.title, "blurb": self.blurb, "geoms": geoms, "parts": parts,
                "dims": self.dims, "checks": self.checks, "bom": self.bom(), "notes": self.notes,
                "view": self.view, "stats": {"parts": len(self.items), "unique": len(geoms), "tris": tri}}

    def to_step(self, path):
        kids = []
        for n, it in enumerate(self.items):
            w = it.shape.moved(it.loc)
            w.label = f"{it.mark} {it.name} #{n}"
            w.color = Color(*CLS_RGB.get(it.cls, (0.6, 0.6, 0.6)))
            kids.append(w)
        # the model is in inches: naming the unit makes the writer convert, and the file comes out in true millimetres
        export_step(Compound(label=self.id, children=kids), str(path), unit=Unit.IN)

    def to_compound(self, scale: float = 25.4):
        """One labelled, coloured compound of every part, scaled for a host that works in
        millimetres (the text-to-cad `cad` command). Labels are mark, then a running number."""
        kids, seen = [], {}
        for it in self.items:
            # scale the solid in its own frame, then place it with the offset scaled as well
            t = it.loc.wrapped.Transformation()
            v = t.TranslationPart()
            t.SetTranslationPart(gp_Vec(v.X() * scale, v.Y() * scale, v.Z() * scale))
            w = it.shape.scale(scale).moved(Location(t))
            n = seen[it.mark] = seen.get(it.mark, 0) + 1
            w.label = f"{it.mark}_{n}".replace(".", "_")
            r, g, b = CLS_RGB.get(it.cls, (0.6, 0.6, 0.6))
            w.color = Color(r, g, b)
            kids.append(w)
        return Compound(label=self.id, children=kids)

    def to_ifc(self, path):
        import importlib

        import ifcopenshell.api as api

        for sub in ("project", "root", "unit", "context", "aggregate", "geometry", "spatial", "pset"):
            importlib.import_module(f"ifcopenshell.api.{sub}")
        mm = 25.4
        f = api.project.create_file(version="IFC4")
        proj = api.root.create_entity(f, ifc_class="IfcProject", name=self.title)
        api.unit.assign_unit(f)  # millimetres
        ctx = api.context.add_context(f, context_type="Model")
        body = api.context.add_context(f, context_type="Model", context_identifier="Body",
                                       target_view="MODEL_VIEW", parent=ctx)
        site = api.root.create_entity(f, ifc_class="IfcSite", name="Site")
        bldg = api.root.create_entity(f, ifc_class="IfcBuilding", name="Detail")
        lvl = api.root.create_entity(f, ifc_class="IfcBuildingStorey", name="Level 1")
        api.aggregate.assign_object(f, products=[site], relating_object=proj)
        api.aggregate.assign_object(f, products=[bldg], relating_object=site)
        api.aggregate.assign_object(f, products=[lvl], relating_object=bldg)
        gm = self._geoms()
        for it in self.items:
            pos, idx, _ = gm[it.geom]
            el = api.root.create_entity(f, ifc_class=it.ifc, name=f"{it.mark} {it.name}")
            verts = (pos.reshape(-1, 3).astype(float) * mm).tolist()
            faces = idx.reshape(-1, 3).tolist()
            rep = api.geometry.add_mesh_representation(f, context=body, vertices=[verts], faces=[faces])
            api.geometry.assign_representation(f, product=el, representation=rep)
            m = np.array(loc_matrix(it.loc)).reshape(4, 4)
            m[:3, 3] *= mm
            api.geometry.edit_object_placement(f, product=el, matrix=m, is_si=False)
            api.spatial.assign_container(f, products=[el], relating_structure=lvl)
            ps = api.pset.add_pset(f, product=el, name="DetailTwin")
            props = {"Mark": it.mark, "Class": it.cls, "DimensionSource": it.source}
            props.update({k: str(v) for k, v in it.props.items()})
            if it.weight is not None:
                props["Weight_lb"] = round(it.weight, 3)
            api.pset.edit_pset(f, pset=ps, properties=props)
        f.write(str(path))
        return f


CLS_RGB = {
    "steel": (0.36, 0.40, 0.45), "plate": (0.50, 0.55, 0.60), "bolt": (0.74, 0.75, 0.77),
    "weld": (0.80, 0.50, 0.20), "concrete": (0.73, 0.72, 0.69), "grout": (0.55, 0.57, 0.55),
    "rebar": (0.55, 0.30, 0.22), "tie": (0.66, 0.40, 0.26), "anchor": (0.70, 0.71, 0.73),
    "wood": (0.80, 0.65, 0.43), "sill": (0.55, 0.54, 0.36), "sheathing": (0.74, 0.60, 0.38),
    "connector": (0.70, 0.72, 0.74), "nail": (0.42, 0.45, 0.48),
}
