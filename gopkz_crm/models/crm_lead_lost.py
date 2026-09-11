# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class CrmLeadLost(models.TransientModel):
    _inherit = 'crm.lead.lost'

    # ── "Other" reason detail ─────────────────────────────────────────────────
    lost_reason_other = fields.Char(
        string='Please specify',
        help='Required when "Other" is selected as the lost reason.',
    )

    # Computed helper — drives visibility and required-ness in the view.
    is_other_reason = fields.Boolean(
        string='Is Other Reason',
        compute='_compute_is_other_reason',
        store=False,
    )

    @api.depends('lost_reason_id')
    def _compute_is_other_reason(self):
        other_reason = self.env.ref(
            'gopkz_crm.lost_reason_other', raise_if_not_found=False
        )
        for wizard in self:
            wizard.is_other_reason = bool(
                other_reason and wizard.lost_reason_id == other_reason
            )

    # ── Override action to add validation and store "Other" detail ────────────

    def action_lost_reason_apply(self):
        self.ensure_one()

        # 1. Lost reason is mandatory.
        if not self.lost_reason_id:
            raise UserError(
                'Please select a lost reason before marking the lead as lost.'
            )

        # 2. When "Other" is selected, the detail text is also mandatory.
        other_reason = self.env.ref(
            'gopkz_crm.lost_reason_other', raise_if_not_found=False
        )
        if other_reason and self.lost_reason_id == other_reason:
            detail = (self.lost_reason_other or '').strip()
            if not detail:
                raise UserError(
                    'Please describe the reason in the "Please specify" field '
                    'when "Other" is selected.'
                )

        # 3. Run the standard mark-lost flow (logs feedback, archives lead,
        #    writes lost_reason_id + probability = 0).
        res = super().action_lost_reason_apply()

        # 4. Persist the "Other" detail text on the now-archived lead(s).
        if other_reason and self.lost_reason_id == other_reason and self.lost_reason_other:
            self.lead_ids.with_context(active_test=False).write({
                'x_lost_reason_detail': self.lost_reason_other.strip(),
            })

        return res
