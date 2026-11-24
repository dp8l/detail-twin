# detailtwin, the library in one page

All lengths in inches. Read the source when a signature here is not enough: `src/detailtwin` in the repository.

## A case, start to finish

```python
"""<What the detail is>."""
from __future__ import annotations

from detailtwin.catalog import BOLT, HAND, w_shape
from detailtwin.core import Assembly, fmt_in, frame, min_distance
from detailtwin.parts import drill, plate, w_section

SPEC = dict(col="W10X49", pl_t=0.75, pl_w=12.0)          # every size the detail needs


def build() -> Assembly:
    s = SPEC
    col = w_shape(s["col"])                               # d, bf, tf, tw, kdes, A, W, source
    a = Assembly("cap_plate", "Column cap plate", f"{s['col']} with a {fmt_in(s['pl_t'])} cap")
    a.add("C1", f"{s['col']} column", "steel", f"{s['col']}x36",
          w_section(col["d"], col["bf"], col["tf"], col["tw"], col["kdes"], 36.0),
          frame((0, 0, 0), (0, 1, 0), (0, 0, 1)),          # local X -> world Y, local Z -> world Z
          {"Section": s["col"], "Length shown": fmt_in(36.0)}, col["source"],
          ifc="IfcColumn", steel=True, length=36.0)
    cap = a.add("PL1", "Cap plate", "plate", "cap", plate(s["pl_w"], s["pl_w"], s["pl_t"]),
                frame((-s["pl_w"] / 2, -s["pl_w"] / 2, 36.0), (1, 0, 0), (0, 0, 1)),
                {"Thickness": fmt_in(s["pl_t"])}, "Detail spec", explode=(0, 0, 6), ifc="IfcPlate", steel=True)
    a.dim((-6, -6, 36.75), (6, -6, 36.75), (0, -3, 0))    # text is measured, not typed
    gap = min_distance(cap.world, a.items[0].world)
    a.check("Cap plate seated on the column", f"{gap:.4f} in.", "0", gap < 1e-6)
    tested, clashes = a.interference()
    a.check("Interference between parts", f"{len(clashes)} clashes in {tested} overlapping pairs", "0 clashes",
            not clashes, "; ".join(f"{x.mark}/{y.mark} {v:.4f} in.3" for x, y, v in clashes[:4]))
    a.notes = ["This is a geometry sample. Nothing was designed for load."]
    a.view = {"dir": [1.0, -1.2, 0.6], "section": {"axis": "y", "pos": 0.0}}
    return a
```

`python tools/build.py cap_plate` then builds the module `cases/cap_plate.py` and writes
`out/cap_plate.json`, `.step` and `.ifc` under the Assembly's id.

## core

| Name | What it does |
|---|---|
| `frame(origin, x_dir, z_dir)` | Placement sending local X to `x_dir` and local Z to `z_dir`. Local Y is `z cross x`. Work the cross product out before trusting an orientation |
| `Assembly(id, title, blurb)` | The detail. `id` names the output files |
| `a.add(mark, name, cls, geom, shape, loc, props, source, explode=(0,0,0), ifc=..., steel=False, length=None)` | Adds one placed part and returns it. `geom` is a key: parts that share a key must share the same canonical `shape`. `steel=True` gives a weight from the volume at 490 lb/ft3. `explode` is the world offset at full explode |
| `a.dim(p1, p2, offset, text=None)` | Dimension between two world points, drawn offset by a vector. The text is the measured distance rounded to 1/16 in. Pass `text=` for a value that is not on a sixteenth |
| `a.check(what, model, ref, ok, note="")` | Records one check. `model` is the measured value as text, `ref` what it is held against |
| `a.interference(allowed=(), tol=1e-5)` | `(pairs_tested, [(item, item, volume)])`. Exact common volume of every pair whose boxes overlap. `allowed` is a list of class pairs embedded by design |
| `item.world` | The placed solid. Use with `min_distance(a, b)`, `.bounding_box()`, `.faces()`, `.volume` |
| `a.notes`, `a.view` | Notes shown on the page. View: `dir` (camera direction), `xray` (see through concrete), `section` (`axis`, `pos`) |
| `a.to_step(path)`, `a.to_ifc(path)`, `a.payload()`, `a.to_compound()` | Exports. The build tool calls the first three. `to_compound()` is the millimetre hand-off to `cad` |

## Material classes (`cls`)

`steel`, `plate`, `bolt`, `weld`, `concrete`, `grout`, `rebar`, `tie`, `anchor`, `wood`, `sill`,
`sheathing`, `connector`, `nail`. The class sets the colour, the section hatch and the clash rules.
A new class is added in three places: `CLS_RGB` in `core.py`, `CLS` in `viewer/template.html`,
`RGB` in `tools/snapshot.py`.

