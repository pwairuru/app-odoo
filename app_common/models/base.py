# -*- coding: utf-8 -*-

import requests
import base64
from io import BytesIO
import uuid
from PIL import Image
from datetime import date, datetime, time
import pytz
import re
import unicodedata

import logging

from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.http import request
from odoo.exceptions import UserError
from odoo.orm.domains import Domain
from ..lib.user_agents import parse

_logger = logging.getLogger(__name__)

# Routinely excluded fields
EXCLU_FIELDS = [
    '__last_update',
    'access_token',
    'access_url',
    'access_warning',
    'activity_date_deadline',
    'activity_exception_decoration',
    'activity_exception_icon',
    'activity_ids',
    'activity_state',
    'activity_summary',
    'activity_type_id',
    'activity_user_id',
    'display_name',
    'message_attachment_count',
    'message_channel_ids',
    'message_follower_ids',
    'message_has_error',
    'message_has_error_counter',
    'message_has_sms_error',
    'message_ids',
    'message_is_follower',
    'message_main_attachment_id',
    'message_needaction',
    'message_needaction_counter',
    'message_partner_ids',
    'message_unread',
    'message_unread_counter',
    'website_message_ids',
    'write_date',
    'write_uid',
]


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _app_check_sys_op(self):
        if self.env.user.has_group('base.group_erp_manager'):
            return True
        return False

    @api.model
    def _get_normal_fields(self):
        f_list = []
        for k, v in self._fields.items():
            if k not in EXCLU_FIELDS:
                f_list.append(k)
        return f_list

    @api.model
    def _app_get_m2o_default(self, fieldname, domain=[]):
        if hasattr(self, fieldname) and self._fields[fieldname].type == 'many2one':
            if self._context.get(fieldname) or self._context.get('default_%s' % fieldname):
                return self._context.get(fieldname) or self._context.get('default_%s' % fieldname)
            else:
                if not domain:
                    domain = self._fields[fieldname].domain or []
                try:
                    rec = self.env[self._fields[fieldname].comodel_name].search(domain, limit=1)
                except Exception as e:
                    rec = self.env[self._fields[fieldname].comodel_name].search([], limit=1)
                return rec.id if rec else False
        return False
    
    @api.model
    def _app_dt2local(self, dt_value, return_format=False):
        """
        Convert a datetime with timezone to the current user env timezone and format as string
        :param dt_value: input datetime (naive datetimes default to UTC, from the database)
        :param format_str: output format string, e.g. '%Y-%m-%d %H:%M:%S, defaults to env.lang settings
        :return: formatted time string in the given user timezone
        """
        if not dt_value:
            return dt_value
        # Handle default format
        if not return_format:
            lang_obj = self.env.ref('base.lang_zh_CN')
            lang_ref = 'base.lang_%s' % self.env.lang
            try:
                lang_obj = self.env.ref(lang_ref)
            except Exception as e:
                pass
            return_format = '%s %s' % (lang_obj.date_format, lang_obj.time_format)

        # User timezone, defaults to China
        local_tz = pytz.timezone(self.env.user.tz or 'Etc/GMT-8')
        
        # If input is a string, parse it to datetime first, assuming standard database time format
        if isinstance(dt_value, str):
            dt_value = datetime.strptime(dt_value, return_format)
            
        # Set source timezone to UTC (PostgreSQL usually stores UTC)
        if dt_value.tzinfo is None:
            dt_value = pytz.utc.localize(dt_value)
        
        local_dt = dt_value.astimezone(local_tz)
        return local_dt.strftime(return_format)
    
    @api.model
    def _app_dt2utc(self, dt_value, return_format=False):
        """
        Convert a datetime with timezone to standard UTC and format as string
        :param dt_value: input datetime (naive datetimes default to the user timezone, from the database)
        :param format_str: output format string, e.g. '%Y-%m-%d %H:%M:%S, defaults to env.lang settings
        :return: formatted time string in the given user timezone
        """
        if not dt_value:
            return dt_value
        # Handle default format
        if not return_format:
            lang_obj = self.env.ref('base.lang_zh_CN')
            lang_ref = 'base.lang_%s' % self.env.lang
            try:
                lang_obj = self.env.ref(lang_ref)
            except Exception as e:
                pass
            return_format = '%s %s' % (lang_obj.date_format, lang_obj.time_format)

        # User timezone, defaults to China
        local_tz = pytz.timezone(self.env.user.tz or 'Etc/GMT-8')
        
        # If input is a string, parse it to datetime first, assuming standard database time format in the default user timezone
        if isinstance(dt_value, str):
            dt_value = datetime.strptime(dt_value, return_format)
            
        # Set source timezone to the user timezone (PostgreSQL usually stores UTC)
        if dt_value.tzinfo is None:
            dt_value = local_tz.localize(dt_value)
        
        utc_dt = dt_value.replace(tzinfo=pytz.timezone('UTC'))
        return utc_dt.strftime(return_format)

    @api.model
    def _get_image_from_url(self, url):
        # Return the base64 encoding of this image
        if not self._app_check_sys_op():
            return False
        return get_image_from_url(url)

    @api.model
    def _get_image_url2attachment(self, url, mimetype_list=None):
        # Todo: mimetype filter
        # Generate a local attachment from a remote url, mainly for images for now
        if not self._app_check_sys_op():
            return False
        image, file_name = get_image_url2attachment(url)
        if image and file_name:
            try:
                attachment = self.env['ir.attachment'].sudo()
                res = {
                    'datas': image,
                    'name': file_name,
                    'website_id': False,
                    'res_model': self._name,
                    'res_id': self.id,
                    'public': True,
                }
                if hasattr(attachment, 'is_from_remote'):
                    # First look for a previously stored attachment
                    res.update({
                        'is_from_remote': True,
                        'remote_url': url,
                    })
                    attachment = attachment.search([('is_from_remote', '=', True), ('remote_url', '=', url)], limit=1)
                if not attachment:
                    attachment = attachment.create(res)
                    attachment.generate_access_token()
                return attachment
            except Exception as e:
                _logger.error('get_image_url2attachment error: %s' % str(e))
                return False
        else:
            return False

    @api.model
    def _get_image_base642attachment(self, data):
        if not self._app_check_sys_op():
            return False
        image, file_name = get_image_base642attachment(data)
        if image and file_name:
            try:
                attachment = self.env['ir.attachment'].create({
                    'datas': image,
                    'name': file_name,
                    'website_id': False,
                    'res_model': self._name,
                    'res_id': self.id,
                    'public': True,
                })
                attachment.generate_access_token()
                return attachment
            except Exception as e:
                _logger.error('get_image_base642attachment error: %s' % str(e))
                return False
        else:
            return False
        
    @api.model
    def _get_video_url2attachment(self, url):
        if not self._app_check_sys_op():
            return False
        video, file_name = get_video_url2attachment(url)
        if video and file_name:
            try:
                attachment = self.env['ir.attachment'].create({
                    'datas': video,
                    'name': file_name,
                    'website_id': False,
                    'res_model': self._name,
                    'res_id': self.id,
                    'public': True,
                })
                attachment.generate_access_token()
                return attachment
            except Exception as e:
                _logger.error('get_video_url2attachment error: %s' % str(e))
                return False
        else:
            return False
    
    @api.model
    def get_ua_type(self):
        return get_ua_type()
    
    @api.model
    def deep_merge(self, a, b):
        # todo: only 2 levels handled here, use a third-party lib for deeper levels
        # from deepmerge import always_merger
        return deep_merge(a, b)

    @api.model
    def CoW(self, vals, ref='name', domain=None):
        if domain is None:
            domain = []
        ref_value = vals.get(ref)
        if ref_value is None:
            raise UserError(_('Key field info is required when creating or updating: %s') % ref)

        search_domain = Domain.AND([domain, [(ref, '=', ref_value)]])
        record = self.search(search_domain, limit=1)

        if record:
            record.write(vals)
        else:
            record = self.create(vals)

        return record

    @api.model
    def CoW_list(self, vals_list, ref='name', domain=None):
        if domain is None:
            domain = []

        records = self.env[self._name]
        for vals in vals_list:
            record = self.CoW(vals, ref=ref, domain=domain)
            records |= record

        return records
    
    def _app_sanitize_filename(self, filename):
        """Convert a string to a safe filename, stripping illegal chars and avoiding mojibake

        :param filename: original filename string
        :return: cleaned safe filename
        """
        if not filename:
            return 'unnamed'
        
        # 1. Unicode normalize, convert chars to NFKC form (compatibility decomposition then composition)
        sanitized = unicodedata.normalize('NFKC', filename)
        
        # 2. Replace common illegal filename chars with underscore or hyphen
        # Chars not allowed on Windows and Unix: < > : " / \ | ? *
        # Also replace spaces, tabs, etc. with hyphens
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)
        sanitized = re.sub(r'[\s\t]+', '-', sanitized)
        
        # 3. Strip control chars and other non-printables (keep CJK, latin, digits, common symbols)
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        # 4. Strip leading/trailing spaces, dots, hyphens, underscores
        sanitized = sanitized.strip(' ._-')
        
        # 5. Return a default name if the filename is empty
        if not sanitized:
            return 'unnamed'
        
        # 6. Limit filename length (Windows max 255 chars, leave room for extension and prefix)
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        
        return sanitized

