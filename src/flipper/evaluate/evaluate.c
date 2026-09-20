/*
 * FlipDoctor — result evaluator implementation.
 *
 * Thresholds match db/thresholds.json. The guiding rule matches the Python
 * core: never emit a false PASS or FAIL. Use RESPONDS for "alive but not fully
 * validated" and INCONCLUSIVE for "insufficient evidence, here's the next step".
 *
 * Sole author: Krishita Sanjay Choksi.
 */
#include "evaluate.h"

/* thresholds (see db/thresholds.json) */
#define BAT_VMIN 3.30f
#define BAT_VNOM_MIN 3.60f
#define BAT_VMAX 4.25f
#define BAT_HEALTH_FAIL 60
#define BAT_HEALTH_WARN 85
#define SUBGHZ_RSSI_FLOOR -110.0f
#define SUBGHZ_RSSI_CEIL 10.0f
#define NFC_FIELD_MIN 1
#define IR_MATCH_MIN 0.75f
#define SD_MIN_FREE_RATIO 0.02f

static FdResult mk(
    FdSubsystem sub,
    FdStatus st,
    FdConfidence cf,
    const char* msg,
    const char* guide,
    bool needs_acc) {
    FdResult r = {
        .subsystem = sub,
        .status = st,
        .confidence = cf,
        .message = msg,
        .guidance = guide,
        .needs_accessory = needs_acc};
    return r;
}

static FdResult eval_battery(const FdReadings* r) {
    if(!r->responds || r->voltage_v <= 0.0f)
        return mk(
            FD_SUB_BATTERY, FD_STATUS_INCONCLUSIVE, FD_CONF_LOW,
            "Could not read battery voltage.",
            "Re-run; if unreadable the fuel-gauge may need attention.", false);
    if(r->voltage_v < BAT_VMIN || r->voltage_v > BAT_VMAX)
        return mk(
            FD_SUB_BATTERY, FD_STATUS_FAIL, FD_CONF_HIGH,
            "Battery voltage out of safe range.",
            "Charge fully and re-run; persistent out-of-range can indicate a "
            "failing cell.", false);
    if(r->health_pct < BAT_HEALTH_FAIL)
        return mk(
            FD_SUB_BATTERY, FD_STATUS_FAIL, FD_CONF_MEDIUM,
            "Battery health severely degraded.",
            "Expect very short runtime; service recommended.", false);
    if(r->health_pct < BAT_HEALTH_WARN || r->voltage_v < BAT_VNOM_MIN)
        return mk(
            FD_SUB_BATTERY, FD_STATUS_WARN, FD_CONF_HIGH,
            "Battery usable but not fresh.",
            "Normal aging; expect shorter runtime than a new unit.", false);
    return mk(FD_SUB_BATTERY, FD_STATUS_PASS, FD_CONF_HIGH, "Battery healthy.", "", false);
}

static FdResult eval_sd(const FdReadings* r) {
    if(!r->detected)
        return mk(
            FD_SUB_SD, FD_STATUS_FAIL, FD_CONF_HIGH, "No SD card detected.",
            "Reseat the card; if still undetected try another card.", false);
    if(!r->write_read_match)
        return mk(
            FD_SUB_SD, FD_STATUS_FAIL, FD_CONF_HIGH,
            "SD write/read mismatch.",
            "Back up now; reseat or try another card.", false);
    if(r->bad_sectors > 0)
        return mk(
            FD_SUB_SD, FD_STATUS_WARN, FD_CONF_MEDIUM, "SD readable but aging.",
            "Back up and consider replacing the card.", false);
    if(r->free_ratio < SD_MIN_FREE_RATIO)
        return mk(
            FD_SUB_SD, FD_STATUS_WARN, FD_CONF_HIGH, "SD nearly full.",
            "Free up space to avoid write failures.", false);
    return mk(FD_SUB_SD, FD_STATUS_PASS, FD_CONF_HIGH, "SD reads/writes cleanly.", "", false);
}

static FdResult eval_subghz(const FdReadings* r) {
    if(!r->responds)
        return mk(
            FD_SUB_SUBGHZ, FD_STATUS_FAIL, FD_CONF_HIGH,
            "Sub-GHz transceiver did not respond.",
            "Reboot and re-run; if it persists the radio may need service.", false);
    if(r->rssi_dbm < SUBGHZ_RSSI_FLOOR || r->rssi_dbm > SUBGHZ_RSSI_CEIL)
        return mk(
            FD_SUB_SUBGHZ, FD_STATUS_WARN, FD_CONF_MEDIUM,
            "Radio responds but ambient RSSI is out of range.",
            "Often a noisy RF environment; move away and re-run.", false);
    if(r->loopback_supported && r->loopback_ok)
        return mk(
            FD_SUB_SUBGHZ, FD_STATUS_PASS, FD_CONF_HIGH,
            "Radio responds and self-loopback succeeded.", "", false);
    return mk(
        FD_SUB_SUBGHZ, FD_STATUS_RESPONDS, FD_CONF_MEDIUM,
        "Transceiver responds.",
        "Alive, not fully validated; a full check needs a reference signal.", false);
}

