# -*- coding: utf-8 -*-

# Created on 2018-10-12
# author: Hopesting, https://www.hopesting.com
# email: 300883@qq.com
# resource of odooai
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

# Odoo online user manual (updated regularly)
# https://www.hopesting.com/documentation/user/10.0/zh_CN/index.html

# Odoo10 offline user manual download
# https://www.hopesting.com/odoo10_user_manual_document_offline/
# Odoo10 offline developer manual download
# https://www.hopesting.com/odoo10_developer_document_offline/
# description:

from odoo import api, SUPERUSER_ID, _


def pre_init_hook(env):
    try:
        # Point enterprise edition links here
        sql = "UPDATE ir_module_module SET website = '%s' WHERE license like '%s' and website <> ''" % ('https://www.hopesting.com', 'OEEL%')
        env.cr.execute(sql)
        env.cr.commit()
    except Exception as e:
        pass

def post_init_hook(env):
    # a = check_module_installed(cr, ['app_web_superbar','aaaaa'])
    env['ir.module.module'].update_list()
    # cr.execute("")

def uninstall_hook(env):
    """
    Init data, runs on uninstall
    """
    pass

def check_module_installed(env, modules):
    # modules arg is a list, e.g. ['base', 'sale']
    installed = False
    m = env['ir.module.module'].sudo().search([('name', 'in', modules), ('state', 'in', ['installed', 'to install', 'to upgrade'])])
    if len(m) == len(modules):
        installed = True
    return installed

