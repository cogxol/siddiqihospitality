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

    # ── Constraints ──────────────────────────────────────────────────────────

    @api.constrains('x_commission_percentage')
    def _check_commission_percentage(self):
        for partner in self:
            if partner.x_commission_percentage < 0 or partner.x_commission_percentage > 100:
                raise ValidationError(
                    f'Commission % must be between 0 and 100 '
                    f'(got {partner.x_commission_percentage}).'
                )
