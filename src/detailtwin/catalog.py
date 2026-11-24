"""Catalog dimensions, each with the place it came from.

W shapes are read from a shape table. Point the environment variable DETAILTWIN_AISC_XLSX, or the
key "aisc_xlsx" in data/local.json, at a copy of the AISC shapes database spreadsheet and any W shape
is read from its own row. Without one, the three shapes the samples use are read from the small
table shipped with the package.

The fastener, bar and lumber tables below were typed by hand for the samples and are marked HAND.
They are to be replaced by sourced tables, each with a test.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_PKG = Path(__file__).resolve().parent
_ROOT = _PKG.parents[1]
SAMPLE = _PKG / "data" / "w_shapes_sample.json"
LOCAL = _ROOT / "data" / "local.json"  # not committed
CACHE = _ROOT / "data" / "aisc_w_cache.json"  # not committed
KEYS = ("W", "A", "d", "bf", "tw", "tf", "kdes", "k1")
HAND = "Typed by hand for the sample, not yet read from a sourced table"


def table_path() -> Path | None:
    p = os.environ.get("DETAILTWIN_AISC_XLSX")
    if not p and LOCAL.exists():
        p = json.loads(LOCAL.read_text()).get("aisc_xlsx")
    return Path(p) if p and Path(p).exists() else None


def w_shape(label: str) -> dict:
    xlsx = table_path()
    if xlsx is None:
        sample = json.loads(SAMPLE.read_text())
        if label not in sample:
            raise KeyError(f"{label} is not in the sample table ({', '.join(sample)}). Set DETAILTWIN_AISC_XLSX "
                           "to an AISC shapes database spreadsheet to read any W shape.")
        s = dict(sample[label])
        s["source"] = f"Sample shape table shipped with detail-twin ({label})"
    else:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        if label not in cache:
            import openpyxl

            ws = openpyxl.load_workbook(xlsx, read_only=True, data_only=True).worksheets[0]
            rows = ws.iter_rows(values_only=True)
            col = {h: i for i, h in enumerate(next(rows))}
            for n, r in enumerate(rows, start=2):
                if r[col["AISC_Manual_Label"]] == label:
                    cache[label] = {k: float(r[col[k]]) for k in KEYS}
                    cache[label]["row"] = n
                    break
            else:
                raise KeyError(label)
            CACHE.parent.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(cache, indent=1))
        s = dict(cache[label])
        s["source"] = f"AISC shapes table file, row {s['row']} ({label})"
    s["label"] = label
    return s


# Heavy hex structural bolt, heavy hex nut and hardened washer, inches. HAND.
#   F  width across flats (bolt head and nut), H head height, Hn nut height,
#   Lt thread length, tpi threads per inch (UNC), wod / wid / wt washer OD, ID, thickness.
BOLT = {
    "5/8": dict(d=0.625, F=1.0625, H=25 / 64, Hn=39 / 64, Lt=1.25, tpi=11, wod=1.3125, wid=0.6875, wt=0.15),
    "3/4": dict(d=0.750, F=1.2500, H=15 / 32, Hn=47 / 64, Lt=1.375, tpi=10, wod=1.468, wid=0.8125, wt=0.15),
    "7/8": dict(d=0.875, F=1.4375, H=35 / 64, Hn=55 / 64, Lt=1.50, tpi=9, wod=1.75, wid=0.9375, wt=0.15),
}

# Deformed bar, nominal diameter (in) and weight (lb/ft). HAND.
REBAR = {"#3": (0.375, 0.376), "#4": (0.500, 0.668), "#5": (0.625, 1.043),
         "#6": (0.750, 1.502), "#7": (0.875, 2.044), "#8": (1.000, 2.670)}

# Dressed lumber, actual size (in). HAND.
LUMBER = {"2x4": (1.5, 3.5), "2x6": (1.5, 5.5), "4x4": (3.5, 3.5), "4x6": (3.5, 5.5)}
