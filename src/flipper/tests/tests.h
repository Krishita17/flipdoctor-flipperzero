/*
 * FlipDoctor — subsystem test modules.
 * Each collector fills an FdReadings struct from the hardware HAL. Keeping the
 * readings separate from the verdict lets the same evaluator run on-device and
 * off-device (against the fault simulator).
 * Sole author: Krishita Sanjay Choksi.
 */
#pragma once

#include "../flipdoctor.h"

/* Populate `out` with raw readings for `sub`, using the Flipper HAL. */
void fd_tests_collect(FdSubsystem sub, FdReadings* out);
