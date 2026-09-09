# -*- coding: utf-8 -*-
from odoo import fields, models


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
