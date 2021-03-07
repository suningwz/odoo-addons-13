# -*- coding: utf-8 -*-
import odoo
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from unittest.mock import patch
from . import paystack_mocks
from ..models.payment import PAYSTACK_SIGNATURE_AGE_TOLERANCE
from odoo.tools import mute_logger


class PaystackCommon(PaymentAcquirerCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.paystack = cls.env.ref('payment.payment_acquirer_paystack')
        cls.paystack.write({
            'paystack_secret_key': 'sk_test_KJtHgNwt2KS3xM7QJPr4O5E8',
            'paystack_public_key': 'pk_test_QSPnimmb4ZhtkEy3Uhdm4S6J',
            'paystack_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprLVXT5jBLxB',
            'state': 'test',
        })
        cls.token = cls.env['payment.token'].create({
            'name': 'Test Card',
            'acquirer_id': cls.paystack.id,
            'acquirer_ref': 'cus_G27S7FqQ2w3fuH',
            'partner_id': cls.buyer.id,
            'verified': True,
        })
        cls.ideal_icon = cls.env.ref("payment.payment_icon_cc_ideal")
        cls.bancontact_icon = cls.env.ref("payment.payment_icon_cc_bancontact")
        cls.p24_icon = cls.env.ref("payment.payment_icon_cc_p24")
        cls.eps_icon = cls.env.ref("payment.payment_icon_cc_eps")
        cls.giropay_icon = cls.env.ref("payment.payment_icon_cc_giropay")
        cls.all_icons = [cls.ideal_icon, cls.bancontact_icon, cls.p24_icon, cls.eps_icon, cls.giropay_icon]
        cls.paystack.write({'payment_icon_ids': [(5, 0, 0)]})


@odoo.tests.tagged('post_install', '-at_install', '-standard', 'external')
class PaystackTest(PaystackCommon):

    def run(self, result=None):
        with mute_logger('odoo.addons.payment.models.payment_acquirer', 'odoo.addons.payment_paystack.models.payment'):
            PaystackCommon.run(self, result)

    def test_10_paystack_s2s(self):
        self.assertEqual(self.paystack.state, 'test', 'test without test environment')
        # Create transaction
        tx = self.env['payment.transaction'].create({
            'reference': 'paystack_test_10_%s' % fields.datetime.now().strftime('%Y%m%d_%H%M%S'),
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.paystack.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 115.0
        })
        tx.with_context(off_session=True).paystack_s2s_do_transaction()

        # Check state
        self.assertEqual(tx.state, 'done', 'Paystack: Transcation has been discarded.')

    def test_20_paystack_form_render(self):
        self.assertEqual(self.paystack.state, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        # render the button
        self.paystack.render('SO404', 320.0, self.currency_euro.id, values=self.buyer_values).decode('utf-8')

    def test_30_paystack_form_management(self):
        self.assertEqual(self.paystack.state, 'test', 'test without test environment')
        ref = 'paystack_test_30_%s' % fields.datetime.now().strftime('%Y%m%d_%H%M%S')
        tx = self.env['payment.transaction'].create({
            'amount': 4700.0,
            'acquirer_id': self.paystack.id,
            'currency_id': self.currency_euro.id,
            'reference': ref,
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id,
            'payment_token_id': self.token.id,
        })
        res = tx.with_context(off_session=True)._paystack_create_payment_intent()
        tx.paystack_payment_reference = res.get('payment_intent')

        # typical data posted by Paystack after client has successfully paid
        paystack_post_data = {'reference': ref}
        # validate it
        tx.form_feedback(paystack_post_data, 'paystack')
        self.assertEqual(tx.state, 'done', 'Paystack: validation did not put tx into done state')
        self.assertEqual(tx.acquirer_reference, paystack_post_data.get('id'), 'Paystack: validation did not update tx id')

    def test_add_available_payment_method_types_local_enabled(self):
        self.paystack.payment_icon_ids = [(6, 0, [i.id for i in self.all_icons])]
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form'
        }
        paystack_session_data = {}

        self.paystack._add_available_payment_method_types(paystack_session_data, tx_values)

        actual = {pmt for key, pmt in paystack_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card', 'bancontact'}, actual)

    def test_add_available_payment_method_types_local_enabled_2(self):
        self.paystack.payment_icon_ids = [(6, 0, [i.id for i in self.all_icons])]
        tx_values = {
            'billing_partner_country': self.env.ref('base.pl'),
            'currency': self.env.ref('base.PLN'),
            'type': 'form'
        }
        paystack_session_data = {}

        self.paystack._add_available_payment_method_types(paystack_session_data, tx_values)

        actual = {pmt for key, pmt in paystack_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card', 'p24'}, actual)

    def test_add_available_payment_method_types_pmt_does_not_exist(self):
        self.bancontact_icon.unlink()
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form'
        }
        paystack_session_data = {}

        self.paystack._add_available_payment_method_types(paystack_session_data, tx_values)

        actual = {pmt for key, pmt in paystack_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card', 'bancontact'}, actual)

    def test_add_available_payment_method_types_local_disabled(self):
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form'
        }
        paystack_session_data = {}

        self.paystack._add_available_payment_method_types(paystack_session_data, tx_values)

        actual = {pmt for key, pmt in paystack_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card'}, actual)

    def test_add_available_payment_method_types_local_all_but_bancontact(self):
        self.paystack.payment_icon_ids = [(4, icon.id) for icon in self.all_icons if icon.name.lower() != 'bancontact']
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form'
        }
        paystack_session_data = {}

        self.paystack._add_available_payment_method_types(paystack_session_data, tx_values)

        actual = {pmt for key, pmt in paystack_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card'}, actual)

    def test_add_available_payment_method_types_recurrent(self):
        tx_values = {
            'billing_partner_country': self.env.ref('base.be'),
            'currency': self.env.ref('base.EUR'),
            'type': 'form_save'
        }
        paystack_session_data = {}

        self.paystack._add_available_payment_method_types(paystack_session_data, tx_values)

        actual = {pmt for key, pmt in paystack_session_data.items() if key.startswith('payment_method_types')}
        self.assertEqual({'card'}, actual)

    def test_discarded_webhook(self):
        self.assertFalse(self.env['payment.acquirer']._handle_paystack_webhook(dict(type='payment.intent.succeeded')))

    def test_handle_checkout_webhook_no_secret(self):
        self.paystack.paystack_webhook_secret = None

        with self.assertRaises(ValidationError):
            self.env['payment.acquirer']._handle_paystack_webhook(dict(type='checkout.session.completed'))

    @patch('odoo.addons.payment_paystack.models.payment.request')
    @patch('odoo.addons.payment_paystack.models.payment.datetime')
    def test_handle_checkout_webhook(self, dt, request):
        # pass signature verification
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Paystack-Signature': paystack_mocks.checkout_session_signature}
        request.httprequest.data = paystack_mocks.checkout_session_body
        # test setup
        tx = self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.paystack.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 30
        })
        res = tx.with_context(off_session=True)._paystack_create_payment_intent()
        tx.paystack_payment_reference = res.get('payment_intent')
        paystack_object = paystack_mocks.checkout_session_object

        actual = self.paystack._handle_checkout_webhook(paystack_object)

        self.assertTrue(actual)

    @patch('odoo.addons.payment_paystack.models.payment.request')
    @patch('odoo.addons.payment_paystack.models.payment.datetime')
    def test_handle_checkout_webhook_wrong_amount(self, dt, request):
        # pass signature verification
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Paystack-Signature': paystack_mocks.checkout_session_signature}
        request.httprequest.data = paystack_mocks.checkout_session_body
        # test setup
        bad_tx = self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook_wrong_amount',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.paystack.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 10
        })
        wrong_amount_paystack_payment_reference = bad_tx.with_context(off_session=True)._paystack_create_payment_intent()
        tx = self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.paystack.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 30
        })
        tx.paystack_payment_reference = wrong_amount_paystack_payment_reference.get('payment_intent')
        paystack_object = paystack_mocks.checkout_session_object

        actual = self.env['payment.acquirer']._handle_checkout_webhook(paystack_object)

        self.assertFalse(actual)

    def test_handle_checkout_webhook_no_odoo_tx(self):
        paystack_object = paystack_mocks.checkout_session_object

        actual = self.paystack._handle_checkout_webhook(paystack_object)

        self.assertFalse(actual)

    @patch('odoo.addons.payment_paystack.models.payment.request')
    @patch('odoo.addons.payment_paystack.models.payment.datetime')
    def test_handle_checkout_webhook_no_paystack_tx(self, dt, request):
        # pass signature verification
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Paystack-Signature': paystack_mocks.checkout_session_signature}
        request.httprequest.data = paystack_mocks.checkout_session_body
        # test setup
        self.env['payment.transaction'].create({
            'reference': 'tx_ref_test_handle_checkout_webhook',
            'currency_id': self.currency_euro.id,
            'acquirer_id': self.paystack.id,
            'partner_id': self.buyer_id,
            'payment_token_id': self.token.id,
            'type': 'server2server',
            'amount': 30
        })
        paystack_object = paystack_mocks.checkout_session_object

        with self.assertRaises(ValidationError):
            self.paystack._handle_checkout_webhook(paystack_object)

    @patch('odoo.addons.payment_paystack.models.payment.request')
    @patch('odoo.addons.payment_paystack.models.payment.datetime')
    def test_verify_paystack_signature(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Paystack-Signature': paystack_mocks.checkout_session_signature}
        request.httprequest.data = paystack_mocks.checkout_session_body

        actual = self.paystack._verify_paystack_signature()

        self.assertTrue(actual)

    @patch('odoo.addons.payment_paystack.models.payment.request')
    @patch('odoo.addons.payment_paystack.models.payment.datetime')
    def test_verify_paystack_signature_tampered_body(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Paystack-Signature': paystack_mocks.checkout_session_signature}
        request.httprequest.data = paystack_mocks.checkout_session_body.replace(b'1500', b'10')

        with self.assertRaises(ValidationError):
            self.paystack._verify_paystack_signature()

    @patch('odoo.addons.payment_paystack.models.payment.request')
    @patch('odoo.addons.payment_paystack.models.payment.datetime')
    def test_verify_paystack_signature_wrong_secret(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652
        request.httprequest.headers = {'Paystack-Signature': paystack_mocks.checkout_session_signature}
        request.httprequest.data = paystack_mocks.checkout_session_body
        self.paystack.write({
            'paystack_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprL_TAMPERED',
        })

        with self.assertRaises(ValidationError):
            self.paystack._verify_paystack_signature()

    @patch('odoo.addons.payment_paystack.models.payment.request')
    @patch('odoo.addons.payment_paystack.models.payment.datetime')
    def test_verify_paystack_signature_too_old(self, dt, request):
        dt.utcnow.return_value.timestamp.return_value = 1591264652 + PAYSTACK_SIGNATURE_AGE_TOLERANCE + 1
        request.httprequest.headers = {'Paystack-Signature': paystack_mocks.checkout_session_signature}
        request.httprequest.data = paystack_mocks.checkout_session_body

        with self.assertRaises(ValidationError):
            self.paystack._verify_paystack_signature()
