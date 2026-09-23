# -*- coding: utf-8 -*-


def _restrict_team_stages(env):
    """In Odoo 19 helpdesk, stages are linked to teams via team.stage_ids
    (junction table team_stage_rel).  When a new team is created, Odoo
    auto-assigns ALL existing stages to it — so our custom teams end up with
    both the default demo stages (New, In Progress, Solved, Cancelled) AND our
    custom stages.

    This hook replaces the full stage_ids on each custom team so only the
    relevant stages remain visible in its kanban.
    """
    supplier_team = env.ref(
        'gopkz_helpdesk.team_supplier_operations', raise_if_not_found=False
    )
    cx_team = env.ref(
        'gopkz_helpdesk.team_customer_experience', raise_if_not_found=False
    )

    supplier_stage_refs = [
        'gopkz_helpdesk.stage_supplier_new',
        'gopkz_helpdesk.stage_supplier_confirmation_pending',
        'gopkz_helpdesk.stage_supplier_confirmed',
        'gopkz_helpdesk.stage_supplier_rejected',
    ]
    cx_stage_refs = [
        'gopkz_helpdesk.stage_cx_pre_travel',
        'gopkz_helpdesk.stage_cx_during_travel',
        'gopkz_helpdesk.stage_cx_post_service',
        'gopkz_helpdesk.stage_cx_feedback',
    ]

    def _stage_ids(refs):
        ids = []
        for ref in refs:
            rec = env.ref(ref, raise_if_not_found=False)
            if rec:
                ids.append(rec.id)
        return ids

    if supplier_team:
        ids = _stage_ids(supplier_stage_refs)
        if ids:
            supplier_team.write({'stage_ids': [(6, 0, ids)]})

    if cx_team:
        ids = _stage_ids(cx_stage_refs)
        if ids:
            cx_team.write({'stage_ids': [(6, 0, ids)]})


def post_init_hook(env):
    """Set each custom team's stages to only its own kanban columns."""
    _restrict_team_stages(env)
