# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GopkzScoringCriteria(models.Model):
    _name = 'gopkz.scoring.criteria'
    _description = 'Vendor Scoring Criteria'
    _order = 'category_id, sequence, name'

    name = fields.Char(string='Criterion Name', required=True)
    category_id = fields.Many2one(
        'gopkz.vendor.category',
        string='Vendor Category',
        required=True,
        ondelete='restrict',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    weight = fields.Integer(string='Weight (%)', required=True)
    evaluation_guide = fields.Text(string='Evaluation Guide')
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('weight', 'category_id', 'active')
    def _check_weights_sum_to_100(self):
        """Active criteria for a given category must sum to exactly 100.

        Skipped during module installation/update (install_mode context) because
        seed data records are created one at a time — the sum only reaches 100
        after all records for a category are loaded.
        """
        if self.env.context.get('install_mode'):
            return
        affected_categories = self.mapped('category_id')
        for category in affected_categories:
            active_criteria = self.search([
                ('category_id', '=', category.id),
                ('active', '=', True),
            ])
            total = sum(active_criteria.mapped('weight'))
            if total != 100:
                raise ValidationError(
                    f'The weights of active scoring criteria for category '
                    f'"{category.name}" must sum to 100 (currently {total}). '
                    f'Please adjust the weights before saving.'
                )
