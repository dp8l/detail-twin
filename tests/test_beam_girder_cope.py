"""Coped beam to girder web: every check passes as specified, and each check fails on a planted fault.

Three ways of planting a fault are used. A size in the spec is changed and the whole case rebuilt
(a clearance must then fail on its own). The geometry is built to one spec and checked against the
real one (an "as built" check must then fail). One placed part is moved (a fit-up check must fail).
"""
from __future__ import annotations

import copy

import pytest
from build123d import Location

from cases.beam_girder_cope import SPEC, assemble, build, run_checks
from detailtwin.core import Assembly
from detailtwin.parts import cope, w_section


def _check(a, start):
    return next(c for c in a.checks if c["what"].startswith(start))


def _fails(a, *starts):
    return all(not _check(a, s)["ok"] for s in starts)


@pytest.fixture(scope="module")
def good():
    return build()


def _moved(good, mark, which=0, dx=0.0, dy=0.0, dz=0.0):
    """The good assembly with one part moved, checked again against the real spec."""
    a = Assembly(good.id, good.title, good.blurb)
    a.items = [copy.copy(i) for i in good.items]
    for i in a.items:
        i._world = None
    it = [i for i in a.items if i.mark == mark][which]
    it.loc = Location((dx, dy, dz)) * it.loc
    run_checks(a, SPEC)
    return a


def _built_wrong(**fault):
    """Geometry built to a faulty spec, checked against the real one."""
    a = assemble(dict(SPEC, **fault))
    run_checks(a, SPEC)
    return a


def test_every_check_passes(good):
    failed = [c for c in good.checks if not c["ok"]]
    assert len(good.checks) >= 25 and not failed, failed


def test_cope_builder_removes_what_it_should():
    """Flange, web strip and both fillets over the cope length, less the metal left in the corner radius."""
    d, bf, tf, tw, k, c, dc = 16.0, 7.0, 0.505, 0.305, 0.907, 4.0, 1.25
    full = w_section(d, bf, tf, tw, k, 36.0)
    square = cope(full, d, c, dc, 0.0)
    r = k - tf
    want = c * (bf * tf + (dc - tf) * tw + 2 * r * r * (1 - 3.141592653589793 / 4))
    assert full.volume - square.volume == pytest.approx(want, rel=1e-6)
    rounded = cope(full, d, c, dc, 0.5)
    assert 0 < rounded.volume - square.volume < 0.5 * 0.5 * (tw + 2 * r)  # the corner keeps a sliver of metal
    far = cope(full, d, c, dc, 0.5, z_end=36.0, into=-1, top=False)  # the other end, bottom flange
    assert far.volume == pytest.approx(rounded.volume, rel=1e-9)


# ---- planted faults: the cope against the girder flange -----------------------------------

def test_short_cope_is_reported():
    a = build(dict(cope_len=2.0))  # the beam flange runs 0.575 in. into the girder flange
    assert _fails(a, "Cope, horizontal clearance", "Cope, vertical clearance below the girder flange",
                  "Beam to girder, clear gap", "Interference")
    assert _check(a, "Cope, horizontal clearance")["model"].startswith("-0.5750")


def test_shallow_cope_is_reported():
    a = build(dict(cope_depth=0.75))  # clear of the flange, but the cut is above the bottom of the fillet
    assert _fails(a, "Cope, vertical clearance below the girder fillet")
    assert _check(a, "Cope, vertical clearance below the girder flange")["ok"]
    a = build(dict(cope_depth=0.25))  # the cut does not get below the girder flange
    assert _fails(a, "Cope, vertical clearance below the girder flange")


@pytest.mark.parametrize("fault", [dict(cope_len=3.5), dict(cope_depth=1.0), dict(cope_r=0.25), dict(cope_r=0.0)])
def test_cope_not_cut_to_spec_is_reported(fault):
    assert _fails(_built_wrong(**fault), "Cope as cut")


# ---- planted faults: members and connection -----------------------------------------------

def test_beam_out_of_place_is_reported(good):
    assert _fails(_moved(good, "BM1", dx=0.125), "Beam to girder, clear gap", "Bolt shank to web hole")
    assert _fails(_moved(good, "BM1", dz=-0.0625), "Top of beam against top of girder")


def test_tab_out_of_place_is_reported(good):
    assert _fails(_moved(good, "PL1", dx=0.05), "Tab seated on the girder web")
    assert _fails(_moved(good, "PL1", dy=0.05), "Tab against the +Y face of the beam web")


def test_bolt_out_of_place_is_reported(good):
    a = _moved(good, "B", which=1, dz=0.02)
    assert _fails(a, "Bolt shank to web hole", "Bolt shank to tab hole", "Bolt line from the girder web face")
    assert _fails(_moved(good, "B", which=0, dy=0.1), "Bolt heads seated on the tab")
    assert _fails(_moved(good, "N", which=2, dy=-0.1), "Washer on the beam web and nut on the washer")


def test_weld_out_of_place_is_reported(good):
    a = _moved(good, "W1", which=1, dx=0.25)  # the weld between tab and beam end, pushed onto the beam end
    assert _fails(a, "Weld on the beam-web side of the tab", "Fillet welds, tab to girder web")


@pytest.mark.parametrize("fault, check", [
    (dict(hole=7 / 8), "Hole diameters"),
    (dict(tab_w=4.0), "Tab as built"),
    (dict(tab_w=4.0), "Tab, hole centre to edge"),
    (dict(edge_v=1.25), "Tab, hole centre to edge"),
    (dict(pitch=2.5), "Bolt line from the girder web face"),
])
def test_connection_not_built_to_spec_is_reported(fault, check):
    assert _fails(_built_wrong(**fault), check)


def test_spec_that_cannot_work_is_reported():
    assert _fails(build(dict(first_bolt=2.5)), "Beam web, hole centre to beam end")  # 1 1/4 in. to the coped edge
    assert _fails(build(dict(bolt_len=1.5)), "Bolt end beyond the nut")
