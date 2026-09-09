# -*- coding: utf-8 -*-
from odoo import api, fields, models


class GopkzBookingVendorLine(models.Model):
    _name = 'gopkz.booking.vendor.line'
    _description = 'HLR Booking Vendor Line'

    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
        required=True,
        ondelete='cascade',
        index=True,
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain=[('supplier_rank', '>', 0)],
    )
    vendor_category_id = fields.Many2one(
        'gopkz.vendor.category',
        string='Vendor Category',
        related='vendor_id.vendor_category_id',
        store=True,
        readonly=True,
    )
    service_type_id = fields.Many2one(
        'gopkz.service.type',
        string='Service Type',
    )
    destination_id = fields.Many2one(
        'gopkz.destination',
        string='Destination',
    )
    service_date_from = fields.Date(string='Check-in / Travel Date')
    service_date_to = fields.Date(string='Check-out / Return Date')

    # ── Currency & Amounts ───────────────────────────────────────────────────

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='lead_id.company_id.currency_id',
        store=True,
        readonly=True,
    )
    vendor_amount = fields.Monetary(
        string='Vendor Amount',
        currency_field='currency_id',
    )
    commission_pct = fields.Float(
        string='Commission %',
        digits=(5, 2),
    )
    commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        compute='_compute_commission_amount',
        store=True,
        readonly=True,
    )
    payable_vendor_amount = fields.Monetary(
        string='Payable to Vendor',
        currency_field='currency_id',
        compute='_compute_payable_vendor_amount',
        store=True,
        readonly=True,
    )

    # ── Compute methods ──────────────────────────────────────────────────────

    @api.depends('vendor_amount', 'commission_pct')
    def _compute_commission_amount(self):
        for line in self:
            line.commission_amount = line.vendor_amount * line.commission_pct / 100.0

    @api.depends('vendor_amount', 'commission_amount')
    def _compute_payable_vendor_amount(self):
        for line in self:
            line.payable_vendor_amount = line.vendor_amount - line.commission_amount
