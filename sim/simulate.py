"""Fault-state result simulator.

Given a named device state, produce a full set of raw readings (one dict per
subsystem) in exactly the shape the on-device HAL would produce. A small
amount of seeded jitter is added to healthy readings so runs look realistic
without changing verdicts.

Usage (from a clean clone, no Flipper needed):

    python3 sim/simulate.py --state healthy
    python3 sim/simulate.py --state ir_rx_fail --json
    python3 sim/simulate.py --list

The mapping from state -> which subsystem is *expected* to be flagged is the
ground truth used by the eval pipeline (``GROUND_TRUTH``).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
from typing import Any, Dict

# Allow running as a script from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flipdoctor.evaluate import evaluate_all  # noqa: E402
from flipdoctor.models import Subsystem  # noqa: E402
from flipdoctor.report import build_report, render_text  # noqa: E402


def _healthy(rng: random.Random) -> Dict[Subsystem, Dict[str, Any]]:
    """A fully healthy device (with realistic jitter that never flips a verdict)."""
    return {
        Subsystem.SUBGHZ: {
            "responds": True,
            "chip_id": "CC1101",
            "loopback_supported": True,
            "loopback_ok": True,
            "rssi_dbm": round(rng.uniform(-95, -70), 1),
        },
        Subsystem.NFC: {
            "responds": True,
            "chip_id": "ST25R3916",
            "field_amplitude": rng.randint(6, 12),
        },
        Subsystem.IR_TX: {"emitted": True},
        Subsystem.IR_RX: {
            "loopback_supported": True,
            "loopback_match_ratio": round(rng.uniform(0.85, 1.0), 2),
            "ir_tx_ok": True,
        },
        Subsystem.GPIO: {
            "self_check_ok": True,
            "jumper_present": True,
            "jumper_loopback_ok": True,
        },
        Subsystem.SD: {
            "detected": True,
            "write_read_match": True,
            "bad_sectors": 0,
            "free_ratio": round(rng.uniform(0.3, 0.9), 2),
            "capacity_mb": 16384,
        },
        Subsystem.BATTERY: {
            "voltage_v": round(rng.uniform(3.85, 4.15), 2),
            "health_pct": rng.randint(92, 100),
            "charging": False,
            "charge_current_ma": 0.0,
        },
        Subsystem.BUTTONS: {"interactive": True, "user_confirmed": True},
        Subsystem.DISPLAY: {"interactive": True, "user_confirmed": True},
    }


# Each fault mutates the healthy baseline. Ground truth = the subsystem(s) a
# correct evaluator must flag as NOT healthy.
def _inject(base: Dict[Subsystem, Dict[str, Any]], state: str) -> Dict[Subsystem, Dict[str, Any]]:
    d = copy.deepcopy(base)
    if state == "healthy":
        pass
    elif state == "nfc_dead":
        d[Subsystem.NFC].update(responds=False, field_amplitude=0)
    elif state == "nfc_coil_weak":
        d[Subsystem.NFC].update(responds=True, field_amplitude=0)
    elif state == "sd_flaky":
        d[Subsystem.SD].update(write_read_match=False)
    elif state == "sd_missing":
        d[Subsystem.SD].update(detected=False)
    elif state == "sd_full":
        d[Subsystem.SD].update(free_ratio=0.005)
    elif state == "sd_aging":
        d[Subsystem.SD].update(bad_sectors=3)
    elif state == "weak_battery":
        d[Subsystem.BATTERY].update(voltage_v=3.15, health_pct=40)
    elif state == "aged_battery":
        d[Subsystem.BATTERY].update(voltage_v=3.7, health_pct=78)
    elif state == "ir_rx_fail":
        d[Subsystem.IR_RX].update(loopback_match_ratio=0.0)
    elif state == "ir_tx_fail":
        d[Subsystem.IR_TX].update(emitted=False)
        d[Subsystem.IR_RX].update(loopback_match_ratio=0.0, ir_tx_ok=False)
    elif state == "gpio_bad":
        d[Subsystem.GPIO].update(self_check_ok=False, jumper_present=True, jumper_loopback_ok=False)
    elif state == "gpio_no_jumper":
        d[Subsystem.GPIO].update(self_check_ok=True, jumper_present=False, jumper_loopback_ok=None)
    elif state == "subghz_dead":
        d[Subsystem.SUBGHZ].update(responds=False)
    elif state == "button_stuck":
        d[Subsystem.BUTTONS].update(user_confirmed=False)
    elif state == "multi_fault":
        d[Subsystem.NFC].update(responds=False, field_amplitude=0)
        d[Subsystem.IR_RX].update(loopback_match_ratio=0.0)
        d[Subsystem.BATTERY].update(voltage_v=3.7, health_pct=80)
    else:
        raise ValueError(f"unknown state: {state}")
    return d


# state -> set of subsystems that should be flagged as NOT healthy.
GROUND_TRUTH: Dict[str, set] = {
    "healthy": set(),
    "nfc_dead": {Subsystem.NFC},
    "nfc_coil_weak": {Subsystem.NFC},
    "sd_flaky": {Subsystem.SD},
    "sd_missing": {Subsystem.SD},
    "sd_full": {Subsystem.SD},
    "sd_aging": {Subsystem.SD},
    "weak_battery": {Subsystem.BATTERY},
    "aged_battery": {Subsystem.BATTERY},
    "ir_rx_fail": {Subsystem.IR_RX},
    "ir_tx_fail": {Subsystem.IR_TX, Subsystem.IR_RX},
    "gpio_bad": {Subsystem.GPIO},
    # No jumper attached is NOT a fault: the device GPIO may be fine, we just
    # can't run the strong check. The honest outcome is RESPONDS/INCONCLUSIVE,
    # so ground truth here is "no fault flagged".
    "gpio_no_jumper": set(),
    "subghz_dead": {Subsystem.SUBGHZ},
    "button_stuck": {Subsystem.BUTTONS},
    "multi_fault": {Subsystem.NFC, Subsystem.IR_RX, Subsystem.BATTERY},
}

FAULT_STATES = list(GROUND_TRUTH.keys())


def simulate_readings(state: str, seed: int = 0) -> Dict[Subsystem, Dict[str, Any]]:
    """Return raw readings for the named device state."""
    if state not in GROUND_TRUTH:
        raise ValueError(f"unknown state {state!r}; choose from {FAULT_STATES}")
    rng = random.Random(seed)
    return _inject(_healthy(rng), state)


def simulate_report(state: str, seed: int = 0, mode: str = "full"):
    """Convenience: readings -> evaluate -> build_report."""
    readings = simulate_readings(state, seed=seed)
    results = evaluate_all(readings)
    return build_report(results, firmware="sim", mode=mode, timestamp="2026-09-19 14:22 UTC")


def _readings_to_jsonable(readings: Dict[Subsystem, Dict[str, Any]]) -> Dict[str, Any]:
    return {sub.value: vals for sub, vals in readings.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="FlipDoctor fault-state simulator")
    ap.add_argument("--state", default="healthy", help="device state to simulate")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for jitter")
    ap.add_argument("--mode", default="full", help="run mode (full/quick/used_buyer)")
    ap.add_argument("--json", action="store_true", help="print report as JSON")
    ap.add_argument("--readings", action="store_true", help="print raw readings as JSON")
    ap.add_argument("--list", action="store_true", help="list available states")
    args = ap.parse_args(argv)

    if args.list:
        for s in FAULT_STATES:
            gt = ", ".join(sorted(x.value for x in GROUND_TRUTH[s])) or "(none)"
            print(f"{s:<16} -> flags: {gt}")
        return 0

    if args.readings:
        readings = simulate_readings(args.state, seed=args.seed)
        print(json.dumps(_readings_to_jsonable(readings), indent=2))
        return 0

    report = simulate_report(args.state, seed=args.seed, mode=args.mode)
    if args.json:
        from flipdoctor.report import to_json

        print(to_json(report))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
