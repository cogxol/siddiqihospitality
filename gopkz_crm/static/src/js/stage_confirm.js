/** @odoo-module **/
/**
 * Stage-change confirmation for CRM leads.
 *
 * Patches StatusBarField.selectItem so that clicking a stage in the form
 * status bar on a crm.lead record shows a browser confirm() dialog before
 * committing the change.  This prevents accidental stage moves.
 *
 * The patch is limited to crm.lead records so no other models are affected.
 */

import { patch } from "@web/core/utils/patch";
import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { _t } from "@web/core/l10n/translation";

patch(StatusBarField.prototype, {
    async selectItem(item) {
        // Already on this stage — nothing to do.
        if (item.isSelected) {
            return super.selectItem(item);
        }
        // Only intercept on CRM lead / opportunity forms.
        if (this.props.record?.resModel !== "crm.lead") {
            return super.selectItem(item);
        }
        // Show a native confirm dialog before committing the stage change.
        if (!window.confirm(_t("Are you sure you want to change the stage?"))) {
            return;
        }
        return super.selectItem(item);
    },
});
