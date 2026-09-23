/** @odoo-module */

import { registry } from "@web/core/registry";
import { today } from "@web/core/l10n/dates";
import { dateField, DateTimeField } from "@web/views/fields/datetime/datetime_field";

/**
 * Date field where the minimum selectable date is the day after check-in,
 * or tomorrow when check-in has not been selected yet.
 */
class HotelDateAfterField extends DateTimeField {
    parseLimitDate(value) {
        if (value === "tomorrow") {
            const checkIn = this.props.record.data.check_in_date;
            return (checkIn || today()).plus({ days: 1 }).startOf("day");
        }
        return super.parseLimitDate(value);
    }
}

registry.category("fields").add("hotel_date_after", {
    ...dateField,
    component: HotelDateAfterField,
});