# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.modules import neutralize as modules_neutralize

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    app_system_name = fields.Char('System Name', help="Setup System Name,which replace Odoo",
                                  default='Hoteli', config_parameter='app_system_name')
    app_show_lang = fields.Boolean('Show Quick Language Switcher',
                                   help="When enable,User can quick switch language in user menu",
                                   config_parameter='app_show_lang')
    app_show_debug = fields.Boolean('Show Quick Debug', help="When enable,everyone login can see the debug menu",
                                    config_parameter='app_show_debug')
    app_show_documentation = fields.Boolean('Show Documentation', help="When enable,User can visit user manual",
                                            config_parameter='app_show_documentation')
    # Disabled
    app_show_documentation_dev = fields.Boolean('Show Developer Documentation',
                                                help="When enable,User can visit development documentation")
    app_show_support = fields.Boolean('Show Support', help="When enable,User can vist your support site",
                                      config_parameter='app_show_support')
    app_show_account = fields.Boolean('Show My Account', help="When enable,User can login to your website",
                                      config_parameter='app_show_account')
    app_show_enterprise = fields.Boolean('Show Enterprise Tag', help="Uncheck to hide the Enterprise tag",
                                         config_parameter='app_show_enterprise')
    app_show_share = fields.Boolean('Show Share Dashboard', help="Uncheck to hide the Odoo Share Dashboard",
                                    config_parameter='app_show_share')
    app_show_poweredby = fields.Boolean('Show Powered by Odoo', help="Uncheck to hide the Powered by text",
                                        config_parameter='app_show_poweredby')
    group_show_author_in_apps = fields.Boolean(string="Show Author in Apps Dashboard", implied_group='app_odoo_customize.group_show_author_in_apps',
                                               help="Uncheck to Hide Author and Website in Apps Dashboard")
    module_odoo_referral = fields.Boolean('Show Odoo Referral', help="Uncheck to remove the Odoo Referral")

    app_documentation_url = fields.Char('Documentation Url', config_parameter='app_documentation_url')
    app_documentation_dev_url = fields.Char('Developer Documentation Url', config_parameter='app_documentation_dev_url')
    app_support_url = fields.Char('Support Url', config_parameter='app_support_url')
    app_account_title = fields.Char('My Odoo.com Account Title', config_parameter='app_account_title')
    app_account_url = fields.Char('My Odoo.com Account Url', config_parameter='app_account_url')
    app_enterprise_url = fields.Char('Customize Module Url(eg. Enterprise)', config_parameter='app_enterprise_url')
    app_ribbon_name = fields.Char('Show Demo Ribbon', config_parameter='app_ribbon_name')
    app_navbar_pos_pc = fields.Selection(string="Navbar PC", selection=[
        ('top', 'Top(Default)'),
        ('bottom', 'Bottom'),
        # ('left', 'Left'),
    ], config_parameter='app_navbar_pos_pc')
    app_navbar_pos_mobile = fields.Selection(string="Navbar Mobile", selection=[
        ('top', 'Top(Default)'),
        ('bottom', 'Bottom'),
        # ('left', 'Left'),
    ], config_parameter='app_navbar_pos_mobile')
    
    # Security and speed
    app_debug_only_admin = fields.Boolean('Debug for Admin', config_parameter='app_debug_only_admin',
                                          help="Check to only Debug / Debug Assets for Odoo Admin. Deny debug from url for other user.")
    app_stop_subscribe = fields.Boolean('Stop Odoo Subscribe', help="Check to stop subscribe and follow. This to make odoo speed up.",
                                        config_parameter='app_stop_subscribe')
    # Handle extra modules
    module_app_odoo_doc = fields.Boolean("Help Document Anywhere", help='Get Help Documentation on current odoo operation or topic.')
    module_app_chatgpt = fields.Boolean("Ai Center", help='Use Ai to boost you business.')
    
    # App help docs
    app_doc_root_url = fields.Char('Help of topic domain', config_parameter='app_doc_root_url', default='https://hopesting.com')

    @api.model
    def set_module_url(self, rec=None):
        if not self._app_check_sys_op():
            raise UserError(_('Not allow.'))
        config_parameter = self.env['ir.config_parameter'].sudo()
        app_enterprise_url = config_parameter.get_str('app_enterprise_url', 'https://www.hopesting.com')
        modules = self.env['ir.module.module'].search([('license', 'like', 'OEEL%'), ('website', '!=', False)])
        if modules:
            sql = "UPDATE ir_module_module SET website = '%s' WHERE id IN %s" % (app_enterprise_url, tuple(modules.ids))
            try:
                self._cr.execute(sql)
            except Exception as e:
                pass

    def _check_clear_scope(self, method_name):
        """If clear_scope is not set, return a wizard action to pick the clear scope."""
        if not self.env.context.get('clear_scope'):
            action = self.env['ir.actions.actions']._for_xml_id('app_odoo_customize.action_clear_data_wizard')
            action['context'] = {'clear_method': method_name}
            return action
        return None

    # Clear data, o=objects, s=sequences
    def _remove_app_data(self, o, s=[], method_name=None):
        if method_name:
            wizard = self._check_clear_scope(method_name)
            if wizard:
                return wizard
        if not self._app_check_sys_op():
            raise UserError(_('Not allow.'))
        global_clear = self.env.context.get('clear_scope') == 'global'
        company_id = self.env.company.id if not global_clear else None
        failed_models = []
        for line in o:
            # Check it exists
            try:
                ir_model = self.env['ir.model']._get(line)
                if not ir_model:
                    continue
            except Exception as e:
                _logger.warning('remove data error get ir.model: %s,%s', line, e)
                continue
            obj_name = line
            obj = self.pool.get(obj_name)
            if not obj:
                # A broken install may leave a table with no obj
                t_name = obj_name.replace('.', '_')
            else:
                t_name = obj._table

            # Build the DELETE statement
            where_clauses = []
            params = []

            # Extra handling for template-mixin data, keep templates
            try:
                if obj and hasattr(ir_model, 'is_mixin_template') and hasattr(obj, 'is_template'):
                    where_clauses.append("is_template is not true")
            except Exception as e:
                _logger.exception('remove data error check is_template: %s', e)

            # Multi-company: detect company_id field
            if not global_clear and obj and 'company_id' in obj._fields and obj._fields['company_id'].store:
                where_clauses.append("company_id = %s")
                params.append(company_id)
            elif not global_clear and obj and 'record_company_id' in obj._fields:
                # mail.message uses record_company_id instead of company_id
                where_clauses.append("record_company_id = %s")
                params.append(company_id)
            elif not global_clear:
                # Models without a company field (e.g. mail.followers, mail.activity) are skipped in company mode
                continue

            sql = "delete from %s" % t_name
            if where_clauses:
                sql += " where " + " and ".join(where_clauses)

            try:
                self._cr.execute(sql, tuple(params) if params else ())
                self._cr.commit()
            except Exception as e:
                try:
                    self._cr.rollback()
                except Exception:
                    pass
                failed_models.append(line)
                _logger.warning('remove data error: %s,%s', line, e)
        # Reset sequences
        for line in s:
            if global_clear:
                domain = ['|', ('code', '=ilike', line + '%'), ('prefix', '=ilike', line + '%')]
            else:
                domain = [
                    '|', ('code', '=ilike', line + '%'), ('prefix', '=ilike', line + '%'),
                    ('company_id', '=', company_id),
                ]
            try:
                seqs = self.env['ir.sequence'].sudo().search(domain)
                if seqs.exists():
                    seqs.write({
                        'number_next': 1,
                    })
            except Exception as e:
                _logger.warning('reset sequence data error: %s,%s', line, e)
        if failed_models:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Partial Cleanup Failed'),
                    'message': _('The following models failed to clean up and were skipped: %s') % ', '.join(failed_models),
                    'type': 'warning',
                    'sticky': True,
                    'next': 'soft_reload',
                }
            }
        return True
    
    def remove_sales(self):
        to_removes = [
            # Clear sale orders
            'sale.order.return.line',
            'sale.order.return',
            'helpdesk.ticket',
            'sale.order.fix.line',
            'sale.order.fix',
            'sale.order.line',
            'sale.order',
            # Sales commission, internal use
            # 'sale.commission.line',
            # Never delete quotation templates
            'sale.order.template.option',
            'sale.order.template.line',
            'sale.order.template',
            'sale.requisition.line',
            'sale.requisition',
        ]
        seqs = [
            'sale',
        ]
        return self._remove_app_data(to_removes, seqs, 'remove_sales')

    def remove_product(self):
        to_removes = [
            # Clear product data
            'product.product',
            'product.template',
        ]
        seqs = [
            'product.product',
        ]
        return self._remove_app_data(to_removes, seqs, 'remove_product')

    def remove_product_attribute(self):
        to_removes = [
            # Clear product attributes
            'product.attribute.value',
            'product.attribute',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs, 'remove_product_attribute')

    def remove_pos(self):
        to_removes = [
            # Clear POS orders
            'pos.payment',
            'pos.order.line',
            'pos.order',
            'pos.session',
        ]
        seqs = [
            'pos',
        ]
        res = self._remove_app_data(to_removes, seqs, 'remove_pos')
        if isinstance(res, dict):
            return res

        # Refresh closing values, stored computed fields must reset

        try:
            statement = self.env['account.bank.statement'].search([])
            for s in statement:
                s._end_balance()
        except Exception as e:
            _logger.error('reset sequence data error: %s', e)
        return res

    def remove_purchase(self):
        to_removes = [
            # Clear purchase orders
            'purchase.order.return.line',
            'purchase.order.return',
            'helpdesk.ticket',
            'purchase.order.fix.line',
            'purchase.order.fix',
            'purchase.order.line',
            'purchase.order',
            'purchase.requisition.line',
            'purchase.requisition',
        ]
        seqs = [
            'purchase',
        ]
        return self._remove_app_data(to_removes, seqs, 'remove_purchase')

    def remove_expense(self):
        to_removes = [
            # Clear expenses
            'hr.expense.pc.use.plan',
            'hr.expense',
            'hr.expense.sheet',
            'hr.payslip',
            'hr.payslip.run',
        ]
        seqs = [
            'hr.expense',
        ]
        return self._remove_app_data(to_removes, seqs, 'remove_expense')

    def remove_mrp(self):
        to_removes = [
            # Clear manufacturing orders
            'mrp.workcenter.productivity',
            'mrp.workorder',
            # 'mrp.production.workcenter.line',
            'change.production.qty',
            'mrp.production',
            # 'mrp.production.product.line',
            'mrp.unbuild',
            # Include our app modules
            'mrp.production.plan',
            'change.production.qty',
            'mrp.request.line',
            'mrp.request.line.merge',
            'mrp.request.line.semi',
            'mrp.request.line.semi.merge',
            'mrp.request.plan.line.merge',
            'mrp.request.plan.line.semi.merge',
            'mrp.request',
            'mrp.request.plan',
        ]
        seqs = [
            'mrp',
        ]
        return self._remove_app_data(to_removes, seqs, 'remove_mrp')

    def remove_mrp_bom(self):
        to_removes = [
            # Clear manufacturing BoMs
            'mrp.bom.line',
            'mrp.bom',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs, 'remove_mrp_bom')

    def remove_inventory(self):
        to_removes = [
            # Clear inventory documents
            'stock.quant',
            'stock.move.line',
            'stock.package_level',
            'stock.quantity.history',
            'stock.quant.package',
            'stock.move',
            # 'stock.pack.operation',
            'stock.picking',
            'stock.scrap',
            'stock.picking.batch',
            'stock.inventory.adjustment.name',
            'stock.valuation.adjustment.lines',
            'stock.landed.cost.lines',
            'stock.landed.cost',
            'stock.valuation.layer',
            'stock.lot',
            # 'stock.fixed.putaway.strat',
            'procurement.group',
        ]
        seqs = [
            'stock',
            'picking',
            'procurement.group',
            'product.tracking.default',
            'WH/',
        ]
        return self._remove_app_data(to_removes, seqs, 'remove_inventory')

    def remove_account(self):
        to_removes = [
            # Clear accounting documents
            'payment.transaction',
            # 'account.voucher.line',
            # 'account.voucher',
            # 'account.invoice.line',
            # 'account.invoice.refund',
            # 'account.invoice',
            'account.bank.statement.line',
            'account.payment',
            'account.batch.payment',
            'account.analytic.line',
            # 'account.analytic.account',
            'account.partial.reconcile',
            'account.move.line',
            'hr.expense.sheet',
            'account.move',
            'account.billing',
        ]
        res = self._remove_app_data(to_removes, [], 'remove_account')
        if isinstance(res, dict):
            return res

        # Extra sequence reset
        global_clear = self.env.context.get('clear_scope') == 'global'
        if global_clear:
            domain = [
                '|', ('code', '=ilike', 'account.%'),
                '|', ('prefix', '=ilike', 'BNK1/%'),
                '|', ('prefix', '=ilike', 'CSH1/%'),
                '|', ('prefix', '=ilike', 'INV/%'),
                '|', ('prefix', '=ilike', 'EXCH/%'),
                '|', ('prefix', '=ilike', 'MISC/%'),
                '|', ('prefix', '=ilike', '账单/%'),
                ('prefix', '=ilike', '杂项/%')
            ]
        else:
            domain = [
                ('company_id', '=', self.env.company.id),
                '|', ('code', '=ilike', 'account.%'),
                '|', ('prefix', '=ilike', 'BNK1/%'),
                '|', ('prefix', '=ilike', 'CSH1/%'),
                '|', ('prefix', '=ilike', 'INV/%'),
                '|', ('prefix', '=ilike', 'EXCH/%'),
                '|', ('prefix', '=ilike', 'MISC/%'),
                '|', ('prefix', '=ilike', '账单/%'),
                ('prefix', '=ilike', '杂项/%')
            ]
        try:
            seqs = self.env['ir.sequence'].search(domain)
            if seqs.exists():
                seqs.write({
                    'number_next': 1,
                })
        except Exception as e:
            _logger.error('reset sequence data error: %s,%s', domain, e)
        return res

    def remove_account_chart(self):
        to_removes = [
            # Clear chart of accounts for reset, including enterprise ones
            # Analytic items are base data, delete manually
            # 'account.analytic.account',
            'account.report.budget.item',
            'account.report.budget',
            'account.reconcile.model',
            'account.transfer.model.line',
            'account.transfer.model',
            'res.partner.bank',
            # 'account.invoice',
            'account.payment',
            'account.bank.statement',
            'account.fiscal.position.account',
            'account.fiscal.position.tax',
            'account.tax.repartition.line',
            # 'account.tax.account.tag',
            'account.tax',
            'account.tax.template',
            # 'wizard_multi_charts_accounts',
            'account.account',
            # 'account.journal',
        ]
        seqs = []
        res = self._remove_app_data(to_removes, seqs, 'remove_account_chart')
        if isinstance(res, dict):
            return res
        global_clear = self.env.context.get('clear_scope') == 'global'
        company_id = self.env.company.id if not global_clear else None
        # todo: add remove_hr, payslips use accounts
        # Update account links, many are multi-company fields kept in ir_property, so update on the model
        try:
            field1 = self.env['ir.model.fields']._get('product.template', "taxes_id").id
            field2 = self.env['ir.model.fields']._get('product.template', "supplier_taxes_id").id
            if global_clear:
                sql = "delete from ir_default where (field_id = %s or field_id = %s)" \
                      % (field1, field2)
                sql2 = "update account_journal set bank_account_id=NULL"
            else:
                sql = "delete from ir_default where (field_id = %s or field_id = %s) and company_id=%d" \
                      % (field1, field2, company_id)
                sql2 = "update account_journal set bank_account_id=NULL where company_id=%d;" % company_id
            self._cr.execute(sql)
            self._cr.execute(sql2)
            self._cr.commit()
        except Exception as e:
            try:
                self._cr.rollback()
            except Exception:
                pass
            _logger.error('remove data error: %s,%s', 'account_chart: set tax and account_journal', e)

        # Also handle POS
        if self.env['ir.model']._get('pos.config'):
            self.env['pos.config'].write({
                'journal_id': False,
            })
        #     todo: following res.partner merge, handle all m2o at once instead of per model
        # Partner handling
        try:
            rec = self.env['res.partner'].search([])
            rec.write({
                'property_account_receivable_id': None,
                'property_account_payable_id': None,
            })
            self._cr.commit()
        except Exception as e:
            try:
                self._cr.rollback()
            except Exception:
                pass
            _logger.error('remove data error: %s,%s', 'account_chart', e)
        # Category handling
        try:
            rec = self.env['product.category'].search([])
            rec.write({
                'property_account_income_categ_id': None,
                'property_account_expense_categ_id': None,
                'property_account_creditor_price_difference_categ': None,
                'property_stock_account_input_categ_id': None,
                'property_stock_account_output_categ_id': None,
                'property_stock_valuation_account_id': None,
                'property_stock_journal': None,
            })
            self._cr.commit()
        except Exception as e:
            try:
                self._cr.rollback()
            except Exception:
                pass
            pass
        # Product handling
        try:
            rec = self.env['product.template'].search([])
            rec.write({
                'property_account_income_id': None,
                'property_account_expense_id': None,
                'property_account_creditor_price_difference': None,
            })
            self._cr.commit()
        except Exception as e:
            try:
                self._cr.rollback()
            except Exception:
                pass
            pass
        # POS handling, clear payments and journals
        try:
            rec = self.env['pos.config'].search([])
            rec.write({
                'invoice_journal_id': None,
                'journal_id': None,
                'payment_method_ids': None,
                'fiscal_position_ids': None,
            })
            self._cr.commit()
        except Exception as e:
            try:
                self._cr.rollback()
            except Exception:
                pass
            pass
        # Journal handling
        try:
            rec = self.env['account.journal'].search([])
            rec.write({
                'account_control_ids': None,
                'bank_account_id': None,
                'default_account_id': None,
                'loss_account_id': None,
                'profit_account_id': None,
                'suspense_account_id': None,
            })
            self._cr.commit()
        except Exception as e:
            try:
                self._cr.rollback()
            except Exception:
                pass
            pass  # raise Warning(e)

        # Stock valuation handling
        try:
            rec = self.env['stock.location'].search([])
            rec.write({
                'valuation_in_account_id': None,
                'valuation_out_account_id': None,
            })
            self._cr.commit()
        except Exception as e:
            try:
                self._cr.rollback()
            except Exception:
                pass
            pass  # raise Warning(e)
        # Stock valuation defaults handling
        try:
            # Some journal defaults live in ir.property _set_default, tricky
            todo_list = [
                'property_stock_account_input_categ_id',
                'property_stock_account_output_categ_id',
                'property_stock_valuation_account_id',
                'property_stock_journal',
            ]
            for name in todo_list:
                field_id = self.env['ir.model.fields']._get('product.category', name).id
                prop = self.env['ir.property'].sudo().search([
                    ('fields_id', '=', field_id),
                ])
                if prop:
                    prop.unlink()
            self._cr.commit()
        except Exception as e:
            try:
                self._cr.rollback()
            except Exception:
                pass
            pass  # raise Warning(e)
        # Unlink first
        j_ids = self.env['account.journal'].sudo().search([])
        if j_ids:
            try:
                j_ids.unlink()
                self._cr.commit()
            except Exception as e:
                try:
                    self._cr.rollback()
                except Exception:
                    pass
                pass  # raise Warning(e)
        try:
            c_ids = self.env['res.company'].sudo().search([])
            c_ids.sudo().write({
                'chart_template_id': False,
            })
        except Exception as e:
            try:
                self._cr.rollback()
            except Exception:
                pass
            pass  # raise Warning(e)
        return res

    def remove_project(self):
        to_removes = [
            # Clear projects
            'account.analytic.line',
            'project.task',
            # 'project.forecast',
            'project.update',
            'project.project',
            'project.collaborator',
            'project.milestone',
            # 'project.project.stage',
            'project.task.recurrence',
            # Table name is project_task_user_rel
            'project.task.stage.personal',
        ]
        seqs = []
        # Cache all project alias_ids first, delete the mail.alias records after deleting projects
        alias_ids = []
        try:
            projects = self.env['project.project'].sudo().with_context(active_test=False).search([])
            alias_ids = projects.mapped('alias_id').ids
        except Exception as e:
            pass  # raise Warning(e)
        res = self._remove_app_data(to_removes, seqs, 'remove_project')
        if isinstance(res, dict):
            return res
        # After deleting project records, delete the cached alias_ids
        if alias_ids:
            try:
                aliases = self.env['mail.alias'].sudo().browse(alias_ids).exists()
                if aliases:
                    aliases.unlink()
                    self._cr.commit()
            except Exception as e:
                pass  # raise Warning(e)
        return res

    def remove_quality(self):
        to_removes = [
            # Clear quality data
            'quality.check',
            'quality.alert',
            # 'quality.point',
            # 'quality.alert.stage',
            # 'quality.alert.team',
            # 'quality.point.test_type',
            # 'quality.reason',
            # 'quality.tag',
        ]
        seqs = [
            'quality.check',
            'quality.alert',
            # 'quality.point',
        ]
        return self._remove_app_data(to_removes, seqs, 'remove_quality')

    def remove_quality_setting(self):
        to_removes = [
            # Clear quality settings
            'quality.point',
            'quality.alert.stage',
            'quality.alert.team',
            'quality.point.test_type',
            'quality.reason',
            'quality.tag',
        ]
        return self._remove_app_data(to_removes, method_name='remove_quality_setting')

    def remove_event(self):
        to_removes = [
            # Clear events
            'website.event.menu',
            'event.sponsor',
            'event.sponsor.type',
            'event.meeting.room',
            'event.registration.answer',
            'event.question.answer',
            'event.question',
            'event.quiz',
            'event.quiz.answer',
            'event.quiz.question',
            'event.track',
            'event.track.visitor',
            'event.track.location',
            'event.track.tag',
            'event.track.tag.category',
            'event.track.stage',
            'event.mail.registration',
            'event.mail',
            'event.type.mail',
            'event.lead.rule',
            'event.booth.registration',
            'event.booth',
            'event.type',
            'event.type.booth',
            'event.booth.category',
            'event.registration',
            'event.ticket',
            'event.type.ticket',
            'event.event',
            'event.stage',
            'event.tag',
            'event.tag.category',
            'event.type',
        ]
        seqs = [
            'event.event',
        ]
        return self._remove_app_data(to_removes, seqs, 'remove_event')
    
    def remove_website_blog(self):
        to_removes = [
            # Clear website data, w, w_blog
            'blog.tag.category',
            'blog.tag',
            'blog.post',
            # 'blog.blog',
            # 'product.wishlist',
            # 'website.published.multi.mixin',
            # 'website.published.mixin',
            # 'website.multi.mixin',
            # 'website.visitor',
            # 'website.rewrite',
            # 'website.seo.metadata',
            # 'website.page',
            # 'website.menu',
            # 'website',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs, 'remove_website_blog')

    def remove_website(self):
        to_removes = [
            # Clear website base
            'blog.blog',
            'product.wishlist',
            'website.published.multi.mixin',
            'website.published.mixin',
            'website.multi.mixin',
            'website.visitor',
            'website.rewrite',
            'website.seo.metadata',
            # 'website.page',
            # 'website.menu',
            # 'website',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs, 'remove_website')

    def remove_message(self):
        to_removes = [
            # Clear message data
            'mail.message',
            'mail.followers',
            'mail.activity',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs, 'remove_message')

    def remove_workflow(self):
        to_removes = [
            # Clear workflows
            # 'wkf.workitem',
            # 'wkf.instance',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs, 'remove_workflow')

    def remove_all_biz(self):
        wizard = self._check_clear_scope('remove_all_biz')
        if wizard:
            return wizard
        self.remove_account()
        self.remove_quality()
        self.remove_inventory()
        self.remove_purchase()
        self.remove_mrp()
        self.remove_sales()
        self.remove_project()
        self.remove_pos()
        self.remove_expense()
        self.remove_message()
        return True

    def reset_cat_loc_name(self):
        ids = self.env['product.category'].search([
            ('parent_id', '!=', False)
        ], order='complete_name')
        for rec in ids:
            try:
                rec._compute_complete_name()
            except:
                pass
        ids = self.env['stock.location'].search([
            ('location_id', '!=', False),
            ('usage', '!=', 'views'),
        ], order='complete_name')
        for rec in ids:
            try:
                rec._compute_complete_name()
            except:
                pass
        return True

    def action_set_app_doc_root_to_my(self):
        base_url = self.env['ir.config_parameter'].sudo().get_str('web.base.url')
        self.app_doc_root_url = base_url

    def action_neutralize_database(self):
        if not self._app_check_sys_op():
            raise UserError(_('Not allow.'))
        try:
            modules_neutralize.neutralize_database(self.env.cr)
        except Exception as e:
            _logger.exception('Neutralize database error: %s', e)
            raise UserError(_('Failed to neutralize database. Please check server logs.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Neutralization complete'),
                'message': _('The current database has been successfully neutralized and marked as test.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                },
            }
        }

    def action_mark_database_as_production(self):
        """Mark the database as production. Note: anonymized or deleted data cannot be recovered! Reconfigure mail, payment and similar settings."""
        if not self._app_check_sys_op():
            raise UserError(_('Not allow.'))
        try:
            banner_view = self.env.ref('web.neutralize_banner', raise_if_not_found=False)
            if banner_view:
                banner_view.sudo().write({'active': False})
            ribbon_view = self.env.ref('website.neutralize_ribbon', raise_if_not_found=False)
            if ribbon_view:
                ribbon_view.sudo().write({'active': False})
        except Exception as e:
            _logger.exception('Unneutralize database error: %s', e)
            raise UserError(_('Failed to mark database as production. Please check server logs.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Production mode enabled'),
                'message': _(
                    'This database is now marked as production-like. '
                    'Anonymized or deleted data cannot be restored automatically. '
                    'Please review and reconfigure outgoing email servers, payment providers, and other integrations before using it as a real production database.'
                ),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                },
            }
        }

    # def action_set_all_to_app_doc_root_url(self):
    #     if self.app_doc_root_url:
