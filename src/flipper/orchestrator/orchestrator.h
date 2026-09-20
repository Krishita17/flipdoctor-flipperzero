/*
 * FlipDoctor — test orchestrator.
 * Sequences the subsystem tests for a chosen mode, collects readings, runs the
 * evaluator, and fills an FdReport.
 * Sole author: Krishita Sanjay Choksi.
 */
#pragma once

#include "../flipdoctor.h"

/* Run the chosen mode: collect readings for each in-scope subsystem, evaluate,
 * and populate `out`. */
void fd_orchestrator_run(FdMode mode, FdReport* out);
