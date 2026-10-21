# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

import re
import logging
_logger = logging.getLogger(__name__)

class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'
    _order = 'sequence'
    
    # Change default send logic
    @api.model
    def send_email(self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption=None,
                   smtp_ssl_certificate=None, smtp_ssl_private_key=None,
                   smtp_debug=False, smtp_session=None):
        email_to = message['To']
        
        # Skip invalid emails to avoid being banned
        if email_to:
            BLOCK_EMAIL_PATTERNS = [
                re.compile(r'example\.com'),                     # Block example. addresses
                re.compile(r'@sunpop\.cn'),                   # Block sunpop.cn domain
                re.compile(r'@odooapp\.cn'),                  # Block odooapp.cn domain
            ]
            
            # Check against blocked email patterns
            is_blocked = any(pattern.search(email_to) for pattern in BLOCK_EMAIL_PATTERNS)
            
            if is_blocked:
                _logger.warning(_("=================Email to ignore: %s") % email_to)
                raise AssertionError(_("Email to ignore: %s") % email_to)

        return super(IrMailServer, self).send_email(message, mail_server_id, smtp_server, smtp_port,
                                                    smtp_user, smtp_password, smtp_encryption, smtp_ssl_certificate, smtp_ssl_private_key,
                                                    smtp_debug, smtp_session)
