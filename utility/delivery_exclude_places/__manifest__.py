# -*- coding: utf-8 -*-
{
    'name': "Delivery Exclude Places",

    'description': """
    allow you to add excluded states and countries in delivery carrier
    """,

    'author': "theGleam",
    'website': "https://thegleam.tech",

    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    'category': 'Inventory/Delivery',
    'version': '0.1',

    'depends': ['delivery'],

    'data': [
        'views/delivery_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
