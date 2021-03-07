odoo.define('payment_paystack.paystack', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');

    var qweb = core.qweb;
    var _t = core._t;

    ajax.loadXML('/payment_paystack/static/src/xml/paystack_templates.xml', qweb);

    if ($.blockUI) {
        // our message needs to appear above the modal dialog
        $.blockUI.defaults.baseZ = 2147483647; //same z-index as PaystackCheckout
        $.blockUI.defaults.css.border = '0';
        $.blockUI.defaults.css["background-color"] = '';
        $.blockUI.defaults.overlayCSS["opacity"] = '0.9';
    }

    require('web.dom_ready');
    if (!$('.o_payment_form').length) {
        return Promise.reject("DOM doesn't contain '.o_payment_form'");
    }

    var observer = new MutationObserver(function (mutations, observer) {
        for (var i = 0; i < mutations.length; ++i) {
            for (var j = 0; j < mutations[i].addedNodes.length; ++j) {
                if (mutations[i].addedNodes[j].tagName.toLowerCase() === "form" && mutations[i].addedNodes[j].getAttribute('provider') === 'paystack') {
                    _redirectToPaystackCheckout($(mutations[i].addedNodes[j]));
                }
            }
        }
    });

    function displayError(message) {
        var wizard = $(qweb.render('paystack.error', { 'msg': message || _t('Payment error') }));
        wizard.appendTo($('body')).modal({ 'keyboard': true });
        if ($.blockUI) {
            $.unblockUI();
        }
        $("#o_payment_form_pay").removeAttr('disabled');
    }


    function _redirectToPaystackCheckout(providerForm) {
        // Open Checkout with further options

        var paymentForm = $('.o_payment_form');
        if (!paymentForm.find('i').length) {
            paymentForm.append('<i class="fa fa-spinner fa-spin"/>');
            paymentForm.attr('disabled', 'disabled');
        }

        // ajax.jsonRpc('/payment/process/poll')
        //     .then(function (result) {
        //         console.log(result);
        //         console.table(result);
        //         if (result.error) {
        //             return Promise.reject({ "message": { "data": { "message": result.error.message } } });
        //         }
        //     }).then(function () {
        //         console.log("Done with payment polling");
        //     })
        //     // .guardedCatch(function () {
        //     //     this._authInProgress = false;
        //     // });
        var _getTransactionUrl = function (name) {
            return providerForm.find('input[name="' + name + '"]').val();
        };
        var key = _getTransactionUrl('key');
        var ref = _getTransactionUrl('ref');
        var amount = _getTransactionUrl('amount');
        var email = _getTransactionUrl('email');
        var channels = JSON.parse(_getTransactionUrl('channels'));
        var currency = _getTransactionUrl('currency');
        var label = _getTransactionUrl('label');
        var cancel_url = _getTransactionUrl('cancel_url');
        var success_url = _getTransactionUrl('success_url');

        var paystack = PaystackPop.setup({
            key, 
            email,
            amount,
            currency,
            ref,
            channels,
            label,
            callback: function (response) {
                // var reference = response.reference;
                // alert('Payment complete! Reference: ' + reference);
                window.location = success_url;
                // ajax.jsonRpc(success_url)
                //     .then(function (result) {
                //         if (result.error) {
                //             return Promise.reject({ "message": { "data": { "message": result.error.message } } });
                //         }
                //     }).then(function () {
                //         window.location = '/payment/process';
                //     })
            },
            onClose: function () {
                window.location = cancel_url;   
                // ajax.jsonRpc(cancel_url)
                //     .then(function (result) {
                //         if (result.error) {
                //             return Promise.reject({ "message": { "data": { "message": result.error.message } } });
                //         }
                //     }).then(function () {
                //         window.location = '/payment/process';
                //     })
            },
        });
        paystack.openIframe();

    }

    $.getScript("https://js.paystack.co/v1/inline.js", function (data, textStatus, jqxhr) {
        observer.observe(document.body, { childList: true });
        _redirectToPaystackCheckout($('form[provider="paystack"]'));
    });
});
