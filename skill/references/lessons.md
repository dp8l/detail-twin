# Traps already paid for

Each of these cost time on 2026-11-23. Read before touching the library, the exports or the viewer.

## Scale and units
- **STEP.** `export_step` without `unit=Unit.IN` writes inch numbers under a millimetre label, so the
  file opens 25.4 times too small. With it, the writer converts and the file holds true millimetres.
  `tests/test_cases.py::test_step_is_to_scale` re-reads the file and holds this.
- **`Shape.scale` leaves the placement alone.** Scaling a placed solid scales its geometry in its own
  frame and keeps the offset in inches. `to_compound` scales the canonical solid and the translation
  separately. The symptom was `cad run` printing bounds of 1,047 x 254 x 1,496 mm for a detail that
  is 1,181 x 254 x 1,219 mm.
- **IFC** is written in millimetres with the mesh and the placement both multiplied by 25.4.

## Checks
- A check that measures to the wrong feature passes for the wrong reason. The first bolt-to-hole
  check measured to the plate the head bears on and read 0. Measure to the part the shank passes
  through without touching.
- A nail edge-distance check measured to the head rim, read 0.675 against 0.750 and was passed by a
  loose tolerance. Measure centre to edge, and keep tolerances at 1e-3 in.
- A corner bar sits inside the tie bend, not against the tie's straight faces. Its centre is at
  `inner - r_in + (r_in - db/2)/sqrt(2)` from the pedestal centre. Placed at `inner - db/2` it
  clashes with the bend. `test_planted_bar_clash_is_caught` holds this.
- Anchor rods, their washers and nuts need room from the column flanges and welds. A 4-rod pattern
  on the flange tips clashes. The sample puts the rods inside the flanges.

## Viewer
- three.js r147 treats material colours as linear. Convert every hex colour with
  `convertSRGBToLinear()` or steel renders nearly white.
- The cut side is chosen from the camera position when the section is switched on. Set the camera
  first, then cut.
- Dimensions that measure removed geometry are hidden while a cut is on.
- The page is published without a viewport meta of its own. Use `out/preview.html` to test a phone
  width locally.
