# -*- coding: utf-8 -*-
import calendar
from odoo import api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ── Booking ID ──────────────────────────────────────────────────────────
    booking_id = fields.Char(
        string='Booking ID',
        readonly=True,
        copy=False,
        tracking=True,
    )

    # ── Vendor Category ──────────────────────────────────────────────────────
    vendor_category_id = fields.Many2one(
        'gopkz.vendor.category',
        string='Vendor Category',
        tracking=True,
    )

    # ── Scoring lines ────────────────────────────────────────────────────────
    score_line_ids = fields.One2many(
        'gopkz.lead.score.line',
        'lead_id',
        string='Score Lines',
    )

    # ── Computed totals ──────────────────────────────────────────────────────
    total_score = fields.Float(
        string='Total Score',
        compute='_compute_total_score',
        store=True,
        digits=(6, 2),
    )
    score_tier = fields.Selection(
        selection=[
            ('A', 'A  (85 – 100)'),
            ('B', 'B  (70 – 84)'),
            ('C', 'C  (55 – 69)'),
            ('D', 'D  (40 – 54)'),
            ('E', 'E  (< 40)'),
        ],
        string='Score Tier',
        compute='_compute_score_tier',
        store=True,
    )

    # ── Gate flag ────────────────────────────────────────────────────────────
    scoring_confirmed = fields.Boolean(
        string='Scoring Confirmed',
        default=False,
        store=True,
    )

    # ── Lost reason "Other" detail ───────────────────────────────────────────
    x_lost_reason_detail = fields.Char(
        string='Other Reason Detail',
        help='Manual reason text entered when "Other" is selected as the lost reason.',
    )
    # Non-stored helper: True when lost_reason_id is our "Other" record.
    # Used in the view to toggle x_lost_reason_detail visibility without
    # relying on ref() in XML expressions (which isn't supported there).
    x_is_lost_other = fields.Boolean(
        compute='_compute_x_is_lost_other',
        store=False,
    )

    # ── Hot Lead Recovery vendor lines ───────────────────────────────────────
    hlr_vendor_line_ids = fields.One2many(
        'gopkz.booking.vendor.line',
        'lead_id',
        string='Vendors',
    )

    # ── Hot Lead Recovery customer type ─────────────────────────────────────
    hlr_customer_type = fields.Selection(
        selection=[
            ('corporate_reservation', 'Corporate Reservation'),
            ('direct_customer', 'Direct Customer'),
        ],
        string='Customer Type',
        tracking=True,
    )

    # ── UI helpers (non-stored) ──────────────────────────────────────────────
    is_vendor_onboarding = fields.Boolean(
        string='Is Vendor Onboarding Team',
        compute='_compute_is_vendor_onboarding',
        store=False,
    )

    is_hot_lead_recovery = fields.Boolean(
        string='Is Hot Lead Recovery Team',
        compute='_compute_is_hot_lead_recovery',
        store=False,
    )

    # True when the lead is on the Vendor Onboarding team AND past Qualifying.
    # When True the score lines become read-only and Confirm Scoring is hidden.
    scoring_locked = fields.Boolean(
        string='Scoring Locked',
        compute='_compute_scoring_locked',
        store=False,
    )

    # True only for Odoo System Administrators.
    # Drives readonly="not is_pipeline_editor" on the team_id (Pipeline) field
    # so that ordinary users can see the pipeline but cannot reassign it.
    # @api.depends_context('uid') caches the result per user, not per record.
    is_pipeline_editor = fields.Boolean(
        string='Can Edit Pipeline',
        compute='_compute_is_pipeline_editor',
        store=False,
    )

    # ── Compute methods ──────────────────────────────────────────────────────

    @api.depends('team_id')
    def _compute_is_vendor_onboarding(self):
        vo_team = self.env.ref(
            'gopkz_crm.team_vendor_onboarding', raise_if_not_found=False
        )
        for lead in self:
            lead.is_vendor_onboarding = bool(
                vo_team and lead.team_id.id == vo_team.id
            )

    @api.depends('team_id')
    def _compute_is_hot_lead_recovery(self):
        hlr_team = self.env.ref(
            'gopkz_crm.team_hot_lead_recovery', raise_if_not_found=False
        )
        for lead in self:
            lead.is_hot_lead_recovery = bool(
                hlr_team and lead.team_id.id == hlr_team.id
            )

    @api.depends('team_id', 'stage_id')
    def _compute_scoring_locked(self):
        """Lock scoring once the lead has advanced past Qualifying in the
        Vendor Onboarding pipeline.  Moving back to Qualifying unlocks it."""
        vo_team = self.env.ref(
            'gopkz_crm.team_vendor_onboarding', raise_if_not_found=False
        )
        qualifying = self.env.ref(
            'gopkz_crm.stage_vo_qualifying', raise_if_not_found=False
        )
        for lead in self:
            lead.scoring_locked = bool(
                vo_team
                and qualifying
                and lead.team_id.id == vo_team.id
                and lead.stage_id.sequence > qualifying.sequence
            )

    @api.depends_context('uid')
    def _compute_is_pipeline_editor(self):
        """True only for Odoo System Administrators.
        Cached per user (depends_context uid) so the flag re-evaluates
        when a different user opens the record — not on every field change.
        """
        is_admin = self.env.user.has_group('base.group_system')
        for lead in self:
            lead.is_pipeline_editor = is_admin

    @api.depends('lost_reason_id')
    def _compute_x_is_lost_other(self):
        other = self.env.ref('gopkz_crm.lost_reason_other', raise_if_not_found=False)
        for lead in self:
            lead.x_is_lost_other = bool(other and lead.lost_reason_id == other)

    @api.depends('score_line_ids.weighted_score')
    def _compute_total_score(self):
        for lead in self:
            lead.total_score = sum(lead.score_line_ids.mapped('weighted_score'))

    @api.depends('total_score')
    def _compute_score_tier(self):
        for lead in self:
            score = lead.total_score
            if score >= 85:
                lead.score_tier = 'A'
            elif score >= 70:
                lead.score_tier = 'B'
            elif score >= 55:
                lead.score_tier = 'C'
            elif score >= 40:
                lead.score_tier = 'D'
            else:
                lead.score_tier = 'E'

    # ── Onchange handlers ────────────────────────────────────────────────────

    @api.onchange('vendor_category_id')
    def _onchange_vendor_category_id(self):
        """Rebuild score lines whenever the category changes.
        Clears all existing lines and creates one per active criterion for the
        new category.  Also clears scoring_confirmed so the badge resets.
        """
        # Clear existing lines
        self.score_line_ids = [(5, 0, 0)]
        self.scoring_confirmed = False

        if self.vendor_category_id:
            criteria = self.env['gopkz.scoring.criteria'].search([
                ('category_id', '=', self.vendor_category_id.id),
                ('active', '=', True),
            ])
            self.score_line_ids = [
                (0, 0, {
                    'criteria_id': c.id,
                    'score': 0.0,
                    'score_entered': False,
                })
                for c in criteria
            ]

    @api.onchange('score_line_ids')
    def _onchange_score_line_ids(self):
        """Clear the confirmed badge when score lines change — but only while
        still at or before Qualifying.  Past Qualifying the scores are locked
        so this onchange won't fire from the UI anyway, but the guard keeps
        the ORM path consistent."""
        if self.scoring_confirmed and not self.scoring_locked:
            self.scoring_confirmed = False

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_confirm_scoring(self):
        """Confirm that all criteria have been explicitly scored.

        Refuses (hard block) if any line still has score_entered = False.
        A deliberate 0 is accepted — the gate checks the flag, not the value.
        """
        self.ensure_one()
        unscored = self.score_line_ids.filtered(lambda l: not l.score_entered)
        if unscored:
            criteria_names = ', '.join(
                unscored.mapped('criteria_id.name')
            )
            raise UserError(
                f'{len(unscored)} criterion/criteria have not been scored yet: '
                f'{criteria_names}.\n\n'
                'Please enter a score (including a deliberate 0) for every '
                'criterion before confirming.'
            )
        # Only does two things: gate check (above) and set flag (below).
        self.write({'scoring_confirmed': True})

    # ── Create override — auto-assign sequential Booking ID ─────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('booking_id'):
                vals['booking_id'] = self._generate_booking_id()
        return super().create(vals_list)

    def _generate_booking_id(self):
        """Return the next booking ID, resetting the counter every month.

        Odoo's ir.sequence with use_date_range=True resets per date-range
        record.  By default it creates *yearly* ranges; we pre-create a
        monthly range before calling next_by_code() so the counter starts
        fresh on the 1st of each month while the prefix (BK%(y)s%(month)s)
        correctly reflects the range's date_from.
        """
        today = fields.Date.today()
        seq = self.env['ir.sequence'].sudo().search(
            [('code', '=', 'crm.lead.booking')], limit=1
        )
        if not seq:
            return False

        first_day = today.replace(day=1)
        last_day = today.replace(
            day=calendar.monthrange(today.year, today.month)[1]
        )

        # Create the monthly date-range if it does not yet exist.
        existing = self.env['ir.sequence.date_range'].sudo().search([
            ('sequence_id', '=', seq.id),
            ('date_from', '=', first_day),
        ], limit=1)
        if not existing:
            self.env['ir.sequence.date_range'].sudo().create({
                'sequence_id': seq.id,
                'date_from': first_day,
                'date_to': last_day,
            })

        # next_by_code() will now find the monthly range and use its counter.
        return self.env['ir.sequence'].next_by_code('crm.lead.booking')

    # ── Write override — scoring gate on stage progression ───────────────────

    def write(self, vals):
        """Block Vendor Onboarding leads from moving past Qualifying without
        confirmed scoring.

        Applies the Section 0.2 pattern for determining the effective team:
        reads vals.get('team_id') first (with an explicit is-not-None check),
        falling back to the record's current team_id only when team_id is
        absent from this write entirely.

        Marking Lost (active=False or lost_reason_id in same write) is always
        exempt from this check.
        """
        if 'stage_id' in vals and not self.env.context.get('skip_scoring_gate'):
            # Marking Lost is unconditionally exempt from the scoring gate.
            is_lost = (
                vals.get('active') is False
                or 'lost_reason_id' in vals
            )

            if not is_lost:
                new_stage_id = vals.get('stage_id')
                if new_stage_id:
                    target_stage = self.env['crm.stage'].browse(new_stage_id)
                    vo_team = self.env.ref(
                        'gopkz_crm.team_vendor_onboarding',
                        raise_if_not_found=False,
                    )
                    qualifying_stage = self.env.ref(
                        'gopkz_crm.stage_vo_qualifying',
                        raise_if_not_found=False,
                    )

                    if vo_team and qualifying_stage:
                        for lead in self:
                            # Section 0.2: read effective team from vals first.
                            # vals.get('team_id') returns None when the key is
                            # absent — not the same as an intentional clear (False/0).
                            new_team_id = vals.get('team_id')
                            effective_team_id = (
                                new_team_id
                                if new_team_id is not None
                                else lead.team_id.id
                            )

                            if effective_team_id == vo_team.id:
                                if target_stage.sequence > qualifying_stage.sequence:
                                    if not lead.scoring_confirmed:
                                        raise UserError(
                                            f'"{lead.name}" cannot advance past '
                                            'Qualifying in the Vendor Onboarding '
                                            'pipeline until scoring is confirmed.\n\n'
                                            'Open the Vendor Scoring tab and click '
                                            '"Confirm Scoring" after entering all scores.'
                                        )

        return super().write(vals)
