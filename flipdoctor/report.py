"""Report generation: turn evaluated results into the deliverable.

Produces the overall verdict, a plain-language text report (the on-screen /
exported checkup), a shareable used-buyer "health certificate", and a JSON
form for save/export to SD and for the eval pipeline.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional

from .models import Report, Status, SubsystemResult


def _make_report_id(results: List[SubsystemResult], timestamp: str) -> str:
    raw = timestamp + "|" + "|".join(
        f"{r.subsystem.value}:{r.status.value}" for r in results
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest().upper()
    return f"FD-{digest[:4]}-{digest[4:8]}"


def build_report(
    results: List[SubsystemResult],
    *,
    device: str = "Flipper Zero",
    firmware: str = "unknown",
    mode: str = "full",
    timestamp: Optional[str] = None,
) -> Report:
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return Report(
        results=results,
        device=device,
        firmware=firmware,
        mode=mode,
        timestamp=ts,
        report_id=_make_report_id(results, ts),
    )


# --------------------------------------------------------------------------
# Renderers
# --------------------------------------------------------------------------
def render_text(report: Report) -> str:
    """Plain-language checkup report (what the app shows / exports)."""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  FlipDoctor — {} CHECKUP".format(report.mode.upper()))
    lines.append(
        "  Device: {}   FW: {}   {}".format(
            report.device, report.firmware, report.timestamp
        )
    )
    lines.append("  Report ID: {}".format(report.report_id))
    lines.append("=" * 60)
    c = report.counts
    lines.append(
        "  OVERALL HEALTH: {}  {}".format(
            report.overall.symbol, report.overall_label
        )
    )
    lines.append(
        "  {} passed  {} responds  {} warn  {} inconclusive  {} failed".format(
            c[Status.PASS.value], c[Status.RESPONDS.value], c[Status.WARN.value],
            c[Status.INCONCLUSIVE.value], c[Status.FAIL.value],
        )
    )
    lines.append("-" * 60)
    for r in report.results:
        acc = " [needs accessory]" if r.needs_accessory else ""
        lines.append(
            "  {} {:<24} {:<12} ({}){}".format(
                r.status.symbol,
                r.subsystem.label,
                r.status.value,
                r.confidence.value,
                acc,
            )
        )
    lines.append("-" * 60)
    lines.append("  DETAILS")
    for r in report.results:
        lines.append("  {} {}: {}".format(r.status.symbol, r.subsystem.label, r.message))
        if r.guidance:
            for chunk in _wrap(r.guidance, 54):
                lines.append("      " + chunk)
    lines.append("=" * 60)
    lines.append("  Honesty note: 'RESPONDS' means alive, not perfect.")
    lines.append("  'INCONCLUSIVE' means we won't guess — see guidance above.")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_certificate(report: Report) -> str:
    """Shareable used-buyer health certificate (evidence, not a guarantee)."""
    w = 58
    lines: List[str] = []
    top = "+" + "-" * w + "+"
    lines.append(top)
    lines.append(_row("FLIPDOCTOR . HEALTH CERTIFICATE", w, center=True))
    lines.append(_row("", w))
    lines.append(_row("Device .... {}".format(report.device), w))
    lines.append(_row("Checked ... {}".format(report.timestamp), w))
    lines.append(_row("Mode ...... {}".format(report.mode), w))
    lines.append(_row("Report ID . {}".format(report.report_id), w))
    lines.append("+" + "-" * w + "+")
    for r in report.results:
        dots = "." * max(1, 30 - len(r.subsystem.label))
        lines.append(
            _row(
                "{} {} {} {}".format(
                    r.subsystem.label, dots, r.status.symbol, r.status.value
                ),
                w,
            )
        )
    lines.append("+" + "-" * w + "+")
    lines.append(_row("VERDICT: {} {}".format(report.overall.symbol, report.overall_label), w))
    lines.append(_row("", w))
    lines.append(_row("Note: reflects the tests run at this moment.", w))
    lines.append(_row("Strong evidence, not a lifetime guarantee.", w))
    lines.append(top)
    return "\n".join(lines)


def to_json(report: Report, *, indent: int = 2) -> str:
    return json.dumps(report.to_dict(), indent=indent)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _wrap(text: str, width: int) -> List[str]:
    words = text.split()
    out: List[str] = []
    cur = ""
    for word in words:
        if len(cur) + len(word) + 1 > width:
            out.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        out.append(cur)
    return out


def _row(text: str, width: int, center: bool = False) -> str:
    text = text[: width - 2]
    if center:
        pad = width - len(text)
        left = pad // 2
        right = pad - left
        return "|" + " " * left + text + " " * right + "|"
    return "| " + text.ljust(width - 2) + " |"
