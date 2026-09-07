# -*- coding: utf-8 -*-
{
    'name': 'GOPKZ CRM — Siddiqi Hospitality',
    'version': '19.0.1.0.0',
    'summary': 'Vendor Onboarding, Scoring, Destinations and Corporate Account fields for Siddiqi Hospitality',
    'author': 'COGXOL',
    'depends': ['crm'],
    'data': [
        # Security first (group definition must precede the CSV)
        'security/gopkz_security.xml',
        'security/ir.model.access.csv',
        # Master data (categories before criteria; teams before stages)
        'data/gopkz_vendor_category_data.xml',
        'data/crm_team_data.xml',
        'data/crm_stage_data.xml',
        'data/gopkz_scoring_criteria_data.xml',
        'data/gopkz_destination_data.xml',
        'data/crm_lost_reason_data.xml',
        # Views
        'views/gopkz_vendor_category_views.xml',
        'views/gopkz_scoring_criteria_views.xml',
        'views/gopkz_destination_views.xml',
        'views/crm_lead_views.xml',
        'views/res_partner_views.xml',
        'views/menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
