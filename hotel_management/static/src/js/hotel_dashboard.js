/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";


export class HotelDashboard extends Component {
    static template = "hotel_management.HotelDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: null,
            error: null,
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.orm.call(
                "hotel.dashboard", "get_dashboard_data", [],
            );
            this.state.data = data;
        } catch (e) {
            console.error("Hotel dashboard load failed:", e);
            this.state.error = e.message || String(e);
        } finally {
            this.state.loading = false;
        }
    }

    _openAction(resModel, domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: resModel,
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: domain,
            target: "current",
        });
    }

    openArrivals() {
        this._openAction(
            "hotel.reservation",
            [["check_in_date", "=", this.state.data.today],
             ["state", "=", "confirmed"]],
            "Arrivals Today",
        );
    }

    openDepartures() {
        this._openAction(
            "hotel.reservation",
            [["check_out_date", "=", this.state.data.today],
             ["state", "=", "checked_in"]],
            "Departures Today",
        );
    }

    openInHouse() {
        this._openAction(
            "hotel.reservation",
            [["state", "=", "checked_in"]],
            "In-House Guests",
        );
    }

    openUrgentTasks() {
        this._openAction(
            "hotel.housekeeping.task",
            [["state", "in", ["pending", "in_progress"]],
             ["priority", "in", ["1", "2"]]],
            "Urgent Housekeeping Tasks",
        );
    }

    openAllTasks() {
        this._openAction(
            "hotel.housekeeping.task",
            [["state", "in", ["pending", "in_progress"]]],
            "Open Housekeeping Tasks",
        );
    }

    openToInvoice() {
        this._openAction(
            "hotel.reservation",
            [["invoice_status", "=", "to_invoice"],
             ["state", "=", "checked_out"]],
            "Reservations To Invoice",
        );
    }

    openCleanRooms() {
        this._openAction(
            "hotel.room",
            [["housekeeping_state", "=", "clean"],
             ["maintenance_hold", "=", false]],
            "Clean Rooms",
        );
    }

    openDirtyRooms() {
        this._openAction(
            "hotel.room",
            [["housekeeping_state", "=", "dirty"]],
            "Dirty Rooms",
        );
    }

    openCleaningRooms() {
        this._openAction(
            "hotel.room",
            [["housekeeping_state", "=", "cleaning"]],
            "Rooms Being Cleaned",
        );
    }

    openMaintenanceRooms() {
        this._openAction(
            "hotel.room",
            [["maintenance_hold", "=", true]],
            "Rooms Under Maintenance",
        );
    }

    openOrdersInProgress() {
        this._openAction(
            "hotel.room.service.order",
            [["state", "in", ["draft", "preparing"]]],
            "Orders In Progress",
        );
    }
}

registry.category("actions").add("hotel_dashboard", HotelDashboard);