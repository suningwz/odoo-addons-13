# coding: utf-8

from collections import namedtuple
from datetime import datetime
from hashlib import sha512
import hmac
import json
import logging
import requests
import pprint
from requests.exceptions import HTTPError
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.http import request
from odoo.tools.float_utils import float_round
from odoo.tools import consteq
from odoo.exceptions import ValidationError

from odoo.addons.payment_paystack.controllers.main import PaystackController

_logger = logging.getLogger(__name__)

INT_CURRENCIES = [
    u'NGN', u'GHS'
]


class PaymentAcquirerPaystack(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('paystack', 'Paystack')
    ], ondelete={'paystack': 'set default'})
    paystack_secret_key = fields.Char(groups='base.group_user')
    paystack_public_key = fields.Char(groups='base.group_user')

    def paystack_form_generate_values(self, tx_values):
        self.ensure_one()

        base_url = self.get_base_url()

        partner_email = tx_values.get('partner_email') or tx_values.get('billing_partner_email')
        partner_name = tx_values.get('partner_name', None)
        paystack_payment_data = {
            'key': self.sudo().paystack_public_key,
            'amount': int(float_round(tx_values['amount'] * 100, 2)),
            'email': partner_email,
            'success_url':
                urls.url_join(base_url, PaystackController._success_url) +
                '?reference=%s' % tx_values['reference'],
            'cancel_url':
                urls.url_join(base_url, PaystackController._cancel_url) +
                '?reference=%s' % tx_values['reference'],
            'currency': tx_values['currency'].name,
            'ref': tx_values['reference'],
        }
        if partner_name:
            paystack_payment_data.update({
                'label': '%s | %s'%(partner_email, partner_name)
            })

        self._add_available_payment_channels(paystack_payment_data)
        tx_values.update(paystack_payment_data)
        
        return tx_values

    @api.model
    def _add_available_payment_channels(self, paystack_payment_data):
        """
        Add payment channels you want to make available for the given transaction

        :param paystack_payment_data: dictionary to add the payment channels types to
        """
        import json
        paystack_payment_data.update({
            "channels": json.dumps([
                "card", "bank", "ussd", "qr", 
                "mobile_money", "bank_transfer"])
        })

    def _paystack_request(self, url, data=None, method='POST'):
        self.ensure_one()
        url = urls.url_join(self._get_paystack_api_url(), url)
        headers = {
            'AUTHORIZATION': 'Bearer %s' % self.sudo().paystack_secret_key,
            }
        resp = requests.request(method, url, data=data, headers=headers)
        # Paystack can send 4XX errors for payment failure (not badly-formed requests)
        # check if error `code` is present in 4XX response and raise only if not
        # cfr https://paystack.com/docs/error-codes
        # these can be made customer-facing, as they usually indicate a problem with the payment
        # (e.g. insufficient funds, expired card, etc.)
        
        if not resp.ok and (400 <= resp.status_code < 500 and resp.json().get('message', None)):
            try:
                resp.raise_for_status()
            except HTTPError:
                _logger.error(resp.text)
                paystack_error = resp.json().get('message', "")
                error_msg = " " + (_("Paystack gave us the following info about the problem: '%s'", paystack_error))
                raise ValidationError(error_msg)
        return resp.json()

    @api.model
    def _get_paystack_api_url(self):
        return 'https://api.paystack.co/'

    @api.model
    def paystack_s2s_form_process(self, data):
        if data.get("payment_method") != "card":
            # coming back from a checkout payment and iDeal (or another non-card pm)
            # can't save the token if it's not a card
            # note that in the case of a s2s payment, 'card' wont be
            # in the data dict because we need to fetch it from the paystack server
            _logger.info('unable to save card info from Paystack since the payment was not done with a card')
            return self.env['payment.token']
        customer_data = data.get("customer", {})
        auth_data = data.get("authorization", {})
        last4 = auth_data.get('last4')
        
        paystack_payment_auth_token = self.env['payment.token'].sudo().create({
            'acquirer_id': int(data['acquirer_id']),
            'partner_id': int(data['partner_id']),
            'name': 'XXXXXXXXXXXX%s' % last4,
            'acquirer_ref': auth_data.get("authorization_code"),
            'paystack_auth_code': auth_data.get("authorization_code"),
            'paystack_auth_account_name': auth_data.get("account_name"),
            'paystack_auth_country_code': auth_data.get("country_code"),
            'paystack_auth_reusable': auth_data.get("reusable"),
            'paystack_auth_signature': auth_data.get("signature"),
            'paystack_auth_card_type': auth_data.get("card_type"),
            'paystack_auth_bank': auth_data.get("bank"),

            'paystack_customer_code': customer_data.get("customer_code"),
            'paystack_customer_email': customer_data.get("email"),
            'paystack_customer_id': customer_data.get("id"),
        })
        return paystack_payment_auth_token

    def _handle_paystack_webhook(self, data):
        """Process a webhook payload from Paystack.

        Post-process a webhook payload to act upon the matching payment.transaction
        record in Odoo.
        """
        wh_event = data.get('event')
        if wh_event != 'charge.success':
            _logger.info('unsupported webhook type %s, ignored', wh_event)
            return False

        _logger.info('handling %s webhook event from paystack', wh_event)

        paystack_data = data.get('data', {})
        if not paystack_data:
            raise ValidationError('Paystack Webhook data does not conform to the expected API.')
        if wh_event == 'charge.success':
            return self._handle_checkout_webhook(paystack_data)
        return False

    def _verify_paystack_signature(self):
        """
        :return: true if and only if signature matches hash of payload calculated with secret
        :raises ValidationError: if signature doesn't match
        """
        actual_signature = request.httprequest.headers.get('x-paystack-signature')
        body = request.httprequest.data

        signed_payload = "%s" % (body.decode('utf-8'))

        expected_signature = hmac.new(signed_payload.encode('utf-8'),
                                      "".encode('utf-8'),
                                      sha512).hexdigest()
                                      
        if not consteq(expected_signature, actual_signature):
            _logger.error(
                'incorrect webhook signature from Paystack, check if the webhook signature '
                'in Odoo matches to one in the Paystack dashboard')
            raise ValidationError('incorrect webhook signature')

        return True

    def _handle_checkout_webhook(self, checkout_object: dir):
        """
        Process a checkout.session.completed Paystack web hook event,
        mark related payment successful

        :param checkout_object: provided in the request body
        :return: True if and only if handling went well, False otherwise
        :raises ValidationError: if input isn't usable
        """
        tx_reference = checkout_object.get('reference')
        data = {'reference': tx_reference}
        try:
            odoo_tx = self.env['payment.transaction']._paystack_form_get_tx_from_data(data)
        except ValidationError as e:
            _logger.info('Received notification for tx %s. Skipped it because of %s', tx_reference, e)
            return False

        PaymentAcquirerPaystack._verify_paystack_signature(odoo_tx.acquirer_id)

        url = 'payment_intents/%s' % odoo_tx.reference
        paystack_tx = odoo_tx.acquirer_id._paystack_request(url)

        if 'error' in paystack_tx:
            error = paystack_tx['error']
            raise ValidationError("Could not fetch Paystack payment intent related to %s because of %s; see %s" % (
                odoo_tx, error['message'], error['doc_url']))

        if paystack_tx.get('charges') and paystack_tx.get('charges').get('total_count'):
            charge = paystack_tx.get('charges').get('data')[0]
            data.update(charge)

        return odoo_tx.form_feedback(data, 'paystack')