IFC classes used so far: `IfcBeam`, `IfcColumn`, `IfcPlate`, `IfcMember`, `IfcFooting`,
`IfcReinforcingBar`, `IfcMechanicalFastener`, `IfcFastener` (welds), `IfcDiscreteAccessory`.

## catalog

| Name | Content | Source |
|---|---|---|
| `w_shape("W16X40")` | `W, A, d, bf, tw, tf, kdes, k1`, plus `source` naming the table row | The three sample shapes ship with the package. Any other shape is read from the AISC shapes table named by `DETAILTWIN_AISC_XLSX` |
| `BOLT["3/4"]` | `d, F, H, Hn, Lt, tpi, wod, wid, wt` for 5/8, 3/4, 7/8 | `HAND` |
| `REBAR["#5"]` | `(diameter, lb/ft)` for #3 to #8 | `HAND` |
| `LUMBER["2x6"]` | actual `(b, d)` | `HAND` |

## parts (canonical solids)

| Builder | Local frame |
|---|---|
| `w_section(d, bf, tf, tw, k, length)` | Depth along Y, flange width along X, length along +Z from 0. Fillet radius `k - tf` |
| `plate(lx, ly, lz)` | Minimum corner at the origin |
| `drill(solid, dia, at, axis="Y")` | Through hole centred at `at` along local X, Y or Z. Returns the cut solid |
| `hex_bolt(size, length)` | Bearing face of the head at z = 0, shank toward -Z. Thread drawn as grooves |
| `hex_nut(size)`, `round_washer(od, id, t)`, `plate_washer(side, t, hole)` | Sit on z = 0, thickness toward +Z |
| `fillet_weld(leg, length)` | Triangle legs along +X and +Y, length along +Z |
| `bar(points, db, bend_radius)` | Bar swept along a polyline, returns `(solid, cut_length)`. `bend_radius` is to the bar centreline |
| `round_rod(dia, length)` | Top at z = 0, running toward -Z |
| `nail(shank, length, head)`, `hex_screw(shank, length)` | Underside of the head at z = 0, shank toward -Z |

## families (`detailtwin.families`)

| Call | Adds |
|---|---|
| `shear_tab.add_connection(a, spec, x_face, sign, z_tos, tag="", dims=True)` | Tab, welds, bolts, washers, nuts at a vertical face at `x = x_face`. `sign` +1 when the beam runs toward +X. Returns `(x_bolt_line, bolt_z_list, tab_length)` |
| `shear_tab.beam_with_holes(spec, length, ends=("start",))` | Beam solid with web holes at the named ends, and its section dict |
| `footing.add_footing(a, spec, x0, y0, tag="", col_len=None, dims=True)` | Footing, pedestal, mat, ties, hooked verticals, anchor rods, grout, base plate, column, welds. Top of footing at z = 0 |
| `footing.cage_checks(a, spec, tag="")` | Cover, seating and bar weight checks for that footing |
| `footing.EMBEDDED` | The class pairs to allow in `a.interference` |

`add_connection` reads these spec keys: `beam, bolt, n_bolts, pitch, first_bolt, edge_v, a, tab_t, tab_w,
hole, weld, bolt_len, setback`, and `bolt_grade`, `nut_grade` when the drawing gives them (a grade is
shown only when the spec gives one, the family never supplies it). The tab length is derived as `(n_bolts - 1) * pitch + 2 * edge_v`.
`to=` names what the tab is welded to and `source=` what its sizes came from. `ex_scale` scales the
explode offsets. `add_footing` reads every key of the footing `SPEC`, and `rod_grade` when given.

The specs these take are the `SPEC` dicts in `cases/steel_shear_tab.py` and `cases/footing_pedestal.py`.
`cases/portal_bent.py` shows two families placed at building scale with tags.

## Measuring

- `min_distance(a, b)` is the smallest gap between two solids, and 0 when they touch **or overlap**.
  It cannot tell seated from clashing. Pair it with `a.interference()`.
- A signed clearance (how far past, how far below) comes from bounding boxes: `item.world.bounding_box()`
  gives `.min` and `.max`. To measure one region of a part, intersect it with a `Box` slice first.
- A radius or a hole comes from the cylindrical faces: `[f for f in solid.faces() if f.geom_type.name == "CYLINDER"]`,
  then `f.radius`. Filter by position as well as size: the W16X40 web fillet (0.402 in.) and a
  13/16 in. hole (0.406 in. radius) differ by 0.004 in.
- Weight per foot is `item.weight / item.length * 12` for a part added with `steel=True` and `length=`.

## Where files land

`w_shape` caches the rows it reads in `data/aisc_w_cache.json` (not committed). `cad run` keeps
its environments under `~/.cache/cad`, outside the repository.
