# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Vendor Category (controls vendor section visibility) ─────────────────
    vendor_category_id = fields.Many2one(
        'gopkz.vendor.category',
        string='Vendor Category',
    )

    # ── Vendor Data Fields (visible when vendor_category_id is set) ──────────
    x_destination_ids = fields.Many2many(
        'gopkz.destination',
        string='Destinations',
    )
    x_capacity = fields.Integer(
        string='Inventory / Capacity',
        help='Number of rooms, vehicles, or products, depending on vendor type.',
    )
    x_commission_percentage = fields.Float(
        string='Commission %',
        digits=(6, 2),
    )
    x_settlement_cycle = fields.Selection(
        selection=[
            ('same_day', 'Same Day'),
            ('weekly', 'Weekly'),
            ('fortnightly', 'Fortnightly'),
        ],
        string='Settlement Cycle',
    )
    x_has_api_extranet = fields.Boolean(
        string='Has API / Extranet Integration',
        default=False,
    )

    # ── Hot Lead Recovery ────────────────────────────────────────────────────

    # Inverse of gopkz.booking.vendor.line.vendor_id — used as a @api.depends
    # anchor so the ORM can propagate lead stage/date changes to this partner.
    hlr_vendor_line_ids = fields.One2many(
        'gopkz.booking.vendor.line',
        'vendor_id',
        string='HLR Vendor Lines',
    )

    hlr_last_booking_date = fields.Datetime(
        string='Last Booking Date',
        compute='_compute_hlr_last_booking_date',
        store=True,
        readonly=True,
        help='Latest date_closed of a won Hot Lead Recovery lead this vendor '
             'appears on.',
    )

    # ── Corporate Account Fields ─────────────────────────────────────────────
    x_is_corporate_account = fields.Boolean(
        string='Corporate Account',
        default=False,
    )
    x_company_size = fields.Selection(
        selection=[
            ('1_10', '1–10'),
            ('11_50', '11–50'),
            ('51_200', '51–200'),
            ('200_plus', '200+'),
        ],
        string='Company Size',
    )
    x_annual_travel_volume = fields.Integer(
        string='Est. Annual Trips',
    )
    x_current_travel_provider = fields.Char(
        string='Current Travel Provider',
    )

    # ── Compute methods ──────────────────────────────────────────────────────

    @api.depends(
        'hlr_vendor_line_ids.lead_id.date_closed',
        'hlr_vendor_line_ids.lead_id.stage_id.is_won',
        'hlr_vendor_line_ids.lead_id.team_id',
    )
    def _compute_hlr_last_booking_date(self):
        """Latest date_closed of a won HLR lead this partner appears on as a
        vendor.  A lead counts as "won" when its stage has is_won=True or when
        date_closed is already set."""
        hlr_team = self.env.ref(
            'gopkz_crm.team_hot_lead_recovery', raise_if_not_found=False
        )
        for partner in self:
            if not hlr_team:
                partner.hlr_last_booking_date = False
                continue
            dates = [
                line.lead_id.date_closed
                for line in partner.hlr_vendor_line_ids
                if line.lead_id.team_id.id == hlr_team.id
                and (line.lead_id.stage_id.is_won or line.lead_id.date_closed)
                and line.lead_id.date_closed
            ]
            partner.hlr_last_booking_date = max(dates) if dates else False

    # ── Constraints ──────────────────────────────────────────────────────────

    @api.constrains('x_commission_percentage')
    def _check_commission_percentage(self):
        for partner in self:
            if partner.x_commission_percentage < 0 or partner.x_commission_percentage > 100:
                raise ValidationError(
                    f'Commission % must be between 0 and 100 '
                    f'(got {partner.x_commission_percentage}).'
                )
