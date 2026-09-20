/*
 * FlipDoctor — application entry point and shared helpers.
 *
 * This is the on-device orchestration shell. It wires the GUI, runs the chosen
 * mode via the orchestrator, and shows the report. Hardware access lives in the
 * test modules under tests/; the verdict logic in evaluate/ mirrors the
 * validated Python core so on-device results match the off-device eval.
 *
 * Sole author: Krishita Sanjay Choksi.
 */
#include "flipdoctor.h"
#include "orchestrator/orchestrator.h"
#include "report/report.h"

#include <furi.h>
#include <gui/gui.h>
#include <gui/view_dispatcher.h>
#include <gui/modules/widget.h>
#include <gui/modules/submenu.h>

typedef enum {
    FdViewMenu = 0,
    FdViewReport,
} FdView;

typedef enum {
    FdMenuFull = 0,
    FdMenuQuick,
    FdMenuUsedBuyer,
    FdMenuSingle,
} FdMenuIndex;

typedef struct {
    Gui* gui;
    ViewDispatcher* view_dispatcher;
    Submenu* menu;
    Widget* report_widget;
    FdReport report;
} FdApp;

/* ---- shared label helpers (used by all modules) ------------------------ */
const char* fd_subsystem_label(FdSubsystem s) {
    switch(s) {
    case FD_SUB_SUBGHZ: return "Sub-GHz radio";
    case FD_SUB_NFC: return "NFC / RFID coil";
    case FD_SUB_IR_TX: return "IR transmitter";
    case FD_SUB_IR_RX: return "IR receiver";
    case FD_SUB_GPIO: return "GPIO pins";
    case FD_SUB_SD: return "SD card";
    case FD_SUB_BATTERY: return "Battery";
    case FD_SUB_BUTTONS: return "Buttons / D-pad";
    case FD_SUB_DISPLAY: return "Display / LED / vibro";
    default: return "?";
    }
}

const char* fd_status_str(FdStatus s) {
    switch(s) {
    case FD_STATUS_PASS: return "PASS";
    case FD_STATUS_RESPONDS: return "RESPONDS";
    case FD_STATUS_WARN: return "WARN";
    case FD_STATUS_INCONCLUSIVE: return "INCONCLUSIVE";
    case FD_STATUS_FAIL: return "FAIL";
    default: return "?";
    }
}

const char* fd_status_symbol(FdStatus s) {
    switch(s) {
    case FD_STATUS_PASS:
    case FD_STATUS_RESPONDS: return "[OK]";
    case FD_STATUS_WARN: return "[! ]";
    case FD_STATUS_INCONCLUSIVE: return "[~ ]";
    case FD_STATUS_FAIL: return "[X ]";
    default: return "[? ]";
    }
}

const char* fd_confidence_str(FdConfidence c) {
    switch(c) {
    case FD_CONF_HIGH: return "high";
    case FD_CONF_MEDIUM: return "medium";
    case FD_CONF_LOW: return "low";
    default: return "?";
    }
}

bool fd_status_is_healthy(FdStatus s) {
    return s == FD_STATUS_PASS || s == FD_STATUS_RESPONDS;
}

/* ---- navigation -------------------------------------------------------- */
static uint32_t fd_exit_callback(void* context) {
    UNUSED(context);
    return VIEW_NONE;
}

static uint32_t fd_back_to_menu_callback(void* context) {
    UNUSED(context);
    return FdViewMenu;
}

static void fd_run_and_show(FdApp* app, FdMode mode) {
    fd_orchestrator_run(mode, &app->report);
    fd_report_render_to_widget(&app->report, app->report_widget);
    view_dispatcher_switch_to_view(app->view_dispatcher, FdViewReport);
}

static void fd_menu_callback(void* context, uint32_t index) {
    FdApp* app = context;
    switch(index) {
    case FdMenuFull: fd_run_and_show(app, FD_MODE_FULL); break;
    case FdMenuQuick: fd_run_and_show(app, FD_MODE_QUICK); break;
    case FdMenuUsedBuyer: fd_run_and_show(app, FD_MODE_USED_BUYER); break;
    case FdMenuSingle: fd_run_and_show(app, FD_MODE_SINGLE); break;
    default: break;
    }
}

static FdApp* fd_app_alloc(void) {
    FdApp* app = malloc(sizeof(FdApp));
    memset(app, 0, sizeof(FdApp));

    app->gui = furi_record_open(RECORD_GUI);
    app->view_dispatcher = view_dispatcher_alloc();
    view_dispatcher_attach_to_gui(app->view_dispatcher, app->gui, ViewDispatcherTypeFullscreen);

    app->menu = submenu_alloc();
    submenu_set_header(app->menu, "FlipDoctor - checkup");
    submenu_add_item(app->menu, "Full checkup", FdMenuFull, fd_menu_callback, app);
    submenu_add_item(app->menu, "Quick check", FdMenuQuick, fd_menu_callback, app);
    submenu_add_item(app->menu, "Used-buyer verify", FdMenuUsedBuyer, fd_menu_callback, app);
    submenu_add_item(app->menu, "Single subsystem", FdMenuSingle, fd_menu_callback, app);
    view_set_previous_callback(submenu_get_view(app->menu), fd_exit_callback);
    view_dispatcher_add_view(app->view_dispatcher, FdViewMenu, submenu_get_view(app->menu));

    app->report_widget = widget_alloc();
    view_set_previous_callback(widget_get_view(app->report_widget), fd_back_to_menu_callback);
    view_dispatcher_add_view(
        app->view_dispatcher, FdViewReport, widget_get_view(app->report_widget));

    return app;
}

static void fd_app_free(FdApp* app) {
    view_dispatcher_remove_view(app->view_dispatcher, FdViewMenu);
    view_dispatcher_remove_view(app->view_dispatcher, FdViewReport);
    submenu_free(app->menu);
    widget_free(app->report_widget);
    view_dispatcher_free(app->view_dispatcher);
    furi_record_close(RECORD_GUI);
    free(app);
}

int32_t flipdoctor_app(void* p) {
    UNUSED(p);
    FdApp* app = fd_app_alloc();
    view_dispatcher_switch_to_view(app->view_dispatcher, FdViewMenu);
    view_dispatcher_run(app->view_dispatcher);
    fd_app_free(app);
    return 0;
}
