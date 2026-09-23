# -*- coding: utf-8 -*-
{
    'name': 'GOPKZ CX Helpdesk — Siddiqi Hospitality',
    'version': '19.0.1.0.0',
    'summary': 'Supplier Confirmation, Customer Travel Support, and Vendor/Corporate account-level support for Siddiqi Hospitality',
    'author': 'COGXOL',
    'depends': ['helpdesk', 'gopkz_crm'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Master data — extend vendor categories before team/stage data
        'data/gopkz_vendor_category_data.xml',
        # Teams must exist before stages reference them
        'data/helpdesk_team_data.xml',
        'data/helpdesk_stage_data.xml',
        # Cron
        'data/ir_cron_data.xml',
        # Views
        'views/helpdesk_ticket_views.xml',
        'views/res_partner_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
