# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Hide default blank-team CRM stages from all active pipelines.

    Odoo 19's crm.stage model has no `active` field; a stage with empty
    team_ids appears in EVERY team's kanban via the domain:
        ('team_ids', '=', False)
    The four default stages (New, Qualified, Proposition, Won) have no
    team_ids and must be hidden so each team shows only its own stages.

    WHY WE REASSIGN INSTEAD OF DELETING:
    Deleting those stages also removes their ir.model.data XML-ID entries.
    Odoo's crm_stage_demo.xml (loaded by "odoo-bin module force-demo") holds
    a reference to stage_lead3; without its XML ID the demo loader tries to
    INSERT a brand-new crm.stage with only `rotting_threshold_days` set and
    no `name`, hitting a NOT-NULL violation and marking the build as failed.

    SOLUTION:
    Assign the blank-team stages to an archived "sink" team
    (gopkz_crm.team_default_stages_sink).  They keep their XML IDs so
    crm_stage_demo.xml can UPDATE them, but they no longer satisfy
        ('team_ids', '=', False)
    and they will never match any active team's kanban domain either, so
    they are effectively invisible to all live pipelines.

    Steps:
    1. Find any leads currently on blank-team stages and move them to the
       Vendor Onboarding "New" stage (using skip_scoring_gate context so
       our write() override doesn't block the hook-level move).
    2. Assign the blank-team stages to the archived sink team.
    """
    blank_team_stages = env['crm.stage'].search([('team_ids', '=', False)])
    if not blank_team_stages:
        return

    # 1. Reroute leads off blank-team stages before hiding them.
    leads_to_move = env['crm.lead'].with_context(active_test=False).search([
        ('stage_id', 'in', blank_team_stages.ids),
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
        blank_team_stages.write({'team_ids': [(4, sink_team.id)]})
