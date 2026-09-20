"""Run modes and baseline comparison.

Modes select *which* subsystems are exercised and how the report is framed:

* ``full``       — every subsystem.
* ``quick``      — fast, fully self-contained subset.
* ``used_buyer`` — the pre-purchase verification flow (drives the certificate).
* ``single``     — one subsystem only.

Baseline compare diffs two reports to catch degradation over time.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .models import Report, Status, Subsystem, SubsystemResult

# Subsystems that need no external accessory and are non-interactive: safe for
# the "quick" self-contained subset.
QUICK_SUBSYSTEMS = [
    Subsystem.SD,
    Subsystem.BATTERY,
    Subsystem.SUBGHZ,
    Subsystem.NFC,
    Subsystem.IR_TX,
    Subsystem.IR_RX,
]

FULL_SUBSYSTEMS = list(Subsystem)

# Used-buyer flow prioritizes the things a buyer most wants proven, and pushes
# for the stronger GPIO jumper check.
USED_BUYER_SUBSYSTEMS = list(Subsystem)


def subsystems_for_mode(mode: str, single: Subsystem = None) -> List[Subsystem]:
    if mode == "quick":
        return list(QUICK_SUBSYSTEMS)
    if mode == "single":
        if single is None:
            raise ValueError("mode 'single' requires a subsystem")
        return [single]
    if mode in ("full", "used_buyer"):
        return list(FULL_SUBSYSTEMS)
    raise ValueError(f"unknown mode: {mode}")


def compare_baseline(baseline: Report, current: Report) -> Dict[str, Any]:
    """Diff two reports to surface degradation or recovery.

    Returns a dict with per-subsystem transitions and an overall assessment.
    Degradation = a subsystem moved from a healthier status to a worse one.
    """
    severity = {
        Status.PASS: 0,
        Status.RESPONDS: 1,
        Status.WARN: 2,
        Status.INCONCLUSIVE: 2,
        Status.FAIL: 3,
    }
    base = {r.subsystem: r for r in baseline.results}
    changes: List[Dict[str, Any]] = []
    degraded = 0
    improved = 0
    for r in current.results:
        b = base.get(r.subsystem)
        if b is None:
            continue
        delta = severity[r.status] - severity[b.status]
        if delta != 0:
            direction = "degraded" if delta > 0 else "improved"
            if delta > 0:
                degraded += 1
            else:
                improved += 1
            changes.append(
                {
                    "subsystem": r.subsystem.value,
                    "label": r.subsystem.label,
                    "from": b.status.value,
                    "to": r.status.value,
                    "direction": direction,
                }
            )
    if degraded:
        assessment = f"Degradation detected in {degraded} subsystem(s) since baseline."
    elif improved:
        assessment = f"{improved} subsystem(s) improved since baseline; none degraded."
    else:
        assessment = "No change since baseline — device is stable."
    return {
        "baseline_id": baseline.report_id,
        "current_id": current.report_id,
        "degraded": degraded,
        "improved": improved,
        "changes": changes,
        "assessment": assessment,
    }
