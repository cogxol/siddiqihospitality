# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


# ── Ticket type selection (shared constant) ──────────────────────────────────
TICKET_TYPE_SELECTION = [
    # BRD §10 types
    ('inquiry',           'Inquiry'),
    ('lead',              'Lead'),
    ('booking_support',   'Booking Support'),
    ('travel_support',    'Travel Support'),
    ('complaint',         'Complaint'),
    ('modification',      'Modification'),
    ('refund_case',       'Refund Case'),
    ('escalation',        'Escalation'),
    ('service_recovery',  'Service Recovery'),
    ('feedback',          'Feedback'),
    ('follow_up',         'Follow-up'),
    # This-build additions
    ('vendor_support',      'Vendor Support'),        # non-booking vendor issue
    ('corporate_support',   'Corporate Support'),     # non-booking corporate issue
    # Auto-created by trigger
    ('supplier_confirmation', 'Supplier Confirmation'),  # Track A
]


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    # ── Ticket type ───────────────────────────────────────────────────────────
    x_ticket_type = fields.Selection(
        selection=TICKET_TYPE_SELECTION,
        string='Ticket Type',
        tracking=True,
    )

    # ── Service Category (reuse gopkz.vendor.category, not a new model) ──────
    x_service_category_ids = fields.Many2many(
        'gopkz.vendor.category',
        relation='helpdesk_ticket_vendor_category_rel',
        column1='ticket_id',
        column2='category_id',
        string='Service Category',
        help='Which service types are involved in this ticket.',
    )

    # ── Booking linkage ───────────────────────────────────────────────────────
    x_hlr_lead_id = fields.Many2one(
        'crm.lead',
        string='Booking',
        tracking=True,
        help='The Hot Lead Recovery booking this ticket is about.',
    )

    # ── Vendor / Business linkage ─────────────────────────────────────────────
    # For Track A (Supplier Confirmation) and Vendor Support tickets.
    x_vendor_business_id = fields.Many2one(
        'res.partner',
        string='Business',
        domain=[('vendor_category_id', '!=', False)],
        tracking=True,
        help='The specific business contact (with a Service Type) this ticket is about.',
    )

    # ── Booking vendor line ───────────────────────────────────────────────────
    # Set only on Supplier Confirmation tickets — one ticket per vendor line.
    x_booking_vendor_line_id = fields.Many2one(
        'gopkz.booking.vendor.line',
        string='Booking Vendor Line',
        ondelete='set null',
        help='The specific vendor line in the booking. Set automatically on Supplier Confirmation tickets.',
    )

    # ── Corporate account linkage ─────────────────────────────────────────────
    # For Corporate Support tickets not tied to any specific booking.
    x_corporate_account_id = fields.Many2one(
        'res.partner',
        string='Corporate Account',
        domain=[('x_is_corporate_account', '=', True)],
        tracking=True,
        help='The corporate account this issue relates to (non-booking corporate support).',
    )

    # ── Escalation ────────────────────────────────────────────────────────────
    # Required for escalation-type tickets before any stage change.
    x_escalation_team_id = fields.Many2one(
        'helpdesk.team',
        string='Escalation Department',
        help='The department this ticket is being escalated to.',
    )

    # ── Closure outcome ───────────────────────────────────────────────────────
    # Required before any closed-stage transition (BRD §17).
    x_closure_outcome = fields.Text(
        string='Closure Outcome',
        help='Describe the final outcome before closing the ticket.',
    )

    # ── Computed helper ───────────────────────────────────────────────────────
    x_is_supplier_confirmation = fields.Boolean(
        compute='_compute_x_is_supplier_confirmation',
        store=False,
    )

    @api.depends('x_ticket_type')
    def _compute_x_is_supplier_confirmation(self):
        for t in self:
            t.x_is_supplier_confirmation = (t.x_ticket_type == 'supplier_confirmation')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_first_stage(self):
        """Return the lowest-sequence helpdesk.stage for this ticket's team."""
        if not self.team_id:
            return self.env['helpdesk.stage'].browse()
        return self.env['helpdesk.stage'].search(
            [('team_ids', 'in', self.team_id.id)],
            order='sequence asc',
            limit=1,
        )

    # ── Write gate ────────────────────────────────────────────────────────────

    def write(self, vals):
        """Gate stage progression on helpdesk tickets.

        Gate 1 — Owner required before leaving the first stage.
        Gate 2 — Closure Outcome required for every closed-stage transition.
        Gate 3 — Escalation Department required before any stage change on
                  escalation-type tickets.

        All gates are bypassed for Administrators (base.group_system) and
        when the 'skip_helpdesk_gate' context key is set (used by the cron).
        """
        if 'stage_id' in vals:
            is_admin = self.env.user.has_group('base.group_system')
            skip = self.env.context.get('skip_helpdesk_gate')
            if not is_admin and not skip:
                target = self.env['helpdesk.stage'].browse(vals['stage_id'])
                for ticket in self:
                    # Gate 1: owner required before leaving the first stage
                    first = ticket._get_first_stage()
                    if (first
                            and ticket.stage_id.id == first.id
                            and target.sequence > first.sequence):
                        eff_user = vals.get('user_id') or ticket.user_id.id
                        if not eff_user:
                            raise UserError(
                                f'Assign an owner to "{ticket.name}" before '
                                'advancing it from the first stage.'
                            )

                    # Gate 2: closure outcome required on every closed-stage move
                    if target.fold:
                        eff_outcome = vals.get('x_closure_outcome') or ticket.x_closure_outcome
                        if not eff_outcome:
                            raise UserError(
                                f'Fill in the Closure Outcome for "{ticket.name}" '
                                'before moving it to a closed stage.'
                            )

                    # Gate 3: escalation tickets need a responsible department
                    eff_type = vals.get('x_ticket_type') or ticket.x_ticket_type
                    if eff_type == 'escalation':
                        eff_team = (
                            vals.get('x_escalation_team_id')
                            or ticket.x_escalation_team_id.id
                        )
                        if not eff_team:
                            raise UserError(
                                f'Identify the responsible department for escalation '
                                f'ticket "{ticket.name}" before changing its stage.'
                            )

        return super().write(vals)

    # ── Cron: progress travel-support tickets against lead travel dates ───────

    @api.model
    def _cron_progress_travel_support(self):
        """Daily cron that advances Customer Experience (Track B) tickets
        through their stages based on the linked booking's travel dates.

        Pre-Travel → During Travel  when today >= hlr_travel_date_from
        During Travel → Post-Service when today >  hlr_travel_date_to

        The Post-Service → Feedback transition is deliberately NOT automated;
        it is a manual action by the CX agent (BRD §3.3).

        Stage transitions use skip_helpdesk_gate so the cron is never blocked
        by Gate 1 (owner check) on an automated move.
        """
        today = fields.Date.today()
        pre    = self.env.ref('gopkz_helpdesk.stage_cx_pre_travel',      raise_if_not_found=False)
        during = self.env.ref('gopkz_helpdesk.stage_cx_during_travel',   raise_if_not_found=False)
        post   = self.env.ref('gopkz_helpdesk.stage_cx_post_service',    raise_if_not_found=False)

        if not (pre and during and post):
            return

        tickets = self.search([('x_hlr_lead_id', '!=', False)])
        for ticket in tickets:
            lead = ticket.x_hlr_lead_id
            if ticket.stage_id.id == pre.id:
                if lead.hlr_travel_date_from and today >= lead.hlr_travel_date_from:
                    ticket.with_context(skip_helpdesk_gate=True).write(
                        {'stage_id': during.id}
                    )
            elif ticket.stage_id.id == during.id:
                if lead.hlr_travel_date_to and today > lead.hlr_travel_date_to:
                    ticket.with_context(skip_helpdesk_gate=True).write(
                        {'stage_id': post.id}
                    )
