/*
 * FlipDoctor — report generation (on-device).
 * Sole author: Krishita Sanjay Choksi.
 */
#pragma once

#include "../flipdoctor.h"
#include <gui/modules/widget.h>

/* Compute overall verdict, report id, and timestamp after results are filled. */
void fd_report_finalize(FdReport* report);

/* Overall verdict for a finalized report. */
FdStatus fd_report_overall(const FdReport* report);
const char* fd_report_overall_label(const FdReport* report);

/* Render the report into a scrollable widget (the on-screen deliverable). */
void fd_report_render_to_widget(const FdReport* report, Widget* widget);

/* Save the report to SD as a text file; returns true on success. */
bool fd_report_export(const FdReport* report);
