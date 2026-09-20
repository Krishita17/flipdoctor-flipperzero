/*
 * FlipDoctor — on-device data model.
 *
 * This header mirrors the portable Python core in ../../flipdoctor/ so the
 * on-device verdicts match what the simulator/eval validate off-device.
 *
 * Sole author: Krishita Sanjay Choksi.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define FLIPDOCTOR_VERSION "0.1.0"

/* The honest verdict for a single test. RESPONDS is intentionally distinct
 * from PASS: alive/answering, but not fully validated without an accessory. */
typedef enum {
    FD_STATUS_PASS = 0,
    FD_STATUS_RESPONDS,
    FD_STATUS_WARN,
    FD_STATUS_INCONCLUSIVE,
    FD_STATUS_FAIL,
    FD_STATUS_COUNT,
} FdStatus;

typedef enum {
    FD_CONF_HIGH = 0,
    FD_CONF_MEDIUM,
    FD_CONF_LOW,
} FdConfidence;

typedef enum {
    FD_SUB_SUBGHZ = 0,
    FD_SUB_NFC,
    FD_SUB_IR_TX,
    FD_SUB_IR_RX,
    FD_SUB_GPIO,
    FD_SUB_SD,
    FD_SUB_BATTERY,
    FD_SUB_BUTTONS,
    FD_SUB_DISPLAY,
    FD_SUB_COUNT,
} FdSubsystem;

typedef enum {
    FD_MODE_FULL = 0,
    FD_MODE_QUICK,
    FD_MODE_USED_BUYER,
    FD_MODE_SINGLE,
} FdMode;

/* Raw readings for a subsystem, produced by the HAL-backed test modules.
 * A superset struct keeps the on-device code allocation-free. Unused fields
 * for a given subsystem are simply ignored by its evaluator. */
typedef struct {
    /* generic */
    bool responds;
    /* subghz / nfc */
    const char* chip_id;
    bool loopback_supported;
    bool loopback_ok;
    float rssi_dbm;
    int32_t field_amplitude;
    /* ir */
    bool emitted;
    float loopback_match_ratio;
    bool ir_tx_ok;
    /* gpio */
    bool self_check_ok;
    bool jumper_present;
    bool jumper_loopback_ok;
    /* sd */
    bool detected;
    bool write_read_match;
    int32_t bad_sectors;
    float free_ratio;
    /* battery */
    float voltage_v;
    int32_t health_pct;
    /* interactive */
    bool interactive_confirmed;
    bool interactive_done;
} FdReadings;

typedef struct {
    FdSubsystem subsystem;
    FdStatus status;
    FdConfidence confidence;
    bool needs_accessory;
    const char* message;
    const char* guidance;
} FdResult;

typedef struct {
    FdResult results[FD_SUB_COUNT];
    size_t result_count;
    FdMode mode;
    char report_id[16];
    char timestamp[24];
} FdReport;

/* Labels / helpers shared across modules. */
const char* fd_subsystem_label(FdSubsystem s);
const char* fd_status_str(FdStatus s);
const char* fd_status_symbol(FdStatus s);
const char* fd_confidence_str(FdConfidence c);
bool fd_status_is_healthy(FdStatus s);

/* App entry point (see application.fam entry_point). */
int32_t flipdoctor_app(void* p);
