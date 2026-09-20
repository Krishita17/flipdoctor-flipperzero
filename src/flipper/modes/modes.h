/*
 * FlipDoctor — run modes (on-device).
 * Selects which subsystems a mode exercises. Mirrors flipdoctor/modes.py.
 * Sole author: Krishita Sanjay Choksi.
 */
#pragma once

#include "../flipdoctor.h"

/* Fill `out` (capacity FD_SUB_COUNT) with the subsystems for `mode`.
 * Returns the count written. */
size_t fd_modes_subsystems(FdMode mode, FdSubsystem* out);
