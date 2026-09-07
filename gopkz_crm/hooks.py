# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Remove default blank-team CRM stages from all pipelines.

    Odoo 19's crm.stage model has no `active` field; a stage with empty
    team_ids appears in EVERY team's kanban via the domain:
        ('team_ids', '=', False)
    The four default stages (New, Qualified, Proposition, Won) have no
    team_ids and must be removed so each team shows only its own stages.

    Steps:
    1. Find any leads currently on blank-team stages and move them to the
       Vendor Onboarding "New" stage (using skip_scoring_gate context so
       our write() override doesn't block the hook-level move).
    2. Unlink the blank-team stages (now safe — no leads reference them).
    """
    blank_team_stages = env['crm.stage'].search([('team_ids', '=', False)])
    if not blank_team_stages:
        return

    # Reroute leads off blank-team stages before deleting them
    leads_to_move = env['crm.lead'].with_context(active_test=False).search([
        ('stage_id', 'in', blank_team_stages.ids),
    ])
    if leads_to_move:
        vo_new_stage = env.ref('gopkz_crm.stage_vo_new', raise_if_not_found=False)
        if vo_new_stage:
            leads_to_move.with_context(skip_scoring_gate=True).write(
                {'stage_id': vo_new_stage.id}
            )

    # Now safe to remove the blank-team stages
    blank_team_stages.unlink()
