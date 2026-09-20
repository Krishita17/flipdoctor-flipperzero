/*
 * FlipDoctor — report generation implementation.
 * Sole author: Krishita Sanjay Choksi.
 */
#include "report.h"

#include <furi.h>
#include <furi_hal_rtc.h>
#include <datetime/datetime.h>
#include <storage/storage.h>

FdStatus fd_report_overall(const FdReport* report) {
    bool any_fail = false, any_attention = false;
    for(size_t i = 0; i < report->result_count; i++) {
        FdStatus s = report->results[i].status;
        if(s == FD_STATUS_FAIL) any_fail = true;
        if(s == FD_STATUS_WARN || s == FD_STATUS_INCONCLUSIVE) any_attention = true;
    }
    if(any_fail) return FD_STATUS_FAIL;
    if(any_attention) return FD_STATUS_WARN;
    return FD_STATUS_PASS;
}

const char* fd_report_overall_label(const FdReport* report) {
    switch(fd_report_overall(report)) {
    case FD_STATUS_PASS: return "HEALTHY";
    case FD_STATUS_FAIL: return "FAULT DETECTED";
    default: return "NEEDS ATTENTION";
    }
}

void fd_report_finalize(FdReport* report) {
    /* Timestamp from RTC. */
    DateTime dt;
    furi_hal_rtc_get_datetime(&dt);
    snprintf(
        report->timestamp, sizeof(report->timestamp), "%04u-%02u-%02u %02u:%02u",
        (unsigned)dt.year, (unsigned)dt.month, (unsigned)dt.day, (unsigned)dt.hour,
        (unsigned)dt.minute);

    /* Simple stable-ish report id from statuses + minute. */
    uint32_t h = 2166136261u;
    for(size_t i = 0; i < report->result_count; i++) {
        h = (h ^ (uint32_t)report->results[i].subsystem) * 16777619u;
        h = (h ^ (uint32_t)report->results[i].status) * 16777619u;
    }
    h ^= (uint32_t)(dt.minute + dt.hour * 60);
    snprintf(report->report_id, sizeof(report->report_id), "FD-%04lX-%04lX",
             (unsigned long)((h >> 16) & 0xFFFF), (unsigned long)(h & 0xFFFF));
}

void fd_report_render_to_widget(const FdReport* report, Widget* widget) {
    widget_reset(widget);
    FuriString* s = furi_string_alloc();

    furi_string_cat_printf(s, "OVERALL: %s\n", fd_report_overall_label(report));
    furi_string_cat_printf(s, "ID %s  %s\n", report->report_id, report->timestamp);
    furi_string_cat_str(s, "----------------------\n");
    for(size_t i = 0; i < report->result_count; i++) {
        const FdResult* r = &report->results[i];
        furi_string_cat_printf(
            s, "%s %s\n   %s (%s)%s\n",
            fd_status_symbol(r->status),
            fd_subsystem_label(r->subsystem),
            fd_status_str(r->status),
            fd_confidence_str(r->confidence),
            r->needs_accessory ? " [acc]" : "");
        if(r->guidance && r->guidance[0]) {
            furi_string_cat_printf(s, "   > %s\n", r->guidance);
        }
    }
    furi_string_cat_str(s, "\nHonesty: RESPONDS=alive not perfect.\n");

    widget_add_text_scroll_element(widget, 0, 0, 128, 64, furi_string_get_cstr(s));
    furi_string_free(s);
}

bool fd_report_export(const FdReport* report) {
    Storage* storage = furi_record_open(RECORD_STORAGE);
    storage_common_mkdir(storage, EXT_PATH("apps_data/flipdoctor"));
    FuriString* path = furi_string_alloc();
    furi_string_printf(
        path, EXT_PATH("apps_data/flipdoctor/%s.txt"), report->report_id);

    File* f = storage_file_alloc(storage);
    bool ok = false;
    if(storage_file_open(f, furi_string_get_cstr(path), FSAM_WRITE, FSOM_CREATE_ALWAYS)) {
        FuriString* line = furi_string_alloc();
        furi_string_printf(
            line, "FlipDoctor report %s  %s\nOVERALL: %s\n",
            report->report_id, report->timestamp, fd_report_overall_label(report));
        storage_file_write(f, furi_string_get_cstr(line), furi_string_size(line));
        for(size_t i = 0; i < report->result_count; i++) {
            const FdResult* r = &report->results[i];
            furi_string_printf(
                line, "%s %s (%s)\n  %s\n  %s\n",
                fd_status_str(r->status), fd_subsystem_label(r->subsystem),
                fd_confidence_str(r->confidence), r->message,
                (r->guidance && r->guidance[0]) ? r->guidance : "-");
            storage_file_write(f, furi_string_get_cstr(line), furi_string_size(line));
        }
        furi_string_free(line);
        storage_file_close(f);
        ok = true;
    }
    storage_file_free(f);
    furi_string_free(path);
    furi_record_close(RECORD_STORAGE);
    return ok;
}
