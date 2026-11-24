"""The sample cases build, every measured check passes, and the exports are to scale.

The second half plants faults. A gate that has not been seen to fail on a planted fault
has shown nothing, so each gate is made to fail once here.
"""
from __future__ import annotations

import copy
import importlib

import pytest
from build123d import Location, import_step

from detailtwin.catalog import REBAR
from detailtwin.core import STEEL_PCI, Assembly

CASES = ["steel_shear_tab", "footing_pedestal", "wood_holddown", "portal_bent"]


@pytest.fixture(scope="module")
def built():
    return {n: importlib.import_module(f"cases.{n}").build() for n in CASES}


@pytest.mark.parametrize("name", CASES)
def test_every_check_passes(built, name):
    a = built[name]
    failed = [c for c in a.checks if not c["ok"]]
    assert a.checks and not failed, failed


@pytest.mark.parametrize("name", CASES)
def test_display_mesh_matches_solids(built, name):
    assert built[name].mesh_fidelity() < 0.005


def test_step_is_to_scale(built, tmp_path):
    """The model is in inches. The file must re-read at 25.4 mm per model inch."""
    a = built["steel_shear_tab"]
    path = tmp_path / "tab.step"
    a.to_step(path)
    back = import_step(str(path)).bounding_box().size  # the reader returns millimetres
    lo = [min(getattr(i.world.bounding_box().min, ax) for i in a.items) for ax in "XYZ"]
    hi = [max(getattr(i.world.bounding_box().max, ax) for i in a.items) for ax in "XYZ"]
    for got, want in zip((back.X, back.Y, back.Z), (h - l for h, l in zip(hi, lo))):
        assert got == pytest.approx(want * 25.4, rel=1e-4)


@pytest.mark.parametrize("name", ["steel_shear_tab", "portal_bent"])
def test_compound_for_cad_is_to_scale(built, name):
    """The hand-off to the cad command is in millimetres, placements included."""
    a = built[name]
    size = a.to_compound().bounding_box().size
    lo = [min(getattr(i.world.bounding_box().min, ax) for i in a.items) for ax in "XYZ"]
    hi = [max(getattr(i.world.bounding_box().max, ax) for i in a.items) for ax in "XYZ"]
    for got, want in zip((size.X, size.Y, size.Z), (h - l for h, l in zip(hi, lo))):
        assert got == pytest.approx(want * 25.4, rel=1e-4)


def test_ifc_round_trip(built, tmp_path):
    import ifcopenshell
    import ifcopenshell.util.placement as placement

    a = built["steel_shear_tab"]
    path = tmp_path / "tab.ifc"
    a.to_ifc(path)
    f = ifcopenshell.open(str(path))
    assert len(f.by_type("IfcElement")) == len(a.items)
    assert len(f.by_type("IfcBeam")) == 1 and len(f.by_type("IfcColumn")) == 1
    beam = f.by_type("IfcBeam")[0]
    m = placement.get_local_placement(beam.ObjectPlacement)
    want = next(i for i in a.items if i.mark == "BM1").loc.position
    assert m[0][3] == pytest.approx(want.X * 25.4, abs=1e-3)
    assert m[2][3] == pytest.approx(want.Z * 25.4, abs=1e-3)


def test_sample_shapes_match_the_table():
    """The shapes shipped for the samples are the table's own rows, where a table is at hand."""
    import json

    from detailtwin import catalog

    if catalog.table_path() is None:
        pytest.skip("no shape table on this machine")
    for label, row in json.loads(catalog.SAMPLE.read_text()).items():
        got = catalog.w_shape(label)
        assert {k: got[k] for k in catalog.KEYS} == row, label


def test_bar_table_is_self_consistent():
    for size, (d, plf) in REBAR.items():
        solid = 3.141592653589793 / 4 * d * d * 12 * STEEL_PCI
        assert solid == pytest.approx(plf, rel=0.01), size


# ---- planted faults ----------------------------------------------------------------------

def _clone(a: Assembly) -> Assembly:
    b = Assembly(a.id, a.title, a.blurb)
    b.items = [copy.copy(i) for i in a.items]
    for i in b.items:
        i._world = None
    return b


def _shift(item, dx=0.0, dy=0.0, dz=0.0):
    item.loc = Location((dx, dy, dz)) * item.loc
    item._world = None


def test_planted_clash_is_caught(built):
    a = _clone(built["steel_shear_tab"])
    _shift(next(i for i in a.items if i.mark == "B"), dz=0.2)  # a bolt pushed into the side of its hole
    _, clashes = a.interference()
    assert clashes, "a bolt moved 0.2 in. off its hole was not reported"


def test_planted_bar_clash_is_caught(built):
    from detailtwin.families.footing import EMBEDDED

    a = _clone(built["footing_pedestal"])
    _shift(next(i for i in a.items if i.mark == "V1"), dx=0.12, dy=0.12)  # corner bar pushed into the tie bend
    _, clashes = a.interference(allowed=EMBEDDED)
    assert any({x.mark, y.mark} == {"V1", "T1"} for x, y, _ in clashes)


def test_planted_cover_error_is_caught(built):
    from cases.footing_pedestal import SPEC
    from detailtwin.families.footing import cage_checks

    a = _clone(built["footing_pedestal"])
    _shift(next(i for i in a.items if i.mark == "M1"), dz=-1.0)  # one mat bar an inch low
    cage_checks(a, SPEC)
    cover = next(c for c in a.checks if c["what"].startswith("Bottom mat to underside"))
    assert not cover["ok"]
