"""FlipDoctor — one-tap health & self-diagnostics for the Flipper Zero.

This package holds the *portable* diagnostic core: the data model, the
evaluator (raw readings -> pass/fail/warn/inconclusive + confidence), the
report generator, and the run modes. It is deliberately hardware-free so the
whole pipeline runs from a clean clone via the fault simulator (see ``sim/``)
and can be validated against known fault states (see ``eval/``).

The on-device Flipper application (C, in ``src/flipper/``) mirrors this same
logic and feeds it real readings collected from the hardware HAL.

Sole author and contributor: Krishita Sanjay Choksi.
"""

from .models import (
    Confidence,
    Report,
    Status,
    Subsystem,
    SubsystemResult,
)
from .evaluate import evaluate_all, evaluate_subsystem
from .report import build_report, render_certificate, render_text

__all__ = [
    "Confidence",
    "Report",
    "Status",
    "Subsystem",
    "SubsystemResult",
    "evaluate_all",
    "evaluate_subsystem",
    "build_report",
    "render_certificate",
    "render_text",
]

__version__ = "0.1.0"
