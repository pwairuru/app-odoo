# -*- coding: utf-8 -*-

# Created on 2023-02-02
# author: Hopesting, https://www.hopesting.com
# email: 300883@qq.com
# resource of odooai
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

# Odoo16online user manual (updated regularly)
# https://www.hopesting.com/documentation/16.0/zh_CN/index.html

# Odoo16online developer manual (updated regularly)
# https://www.hopesting.com/documentation/16.0/zh_CN/developer.html

# Odoo13online user manual (updated regularly)
# https://www.hopesting.com/documentation/user/13.0/zh_CN/index.html

# Odoo13online developer manual (updated regularly)
# https://www.hopesting.com/documentation/13.0/index.html

# Odoo10online user manual (updated regularly)
# https://www.hopesting.com/documentation/user/10.0/zh_CN/index.html

# Odoo10offline user manual download
# https://www.hopesting.com/odoo10_user_manual_document_offline/
# Odoo10offline developer manual download
# https://www.hopesting.com/odoo10_developer_document_offline/

##############################################################################
#    Copyright (C) 2009-TODAY odooai.cn Ltd. https://www.odooai.cn
#    Author: Ivan Deng，300883@qq.com
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#    See <http://www.gnu.org/licenses/>.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
##############################################################################

{
    'name': "Odoo Debrand Common - Core Util and Tools",
    'version': '20.0.26.10.22',
    'author': 'hopesting.com',
    'category': 'Extra tools',
    'website': 'https://www.hopesting.com',
    'live_test_url': 'https://demo.hopesting.com',
    'license': 'LGPL-3',
    'sequence': 2,
    'price': 0.00,
    'currency': 'EUR',
    'images': ['static/description/banner.png'],
    'summary': "Core module for Odoo Debrand apps with common utilities and tools.",
    'description': '''
    1. Quick import data from excel with .py code.
    2. Quick m2o default value helper.
    3. Filter for useless field.
    4. UTC local timezone convert.
    5. Get browser user-agent.
    6. Image to local, image URL to local, media to local attachment.
    7. Log cron job management.
    8. Boost for less no-use mail.
    9. Customize .rng file.
    10. Misc utilities like get distance between two points.
    11. Multi-language Support. Multi-Company Support.
    12. Support Odoo 20,19,18,17,16,15,14,13, Enterprise and Community and odoo.sh Edition.
    13. Full Open Source.

    Setup: server_wide_modules = web,app_common

    1. Quick data import from Excel via .py code
    2. Quick Many2One default value helper
    3. Useless field filter
    4. UTC local timezone conversion
    5. Browser user-agent detection
    6. Images/URLs/media to local attachments
    7. Cron job log management
    8. Less useless mail, better performance
    9. Custom .rng files
    10. Misc utilities like distance between two points
    11. Multi-language and multi-company support
    12. Odoo 20,19,18,17,16,15,14,13, Enterprise and Community editions
    13. Fully open source
    ''',
    'depends': [
        'mail',
        'base_setup',
        'web',
        # todo: workaround for a web_tour bug, remove once fixed upstream in 20
        'web_tour',
    ],
    'data': [
        'data/ir_config_parameter_data.xml',
        'data/ir_module_category_data.xml',
        'data/res_groups_privilege_data.xml',
        'wizard/mail_compose_message_views.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/ir_cron_views.xml',
        # 'report/.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'assets': {
        # navigator.clipboard is missing in non-secure contexts, polyfill early to avoid web_tour clipboard errors
        'web_tour.helpers': [
            ('before', 'web_tour/static/src/tour_helpers/tour_helpers_clipboard.js',
             'app_common/static/src/js/clipboard_polyfill.js'),
        ],
    },
    'demo': [],
    # 'pre_init_hook': 'pre_init_hook',
    # 'post_init_hook': 'post_init_hook',
    # 'uninstall_hook': 'uninstall_hook',
    # Not needed, kept directly in common
    # 'external_dependencies': {'python': ['pyyaml', 'ua-parser', 'user-agents']},
    'installable': True,
    'application': True,
    'auto_install': True,
}
