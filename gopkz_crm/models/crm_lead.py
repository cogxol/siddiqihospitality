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

    # ── Service Type ─────────────────────────────────────────────────────────
    # Stored, editable field.  Auto-filled from the business contact's service
    # type when partner_id is set/changed, but the user can override it.
    # Changing it triggers _onchange_vendor_category_id which rebuilds the
    # scoring criteria lines.
    vendor_category_id = fields.Many2one(
        'gopkz.vendor.category',
        string='Service Type',
        tracking=True,
    )

    # ── Vendor (parent company of the business contact) ─────────────────────
    # Related field: always mirrors partner_id.parent_id.
    # Visible on every lead where the contact is a Business contact.
    x_vendor_id = fields.Many2one(
        related='partner_id.parent_id',
        string='Vendor',
        store=False,
        readonly=True,
    )

    # Helper: True when the linked contact is a Business (has a Service Type).
    # Used in the view to show/hide the Vendor field without a server round-trip.
    x_partner_is_business = fields.Boolean(
        related='partner_id.is_business',
        string='Partner Is Business',
        store=False,
    )

    # ── Business Channel (related from business contact) ─────────────────────
    x_business_channel = fields.Selection(
        related='partner_id.x_business_channel',
        string='Business Channel',
        store=False,
        readonly=False,
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

    # ── Gate flags ───────────────────────────────────────────────────────────
    scoring_confirmed = fields.Boolean(
        string='Scoring Confirmed',
        default=False,
        store=True,
    )
    x_agreement_approved = fields.Boolean(
        string='Agreement Approved',
        default=False,
        store=True,
        tracking=True,
    )

    # ── Attachment fields (Agreement stage and later) ────────────────────────
    x_attachment_agreement_url = fields.Char(
        string='Signed Agreement',
        help='Hyperlink to the signed agreement document.',
    )
    x_attachment_pictures_url = fields.Char(
        string='Pictures',
        help='Hyperlink to property/business pictures.',
    )
    x_attachment_other_url = fields.Char(
        string='Other Documentation',
        help='Hyperlink to any other supporting documentation.',
    )
    x_attachment_agreement_submitted = fields.Boolean(
        string='Agreement Submitted',
        default=False,
        store=True,
    )
    x_attachment_pictures_submitted = fields.Boolean(
        string='Pictures Submitted',
        default=False,
        store=True,
    )
    x_attachment_other_submitted = fields.Boolean(
        string='Other Docs Submitted',
        default=False,
        store=True,
    )
    x_all_attachments_submitted = fields.Boolean(
        string='All Documents Submitted',
        compute='_compute_x_all_attachments_submitted',
        store=False,
    )

    # ── Lost reason "Other" detail ───────────────────────────────────────────
    x_lost_reason_detail = fields.Char(
        string='Other Reason Detail',
        help='Manual reason text when "Other" is selected as the lost reason.',
    )
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

    # ── Hot Lead Recovery trip summary ───────────────────────────────────────
    hlr_destination_ids = fields.Many2many(
        'gopkz.destination',
        relation='crm_lead_hlr_destination_rel',
        column1='lead_id',
        column2='destination_id',
        string='Destinations',
        compute='_compute_hlr_destinations',
        store=True,
        readonly=True,
    )
    hlr_travel_date_from = fields.Date(
        string='Travel From',
        compute='_compute_hlr_travel_dates',
        store=True,
        readonly=True,
    )
    hlr_travel_date_to = fields.Date(
        string='Travel To',
        compute='_compute_hlr_travel_dates',
        store=True,
        readonly=True,
    )

    # ── Hot Lead Recovery financial totals ───────────────────────────────────
    hlr_total_vendor_amount = fields.Monetary(
        string='Total Vendor Amount',
        compute='_compute_hlr_totals',
        store=True,
        readonly=True,
        currency_field='company_currency',
    )
    hlr_total_commission = fields.Monetary(
        string='Total Commission',
        compute='_compute_hlr_totals',
        store=True,
        readonly=True,
        currency_field='company_currency',
    )
    hlr_total_payable_vendor = fields.Monetary(
        string='Total Payable to Vendors',
        compute='_compute_hlr_totals',
        store=True,
        readonly=True,
        currency_field='company_currency',
    )

    # ── Hot Lead Recovery customer type & payment status ─────────────────────
    hlr_customer_type = fields.Selection(
        selection=[
            ('corporate_reservation', 'Corporate Reservation'),
            ('direct_customer', 'Direct Customer'),
        ],
        string='Customer Type',
        tracking=True,
    )
    x_payment_status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('partial', 'Partially Paid'),
            ('paid', 'Paid'),
            ('refunded', 'Refunded'),
        ],
        string='Payment Status',
        tracking=True,
    )

    # ── Refund Policy ────────────────────────────────────────────────────────
    x_refund_policy = fields.Html(
        string='Refund Policy',
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
    is_corporate_sales = fields.Boolean(
        string='Is Corporate Sales Team',
        compute='_compute_is_corporate_sales',
        store=False,
    )
    x_is_agreement_or_later = fields.Boolean(
        string='Is Agreement Stage or Later',
        compute='_compute_x_is_agreement_or_later',
        store=False,
    )
    x_can_approve = fields.Boolean(
        string='Can Approve',
        compute='_compute_x_can_approve',
        store=False,
    )
    scoring_locked = fields.Boolean(
        string='Scoring Locked',
        compute='_compute_scoring_locked',
        store=False,
    )
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

    @api.depends('team_id')
    def _compute_is_corporate_sales(self):
        cs_team = self.env.ref(
            'gopkz_crm.team_corporate_sales', raise_if_not_found=False
        )
        for lead in self:
            lead.is_corporate_sales = bool(
                cs_team and lead.team_id.id == cs_team.id
            )

    @api.depends('team_id', 'stage_id')
    def _compute_scoring_locked(self):
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

    @api.depends('team_id', 'stage_id')
    def _compute_x_is_agreement_or_later(self):
        vo_team = self.env.ref(
            'gopkz_crm.team_vendor_onboarding', raise_if_not_found=False
        )
        agreement_stage = self.env.ref(
            'gopkz_crm.stage_vo_agreement', raise_if_not_found=False
        )
        for lead in self:
            lead.x_is_agreement_or_later = bool(
                vo_team and agreement_stage
                and lead.team_id.id == vo_team.id
                and lead.stage_id.sequence >= agreement_stage.sequence
            )

    @api.depends(
        'partner_id',
        'partner_id.x_operations_user_id',
        'partner_id.parent_id',
        'partner_id.parent_id.x_operations_user_id',
    )
    @api.depends_context('uid')
    def _compute_x_can_approve(self):
        # Administrators can always approve.
        is_admin = self.env.user.has_group('base.group_system')
        for lead in self:
            if is_admin:
                lead.x_can_approve = True
            else:
                ops_user = lead._get_ops_user()
                lead.x_can_approve = bool(ops_user and ops_user.id == self.env.uid)

    @api.depends_context('uid')
    def _compute_is_pipeline_editor(self):
        is_admin = self.env.user.has_group('base.group_system')
        for lead in self:
            lead.is_pipeline_editor = is_admin

    @api.depends(
        'x_attachment_agreement_submitted',
        'x_attachment_pictures_submitted',
        'x_attachment_other_submitted',
    )
    def _compute_x_all_attachments_submitted(self):
        for lead in self:
            lead.x_all_attachments_submitted = (
                lead.x_attachment_agreement_submitted
                and lead.x_attachment_pictures_submitted
                and lead.x_attachment_other_submitted
            )

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

    @api.depends(
        'hlr_vendor_line_ids.vendor_amount',
        'hlr_vendor_line_ids.commission_amount',
        'hlr_vendor_line_ids.payable_vendor_amount',
    )
    def _compute_hlr_totals(self):
        for lead in self:
            lines = lead.hlr_vendor_line_ids
            lead.hlr_total_vendor_amount = sum(lines.mapped('vendor_amount'))
            lead.hlr_total_commission = sum(lines.mapped('commission_amount'))
            lead.hlr_total_payable_vendor = sum(lines.mapped('payable_vendor_amount'))

    @api.depends('hlr_vendor_line_ids.destination_id')
    def _compute_hlr_destinations(self):
        for lead in self:
            lead.hlr_destination_ids = lead.hlr_vendor_line_ids.mapped('destination_id')

    @api.depends(
        'hlr_vendor_line_ids.service_date_from',
        'hlr_vendor_line_ids.service_date_to',
    )
    def _compute_hlr_travel_dates(self):
        for lead in self:
            dates_from = [l.service_date_from for l in lead.hlr_vendor_line_ids if l.service_date_from]
            dates_to = [l.service_date_to for l in lead.hlr_vendor_line_ids if l.service_date_to]
            lead.hlr_travel_date_from = min(dates_from) if dates_from else False
            lead.hlr_travel_date_to = max(dates_to) if dates_to else False

    # ── Onchange handlers ────────────────────────────────────────────────────

    @api.onchange('partner_id')
    def _onchange_partner_id_fill_vo_fields(self):
        """Auto-fill Service Type (and via it, score lines) from the linked
        business contact whenever partner_id is set or changed interactively.

        We do NOT gate on team_id: the user may pick the contact before
        selecting the pipeline.  The scoring tab is invisible for non-VO
        pipelines so populating these fields elsewhere is harmless.
        """
        if not self.partner_id or not self.partner_id.vendor_category_id:
            return
        # Auto-fill service type from the business contact, then rebuild lines.
        self.vendor_category_id = self.partner_id.vendor_category_id
        self._rebuild_score_lines()
        # x_vendor_id and x_business_channel are related fields — auto-update.

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _rebuild_score_lines(self):
        """Clear and rebuild gopkz.lead.score.line records driven by the
        Service Type (vendor_category_id) field on this lead.

        Called from:
          • _onchange_vendor_category_id — user manually changes Service Type
          • _onchange_partner_id_fill_vo_fields — after auto-filling Service
            Type from the linked business contact
          • create() — when partner_id is pre-set via context/defaults
        """
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

    @api.onchange('vendor_category_id')
    def _onchange_vendor_category_id(self):
        """Rebuild criteria lines whenever Service Type is changed manually."""
        self._rebuild_score_lines()

    @api.onchange('score_line_ids')
    def _onchange_score_line_ids(self):
        if self.scoring_confirmed and not self.scoring_locked:
            self.scoring_confirmed = False

    def _get_ops_user(self):
        """Return the Operations Manager for this lead's business contact."""
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return False
        if partner.x_operations_user_id:
            return partner.x_operations_user_id
        if partner.parent_id and partner.parent_id.x_operations_user_id:
            return partner.parent_id.x_operations_user_id
        return False

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_confirm_scoring(self):
        self.ensure_one()
        unscored = self.score_line_ids.filtered(lambda l: not l.score_entered)
        if unscored:
            criteria_names = ', '.join(unscored.mapped('criteria_id.name'))
            raise UserError(
                f'{len(unscored)} criterion/criteria have not been scored yet: '
                f'{criteria_names}.\n\n'
                'Please enter a score (including a deliberate 0) for every '
                'criterion before confirming.'
            )
        self.write({'scoring_confirmed': True})

    def action_submit_agreement(self):
        """Submit the Signed Agreement link and notify the Operations Manager."""
        self.ensure_one()
        if not self.x_attachment_agreement_url:
            raise UserError('Please enter a hyperlink before submitting.')
        self.x_attachment_agreement_submitted = True
        ops_user = self._get_ops_user()
        if ops_user:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=ops_user.id,
                summary='Review Signed Agreement',
                note=f'Signed Agreement submitted for <b>{self.name}</b>.',
            )
        self.message_post(body='<p>✓ Signed Agreement link submitted.</p>')

    def action_submit_pictures(self):
        """Submit the Pictures link and notify the Operations Manager."""
        self.ensure_one()
        if not self.x_attachment_pictures_url:
            raise UserError('Please enter a hyperlink before submitting.')
        self.x_attachment_pictures_submitted = True
        ops_user = self._get_ops_user()
        if ops_user:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=ops_user.id,
                summary='Review Pictures',
                note=f'Pictures submitted for <b>{self.name}</b>.',
            )
        self.message_post(body='<p>✓ Pictures link submitted.</p>')

    def action_submit_other(self):
        """Submit the Other Documentation link and notify the Operations Manager."""
        self.ensure_one()
        if not self.x_attachment_other_url:
            raise UserError('Please enter a hyperlink before submitting.')
        self.x_attachment_other_submitted = True
        ops_user = self._get_ops_user()
        if ops_user:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=ops_user.id,
                summary='Review Other Documentation',
                note=f'Other documentation submitted for <b>{self.name}</b>.',
            )
        self.message_post(body='<p>✓ Other documentation link submitted.</p>')

    def action_approve_agreement(self):
        """Approve the agreement and auto-advance to the Onboarding stage."""
        self.ensure_one()
        if not self.x_all_attachments_submitted:
            raise UserError('All documents must be submitted before approval.')
        is_admin = self.env.user.has_group('base.group_system')
        if not is_admin:
            ops_user = self._get_ops_user()
            if ops_user and ops_user.id != self.env.uid:
                raise UserError(
                    'Only the assigned Operations Manager can approve the agreement.'
                )
        self.x_agreement_approved = True
        onboarding_stage = self.env.ref(
            'gopkz_crm.stage_vo_onboarding', raise_if_not_found=False
        )
        if onboarding_stage:
            self.with_context(skip_scoring_gate=True).write(
                {'stage_id': onboarding_stage.id}
            )
        self.message_post(body='<p>✓ Agreement approved. Lead advanced to Onboarding.</p>')

    # ── Create override ──────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """Single create override that:
        1. Stamps a sequential Booking ID on every new lead.
        2. Builds score lines from the contact's Service Type when the lead
           is created with a business partner already set (e.g. via context /
           default_get — onchange never fires for pre-set defaults).
        """
        for vals in vals_list:
            if not vals.get('booking_id'):
                vals['booking_id'] = self._generate_booking_id()
        records = super().create(vals_list)
        for lead in records:
            # Build score lines when vendor_category_id is already set (e.g.
            # via context/defaults) since onchange never fires on creation.
            if lead.vendor_category_id and not lead.score_line_ids:
                lead._rebuild_score_lines()
        return records

    def _generate_booking_id(self):
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

        return self.env['ir.sequence'].next_by_code('crm.lead.booking')

    # ── Write override — scoring gate + agreement gate ───────────────────────

    def write(self, vals):
        """Gate stage progression in the Vendor Onboarding pipeline.

        Gate 1 (Scoring): can't advance past Qualifying without confirmed scoring.
        Gate 2 (Agreement): can't advance past Agreement without document approval.

        Both gates are bypassed by the 'skip_scoring_gate' context key.
        Marking Lost is always exempt.
        """
        if 'stage_id' in vals and not self.env.context.get('skip_scoring_gate'):
            # Administrators bypass all stage gates.
            if self.env.user.has_group('base.group_system'):
                return super().write(vals)

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
                    agreement_stage = self.env.ref(
                        'gopkz_crm.stage_vo_agreement',
                        raise_if_not_found=False,
                    )

                    if vo_team and qualifying_stage:
                        for lead in self:
                            new_team_id = vals.get('team_id')
                            effective_team_id = (
                                new_team_id
                                if new_team_id is not None
                                else lead.team_id.id
                            )

                            if effective_team_id == vo_team.id:
                                # Gate 1: Scoring
                                if target_stage.sequence > qualifying_stage.sequence:
                                    if not lead.scoring_confirmed:
                                        raise UserError(
                                            f'"{lead.name}" cannot advance past '
                                            'Qualifying in the Vendor Onboarding '
                                            'pipeline until scoring is confirmed.\n\n'
                                            'Open the Vendor Scoring tab and click '
                                            '"Confirm Scoring" after entering all scores.'
                                        )
                                # Gate 2: Agreement approval
                                if (agreement_stage
                                        and target_stage.sequence > agreement_stage.sequence
                                        and not lead.x_agreement_approved
                                        and not vals.get('x_agreement_approved')):
                                    raise UserError(
                                        f'"{lead.name}" cannot advance past the '
                                        'Agreement stage until all documents have '
                                        'been submitted and the agreement approved.\n\n'
                                        'Complete document submissions in the '
                                        'Attachments tab and obtain approval from '
                                        'the Operations Manager.'
                                    )

        return super().write(vals)
