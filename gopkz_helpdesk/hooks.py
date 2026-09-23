# -*- coding: utf-8 -*-


def _hide_default_helpdesk_stages(env):
    """Assign ALL default global Helpdesk stages (team_ids=False) to the
    archived sink team so they no longer appear as extra columns in every
    custom team's kanban view.

    Mirrors the identical pattern in gopkz_crm/hooks.py for CRM stages.
    We reassign rather than delete to preserve XML IDs that the helpdesk
    module itself may reference internally.
    """
    sink = env.ref(
        'gopkz_helpdesk.team_default_stages_sink', raise_if_not_found=False
    )
    if not sink:
        return

    stages = env['helpdesk.stage'].search([('team_ids', '=', False)])
    if stages:
        stages.write({'team_ids': [(4, sink.id)]})


def post_init_hook(env):
    """Hide all default global Helpdesk stages on fresh module install."""
    _hide_default_helpdesk_stages(env)
