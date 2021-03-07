# -*- coding: utf-8 -*-
import json
import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaystackController(http.Controller):
    _success_url = '/payment/paystack/success'
    _cancel_url = '/payment/paystack/cancel'

    @http.route(['/payment/paystack/success', '/payment/paystack/cancel'], type='http', auth='public')
    def paystack_success(self, **kwargs):
        request.env['payment.transaction'].sudo().form_feedback(kwargs, 'paystack')
        return werkzeug.utils.redirect('/payment/process')

    @http.route('/payment/paystack/webhook', type='json', auth='public', csrf=False)
    def paystack_webhook(self, **kwargs):
        data = json.loads(request.httprequest.data)
        request.env['payment.acquirer'].sudo()._handle_paystack_webhook(data)
        return 'OK'
