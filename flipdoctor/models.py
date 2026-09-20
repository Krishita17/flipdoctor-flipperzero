"""Core data model for FlipDoctor.

Everything is a plain dataclass/enum so results serialize cleanly to JSON for
export to SD and for the eval pipeline. No hardware imports live here.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class Status(enum.Enum):
    """The honest verdict for a single test.

    ``RESPONDS`` is intentionally distinct from ``PASS``: it means the
    subsystem is alive and answering, but the self-test cannot prove full
    correctness without an external accessory. Reporting ``RESPONDS`` instead
    of ``PASS`` is a core part of the honesty layer.
    """

    PASS = "PASS"
    RESPONDS = "RESPONDS"
    WARN = "WARN"
    INCONCLUSIVE = "INCONCLUSIVE"
    FAIL = "FAIL"

    @property
    def is_healthy(self) -> bool:
        """Whether this status counts as 'no fault detected'."""
        return self in (Status.PASS, Status.RESPONDS)

    @property
    def symbol(self) -> str:
        return {
            Status.PASS: "✓",          # check
            Status.RESPONDS: "✓",
            Status.WARN: "⚠",          # warning
            Status.INCONCLUSIVE: "~",
            Status.FAIL: "✗",          # cross
        }[self]


class Confidence(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Subsystem(enum.Enum):
    SUBGHZ = "sub_ghz"
    NFC = "nfc"
    IR_TX = "ir_tx"
    IR_RX = "ir_rx"
    GPIO = "gpio"
    SD = "sd"
    BATTERY = "battery"
    BUTTONS = "buttons"
    DISPLAY = "display"

    @property
    def label(self) -> str:
        return {
            Subsystem.SUBGHZ: "Sub-GHz radio",
            Subsystem.NFC: "NFC / RFID coil",
            Subsystem.IR_TX: "IR transmitter",
            Subsystem.IR_RX: "IR receiver",
            Subsystem.GPIO: "GPIO pins",
            Subsystem.SD: "SD card",
            Subsystem.BATTERY: "Battery",
            Subsystem.BUTTONS: "Buttons / D-pad",
            Subsystem.DISPLAY: "Display / LED / vibro",
        }[self]

    @property
    def self_contained(self) -> bool:
        """True if a definitive result needs no external accessory.

        GPIO and IR RX are the honest exceptions: they *can* run a self-check,
        but a definitive result is stronger with a loopback jumper / known IR
        target. Those are labeled 'needs accessory' in the report.
        """
        return self not in (Subsystem.GPIO,)


@dataclass
class SubsystemResult:
    """The evaluated outcome for one subsystem."""

    subsystem: Subsystem
    status: Status
    confidence: Confidence
    message: str
    guidance: str = ""
    needs_accessory: bool = False
    readings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem": self.subsystem.value,
            "label": self.subsystem.label,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "message": self.message,
            "guidance": self.guidance,
            "needs_accessory": self.needs_accessory,
            "readings": self.readings,
        }


@dataclass
class Report:
    """A full checkup: metadata + per-subsystem results + overall verdict."""

    results: List[SubsystemResult]
    device: str = "Flipper Zero"
    firmware: str = "unknown"
    mode: str = "full"
    timestamp: str = ""
    report_id: str = ""

    # ---- derived counts -------------------------------------------------
    @property
    def counts(self) -> Dict[str, int]:
        c = {s.value: 0 for s in Status}
        for r in self.results:
            c[r.status.value] += 1
        return c

    @property
    def overall(self) -> Status:
        """Aggregate verdict.

        Any FAIL -> FAIL. Else any WARN/INCONCLUSIVE -> WARN (needs
        attention). Else healthy -> PASS. We never upgrade a device to PASS
        while anything is unresolved.
        """
        statuses = {r.status for r in self.results}
        if Status.FAIL in statuses:
            return Status.FAIL
        if Status.WARN in statuses or Status.INCONCLUSIVE in statuses:
            return Status.WARN
        return Status.PASS

    @property
    def overall_label(self) -> str:
        return {
            Status.PASS: "HEALTHY",
            Status.WARN: "NEEDS ATTENTION",
            Status.FAIL: "FAULT DETECTED",
        }.get(self.overall, "NEEDS ATTENTION")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "firmware": self.firmware,
            "mode": self.mode,
            "timestamp": self.timestamp,
            "report_id": self.report_id,
            "overall": self.overall.value,
            "overall_label": self.overall_label,
            "counts": self.counts,
            "results": [r.to_dict() for r in self.results],
        }
