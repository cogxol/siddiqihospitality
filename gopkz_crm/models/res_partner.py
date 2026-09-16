# -*- coding: utf-8 -*-
from datetime import timedelta
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

    # ── Contact-type extension: Vendor Business ──────────────────────────────
    # Adds a third option to the standard Person / Company radio button.
    # Selecting "Vendor Business" marks this contact as a business unit of a
    # vendor company.  The stored boolean x_is_vendor_business persists the
    # selection even before a Service Type is chosen, so the Service Type field
    # stays visible without the radio button snapping back to "Person".

    company_type = fields.Selection(
        selection_add=[('vendor_business', 'Vendor Business')],
        # 'set default' reverts vendor_business partners to 'person' on module
        # uninstall.  default='person' is required by the assertion even though
        # this is a computed field and the default is never used at runtime.
        ondelete={'vendor_business': 'set default'},
        default='person',
    )

    x_is_vendor_business = fields.Boolean(
        string='Is Vendor Business',
        default=False,
        help='True when the user has selected "Vendor Business" as the contact '
             'type.  Stores the intent before a Service Type is chosen.',
    )

    @api.depends('is_company', 'x_is_vendor_business', 'vendor_category_id')
    def _compute_company_type(self):
        for partner in self:
            # is_company wins — a company contact is always "Company".
            if partner.is_company:
                partner.company_type = 'company'
            elif partner.x_is_vendor_business or partner.vendor_category_id:
                partner.company_type = 'vendor_business'
            else:
                partner.company_type = 'person'

    def _write_company_type(self):
        for partner in self:
            if partner.company_type == 'vendor_business':
                partner.is_company = False
                partner.x_is_vendor_business = True
            else:
                # Switching away from Vendor Business clears the vendor fields.
                partner.x_is_vendor_business = False
                partner.vendor_category_id = False
                partner.is_company = partner.company_type == 'company'

    # ── Service Type (identifies a partner as a Business) ────────────────────
    # When set, this partner is a "Business" and the Vendor Details tab appears.
    # One vendor company can have multiple child business contacts, each with
    # a different service type (Hotel, Car Rental, Tour, etc.).
    vendor_category_id = fields.Many2one(
        'gopkz.vendor.category',
        string='Service Type',
    )

    # ── Computed helpers ─────────────────────────────────────────────────────

    is_business = fields.Boolean(
        string='Is Business',
        compute='_compute_is_business',
        store=False,
        help='True when this contact has a Service Type set (i.e. it is a '
             'business unit of a vendor).',
    )
    x_vendor_business_count = fields.Integer(
        string='Businesses',
        compute='_compute_vendor_business_count',
        store=False,
    )

    # ── Filtered One2many views of child_ids ─────────────────────────────────
    # Python-level domain ensures only the right subset is displayed in each tab.

    # Non-business children (regular contacts / employees) — used in the standard
    # "Contacts" tab so that business contacts (with a Service Type) are hidden.
    x_employee_ids = fields.One2many(
        'res.partner',
        'parent_id',
        string='Contacts',
        domain=[('vendor_category_id', '=', False)],
    )

    # Business children (children with a Service Type set) — used in the
    # dedicated "Businesses" tab.
    x_business_ids = fields.One2many(
        'res.partner',
        'parent_id',
        string='Business Contacts',
        domain=[('vendor_category_id', '!=', False)],
    )

    # ── Business Data Fields (visible when vendor_category_id is set) ────────
    x_destination_ids = fields.Many2many(
        'gopkz.destination',
        string='Destinations',
    )
    x_capacity = fields.Integer(
        string='Inventory / Capacity',
        help='Number of rooms, vehicles, or products, depending on service type.',
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
    x_business_channel = fields.Selection(
        selection=[
            ('b2b', 'B2B'),
            ('b2c', 'B2C'),
            ('both', 'B2B & B2C'),
        ],
        string='Business Channel',
        tracking=True,
        help='Whether this business operates in B2B, B2C, or both channels.',
    )

    # ── Business Status — computed from last booking recency ─────────────────
    x_vendor_status = fields.Selection(
        selection=[
            ('live', 'Live'),
            ('dormant', 'Dormant'),
        ],
        string='Business Status',
        compute='_compute_x_vendor_status',
        store=False,
        help='Live if a Hot Lead Recovery booking was closed within the last '
             '5 minutes; Dormant otherwise.',
    )

    # ── Vendor Onboarding ────────────────────────────────────────────────────

    vob_latest_lead_stage_id = fields.Many2one(
        'crm.stage',
        string='Onboarding Lead Status',
        compute='_compute_vob_latest_lead_stage_id',
        store=True,
        readonly=True,
        help='Stage of the most recent lead in the Vendor Onboarding pipeline '
             'where this business (or one of its employee contacts) is the '
             'lead contact.',
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
        help='MAX(date_closed) over Hot Lead Recovery leads where this business '
             'appears and stage_id.is_won = True.',
    )

    hlr_total_commission_earned = fields.Monetary(
        string='Total Commission Earned',
        compute='_compute_hlr_total_commission_earned',
        store=True,
        readonly=True,
        currency_field='hlr_currency_id',
        help='Sum of commission amounts across all won Hot Lead Recovery leads '
             'this business appears on.',
    )

    # ── Hot Lead Recovery — corporate contact ────────────────────────────────
    hlr_last_corporate_booking_date = fields.Datetime(
        string='Last Corporate Booking Date',
        compute='_compute_hlr_last_corporate_booking_date',
        store=True,
        readonly=True,
        help='MAX(date_closed) of won HLR leads where this contact is the '
             'customer and Customer Type = Corporate Reservation.',
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

    @api.depends('vendor_category_id')
    def _compute_is_business(self):
        for partner in self:
            partner.is_business = bool(partner.vendor_category_id)

    @api.depends('child_ids', 'child_ids.vendor_category_id')
    def _compute_vendor_business_count(self):
        for partner in self:
            partner.x_vendor_business_count = len(
                partner.child_ids.filtered('vendor_category_id')
            )

    @api.depends('hlr_last_booking_date')
    def _compute_x_vendor_status(self):
        """Live if the most recent HLR booking was closed within the last 5 minutes."""
        five_min_ago = fields.Datetime.now() - timedelta(minutes=5)
        for partner in self:
            if (partner.hlr_last_booking_date
                    and partner.hlr_last_booking_date >= five_min_ago):
                partner.x_vendor_status = 'live'
            else:
                partner.x_vendor_status = 'dormant'

    @api.depends(
        'opportunity_ids.stage_id',
        'opportunity_ids.team_id',
        'child_ids.opportunity_ids.stage_id',
        'child_ids.opportunity_ids.team_id',
    )
    def _compute_vob_latest_lead_stage_id(self):
        """Stage of the most recently created Vendor Onboarding lead where this
        business or any of its child contacts (employees) is the lead contact."""
        vo_team = self.env.ref(
            'gopkz_crm.team_vendor_onboarding', raise_if_not_found=False
        )
        for partner in self:
            if not vo_team:
                partner.vob_latest_lead_stage_id = False
                continue
            # Include leads where the contact is this business OR any employee
            # contact that belongs to this business.
            partner_ids = [partner.id] + partner.child_ids.ids
            lead = self.env['crm.lead'].search([
                ('partner_id', 'in', partner_ids),
                ('team_id', '=', vo_team.id),
            ], order='id desc', limit=1)
            partner.vob_latest_lead_stage_id = lead.stage_id if lead else False

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
        """Sum of commission_amount over won HLR leads this business appears on."""
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
        """MAX(lead_id.date_closed) over this business's HLR vendor lines where
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

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_view_businesses(self):
        """Open the list of business contacts that are children of this vendor."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Businesses — {self.name}',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id), ('vendor_category_id', '!=', False)],
            'context': {
                'default_parent_id': self.id,
                'default_is_company': True,
            },
        }

    # ── Constraints ──────────────────────────────────────────────────────────

    @api.constrains('x_commission_percentage')
    def _check_commission_percentage(self):
        for partner in self:
            if partner.x_commission_percentage < 0 or partner.x_commission_percentage > 100:
                raise ValidationError(
                    f'Commission % must be between 0 and 100 '
                    f'(got {partner.x_commission_percentage}).'
                )