def get_image_from_url(url):
    if not url:
        return None
    if url.startswith('//') or url.startswith('http://') or url.startswith('https://'):
        pass
    else:
        # Handle relative paths
        web_base_url = request.env['ir.config_parameter'].sudo().get_str('web.base.url', '')
        url = web_base_url + url
    try:
        response = requests.get(url, timeout=5)
    except Exception as e:
        return None
    # Return the base64 encoding of this image
    return base64.b64encode(BytesIO(response.content).read())


def get_image_url2attachment(url):
    if not url:
        return None
    try:
        if url.startswith('//'):
            url = 'https:%s' % url
        response = requests.get(url, timeout=90)
    except Exception as e:
        return None, None
    # Return the base64 encoding of this image
    image = base64.b64encode(BytesIO(response.content).read())
    file_name = url.split('/')[-1]
    return image, file_name


def get_image_base642attachment(data):
    if not data:
        return None
    try:
        image_data = data.split(',')[1]
        img = Image.open(BytesIO(base64.b64decode(image_data)))
        img = img.convert('RGB')
        output = BytesIO()
        img.save(output, format='JPEG')
        file_name = str(uuid.uuid4()) + '.jpeg'
        jpeg_data = output.getvalue()
        jpeg_base64 = base64.b64encode(jpeg_data)
        return jpeg_base64, file_name
    except Exception as e:
        return None, None
    
