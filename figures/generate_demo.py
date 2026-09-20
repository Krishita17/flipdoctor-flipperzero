"""Generate figures/demo.gif — an animated full checkup running start to finish.

This is a code-generated animation of the real report content (a Flipper-screen
style frame revealing each subsystem verdict in turn), suitable for the README
until a screen capture from a physical device is available. Requires Pillow.

Run:  python3 figures/generate_demo.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flipdoctor.report import build_report  # noqa: E402
from flipdoctor.evaluate import evaluate_all  # noqa: E402
from sim.simulate import simulate_readings  # noqa: E402

_FIG = os.path.dirname(os.path.abspath(__file__))

# Flipper-ish 128x64 aspect, scaled up.
W, H = 512, 256
BG = (10, 20, 25)
FG = (230, 237, 243)
GREEN = (72, 187, 120)
RED = (255, 107, 107)
YELLOW = (240, 180, 41)
GREY = (160, 174, 192)


def _color(status: str):
    return {
        "PASS": GREEN, "RESPONDS": GREEN, "WARN": YELLOW,
        "INCONCLUSIVE": GREY, "FAIL": RED,
    }.get(status, FG)


def main() -> int:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:
        print(f"[demo] Pillow required: {exc}")
        return 1

    results = evaluate_all(simulate_readings("multi_fault", seed=3))
    report = build_report(results, mode="full", firmware="sim")

    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 14)
        font_b = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        font_b = font

    frames = []

    def frame(revealed: int, header: str):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.text((10, 8), header, fill=FG, font=font_b)
        d.line((10, 30, W - 10, 30), fill=(60, 70, 80))
        y = 40
        for i, r in enumerate(report.results[:revealed]):
            sym = {"PASS": "OK", "RESPONDS": "OK", "WARN": "! ",
                   "INCONCLUSIVE": "~ ", "FAIL": "X "}.get(r.status.value, "? ")
            line = f"[{sym}] {r.subsystem.label:<20} {r.status.value}"
            d.text((14, y), line, fill=_color(r.status.value), font=font)
            y += 18
        return img

    # Intro
    for _ in range(6):
        frames.append(frame(0, "FlipDoctor: running checkup..."))
    # Reveal each subsystem
    for i in range(1, len(report.results) + 1):
        for _ in range(4):
            frames.append(frame(i, "FlipDoctor: running checkup..."))
    # Verdict hold
    for _ in range(16):
        img = frame(len(report.results), f"VERDICT: {report.overall_label}")
        frames.append(img)

    out = os.path.join(_FIG, "demo.gif")
    frames[0].save(
        out, save_all=True, append_images=frames[1:], duration=120, loop=0, optimize=True)
    print(f"[demo] wrote {out} ({len(frames)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