static FdResult eval_nfc(const FdReadings* r) {
    if(!r->responds)
        return mk(
            FD_SUB_NFC, FD_STATUS_FAIL, FD_CONF_HIGH, "NFC front-end did not respond.",
            "Reboot and re-run; if it persists the NFC hardware may need service.", false);
    if(r->field_amplitude < NFC_FIELD_MIN)
        return mk(
            FD_SUB_NFC, FD_STATUS_FAIL, FD_CONF_MEDIUM,
            "NFC chip responds but drives no detectable field.",
            "Keep metal away and re-run; the coil may be damaged.", false);
    return mk(
        FD_SUB_NFC, FD_STATUS_RESPONDS, FD_CONF_MEDIUM,
        "NFC field detected - the coil is energizing.",
        "Proves the coil drives a field, not that every card will read. Use a "
        "reference card for a stronger check.", false);
}

static FdResult eval_ir_tx(const FdReadings* r) {
    if(r->emitted)
        return mk(FD_SUB_IR_TX, FD_STATUS_PASS, FD_CONF_HIGH, "IR transmitter emitted.", "", false);
    return mk(
        FD_SUB_IR_TX, FD_STATUS_FAIL, FD_CONF_HIGH, "IR transmitter did not fire.",
        "Re-run; if it persists the emitter may need service.", false);
}

static FdResult eval_ir_rx(const FdReadings* r) {
    if(!r->ir_tx_ok)
        return mk(
            FD_SUB_IR_RX, FD_STATUS_INCONCLUSIVE, FD_CONF_MEDIUM,
            "Cannot test IR receive while the transmitter is down.",
            "Fix the IR transmitter first, then re-run.", false);
    if(r->loopback_match_ratio >= IR_MATCH_MIN)
        return mk(FD_SUB_IR_RX, FD_STATUS_PASS, FD_CONF_HIGH, "IR receiver captured the pattern.", "", false);
    if(r->loopback_match_ratio <= 0.0f)
        return mk(
            FD_SUB_IR_RX, FD_STATUS_FAIL, FD_CONF_HIGH, "IR receiver captured nothing.",
            "Emitter works, so likely the receive photodiode. Retry in a dim room.", false);
    return mk(
        FD_SUB_IR_RX, FD_STATUS_INCONCLUSIVE, FD_CONF_LOW, "IR receiver captured a partial pattern.",
        "Often environmental; retry in a dim room. Definitive check needs a known target.", false);
}

static FdResult eval_gpio(const FdReadings* r) {
    if(r->jumper_present) {
        if(r->jumper_loopback_ok)
            return mk(FD_SUB_GPIO, FD_STATUS_PASS, FD_CONF_HIGH, "GPIO jumper loopback passed.", "", true);
        return mk(
            FD_SUB_GPIO, FD_STATUS_FAIL, FD_CONF_HIGH, "GPIO jumper loopback failed.",
            "Recheck wiring against the guide; if correct, a pin may be faulty.", true);
    }
    if(r->self_check_ok)
        return mk(
            FD_SUB_GPIO, FD_STATUS_RESPONDS, FD_CONF_LOW, "GPIO pins respond (weak self-check).",
            "Connect the guided loopback jumper for a definitive result.", true);
    return mk(
        FD_SUB_GPIO, FD_STATUS_INCONCLUSIVE, FD_CONF_LOW, "GPIO self-check inconclusive.",
        "Connect the guided loopback jumper and re-run.", true);
}

static FdResult eval_interactive(FdSubsystem sub, const FdReadings* r) {
    if(!r->interactive_done)
        return mk(
            sub, FD_STATUS_INCONCLUSIVE, FD_CONF_LOW, "Interactive check not completed.",
            "Run it on-device and confirm what you see/feel.", false);
    if(r->interactive_confirmed)
        return mk(sub, FD_STATUS_PASS, FD_CONF_HIGH, "All inputs/outputs confirmed.", "", false);
    return mk(
        sub, FD_STATUS_FAIL, FD_CONF_HIGH, "User reported a missing input/output.",
        "Note which specific button/pixel/LED/vibro failed.", false);
}

FdResult fd_evaluate(FdSubsystem sub, const FdReadings* r) {
    switch(sub) {
    case FD_SUB_BATTERY: return eval_battery(r);
    case FD_SUB_SD: return eval_sd(r);
    case FD_SUB_SUBGHZ: return eval_subghz(r);
    case FD_SUB_NFC: return eval_nfc(r);
    case FD_SUB_IR_TX: return eval_ir_tx(r);
    case FD_SUB_IR_RX: return eval_ir_rx(r);
    case FD_SUB_GPIO: return eval_gpio(r);
    case FD_SUB_BUTTONS:
    case FD_SUB_DISPLAY: return eval_interactive(sub, r);
    default:
        return mk(sub, FD_STATUS_INCONCLUSIVE, FD_CONF_LOW, "No evaluator.", "", false);
    }
}
