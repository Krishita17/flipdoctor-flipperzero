"""The result evaluator: raw readings -> honest verdict + confidence.

This is the trust-critical component. Each subsystem has a small, explicit
rule set. The guiding principle: never emit a false PASS or FAIL. When a
self-test can only prove "alive", emit ``RESPONDS``; when the evidence is
insufficient, emit ``INCONCLUSIVE`` with a concrete next step.

Every function takes a plain ``readings`` dict (produced on-device by the HAL,
or by the fault simulator off-device) and returns a :class:`SubsystemResult`.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .models import Confidence, Status, Subsystem, SubsystemResult
from .thresholds import load_thresholds, match_known_issue


def _with_known_issue(result: SubsystemResult) -> SubsystemResult:
    note = match_known_issue(result.subsystem.value, result.readings)
    if note:
        result.guidance = (result.guidance + " " + note).strip()
    return result


# --------------------------------------------------------------------------
# Per-subsystem evaluators
# --------------------------------------------------------------------------
def _eval_subghz(r: Dict[str, Any], th: Dict[str, Any]) -> SubsystemResult:
    t = th["subghz"]
    if not r.get("responds"):
        return SubsystemResult(
            Subsystem.SUBGHZ, Status.FAIL, Confidence.HIGH,
            "Sub-GHz transceiver did not respond.",
            "The CC1101 radio is not answering on SPI. This usually indicates a "
            "radio front-end fault. Re-run after a reboot; if it persists the "
            "device likely needs service.",
            readings=r,
        )
    if r.get("chip_id") != t["expect_chip_id"]:
        return SubsystemResult(
            Subsystem.SUBGHZ, Status.INCONCLUSIVE, Confidence.MEDIUM,
            f"Radio responded but reported an unexpected chip id "
            f"({r.get('chip_id')!r}).",
            "Could be a firmware/HAL mismatch rather than hardware. Update "
            "firmware and re-run.",
            readings=r,
        )
    rssi = r.get("rssi_dbm")
    if rssi is not None and not (t["rssi_floor_dbm"] <= rssi <= t["rssi_ceiling_dbm"]):
        return SubsystemResult(
            Subsystem.SUBGHZ, Status.WARN, Confidence.MEDIUM,
            f"Radio responds but ambient RSSI ({rssi} dBm) is out of the "
            "expected range.",
            "Often just a noisy RF environment. Move away from strong "
            "transmitters and re-run before suspecting hardware.",
            readings=r,
        )
    if r.get("loopback_supported") and r.get("loopback_ok"):
        return SubsystemResult(
            Subsystem.SUBGHZ, Status.PASS, Confidence.HIGH,
            "Radio responds and TX->RX self-loopback succeeded.",
            "", readings=r,
        )
    return SubsystemResult(
        Subsystem.SUBGHZ, Status.RESPONDS, Confidence.MEDIUM,
        "Transceiver responds and reports the expected chip.",
        "Self-test confirms the radio is alive. A full TX/RX validation needs "
        "a known reference signal; treat this as 'alive', not 'perfect'.",
        readings=r,
    )


def _eval_nfc(r: Dict[str, Any], th: Dict[str, Any]) -> SubsystemResult:
    t = th["nfc"]
    if not r.get("responds"):
        return SubsystemResult(
            Subsystem.NFC, Status.FAIL, Confidence.HIGH,
            "NFC front-end did not respond.",
            "The ST25R NFC chip is not answering. Re-run after a reboot; if it "
            "persists the NFC hardware likely needs service.",
            readings=r,
        )
    amp = r.get("field_amplitude", 0)
    if amp < t["field_min_amplitude"]:
        return SubsystemResult(
            Subsystem.NFC, Status.FAIL, Confidence.MEDIUM,
            "NFC chip responds but is not driving a detectable field.",
            "The coil may be damaged. Keep metal away from the antenna and "
            "re-run; if the field stays absent, the coil likely needs service.",
            readings=r,
        )
    return SubsystemResult(
        Subsystem.NFC, Status.RESPONDS, Confidence.MEDIUM,
        "NFC field detected — the coil is energizing.",
        "This proves the coil is driving a field. It does NOT prove every card "
        "type will read; some cards are simply unsupported. For a stronger "
        "check, present a known reference card.",
        readings=r,
    )


def _eval_ir_tx(r: Dict[str, Any], th: Dict[str, Any]) -> SubsystemResult:
    if r.get("emitted"):
        return SubsystemResult(
            Subsystem.IR_TX, Status.PASS, Confidence.HIGH,
            "IR transmitter emitted the test pattern.",
            "", readings=r,
        )
    return SubsystemResult(
        Subsystem.IR_TX, Status.FAIL, Confidence.HIGH,
        "IR transmitter did not drive the emitter.",
        "The IR LED driver is not firing. Re-run; if it persists the emitter "
        "likely needs service.",
        readings=r,
    )


def _eval_ir_rx(r: Dict[str, Any], th: Dict[str, Any]) -> SubsystemResult:
    t = th["ir"]
    ratio = r.get("loopback_match_ratio", 0.0)
    if not r.get("ir_tx_ok", True):
        return SubsystemResult(
            Subsystem.IR_RX, Status.INCONCLUSIVE, Confidence.MEDIUM,
            "Cannot test IR receive because the transmitter self-test failed.",
            "Fix/confirm the IR transmitter first, then re-run the receiver "
            "test.", readings=r,
        )
    if ratio >= t["loopback_min_match_ratio"]:
        return SubsystemResult(
            Subsystem.IR_RX, Status.PASS, Confidence.HIGH,
            "IR receiver captured the emitted pattern (self-loopback).",
            "", readings=r,
        )
    if ratio <= 0.0:
        return SubsystemResult(
            Subsystem.IR_RX, Status.FAIL, Confidence.HIGH,
            "IR receiver captured nothing during self-loopback.",
            "The emitter works, so the fault is likely the IR receive "
            "photodiode. Retry in a dim room away from bright/IR light; if it "
            "still captures nothing, the receiver may need service.",
            readings=r,
        )
    return SubsystemResult(
        Subsystem.IR_RX, Status.INCONCLUSIVE, Confidence.LOW,
        f"IR receiver captured a partial pattern (match {ratio:.0%}).",
        "Partial capture is often environmental (ambient IR, angle). Retry in "
        "a dim room; a definitive check uses a known IR target.",
        readings=r,
    )


def _eval_gpio(r: Dict[str, Any], th: Dict[str, Any]) -> SubsystemResult:
    # GPIO is the honest 'needs accessory' case.
    if r.get("jumper_present"):
        if r.get("jumper_loopback_ok"):
            return SubsystemResult(
                Subsystem.GPIO, Status.PASS, Confidence.HIGH,
                "GPIO loopback jumper test passed.",
                "", needs_accessory=True, readings=r,
            )
        return SubsystemResult(
            Subsystem.GPIO, Status.FAIL, Confidence.HIGH,
            "GPIO loopback jumper test failed — a pin did not read back "
            "its driven value.",
            "Double-check the jumper wiring against the on-screen guide and "
            "re-run. If wiring is correct, that pin may be faulty.",
            needs_accessory=True, readings=r,
        )
    # No jumper: we can only do a weak self-check.
    if r.get("self_check_ok"):
        return SubsystemResult(
            Subsystem.GPIO, Status.RESPONDS, Confidence.LOW,
            "GPIO pins respond to drive/read self-check.",
            "This is a weak check. For a definitive result, connect the guided "
            "loopback jumper and re-run.",
            needs_accessory=True, readings=r,
        )
    return SubsystemResult(
        Subsystem.GPIO, Status.INCONCLUSIVE, Confidence.LOW,
        "GPIO self-check was inconclusive.",
        "Connect the guided loopback jumper for a definitive GPIO result.",
        needs_accessory=True, readings=r,
    )


def _eval_sd(r: Dict[str, Any], th: Dict[str, Any]) -> SubsystemResult:
    t = th["sd"]
    if not r.get("detected"):
        return SubsystemResult(
            Subsystem.SD, Status.FAIL, Confidence.HIGH,
            "No SD card detected.",
            "Reseat the microSD card and re-run. If still undetected, try a "
            "different card to isolate card vs. slot.",
            readings=r,
        )
    if not r.get("write_read_match", False):
        return SubsystemResult(
            Subsystem.SD, Status.FAIL, Confidence.HIGH,
            "SD write/read test mismatched — data did not come back "
            "intact.",
            "Back up your data now. Reseat or try another card; if mismatches "
            "persist across cards the slot may be at fault.",
            readings=r,
        )
    if r.get("bad_sectors", 0) > t["max_bad_sectors"]:
        return SubsystemResult(
            Subsystem.SD, Status.WARN, Confidence.MEDIUM,
            f"SD readable but reported {r.get('bad_sectors')} bad sector(s).",
            "The card is aging. Back up and consider replacing it.",
            readings=r,
        )
    if r.get("free_ratio", 1.0) < t["min_free_ratio"]:
        return SubsystemResult(
            Subsystem.SD, Status.WARN, Confidence.HIGH,
            "SD card is nearly full.",
            "Free up space to avoid write failures.", readings=r,
        )
    return SubsystemResult(
        Subsystem.SD, Status.PASS, Confidence.HIGH,
        "SD card reads and writes cleanly.",
        "", readings=r,
    )


def _eval_battery(r: Dict[str, Any], th: Dict[str, Any]) -> SubsystemResult:
    t = th["battery"]
    v = r.get("voltage_v")
    if v is None:
        return SubsystemResult(
            Subsystem.BATTERY, Status.INCONCLUSIVE, Confidence.LOW,
            "Could not read battery voltage.",
            "Re-run; if unreadable the fuel-gauge may need attention.",
            readings=r,
        )
    if v < t["voltage_min_v"] or v > t["voltage_max_v"]:
        return SubsystemResult(
            Subsystem.BATTERY, Status.FAIL, Confidence.HIGH,
            f"Battery voltage {v:.2f} V is out of the safe range.",
            "Charge fully and re-run. A persistently out-of-range voltage can "
            "indicate a failing cell or fuel-gauge.",
            readings=r,
        )
    health = r.get("health_pct", 100)
    if health < t["health_fail_pct"]:
        return SubsystemResult(
            Subsystem.BATTERY, Status.FAIL, Confidence.MEDIUM,
            f"Battery health estimated at ~{health}%.",
            "The cell is significantly degraded; expect very short runtime. "
            "Battery service recommended.",
            readings=r,
        )
    if health < t["health_warn_pct"] or v < t["voltage_nominal_min_v"]:
        return SubsystemResult(
            Subsystem.BATTERY, Status.WARN, Confidence.HIGH,
            f"Battery usable but not fresh (health ~{health}%, {v:.2f} V).",
            "Still works; expect shorter runtime than a new unit. This is "
            "normal aging, not a fault.",
            readings=r,
        )
    return SubsystemResult(
        Subsystem.BATTERY, Status.PASS, Confidence.HIGH,
        f"Battery healthy (~{health}%, {v:.2f} V).",
        "", readings=r,
    )


def _eval_interactive(sub: Subsystem, r: Dict[str, Any]) -> SubsystemResult:
    confirmed = r.get("user_confirmed")
    if confirmed is None:
        return SubsystemResult(
            sub, Status.INCONCLUSIVE, Confidence.LOW,
            f"{sub.label} check not completed.",
            "This is an interactive test. Run it on-device and confirm what "
            "you see/feel.",
            readings=r,
        )
    if confirmed:
        return SubsystemResult(
            sub, Status.PASS, Confidence.HIGH,
            f"{sub.label}: all inputs/outputs confirmed by the user.",
            "", readings=r,
        )
    return SubsystemResult(
        sub, Status.FAIL, Confidence.HIGH,
        f"{sub.label}: the user reported a missing input/output.",
        "Note which specific button/pixel/LED/vibro failed; that narrows the "
        "fault.",
        readings=r,
    )


_DISPATCH = {
    Subsystem.SUBGHZ: _eval_subghz,
    Subsystem.NFC: _eval_nfc,
    Subsystem.IR_TX: _eval_ir_tx,
    Subsystem.IR_RX: _eval_ir_rx,
    Subsystem.GPIO: _eval_gpio,
    Subsystem.SD: _eval_sd,
    Subsystem.BATTERY: _eval_battery,
}


def evaluate_subsystem(subsystem: Subsystem, readings: Dict[str, Any]) -> SubsystemResult:
    """Evaluate one subsystem's raw readings into an honest result."""
    th = load_thresholds()
    if subsystem in _DISPATCH:
        return _with_known_issue(_DISPATCH[subsystem](readings, th))
    if subsystem in (Subsystem.BUTTONS, Subsystem.DISPLAY):
        return _with_known_issue(_eval_interactive(subsystem, readings))
    raise ValueError(f"No evaluator for {subsystem}")


def evaluate_all(readings_by_subsystem: Dict[Subsystem, Dict[str, Any]]) -> List[SubsystemResult]:
    """Evaluate every provided subsystem, in canonical subsystem order."""
    order = list(Subsystem)
    return [
        evaluate_subsystem(sub, readings_by_subsystem[sub])
        for sub in order
        if sub in readings_by_subsystem
    ]
