# -*- coding: utf-8 -*-
from odoo import fields, models


class GopkzServiceType(models.Model):
    _name = 'gopkz.service.type'
    _description = 'Service Type'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)
