# /// script
# dependencies = ["../"]
# ///
"""Coped beam to girder web as a text-to-cad model: `cad run models/beam_girder_cope.py` from the repository root.

The detail is built in inches by detailtwin and handed to cad in millimetres.
Check: cad model interference "$ID"
"""
import sys
from pathlib import Path

import build123d as bd  # noqa: F401  (tells cad this script needs the build123d integration)
from cad import model

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cases.beam_girder_cope import build  # noqa: E402


@model
def beam_girder_cope():
    return build().to_compound()


if __name__ == "__main__":
    beam_girder_cope()
