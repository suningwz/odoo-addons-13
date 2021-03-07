# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2015 WT-IO-IT GmbH (https://www.wt-io-it.at)
#                    Mag. Wolfgang Taferner <wolfgang.taferner@wt-io-it.at>

# List of contributors:
# Mag. Wolfgang Taferner <wolfgang.taferner@wt-io-it.at>
# Josse Colpaert <jco@odoo.com>

{
    "name": "Nigeria - Accounting",
    "version": "0.1",
    "author": "theGleam",
    "website": "https://thegleam.tech",
    'category': 'Accounting/Localizations/Account Charts',
    'summary': "Nigerian Standardized Charts & Tax",
    "description": """

Nigerian charts of accounts.
==========================================================
    Features:
    * Defines Nigerian States
    * Defines Nigerian Enterprise Banks

    TODO:
    * Defines the following chart of account templates:
        * Nigerian General Chart of accounts 2010
    * Defines templates for VAT on sales and purchases
    * Defines tax templates
    * Defines fiscal positions for Nigerian fiscal legislation
    * Defines tax reports U1/U30

    """,
    "depends": [
        "account",
        "base_iban",
        "base_vat",
    ],
    "data": [
        'views/res_bank_view.xml',
        'data/res.country.state.csv',
        'data/res.bank.csv',
    ],
}
