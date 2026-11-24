"""Join the rendered blocks of a walkthrough into one clip.

    python sheet/cut.py low                      out/video/low.mp4 from out/video/low/<block>/f_*.jpg
    python sheet/cut.py full --crf 16
    python sheet/cut.py low --blocks tab,footing --name low_trim

Blocks join with a 0.35 s fade. A silent audio track is added and the file is written faststart.
A contact sheet at one frame a second is written beside the clip.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["tab", "footing", "holddown", "bent", "cope"]
FADE = 0.35


def ffmpeg() -> str:
    """The first ffmpeg on PATH that is version 5 or newer (Anaconda ships an old 4.3)."""
    if os.environ.get("DETAILTWIN_FFMPEG"):
        return os.environ["DETAILTWIN_FFMPEG"]
    for d in os.environ["PATH"].split(os.pathsep):
        exe = Path(d) / "ffmpeg.exe"
        if exe.exists():
            out = subprocess.run([str(exe), "-version"], capture_output=True, text=True).stdout
            m = re.search(r"ffmpeg version n?(\d+)", out)
            if m and int(m.group(1)) >= 5:
                return str(exe)
    raise SystemExit("no ffmpeg of version 5 or newer on PATH")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--blocks", default=",".join(ORDER))
    ap.add_argument("--name", default=None)
    a = ap.parse_args()
    src = ROOT / "out" / "video" / a.tag
    blocks = [b for b in a.blocks.split(",") if b]
    counts = [len(list((src / b).glob("f_*.jpg"))) for b in blocks]
    assert all(counts), dict(zip(blocks, counts))
    durs = [n / a.fps for n in counts]
    cmd = [ffmpeg(), "-y", "-loglevel", "error"]
    for b in blocks:
        cmd += ["-framerate", str(a.fps), "-i", str(src / b / "f_%05d.jpg")]
    cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    parts, last, t = [], "[0:v]", durs[0]
    for k in range(1, len(blocks)):
        out = f"[v{k}]"
        parts.append(f"{last}[{k}:v]xfade=transition=fade:duration={FADE}:offset={t - FADE:.4f}{out}")
        last, t = out, t + durs[k] - FADE
    parts.append(f"{last}format=yuv420p[v]")
    out_path = ROOT / "out" / "video" / f"{a.name or a.tag}.mp4"
    cmd += ["-filter_complex", ";".join(parts), "-map", "[v]", "-map", f"{len(blocks)}:a", "-t", f"{t:.4f}",
            "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-r", str(a.fps), "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart", str(out_path)]
    subprocess.run(cmd, check=True)
    cols = 8
    rows = -(-int(t + 1) // cols)
    sheet = out_path.with_name(out_path.stem + "_sheet.jpg")
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(out_path), "-vf", f"fps=1,scale=480:-1,tile={cols}x{rows}",
                    "-frames:v", "1", "-q:v", "3", str(sheet)], check=True)
    print(f"{out_path}  {t:.2f} s  blocks " + ", ".join(f"{b} {d:.2f}" for b, d in zip(blocks, durs)))
    print(sheet)


if __name__ == "__main__":
    main()
