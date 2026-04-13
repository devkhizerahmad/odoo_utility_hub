import { patch } from "@web/core/utils/patch";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { CheckInOut } from "@hr_attendance/components/check_in_out/check_in_out";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * EodDialog Component
 * Renders the popup for EOD report submission.
 */
class EodDialog extends Component {
    static template = "custom_attendance_ip.EodDialog";
    static components = { Dialog };
    static props = {
        onSave: { type: Function },
        onClose: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.state = useState({
            eodText: "",
            error: "",
        });
    }

    get counterClass() {
        const len = this.state.eodText.length;
        if (len > 230) return "danger";
        if (len > 180) return "warning";
        return "normal";
    }

    onInputChange(ev) {
        if (this.state.eodText.length > 255) {
            this.state.eodText = this.state.eodText.substring(0, 255);
        }
        this.state.error = "";
    }

    async onSave() {
        if (this.state.eodText.length < 5) {
            this.state.error = "Please provide a slightly more detailed report (min 5 characters).";
            return;
        }
        await this.props.onSave(this.state.eodText);
        this.props.close();
    }
}

// 1. Patch SYSTRAY (Top Bar) Attendance Menu
patch(ActivityMenu.prototype, {
    setup() {
        super.setup(); // Odoo 18 uses native super
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    async signInOut() {
        // Agar user pehle se check-in hai, toh ye Check-out attempt hai
        if (this.state.checkedIn) {
            this.dialogService.add(EodDialog, {
                onSave: (eodText) => this._submitEodAndCheckout(eodText),
                onClose: () => { }
            });
            return;
        }
        // Check-in ke liye normal flow
        await super.signInOut();
    },

    async _submitEodAndCheckout(eodText) {
        const attendanceId = this.employee && this.employee.id ? this.employee.attendance_id : false;
        try {
            const result = await this.orm.call("hr.attendance", "action_submit_eod_checkout", [attendanceId, eodText]);
            if (result && result.success) {
                await this.searchReadEmployee(); // Refresh systray data
            } else if (result && result.error) {
                this.notification.add(result.error, { type: "danger" });
            }
        } catch (error) {
            this.notification.add("An error occurred during checkout.", { type: "danger" });
        }
    }
});

// 2. Patch Dashboard Widget (CheckInOut)
patch(CheckInOut.prototype, {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.actionService = useService("action");
    },

    async signInOut() {
        if (this.props.checkedIn) {
            this.dialogService.add(EodDialog, {
                onSave: (eodText) => this._submitEodAndCheckoutDashboard(eodText),
                onClose: () => { }
            });
            return;
        }
        await super.signInOut();
    },

    async _submitEodAndCheckoutDashboard(eodText) {
        try {
            const result = await this.orm.call("hr.attendance", "action_submit_eod_checkout", [false, eodText], {
                context: { employee_id: this.props.employeeId }
            });
            
            if (result && result.success) {
                if (this.props.nextAction) {
                    this.actionService.doAction(this.props.nextAction);
                } else {
                    window.location.reload();
                }
            } else if (result && result.error) {
                this.notification.add(result.error, { type: "danger" });
            }
        } catch (error) {
            this.notification.add("An error occurred during checkout.", { type: "danger" });
        }
    }
});