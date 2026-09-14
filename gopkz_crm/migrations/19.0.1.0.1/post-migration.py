# -*- coding: utf-8 -*-
"""Re-apply global-stage hiding after module update.

v19.0.1.0.0 only assigned stages 2 (Qualified) and 3 (Proposition) to the
sink team.  Stages 1 (New) and 4 (Won) were left with team_ids=False, so they
appeared as extra "New" and "Won" columns in every custom pipeline kanban.

This migration reassigns ALL global stages (team_ids=False) to the archived
sink team, removing the spurious columns from Vendor Onboarding, Hot Lead
Recovery, and Corporate Sales.
"""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    from odoo.addons.gopkz_crm.hooks import _hide_default_global_stages

    env = api.Environment(cr, SUPERUSER_ID, {})
    _hide_default_global_stages(env)
