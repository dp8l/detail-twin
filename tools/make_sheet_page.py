"""Build the interactive living detail sheet as one self-contained page.

    python tools/make_sheet_page.py            out/living_sheet.html and out/living_sheet_preview.html

The page carries the viewer (kept off screen as the 3D engine), the case payloads, and the three
sheet scripts. `living_sheet.html` is the fragment a host wraps in its own page head;
`living_sheet_preview.html` is the same thing with a head, to open straight from disk or a server.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["shear_tab", "footing", "holddown", "portal", "beam_girder_cope"]  # the sheet indexes cases in this order
STYLE = """<style>
html, body { height: 100%; margin: 0; overflow: hidden; background: #cbd0d6; }
.app { position: fixed !important; left: -300vw; top: 0; width: 1400px !important; height: 900px !important; visibility: hidden; }
</style>"""


def main():
    cases = [json.loads((ROOT / "out" / f"{i}.json").read_text()) for i in ORDER]
    data = json.dumps(cases, separators=(",", ":")).replace("</", "<\\/")
    html = (ROOT / "viewer" / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/", data)
    html = html.replace("<title>Detail Twin Samples</title>", "<title>Living Detail Sheet</title>", 1)
    first = '<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"></script>'
    assert first in html
    html = html.replace(first, "<script>window.DT_EMBED = true;</script>\n" + first, 1)
    scripts = "".join(f"<script>\n{(ROOT / 'sheet' / n).read_text(encoding='utf-8')}\n</script>\n" for n in ("director.js", "sheet.js", "app.js"))
    html = html + "\n" + STYLE + "\n" + scripts
    out = ROOT / "out" / "living_sheet.html"
    out.write_text(html, encoding="utf-8")
    head = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, '
            'initial-scale=1, viewport-fit=cover"></head><body>')
    (ROOT / "out" / "living_sheet_preview.html").write_text(head + html + "</body></html>", encoding="utf-8")
    print(out, f"{len(html) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
