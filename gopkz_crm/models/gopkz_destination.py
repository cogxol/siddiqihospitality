# -*- coding: utf-8 -*-
from odoo import fields, models


class GopkzDestination(models.Model):
    _name = 'gopkz.destination'
    _description = 'Destination'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)
