"""Inject the case payloads into the viewer template and write the sample page."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHORT = {"shear_tab": "Shear tab", "footing": "Footing and pedestal", "holddown": "Shear wall hold-down",
         "portal": "One-bay bent", "beam_girder_cope": "Coped beam to girder"}


def main(ids):
    name = "detail_twin_samples.html"
    if "--out" in ids:
        k = ids.index("--out")
        name = ids[k + 1]
        ids = ids[:k] + ids[k + 2:]
    cases = []
    for i in ids:
        c = json.loads((ROOT / "out" / f"{i}.json").read_text())
        c["short"] = SHORT.get(i, c["title"])
        cases.append(c)
    data = json.dumps(cases, separators=(",", ":")).replace("</", "<\\/")
    html = (ROOT / "viewer" / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/", data)
    out = ROOT / "out" / name
    out.write_text(html, encoding="utf-8")
    # local preview with the same head the publish step adds
    head = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, '
            'initial-scale=1, viewport-fit=cover"><style>body{margin:0;font:14px system-ui}[hidden]{display:none!important}'
            'img{max-width:100%}</style></head><body>')
    (ROOT / "out" / ("preview.html" if name == "detail_twin_samples.html" else "preview_" + name)).write_text(head + html + "</body></html>", encoding="utf-8")
    print(out, f"{len(html) / 1e6:.2f} MB")


if __name__ == "__main__":
    main(sys.argv[1:])
