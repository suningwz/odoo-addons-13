odoo.define('payment_paystack.processing', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');

    var PaymentProcessing = publicWidget.registry.PaymentProcessing;

    return PaymentProcessing.include({
        init: function () {
            this._super.apply(this, arguments);
            this._authInProgress = false;
        },
        willStart: function () {
            return this._super.apply(this, arguments).then(function () {
                return ajax.loadJS("https://js.paystack.co/v1/inline.js");
            })
        },
        _paystackAuthenticate: function (tx) {
            var paystack = PaystackPop.setup({
                key: tx.paystack_public_key, // Replace with your public key
                email: tx.partner_email,
                amount: tx.amount, // the amount value is multiplied by 100 to convert to the lowest currency unit
                currency: tx.currency, // Use GHS for Ghana Cedis or USD for US Dollars
                ref: tx.paystack_payment_reference, // Replace with a reference you generated
                callback: function (response) {
                    //this happens after the payment is completed successfully
                    var reference = response.reference;
                    alert('Payment complete! Reference: ' + reference);
                    ajax.jsonRpc(tx.success_url)
                        .then(function (result) {
                            if (result.error) {
                                return Promise.reject({ "message": { "data": { "message": result.error.message } } });
                            }
                        }).then(function () {
                            window.location = '/payment/process';
                        }).guardedCatch(function () {
                            this._authInProgress = false;
                        });
                    // Make an AJAX call to your server with the reference to verify the transaction
                },
                onClose: function () {
                    ajax.jsonRpc(tx.cancel_url)
                        .then(function (result) {
                            if (result.error) {
                                return Promise.reject({ "message": { "data": { "message": result.error.message } } });
                            }
                        }).then(function () {
                            window.location = '/payment/process';
                        }).guardedCatch(function () {
                            this._authInProgress = false;
                        });
                },
            });
            paystack.openIframe();
        },
        processPolledData: function (transactions) {
            this._super.apply(this, arguments);
            for (var itx = 0; itx < transactions.length; itx++) {
                var tx = transactions[itx];
                if (tx.acquirer_provider === 'paystack' && tx.state === 'pending' && tx.paystack_payment_reference_secret && !this._authInProgress) {
                    this._authInProgress = true;
                    this._paystackAuthenticate(tx);
                }
            }
        },
    });
});