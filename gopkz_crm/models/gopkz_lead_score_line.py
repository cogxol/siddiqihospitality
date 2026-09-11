# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GopkzLeadScoreLine(models.Model):
    _name = 'gopkz.lead.score.line'
    _description = 'Vendor Lead Score Line'
    _order = 'criteria_id'

    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
        required=True,
        ondelete='cascade',
        index=True,
    )
    criteria_id = fields.Many2one(
        'gopkz.scoring.criteria',
        string='Criterion',
        required=True,
    )
    # related + stored: the server recomputes this after creation, so no
    # force_save needed in the view (Section 0.1).
    weight = fields.Integer(
        string='Weight (%)',
        related='criteria_id.weight',
        store=True,
        readonly=True,
    )
    score = fields.Float(
        string='Score (0–100)',
        digits=(6, 2),
        default=0.0,
    )
    # Not readonly — client includes it in the save payload without force_save.
    score_entered = fields.Boolean(
        string='Score Entered',
        default=False,
        store=True,
    )
    weighted_score = fields.Float(
        string='Weighted Score',
        compute='_compute_weighted_score',
        store=True,
        digits=(6, 2),
    )

    @api.depends('weight', 'score')
    def _compute_weighted_score(self):
        for line in self:
            line.weighted_score = line.weight * line.score / 100.0

    @api.onchange('score')
    def _onchange_score(self):
        """Flip score_entered to True the moment the user edits the field,
        including a deliberate 0.  This is the gate checked by action_confirm_scoring."""
        self.score_entered = True

    def write(self, vals):
        """Server-side fallback: whenever 'score' is explicitly written
        (e.g. non-zero values saved via the form), mark the line as entered.
        This covers cases where the onchange result is not round-tripped by
        the client (invisible field, same-value write, etc.)."""
        if 'score' in vals and not vals.get('score_entered'):
            vals = dict(vals, score_entered=True)
        return super().write(vals)

    @api.constrains('score')
    def _check_score_range(self):
        for line in self:
            if line.score < 0 or line.score > 100:
                raise ValidationError(
                    f'Score must be between 0 and 100 (got {line.score}).'
                )
