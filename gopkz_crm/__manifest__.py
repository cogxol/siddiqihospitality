# -*- coding: utf-8 -*-
{
    'name': 'GOPKZ CRM — Siddiqi Hospitality',
    'version': '19.0.1.1.0',
    'summary': 'Vendor/Business structure, Onboarding pipeline, Scoring, HLR and Corporate Sales for Siddiqi Hospitality',
    'author': 'COGXOL',
    'depends': ['crm'],
    'data': [
        # Security first
        'security/gopkz_security.xml',
        'security/ir.model.access.csv',
        # Sequences
        'data/ir_sequence_data.xml',
        # Master data (service types before criteria; teams before stages)
        'data/gopkz_vendor_category_data.xml',
        'data/gopkz_service_type_data.xml',
        'data/crm_team_data.xml',
        'data/crm_stage_data.xml',
        'data/gopkz_scoring_criteria_data.xml',
        'data/gopkz_destination_data.xml',
        'data/crm_lost_reason_data.xml',
        # Views
        'views/gopkz_vendor_category_views.xml',
        'views/gopkz_service_type_views.xml',
        'views/gopkz_scoring_criteria_views.xml',
        'views/gopkz_destination_views.xml',
        'views/crm_lead_views.xml',
        'views/crm_lead_lost_views.xml',
        'views/res_partner_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gopkz_crm/static/src/js/stage_confirm.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
