# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, SUPERUSER_ID, tools,  _

_logger = logging.getLogger(__name__)


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    # Show field name instead, must override the base model
    def name_get(self):
        res = []
        if self._context.get('show_field_description_only', False) == True:
            for field in self:
                res.append((field.id, field.field_description))
        else:
            for field in self:
                res.append((field.id, '%s (%s,%s)' % (field.field_description, field.name, field.model)))
        return res

    # Allow searching by field name
    @api.model
    def name_search(self, name, domain=None, operator='ilike', limit=100):
        """
        name search that supports searching by tag code
        """
        if name:
            domain = ['|', ('name', operator, name), ('field_description', operator, name)]
            res = self.search_fetch(domain, ['display_name'], limit=limit)
            return [(rec.id, rec.display_name) for rec in res]
        return super().name_search(name, domain, operator, limit)
