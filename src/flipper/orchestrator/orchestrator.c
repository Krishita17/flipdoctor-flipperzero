/*
 * FlipDoctor — test orchestrator implementation.
 * Sole author: Krishita Sanjay Choksi.
 */
#include "orchestrator.h"
#include "../tests/tests.h"
#include "../evaluate/evaluate.h"
#include "../modes/modes.h"
#include "../report/report.h"

#include <furi.h>

void fd_orchestrator_run(FdMode mode, FdReport* out) {
    furi_assert(out);
    memset(out, 0, sizeof(FdReport));
    out->mode = mode;

    FdSubsystem scope[FD_SUB_COUNT];
    size_t n = fd_modes_subsystems(mode, scope);

    for(size_t i = 0; i < n; i++) {
        FdSubsystem sub = scope[i];
        FdReadings readings;
        memset(&readings, 0, sizeof(readings));

        /* Collect readings from hardware for this subsystem. */
        fd_tests_collect(sub, &readings);

        /* Evaluate into an honest verdict (mirrors the validated Python core). */
        out->results[out->result_count++] = fd_evaluate(sub, &readings);
    }

    fd_report_finalize(out);
}
