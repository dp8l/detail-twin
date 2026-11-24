# /// script
# dependencies = ["../"]
# ///
"""Sample 1 as a text-to-cad model: `cad run models/shear_tab.py` from the repository root.

The detail is built in inches by detailtwin and handed to cad in millimetres.
Check: cad model interference "$ID"
"""
import sys
from pathlib import Path

import build123d as bd  # noqa: F401  (tells cad this script needs the build123d integration)
from cad import model

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cases.steel_shear_tab import build  # noqa: E402


@model
def shear_tab():
    return build().to_compound()


if __name__ == "__main__":
    shear_tab()
