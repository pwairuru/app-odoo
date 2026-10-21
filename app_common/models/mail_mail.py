# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class MailMail(models.Model):
    _inherit = 'mail.mail'

    # Change default send logic, skip test addresses
    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None, alias_domain_id=False,
              mail_server=False, post_send_callback=None):
        for m in self:
            email_to = m.email_to
            # Skip invalid emails to avoid being banned
            if email_to:
                if email_to.find('no-reply@odooai.cn') != -1 or email_to.find('postmaster-odoo@odooai.cn') != -1:
                    # Valid
                    pass
                elif email_to.find('example.') != -1 or email_to.find('@sunpop.cn') != -1 or email_to.find('@odooapp.cn') != -1:
                    _logger.warning(_("=================Email to ignore: %s") % email_to)
                    self = self - m
        if not self:
            return True
        return super(MailMail, self)._send(auto_commit, raise_exception, smtp_session, alias_domain_id, mail_server, post_send_callback)
