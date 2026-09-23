# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Relationship Management — customer booking stats ──────────────────────
    # Computed from Hot Lead Recovery leads where this partner is the customer.
    # Follows the exact pattern of hlr_last_booking_date / hlr_total_commission_earned
    # in gopkz_crm/models/res_partner.py.

    x_customer_total_bookings = fields.Integer(
        string='Total Bookings',
        compute='_compute_x_customer_stats',
        store=True,
        readonly=True,
        help='Number of won Hot Lead Recovery leads where this partner is the customer.',
    )
    x_customer_last_booking_date = fields.Datetime(
        string='Last Customer Booking',
        compute='_compute_x_customer_stats',
        store=True,
        readonly=True,
        help='Date the most recent won Hot Lead Recovery booking was closed.',
    )
    x_customer_is_repeat = fields.Boolean(
        string='Repeat Customer',
        compute='_compute_x_customer_stats',
        store=True,
        readonly=True,
        help='True when this customer has more than one won HLR booking.',
    )

    # ── Support Tickets count ─────────────────────────────────────────────────
    # Drives the smart button on the partner form.
    x_support_ticket_count = fields.Integer(
        string='Support Tickets',
        compute='_compute_x_support_ticket_count',
        store=False,
    )

    # ── Compute methods ───────────────────────────────────────────────────────

    @api.depends(
        'opportunity_ids.stage_id.is_won',
        'opportunity_ids.team_id',
        'opportunity_ids.date_closed',
    )
    def _compute_x_customer_stats(self):
        """Aggregate HLR won-lead stats for this partner as a customer."""
        hlr_team = self.env.ref(
            'gopkz_crm.team_hot_lead_recovery', raise_if_not_found=False
        )
        for partner in self:
            if not hlr_team:
                partner.x_customer_total_bookings = 0
                partner.x_customer_last_booking_date = False
                partner.x_customer_is_repeat = False
                continue
            won = [
                lead
                for lead in partner.opportunity_ids
                if lead.team_id.id == hlr_team.id and lead.stage_id.is_won
            ]
            partner.x_customer_total_bookings = len(won)
            dates = [l.date_closed for l in won if l.date_closed]
            partner.x_customer_last_booking_date = max(dates) if dates else False
            partner.x_customer_is_repeat = len(won) > 1

    def _compute_x_support_ticket_count(self):
        """Count helpdesk tickets where this partner appears as:
        • partner_id (the ticket's direct customer / contact)
        • x_vendor_business_id (the business a ticket is about)
        • x_corporate_account_id (the corporate account a ticket is about)
        """
        ticket = self.env['helpdesk.ticket']
        for partner in self:
            count = ticket.search_count([
                '|', '|',
                ('partner_id', '=', partner.id),
                ('x_vendor_business_id', '=', partner.id),
                ('x_corporate_account_id', '=', partner.id),
            ])
            partner.x_support_ticket_count = count

    # ── Action ───────────────────────────────────────────────────────────────

    def action_view_support_tickets(self):
        """Open the support tickets related to this partner."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Support Tickets — {self.name}',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'list,form',
            'domain': [
                '|', '|',
                ('partner_id', '=', self.id),
                ('x_vendor_business_id', '=', self.id),
                ('x_corporate_account_id', '=', self.id),
            ],
            'context': {
                'default_partner_id': self.id,
            },
        }