class PaymentTransactionPaystack(models.Model):
    _inherit = 'payment.transaction'

    def _get_processing_info(self):
        res = super()._get_processing_info()
        if self.acquirer_id.provider == 'paystack':
            paystack_info = {
                'paystack_public_key': self.acquirer_id.paystack_public_key,
                'partner_email': self.partner_email,
            }
            res.update(paystack_info)
        return res

    def form_feedback(self, data, acquirer_name):
        if data.get('reference') and acquirer_name == 'paystack':
            transaction = self.env['payment.transaction'].search([('reference', '=', data['reference'])])

            url = 'transaction/verify/%s' % transaction.reference
            resp = transaction.acquirer_id._paystack_request(url, method="GET")

            data.update(resp)
            _logger.info('Paystack: entering form_feedback with post data %s' % pprint.pformat(data))
        return super(PaymentTransactionPaystack, self).form_feedback(data, acquirer_name)

    def _paystack_charge_authorized_card(self, acquirer_ref=None, email=None):
        charge_params = {
            'amount': int(float_round(self.amount * 100, 2)),
            'currency': self.currency_id.name.lower(),
            'email': email or self.payment_token_id.paystack_customer_email,
            'authorization_code': self.payment_token_id.acquirer_ref,
        }
        _logger.info('_paystack_charge_authorized_card: Sending values to paystack, '
                     'values:\n%s', pprint.pformat(charge_params))
        res = self.acquirer_id._paystack_request('check_authorization', charge_params)
        _logger.info('_paystack_charge_authorized_card: Values received:\n%s', pprint.pformat(res))
        return res

    def paystack_s2s_do_transaction(self, **kwargs):
        self.ensure_one()
        result = self._paystack_charge_authorized_card(
            acquirer_ref=self.payment_token_id.acquirer_ref,
            email=self.partner_email)
        return self._paystack_s2s_validate_tree(result, "charge_auth")

    def _create_paystack_refund(self):
        refund_params = {
            'charge': self.acquirer_reference,
            'amount': int(float_round(self.amount * 100, 2)),
            'metadata[reference]': self.reference,
        }

        _logger.info('_create_paystack_refund: Sending values to paystack URL, values:\n%s', pprint.pformat(refund_params))
        res = self.acquirer_id._paystack_request('refunds', refund_params)
        _logger.info('_create_paystack_refund: Values received:\n%s', pprint.pformat(res))

        return res

    def paystack_s2s_do_refund(self, **kwargs):
        self.ensure_one()
        result = self._create_paystack_refund()
        return self._paystack_s2s_validate_tree(result, action="refund")

    @api.model
    def _paystack_form_get_tx_from_data(self, data):
        """ Given a data dict coming from paystack, verify it and find the related
        transaction record. """
        reference = data.get('reference')
        if not reference:
            paystack_error = data.get('error', {}).get('message', '')
            _logger.error('Paystack: invalid reply received from paystack API, looks like '
                          'the transaction failed. (error: %s)', paystack_error or 'n/a')
            error_msg = _("We're sorry to report that the transaction has failed.")
            if paystack_error:
                error_msg += " " + (_("Paystack gave us the following info about the problem: '%s'") %
                                    paystack_error)
            error_msg += " " + _("Perhaps the problem can be solved by double-checking your "
                                 "credit card details, or contacting your bank?")
            raise ValidationError(error_msg)

        tx = self.search([('reference', '=', reference)])
        if not tx:
            error_msg = _('Paystack: no order found for reference %s', reference)
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        elif len(tx) > 1:
            error_msg = _('Paystack: %(count)s orders found for reference %(reference)s',
                          count=len(tx), reference=reference)
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    def _paystack_s2s_validate_tree(self, tree, action=None):
        self.ensure_one()
        if self.state not in ("draft", "pending"):
            _logger.info('Paystack: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        tree = tree.get('data')
        status = tree.get('status')
        vals = {
            "date": fields.datetime.now(),
        }
        if action in ["charge_auth", "verify_txn"]:
            if status == "success":
                self.write(vals)
                self._set_transaction_done()
                self.execute_callback()
                if self.type == 'form_save':
                    s2s_data = {
                        'authorization': tree.get('authorization'),
                        'acquirer_id': self.acquirer_id.id,
                        'customer': tree.get('customer'),
                        'partner_id': self.partner_id.id,
                        'payment_method': tree.get('channel'),
                    }
                    token = self.acquirer_id.paystack_s2s_form_process(s2s_data)
                    self.payment_token_id = token.id
                if self.payment_token_id:
                    self.payment_token_id.verified = True
                return True
            elif status == "abandoned":
                self._set_transaction_cancel()
                return False
            else:
                error = tree.get("message") or tree.get("gateway_response") 
                self._set_transaction_error(error)
                return False
        elif action == "refund":
            if status:
                self.write(vals)
                self._set_transaction_done()
                self.execute_callback()
                return True
            else:
                error = tree.get("message") 
                self._set_transaction_error(error)
                return False

    def _paystack_form_get_invalid_parameters(self, data):

        payment_data = data.get("data", {})
        invalid_parameters = []
        if payment_data.get('amount') != int(self.amount * 100):
            invalid_parameters.append(('Amount', payment_data.get('amount'), self.amount * 100))
        if payment_data.get('currency') and payment_data.get('currency').upper() != self.currency_id.name:
            invalid_parameters.append(('Currency', payment_data.get('currency'), self.currency_id.name))
        if payment_data.get('reference') and payment_data.get('reference') != self.reference:
            invalid_parameters.append(('Paystack Payment Reference', payment_data.get('reference'), self.reference))
        return invalid_parameters

    def _paystack_form_validate(self, data):
        return self._paystack_s2s_validate_tree(data, action="verify_txn")


class PaymentTokenPaystack(models.Model):
    _inherit = 'payment.token'

    paystack_auth_code = fields.Char('Paystack Authorization Code')
    paystack_auth_account_name = fields.Char('Account name linked to the auth card')
    paystack_auth_bank = fields.Char('Bank linked to the auth card')
    paystack_auth_signature = fields.Char('Paystack signature on the auth card')
    paystack_auth_card_type = fields.Char('Auth card type')
    paystack_auth_country_code = fields.Char('Auth country code')
    paystack_auth_reusable = fields.Boolean('Auth Reusable')

    paystack_customer_email = fields.Char('Customer email address used for this token')
    paystack_customer_id = fields.Char('Paystack customer id')
    paystack_customer_code = fields.Char('Paystack customer code')
