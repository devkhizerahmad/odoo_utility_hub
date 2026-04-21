/**
 * @file my_attendances.js
 * @description Odoo OWL components override to institute End of Day (EOD) reporting popups 
 * upon HR check-out actions. Modifies both Systray and Dashboard widgets.
 */

import { patch } from "@web/core/utils/patch";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { CheckInOut } from "@hr_attendance/components/check_in_out/check_in_out";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * EodDialog Component
 * Framework-native Web Component rendering the modal interface for EOD reports.
 * Employs responsive state management to monitor user input thresholds and submission statuses.
 */
class EodDialog extends Component {
    static template = "custom_attendance_ip.EodDialog";
    static components = { Dialog };
    static props = {
        onSave: { type: Function }, // Callback resolved with sanitized EOD text
        onClose: { type: Function },
        close: { type: Function },
    };

    /**
     * Initializes localized component state defining the report payload,
     * displayable schema violations, and atomic transition locks.
     */
    setup() {
        this.state = useState({
            eodText: "",
            error: "",
            isSubmitting: false,
        });
    }

    /**
     * Computes real-time stylistic classes for character limits highlighting imminent truncation boundaries.
     */
    get counterClass() {
        const len = this.state.eodText.length;
        if (len > 230) return "danger";
        if (len > 180) return "warning";
        return "normal";
    }

    /**
     * Traps generic text inputs, enforcing strict 255-character limits client-side 
     * before routing to ORM logic.
     */
    onInputChange(ev) {
        if (this.state.eodText.length > 255) {
            this.state.eodText = this.state.eodText.substring(0, 255);
        }
        this.state.error = "";
    }

    /**
     * Async save dispatcher enforcing primary heuristics (min 5 chars)
     * Tracks execution boundaries via boolean locks. 
     */
    async onSave() {
        if (this.state.eodText.length < 5) {
            this.state.error = "Please provide a slightly more detailed report (min 5 characters).";
            return;
        }
        this.state.isSubmitting = true;
        try {
            const result = await this.props.onSave(this.state.eodText);
            if (!result || !result.success) {
                this.state.error = (result && result.error) || "Unable to complete checkout. Please try again.";
                return;
            }
            this.props.close();
        } catch (e) {
            this.state.error = e.message || "An error occurred. Please try again.";
        } finally {
            this.state.isSubmitting = false;
        }
    }
}

// ============================================================================
// PATCH: SYSTRAY (Top Navigation Bar) Attendance Menu
// ============================================================================
patch(ActivityMenu.prototype, {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
    },

    /**
     * Intercepts standard checkout behavior. Spawns EOD Dialog natively over the UI index,
     * chaining the original super payload only after positive EOD completion.
     */
    async signInOut() {
        const originalSignInOut = super.signInOut.bind(this);
        if (this.state.checkedIn) {
            this.dialogService.add(EodDialog, {
                onSave: async (eodText) => {
                    const attendanceId = this.employee && this.employee.id ? this.employee.attendance_id : false;
                    try {
                        // Persist auxiliary data block utilizing a decoupled backend RPC invoke
                        const result = await this.orm.call("hr.attendance", "action_save_eod", [attendanceId, eodText]);
                        if (result && result.success) {
                            // Defer strictly to framework APIs to encapsulate Geocoding (Lat/Lng) processes natively
                            await originalSignInOut();
                         //   this.notification.add("Checked out successfully!", { type: "success" });
                            return { success: true };
                        } else if (result && result.error) {
                            this.notification.add(result.error, { type: "danger" });
                            return { success: false, error: result.error };
                        }
                    } catch (error) {
                        const message = "An error occurred during checkout.";
                        this.notification.add(message, { type: "danger" });
                        return { success: false, error: message };
                    }
                    return { success: false, error: "Unable to complete checkout." };
                },
                onClose: () => { }
            });
            return;
        }
        
        // Transparent bypass for standard Check-In lifecycle 
        await originalSignInOut();
    }
});

// ============================================================================
// PATCH: KIOSK & DASHBOARD WIDGET 
// ============================================================================
patch(CheckInOut.prototype, {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.actionService = useService("action");
    },

    async signInOut() {
        const originalSignInOut = super.signInOut.bind(this);
        if (this.props.checkedIn) {
            this.dialogService.add(EodDialog, {
                onSave: async (eodText) => {
                    try {
                        const result = await this.orm.call("hr.attendance", "action_save_eod", [false, eodText], {
                            context: { employee_id: this.props.employeeId }
                        });
                        
                        if (result && result.success) {
                            // Process complete native lifecycle
                            await originalSignInOut();
                            return { success: true };
                        } else if (result && result.error) {
                            this.notification.add(result.error, { type: "danger" });
                            return { success: false, error: result.error };
                        }
                    } catch (error) {
                        const message = "An error occurred during checkout.";
                        this.notification.add(message, { type: "danger" });
                        return { success: false, error: message };
                    }
                    return { success: false, error: "Unable to complete checkout." };
                },
                onClose: () => { }
            });
            return;
        }
        await originalSignInOut();
    }
});