def get_video_url2attachment(url):
    if not url:
        return None
    try:
        if url.startswith('//'):
            url = 'https:%s' % url
        response = requests.get(url, timeout=90)
        video_content = response.content
    except Exception as e:
        return None, None
    # return this video in base64
    base64_video = base64.b64encode(video_content)
    file_name = url.split('/')[-1]
    return base64_video, file_name

def get_ua_type():
    ua = request.httprequest.headers.get('User-Agent')
    ua_parse = str(parse(ua))
    # Temporary agent handling, handle properly in frontend or all in backend later
    # WeChat browser
    #  MicroMessenger: Mozilla/5.0 (Linux; Android 10; ELE-AL00 Build/HUAWEIELE-AL00; wv)
    # AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120
    # MQQBrowser/6.2 TBS/045525 Mobile Safari/537.36 MMWEBID/3135 MicroMessenger/8.0.2.1860(0x2800023B) Process/tools WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64
    # WeChat browser, devtools, web iphone
    # ,Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1
    # wechatdevtools/1.03.2011120 MicroMessenger/7.0.4 Language/zh_CN webview/16178807094901773
    # webdebugger port/27772 token/b91f4a234b918f4e2a5d1a835a09c31e

    # WeChat mini-program
    # MicroMessenger: Mozilla/5.0 (Linux; Android 10; ELE-AL00 Build/HUAWEIELE-AL00; wv)
    # AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2767 MMWEBSDK/20210302 Mobile Safari/537.36 MMWEBID/6689 MicroMessenger/8.0.2.1860(0x2800023B) Process/appbrand2 WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64
    # MiniProgramEnv/android
    # 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_7_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.37(0x18002529) NetType/WIFI Language/zh_CN'
    # WeChat browser, devtools, mini-program, iphone
    # Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1
    # wechatdevtools/1.03.2011120 MicroMessenger/7.0.4 Language/zh_CN webview/
    # Inside WeChat, iphone web
    # Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148
    # MicroMessenger/8.0.3(0x1800032a) NetType/WIFI Language/zh_CN
    # Android app, h5
    # ELE-AL00(Android/10) (cn.erpapp.o20sticks.App/13.20.12.09) Weex/0.26.0 1080x2265

    # web means a regular browser, refine later
    utype = 'web'
    # todo: adopt a ready py lib for WeChat Work
    if 'MicroMessenger' in ua and 'webdebugger' not in ua \
        and ('miniProgram' in ua or 'MiniProgram' in ua or 'MiniProgramEnv' in ua or 'wechatdevtools' in ua):
        # WeChat mini-program and devtools
        utype = 'wxapp'
    elif 'wxwork' in ua:
        utype = 'wxwork'
    elif 'MicroMessenger' in ua:
        # WeChat browser
        utype = 'wxweb'
    elif 'DingTalk' in ua:
        utype = 'dingtalk'
    elif 'cn.erpapp.o20sticks.App' in ua:
        # Android app
        utype = 'native_android'
    elif 'BytedanceWebview' in ua:
        utype = 'dyweb'
    elif 'Chrome Mobile' in ua_parse or 'Mobile Safari' in ua_parse:
    #     Add mobile web
        utype = 'mweb'
    # _logger.warning('=========get ua %s,%s' % (utype, ua))
    return utype

def deep_merge(a, b):
    """
    Deep-merge two 2-level dicts, summing numbers, b wins.
    If a and b share keys, merge their values;
    if a value is a dict, recurse;
    otherwise update a with the value from b.
    """
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                deep_merge(a[key], b[key])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

def int_to_hex_color(color_index):
    color_map = [
        '#a2a2a2', '#ee2d2d', '#dc8534', '#e8bb1d', '#5794dd',
        '#9f628f', '#db8865', '#41a9a2', '#304be0', '#ee2f8a',
        '#61c36e', '#9872e6'
    ]
    if 0 <= color_index < len(color_map):
        return color_map[color_index]
    return color_map[0]
