# -*- coding: utf-8 -*-
from odoo import models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def write(self, vals):
        """After the stage write completes, create helpdesk tickets when a
        Hot Lead Recovery lead reaches the Recovered (won) stage.

        This runs AFTER super().write() so the lead is already persisted at
        the new stage before _create_helpdesk_tickets reads lead.stage_id.

        Idempotent: checks for existing tickets on the lead before creating
        new ones so repeated writes to Recovered don't duplicate tickets.
        """
        res = super().write(vals)
        if vals.get('stage_id'):
            recovered = self.env.ref(
                'gopkz_crm.stage_hlr_recovered', raise_if_not_found=False
            )
            hlr_team = self.env.ref(
                'gopkz_crm.team_hot_lead_recovery', raise_if_not_found=False
            )
            if recovered and hlr_team:
                for lead in self:
                    if (lead.team_id.id == hlr_team.id
                            and lead.stage_id.id == recovered.id
                            and vals['stage_id'] == recovered.id):
                        # Idempotency guard: don't double-create on re-save
                        existing = self.env['helpdesk.ticket'].search(
                            [('x_hlr_lead_id', '=', lead.id)], limit=1
                        )
                        if not existing:
                            lead._create_helpdesk_tickets()
        return res

    def _create_helpdesk_tickets(self):
        """Create one Supplier Confirmation ticket per vendor line (Track A)
        and one Customer Experience ticket for the whole booking (Track B).

        Called when this lead moves to the Recovered stage.
        """
        self.ensure_one()
        ticket = self.env['helpdesk.ticket']
        conf_pending = self.env.ref(
            'gopkz_helpdesk.stage_supplier_confirmation_pending',
            raise_if_not_found=False,
        )
        supplier_team = self.env.ref(
            'gopkz_helpdesk.team_supplier_operations',
            raise_if_not_found=False,
        )
        cx_team = self.env.ref(
            'gopkz_helpdesk.team_customer_experience',
            raise_if_not_found=False,
        )
        pre_travel = self.env.ref(
            'gopkz_helpdesk.stage_cx_pre_travel',
            raise_if_not_found=False,
        )

        # ── Track A: one ticket per vendor line ───────────────────────────────
        if supplier_team:
            for line in self.hlr_vendor_line_ids:
                vals = {
                    'name': f'Supplier Confirmation — {self.name} — {line.vendor_id.name}',
                    'team_id': supplier_team.id,
                    'x_ticket_type': 'supplier_confirmation',
                    'x_booking_vendor_line_id': line.id,
                    'x_vendor_business_id': line.vendor_id.id,
                    'x_hlr_lead_id': self.id,
                    'partner_id': line.vendor_id.id,
                }
                if conf_pending:
                    vals['stage_id'] = conf_pending.id
                ticket.create(vals)

        # ── Track B: one ticket for the whole booking ─────────────────────────
        if cx_team:
            # Collect unique service categories from all vendor lines on this booking
            service_cat_ids = list(
                {line.vendor_id.vendor_category_id.id
                 for line in self.hlr_vendor_line_ids
                 if line.vendor_id.vendor_category_id}
            )
            # Primary vendor: use x_vendor_id if set, else first vendor line
            primary_vendor = self.x_vendor_id
            if not primary_vendor and self.hlr_vendor_line_ids:
                primary_vendor = self.hlr_vendor_line_ids[0].vendor_id

            vals = {
                'name': f'Travel Support — {self.name}',
                'team_id': cx_team.id,
                'x_ticket_type': 'travel_support',
                'x_hlr_lead_id': self.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'x_vendor_business_id': primary_vendor.id if primary_vendor else False,
            }
            if service_cat_ids:
                vals['x_service_category_ids'] = [(6, 0, service_cat_ids)]
            if pre_travel:
                vals['stage_id'] = pre_travel.id
            ticket.create(vals)
