# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Operations Manager ───────────────────────────────────────────────────
    x_operations_user_id = fields.Many2one(
        'res.users',
        string='Operations Manager',
        domain=[('share', '=', False)],
        tracking=True,
        help='Internal user responsible for the day-to-day operational '
             'relationship with this partner.',
    )

    # ── Vendor Category (controls vendor section visibility) ─────────────────
    vendor_category_id = fields.Many2one(
        'gopkz.vendor.category',
        string='Vendor Category',
    )

    # ── Vendor Data Fields (visible when vendor_category_id is set) ──────────
    x_destination_ids = fields.Many2many(
        'gopkz.destination',
        string='Destinations',
    )
    x_capacity = fields.Integer(
        string='Inventory / Capacity',
        help='Number of rooms, vehicles, or products, depending on vendor type.',
    )
    x_commission_percentage = fields.Float(
        string='Commission %',
        digits=(6, 2),
    )
    x_settlement_cycle = fields.Selection(
        selection=[
            ('same_day', 'Same Day'),
            ('weekly', 'Weekly'),
            ('fortnightly', 'Fortnightly'),
        ],
        string='Settlement Cycle',
    )
    x_has_api_extranet = fields.Boolean(
        string='Has API / Extranet Integration',
        default=False,
    )

    # ── Vendor Onboarding ────────────────────────────────────────────────────

    vob_latest_lead_stage_id = fields.Many2one(
        'crm.stage',
        string='Onboarding Lead Status',
        compute='_compute_vob_latest_lead_stage_id',
        store=True,
        readonly=True,
        help='Stage of the most recent lead in the Vendor Onboarding pipeline '
             'where this partner is the contact.',
    )

    # ── Hot Lead Recovery ────────────────────────────────────────────────────

    # Inverse of gopkz.booking.vendor.line.vendor_id — used as a @api.depends
    # anchor so the ORM can propagate lead stage/date changes to this partner.
    hlr_vendor_line_ids = fields.One2many(
        'gopkz.booking.vendor.line',
        'vendor_id',
        string='HLR Vendor Lines',
    )

    # Currency helper: drives the Monetary widget for hlr_total_commission_earned.
    hlr_currency_id = fields.Many2one(
        'res.currency',
        string='HLR Currency',
        related='company_id.currency_id',
    )

    hlr_last_booking_date = fields.Datetime(
        string='Last Booking Date',
        compute='_compute_hlr_last_booking_date',
        store=True,
        readonly=True,
        help='MAX(date_closed) over Hot Lead Recovery leads where this vendor '
             'appears and stage_id.is_won = True.',
    )

    hlr_total_commission_earned = fields.Monetary(
        string='Total Commission Earned (HLR)',
        compute='_compute_hlr_total_commission_earned',
        store=True,
        readonly=True,
        currency_field='hlr_currency_id',
        help='Sum of commission amounts across all won Hot Lead Recovery leads '
             'this vendor appears on.',
    )

    # ── Hot Lead Recovery — corporate contact ────────────────────────────────
    hlr_last_corporate_booking_date = fields.Datetime(
        string='Last Corporate Booking Date',
        compute='_compute_hlr_last_corporate_booking_date',
        store=True,
        readonly=True,
        help='MAX(date_closed) of won Hot Lead Recovery leads where this '
             'contact is the customer and Customer Type = Corporate Reservation.',
    )

    # ── Corporate Account Fields ─────────────────────────────────────────────
    x_is_corporate_account = fields.Boolean(
        string='Corporate Account',
        default=False,
    )
    x_company_size = fields.Selection(
        selection=[
            ('1_10', '1–10'),
            ('11_50', '11–50'),
            ('51_200', '51–200'),
            ('200_plus', '200+'),
        ],
        string='Company Size',
    )
    x_annual_travel_volume = fields.Integer(
        string='Est. Annual Trips',
    )
    x_current_travel_provider = fields.Char(
        string='Current Travel Provider',
    )

    # ── Compute methods ──────────────────────────────────────────────────────

    @api.depends(
        'opportunity_ids.stage_id',
        'opportunity_ids.team_id',
    )
    def _compute_vob_latest_lead_stage_id(self):
        """Stage of the most recently created lead in the Vendor Onboarding
        pipeline where this partner is the contact."""
        vo_team = self.env.ref(
            'gopkz_crm.team_vendor_onboarding', raise_if_not_found=False
        )
        for partner in self:
            if not vo_team:
                partner.vob_latest_lead_stage_id = False
                continue
            leads = partner.opportunity_ids.filtered(
                lambda l: l.team_id.id == vo_team.id
            ).sorted('id', reverse=True)
            partner.vob_latest_lead_stage_id = leads[0].stage_id if leads else False

    @api.depends(
        'opportunity_ids.date_closed',
        'opportunity_ids.stage_id.is_won',
        'opportunity_ids.team_id',
        'opportunity_ids.hlr_customer_type',
    )
    def _compute_hlr_last_corporate_booking_date(self):
        """MAX(date_closed) of won HLR leads where this contact is the customer
        and hlr_customer_type = 'corporate_reservation'."""
        hlr_team = self.env.ref(
            'gopkz_crm.team_hot_lead_recovery', raise_if_not_found=False
        )
        for partner in self:
            if not hlr_team:
                partner.hlr_last_corporate_booking_date = False
                continue
            dates = [
                lead.date_closed
                for lead in partner.opportunity_ids
                if lead.team_id.id == hlr_team.id
                and lead.stage_id.is_won
                and lead.hlr_customer_type == 'corporate_reservation'
                and lead.date_closed
            ]
            partner.hlr_last_corporate_booking_date = max(dates) if dates else False

    @api.depends(
        'hlr_vendor_line_ids.commission_amount',
        'hlr_vendor_line_ids.lead_id.stage_id.is_won',
        'hlr_vendor_line_ids.lead_id.team_id',
    )
    def _compute_hlr_total_commission_earned(self):
        """Sum of commission_amount over won HLR leads this vendor appears on."""
        hlr_team = self.env.ref(
            'gopkz_crm.team_hot_lead_recovery', raise_if_not_found=False
        )
        for partner in self:
            if not hlr_team:
                partner.hlr_total_commission_earned = 0.0
                continue
            partner.hlr_total_commission_earned = sum(
                line.commission_amount
                for line in partner.hlr_vendor_line_ids
                if line.lead_id.team_id.id == hlr_team.id
                and line.lead_id.stage_id.is_won
            )

    @api.depends(
        'hlr_vendor_line_ids.lead_id.date_closed',
        'hlr_vendor_line_ids.lead_id.stage_id.is_won',
        'hlr_vendor_line_ids.lead_id.team_id',
    )
    def _compute_hlr_last_booking_date(self):
        """MAX(lead_id.date_closed) over this vendor's HLR vendor lines where
        lead_id.team_id is the Hot Lead Recovery team AND
        lead_id.stage_id.is_won = True."""
        hlr_team = self.env.ref(
            'gopkz_crm.team_hot_lead_recovery', raise_if_not_found=False
        )
        for partner in self:
            if not hlr_team:
                partner.hlr_last_booking_date = False
                continue
            dates = [
                line.lead_id.date_closed
                for line in partner.hlr_vendor_line_ids
                if line.lead_id.team_id.id == hlr_team.id
                and line.lead_id.stage_id.is_won
                and line.lead_id.date_closed
            ]
            partner.hlr_last_booking_date = max(dates) if dates else False

    # ── Constraints ──────────────────────────────────────────────────────────

    @api.constrains('x_commission_percentage')
    def _check_commission_percentage(self):
        for partner in self:
            if partner.x_commission_percentage < 0 or partner.x_commission_percentage > 100:
                raise ValidationError(
                    f'Commission % must be between 0 and 100 '
                    f'(got {partner.x_commission_percentage}).'
                )
