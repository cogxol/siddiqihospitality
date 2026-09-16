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

    # ── Business contact (partner with a Service Type set) ───────────────────
    vendor_id = fields.Many2one(
        'res.partner',
        string='Business',
        required=True,
        domain=[('vendor_category_id', '!=', False)],
    )
    # Parent vendor company of the selected business — related, read-only.
    vendor_parent_id = fields.Many2one(
        related='vendor_id.parent_id',
        string='Vendor',
        store=False,
        readonly=True,
    )
    # Service Type pulled automatically from the selected business.
    vendor_category_id = fields.Many2one(
        'gopkz.vendor.category',
        string='Service Type',
        related='vendor_id.vendor_category_id',
        store=True,
        readonly=True,
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

    # ── Onchange ─────────────────────────────────────────────────────────────

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        """Auto-fill Commission % from the selected business contact."""
        if self.vendor_id:
            self.commission_pct = self.vendor_id.x_commission_percentage
