/*
 * FlipDoctor — run modes implementation.
 * Sole author: Krishita Sanjay Choksi.
 */
#include "modes.h"

size_t fd_modes_subsystems(FdMode mode, FdSubsystem* out) {
    size_t n = 0;
    if(mode == FD_MODE_QUICK) {
        /* Fast, self-contained, non-interactive subset. */
        const FdSubsystem quick[] = {
            FD_SUB_SD, FD_SUB_BATTERY, FD_SUB_SUBGHZ,
            FD_SUB_NFC, FD_SUB_IR_TX, FD_SUB_IR_RX};
        for(size_t i = 0; i < sizeof(quick) / sizeof(quick[0]); i++) out[n++] = quick[i];
        return n;
    }
    if(mode == FD_MODE_SINGLE) {
        /* The single-subsystem picker sets this; default to SD as a safe pick. */
        out[n++] = FD_SUB_SD;
        return n;
    }
    /* FULL and USED_BUYER exercise everything. */
    for(FdSubsystem s = 0; s < FD_SUB_COUNT; s++) out[n++] = s;
    return n;
}
