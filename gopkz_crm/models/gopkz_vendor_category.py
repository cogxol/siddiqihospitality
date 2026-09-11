# -*- coding: utf-8 -*-
from odoo import fields, models


class GopkzVendorCategory(models.Model):
    _name = 'gopkz.vendor.category'
    _description = 'Vendor Category'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)
