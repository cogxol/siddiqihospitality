# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Reduce clutter in custom pipeline kanbans by hiding most default stages.

    Odoo 19's crm.stage has no `active` field; a stage with empty team_ids
    appears in EVERY team's kanban via the domain:
        ('team_ids', '=', False)

    Odoo ships four default stages: New(1), Qualified(2), Proposition(3),
    Won(70).  All four start with team_ids = False (global).

    We hide the two middle non-won stages (Qualified, Proposition) by
    assigning them to an archived "sink" team.  This keeps the Won stage and
    the "New" stage (sequence = 1) as the only remaining global stages.

    WHY WE KEEP stage_lead1 ("New") GLOBAL:
    1.  It is the lowest-sequence global non-won stage — the Predictive Lead
        Scoring engine (`_pls_get_won_lost_total_count`) uses this stage as
        the reference for total won/lost counts.  If it disappears from the
        global pool, PLS computes wrong totals and probabilities.
    2.  When a fresh lead is created in any team that has no team-specific
        stages (including ad-hoc teams in automated tests), Odoo's
        `_stage_find(domain=[('fold','=',False)])` picks the first global
        non-folded stage.  Without stage_lead1 global, the fallback becomes
        stage_lead4 (Won), and subsequent `action_set_lost()` calls trigger
        the _check_won_validity constraint (ValidationError).

    WHY WE KEEP stage_lead4 ("Won") GLOBAL:
    1.  `action_set_won()` uses ('team_ids', '=', False) as a fallback to
        locate a won stage for leads whose team has no dedicated won stage —
        including teams created by the standard CRM automated tests.
    2.  stage_lead4 has sequence=70; our custom won stages have sequences
        60/130/260, so within each pipeline the correct won stage is always
        found first by action_set_won().

    WHY WE REASSIGN INSTEAD OF DELETING:
    Deleting stages also removes their ir.model.data XML-ID entries.  Odoo's
    crm_stage_demo.xml holds a reference to stage_lead3; without its XML ID
    the demo loader tries to INSERT a brand-new crm.stage record with only
    `rotting_threshold_days` set and no `name`, hitting a NOT-NULL violation
    that marks the build as failed.

    SOLUTION:
    Assign only stage_lead2 and stage_lead3 to the archived sink team.
    They keep their XML IDs, no longer satisfy ('team_ids','=',False), and
    are invisible to all active pipeline kanban views.

    Steps:
    1. Find the two non-won blank-team stages to hide (seq 2 and 3).
    2. Reroute any leads currently on those stages to Vendor Onboarding "New".
    3. Assign those stages to the archived sink team.
    """
    # Target only stage_lead2 (seq=2) and stage_lead3 (seq=3).
    # stage_lead1 (seq=1) must remain global (PLS anchor + default stage).
    # stage_lead4 (seq=70, is_won=True) must remain global (action_set_won).
    stages_to_hide = env['crm.stage'].search([
        ('team_ids', '=', False),
        ('is_won', '=', False),
        ('sequence', '>', 1),          # skip stage_lead1 (seq=1)
    ])
    if not stages_to_hide:
        return

    # 1. Reroute leads off those stages before hiding them.
    leads_to_move = env['crm.lead'].with_context(active_test=False).search([
        ('stage_id', 'in', stages_to_hide.ids),
    ])
    if leads_to_move:
        vo_new_stage = env.ref('gopkz_crm.stage_vo_new', raise_if_not_found=False)
        if vo_new_stage:
            leads_to_move.with_context(skip_scoring_gate=True).write(
                {'stage_id': vo_new_stage.id}
            )

    # 2. Assign to archived sink team — stages remain alive (XML IDs intact)
    #    but disappear from every active pipeline kanban.
    sink_team = env.ref(
        'gopkz_crm.team_default_stages_sink', raise_if_not_found=False
    )
    if sink_team:
        stages_to_hide.write({'team_ids': [(4, sink_team.id)]})
