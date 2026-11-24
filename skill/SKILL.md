---
name: detail-twin
description: Model a structural detail or a small frame to scale as exact solids (build123d / OpenCascade) with part marks, dimension sources and checks measured on the geometry, then write STEP, IFC and the interactive detailing page. Use when asked to model, twin or 3D a connection, footing, bar cage, base plate, hold-down, framing detail, or a frame assembled from details; to check a detail for clashes, cover, fit-up or quantities; to cut a section, explode or list the parts of a detail; or to turn a drawing detail into a model. Triggers "detail twin", "twin this detail", "model this detail", "3D this connection", "to-scale model", "clash check", "rebar cage model", "IFC of this detail", "STEP of this connection". Not for structural design or code checks (the code and engine skills own those), not for sensor dashboards (dfos-digital-twin).
---

# Detail Twin

A detail is a Python file that builds an `Assembly` of exact solids in inches. Each part carries a
mark, a material class, its properties and the source of its dimensions. Building the file runs the
checks, writes STEP, IFC and the page payload. Nothing is quoted that the build did not measure.

## Where it lives

Everything is in the detail-twin repository: `src/detailtwin` (library), `cases/`, `models/`, `sheet/`,
`tools/`, `viewer/`, `tests/`. Run every command from the repository root with the project's Python
(`.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere). Outputs go to `out/`.

Read `references/api.md` before writing a case. Read `references/lessons.md` before changing the
library, the exports or the viewer.

## The loop

1. **Fix the spec.** List every size the detail needs. Each one comes from the engineer, a drawing they
   gave, or a table read from a file. A size that is missing and changes the result is theirs to give.
   A size chosen in its place is an assumption: put it in `a.notes` and say it in the hand-off.
2. **Write the case** in `cases/<name>.py`: a `SPEC` dict, `assemble(spec)`, `run_checks(a, spec)`
   and `build(spec=None)` returning the `Assembly`, so a fault can be planted by passing a changed
   spec. `cases/beam_girder_cope.py` and its test file are the pattern. Reuse a family from `detailtwin.families` where one fits. New geometry goes in
   `detailtwin/parts.py` as a canonical solid built once and placed many times.
3. **Write the checks in `build()`**, measured on the solids with `min_distance`, bounding boxes,
   volumes and `a.interference(...)`. One check per thing the detail must satisfy: fit-up gaps,
   seating, cover, spacing, projection, weight per foot against the table, and interference last.
4. **Build**: `python tools/build.py <name>`. Read every line. A FAIL is fixed in the geometry or
   the spec, never by loosening the tolerance or changing what is measured.
5. **Look at it**: `python tools/snapshot.py <id> out/shots/<id>_<view>.png ...`. `--dir` is the
   direction from the focus to the camera, `--span` the view height in inches, `--only` and `--hide`
   take classes or marks, `--size` the pixels. Cuts are open, with no hatched face, and dimensions
   are not drawn, so coincident faces can read wrongly: hide a part to tell. Take the whole
   detail, then each joint close up, then a cut, then exploded. Open each picture and ask what every
   part is doing there. A number comes from the geometry, never from a picture.
6. **Page**: `python tools/make_page.py <id> --out <id>.html`, and open it for the engineer.
7. **Hand off**: what was modelled, the files, every check with its measured value, what no check
   covered, and every assumption.

## Rules

- **Units.** Inches and pounds inside the model, +Z up. STEP and IFC are written in true
  millimetres by the exporters. Never scale by hand.
- **Sources.** The `source` of a part says where its dimensions came from. W shapes come from
  `catalog.w_shape` (a file row). Tables marked `HAND` in `catalog.py` were typed by hand: say so in
  the hand-off every time one is used, until a sourced table with a test replaces it.
- **No recalled code values.** Minimum edge distances, covers, bend diameters, development lengths
  and the like are spec inputs here. Do not name a code clause or quote its limit from memory. A
  code check belongs to the skill that owns that code.
- **A new check must be seen to fail.** Before trusting a check you wrote, plant the fault it guards
  against (move a part, shrink a hole) and see it fail. Keep the planted fault as a test in
  `tests/` when the check will be reused.
- **Embedded by design.** Bars and anchors cast in concrete, and nails in wood, share volume on
  purpose. Pass those class pairs to `a.interference(allowed=[...])`, and nothing else.
- **Simplifications are stated.** Anything drawn simpler than it is (threads as grooves, smooth
  bars) goes in `a.notes`.
- **It is geometry, not design.** Say in the hand-off that nothing was designed for load unless a
  design skill ran.
- **Private data stays local.** A detail from a real job is not published to a page outside this
  computer without the engineer saying so.

## The text-to-cad tools

The text-to-cad `cad` command reads a detail through `Assembly.to_compound()`, which hands it over in
millimetres. Use it for an independent interference check, hidden-line views and, later, drawing
sheets. It sends usage telemetry and updates itself unless both are switched off (`cad telemetry off`, `cad update auto off`).

```bash
cad server start                                  # once
cad run models/<name>.py                          # prints parts, bounds in mm, and the id
cad model interference "$ID"                      # exact, independent of detailtwin's own check
cad model snapshot "$ID" out.png --display hidden-line --camera front
```

Compare the bounds `cad run` prints with the detail's size in inches times 25.4. A mismatch is a
placement or scale fault, fix it before anything else. `models/shear_tab.py` is the pattern.
The text-to-cad repository documents the rest of `cad`. Stop the server (`cad server stop`) before moving or renaming the repository
folder: it holds the folder open.

## The living detail sheet

The sheet is a structural detail sheet (42 x 30 in., true drawing scales) on which every detail box
holds the 2D detail beside a 3D pane with four views: assembled, exploded, section, x-ray. It is
drawn by `sheet/sheet.js` on top of the same viewer, from the same case payloads.

- **What is typed and what is read.** Titles, the sheet number, the sheet notes and where each label
  sits are typed in `sheet/sheet.js`. Dimensions are measured from the parts, callouts are the parts'
  own names and counts, weld sizes are the weld parts' own legs. Never type a dimension or a size.
- **A box** is one entry of `CELLS`: the case index, the box and its two panes, the drawing `scale`
  (paper inches per model inch, one of the standard scales), the 2D view `v2`, an `annot()` that
  returns dimensions, callouts, weld symbols, bolt centre marks, break lines, grid lines, elevation
  tags and detail markers, and the 3D keyframes for the video.
- **Callouts must not cross.** Stack labels so the top label goes to the leftmost anchor when the
  leaders run up and to the right. A short dimension reads outside, away from its neighbour.
- **Interactive page**: `python tools/make_sheet_page.py` writes `out/living_sheet.html` (a fragment
  for a host page) and `out/living_sheet_preview.html` (stand-alone). `docs/index.html` is a copy.
- **Video**: start `python tools/serve.py 8765`, open `preview.html?shot=1&theme=light&dims=0`, load
  `/director.js` then `/sheet.js` in the page, run `__sheet.run('sheet_full', 1920, 1080, 30)`, then
  `python sheet/cut.py sheet_full --blocks sheet --crf 16`. Check stills with `__sheet.still(t, w, h, name)`
  before a full run. No captions or slogans go on a frame. The end card carries the name only.

## Commands

```bash
.venv/Scripts/python.exe tools/build.py <case module> [...]        # checks, out/<id>.json .step .ifc
.venv/Scripts/python.exe tools/snapshot.py <id> out/shots/x.png --dir 1,1.3,0.5 --focus x,y,z --span 20
.venv/Scripts/python.exe tools/snapshot.py <id> out/shots/x.png --xray --cut y:0 --explode 1 --hide concrete
.venv/Scripts/python.exe tools/make_sheet_page.py                         # the interactive detail sheet
.venv/Scripts/python.exe tools/make_page.py <id> [...] --out page.html   # also writes out/preview_page.html, a stand-alone copy
.venv/Scripts/python.exe -m pytest -q                              # the whole suite, about a minute
.venv/Scripts/python.exe tools/serve.py 8765                        # serves out/, then open http://localhost:8765/preview_page.html
```
