# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResBank(models.Model):
    _inherit = 'res.bank'

    l10n_ng_cbn_code = fields.Char('CBN Code',
        help="Three-digit number assigned by the CBN to identify banking "
        "institutions (CBN is an acronym for the Central Bank of Nigeria)")
