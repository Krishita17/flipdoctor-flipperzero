"""Generate all rendered figures for the README.

Outputs (all code-generated, none hand-drawn):
  figures/hero_report.png         - the sample health report (hero asset)
  figures/health_certificate.png  - the used-buyer certificate
  figures/architecture.png        - the system architecture diagram

The accuracy/coverage charts are produced by ``eval/run_eval.py``.

Run:  python3 figures/generate_figures.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flipdoctor.report import render_certificate, render_text  # noqa: E402
from sim.simulate import simulate_report  # noqa: E402

_FIG = os.path.dirname(os.path.abspath(__file__))


def _require_mpl():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _text_to_png(text: str, path: str, title_color: str = "#1a202c",
                 bg: str = "#0f1419", fg: str = "#e6edf3") -> None:
    plt = _require_mpl()
    lines = text.split("\n")
    # Colorize status glyphs a little for the hero image.
    fig_h = max(2.0, 0.22 * len(lines) + 0.4)
    fig_w = max(7.0, 0.098 * max(len(l) for l in lines) + 0.6)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.axis("off")
    y = 1.0
    dy = 1.0 / (len(lines) + 1)
    for line in lines:
        color = fg
        if "✗" in line or "FAIL" in line or "FAULT" in line:
            color = "#ff6b6b"
        elif "⚠" in line or "WARN" in line or "ATTENTION" in line:
            color = "#f0b429"
        elif "~" in line[:6] or "INCONCL" in line:
            color = "#a0aec0"
        elif "✓" in line or "PASS" in line or "RESPONDS" in line or "HEALTHY" in line:
            color = "#48bb78"
        ax.text(0.01, y, line, family="monospace", fontsize=9.5,
                color=color, va="top", ha="left", transform=ax.transAxes)
        y -= dy
    fig.tight_layout(pad=0.4)
    fig.savefig(path, dpi=150, facecolor=bg, bbox_inches="tight")
    plt.close(fig)
    print(f"[figures] wrote {path}")


def make_hero() -> None:
    report = simulate_report("multi_fault", seed=3)
    _text_to_png(render_text(report), os.path.join(_FIG, "hero_report.png"))


def make_certificate() -> None:
    report = simulate_report("healthy", seed=7, mode="used_buyer")
    _text_to_png(
        render_certificate(report),
        os.path.join(_FIG, "health_certificate.png"),
        bg="#111827", fg="#e6edf3",
    )


def make_architecture() -> None:
    plt = _require_mpl()
    import matplotlib.patches as mpatches

    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    def box(x, y, w, h, text, color):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.08",
            linewidth=1.5, edgecolor="#2d3748", facecolor=color)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=9, wrap=True)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#4a5568", lw=1.6))

    box(3.2, 8.7, 3.6, 0.9, "User taps\n\"Run checkup\"", "#e2e8f0")
    box(2.6, 7.0, 4.8, 1.1, "Test orchestrator\n(sequences tests, guides user)", "#bee3f8")
    box(0.4, 4.9, 9.2, 1.3,
        "Subsystem test modules\nSub-GHz . NFC . IR TX/RX . GPIO . SD . Battery . Buttons/Display",
        "#c6f6d5")
    box(0.6, 3.0, 4.0, 1.1, "Result evaluator\npass/fail/warn/inconclusive\n+ confidence", "#fefcbf")
    box(5.4, 3.0, 4.0, 1.1, "Report generator\nverdict . guidance . export", "#fed7aa")
    box(0.6, 1.0, 4.0, 1.0, "Modes\nFull . Quick . Used-buyer . Single", "#e9d8fd")
    box(5.4, 1.0, 4.0, 1.0, "Baseline compare\nre-run -> detect degradation", "#fbb6ce")

    arrow(5.0, 8.7, 5.0, 8.1)
    arrow(5.0, 7.0, 5.0, 6.2)
    arrow(3.0, 4.9, 2.6, 4.1)
    arrow(5.0, 4.9, 6.0, 4.1)
    arrow(4.6, 3.55, 5.4, 3.55)
    arrow(2.6, 3.0, 2.6, 2.0)
    arrow(7.4, 3.0, 7.4, 2.0)

    ax.set_title("FlipDoctor — system architecture", fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(_FIG, "architecture.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[figures] wrote {os.path.join(_FIG, 'architecture.png')}")


def main() -> int:
    try:
        _require_mpl()
    except Exception as exc:
        print(f"[figures] matplotlib required: {exc}")
        return 1
    make_hero()
    make_certificate()
    make_architecture()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
