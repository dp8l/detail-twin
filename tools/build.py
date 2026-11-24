"""Build the sample cases: checks to the console, payload JSON, STEP and IFC files."""
from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CASES = ["steel_shear_tab", "footing_pedestal", "wood_holddown", "portal_bent", "beam_girder_cope"]


def main(names):
    OUT.mkdir(exist_ok=True)
    payload = []
    for name in names:
        t0 = time.time()
        a = importlib.import_module(f"cases.{name}").build()
        fid = a.mesh_fidelity()
        a.check("Display mesh volume against exact solid volume, worst part", f"{fid * 100:.3f}% off",
                "under 0.5%", fid < 0.005)
        p = a.payload()
        a.to_step(OUT / f"{a.id}.step")
        f = a.to_ifc(OUT / f"{a.id}.ifc")
        import ifcopenshell

        back = ifcopenshell.open(str(OUT / f"{a.id}.ifc"))
        n_back = len(back.by_type("IfcElement"))
        p["files"] = {"step": f"{a.id}.step", "ifc": f"{a.id}.ifc"}
        payload.append(p)
        print(f"\n=== {a.title}  [{time.time() - t0:.1f} s]  parts {p['stats']['parts']}, unique solids "
              f"{p['stats']['unique']}, triangles {p['stats']['tris']}, IFC elements re-read {n_back}")
        for c in a.checks:
            print(f"  {'PASS' if c['ok'] else 'FAIL'}  {c['what']}: {c['model']}  |  {c['ref']}  {c['note']}")
        (OUT / f"{a.id}.json").write_text(json.dumps(p))
    return payload


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main(sys.argv[1:] or CASES)
