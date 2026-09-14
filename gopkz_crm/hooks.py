# -*- coding: utf-8 -*-


def _hide_default_global_stages(env):
    """Assign ALL default global Odoo stages (team_ids=False) to the archived
    sink team so they no longer appear as extra columns in every custom
    pipeline's kanban view.

    Odoo ships four default stages, all starting with team_ids = False
    (i.e. visible in EVERY pipeline):
        New (seq=1), Qualified (seq=2), Proposition (seq=3), Won (seq=70)

    Because all three custom pipelines — Vendor Onboarding, Hot Lead Recovery,
    and Corporate Sales — each define their own opening stage and their own
    is_won=True closing stage, no global-stage fallback is required:

    • action_set_won() searches team-specific is_won stages first; our custom
      won stages (Live/Recovered/Active) are always found before any fallback.
    • _stage_find() for a lead inside one of our teams finds the team's own
      stages, so the global "New" is never needed as a default.
    • PLS scoring works off the team-scoped stages once global stages are gone.

    WHY WE REASSIGN INSTEAD OF DELETING:
    Deleting stages removes their ir.model.data XML-IDs.  Odoo's
    crm_stage_demo.xml references stage_lead3; without its XML-ID the demo
    loader tries to INSERT a record with no `name`, hitting a NOT-NULL error.
    We keep the records alive but invisible by assigning them to the archived
    sink team.

    Steps:
    1. Find every global (team_ids=False) crm.stage record.
    2. Reroute any leads currently on those stages to Vendor Onboarding "New".
    3. Assign the stages to the archived sink team.
    """
    sink_team = env.ref(
        'gopkz_crm.team_default_stages_sink', raise_if_not_found=False
    )
    if not sink_team:
        return

    stages_to_hide = env['crm.stage'].search([('team_ids', '=', False)])
    if not stages_to_hide:
        return

    # 1. Reroute leads off global stages before hiding them.
    leads_to_move = env['crm.lead'].with_context(active_test=False).search([
        ('stage_id', 'in', stages_to_hide.ids),
    ])
    if leads_to_move:
        vo_new_stage = env.ref('gopkz_crm.stage_vo_new', raise_if_not_found=False)
        if vo_new_stage:
            leads_to_move.with_context(skip_scoring_gate=True).write(
                {'stage_id': vo_new_stage.id}
            )

    # 2. Assign to archived sink team — records stay alive (XML IDs intact)
    #    but disappear from every active pipeline kanban.
    stages_to_hide.write({'team_ids': [(4, sink_team.id)]})


def post_init_hook(env):
    """Hide all default global CRM stages on fresh module install."""
    _hide_default_global_stages(env)
