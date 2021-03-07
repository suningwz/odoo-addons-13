odoo.define('odoo-debrand.title', function (require) {
    "use strict";

    var WebClient = require('web.AbstractWebClient');
    var session = require('web.session');

    var myWebClient = WebClient.include({

        init: function () {

            this._super();
            this.set('title_part', {"zopenerp": "Dashboard"});
            var domain = session.user_context?.allowed_company_ids;
            var obj = this;
            if (domain){
                this._rpc({
                    fields: ['name', 'id',],
                    domain: [['id', 'in', domain]],
                    model: 'res.company',
                    method: 'search_read',
                })
                    .then(function (result) {
                        obj.set('title_part', { "zopenerp": result[0].name });  // Replacing the name 'Oodo' to selected company name near favicon
                    });
            }
        },
    });
});
