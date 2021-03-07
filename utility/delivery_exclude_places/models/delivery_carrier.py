# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DeliveryExcludeCountryStateIDs(models.Model):
    _inherit = "delivery.carrier"

    exclude_country_ids = fields.Many2many('res.country', 'delivery_carrier_exclude_country_rel', 'carrier_id', 'country_id', 'Excluded Countries')
    exclude_state_ids = fields.Many2many('res.country.state', 'delivery_carrier_exclude_state_rel', 'carrier_id', 'state_id', 'Excluded States')

    
    def _match_address(self, partner):
        self.ensure_one()
        has_match = super(DeliveryExcludeCountryStateIDs, self)._match_address(partner)
        if self.country_ids and partner.country_id in self.exclude_country_ids:
            return False
        if self.state_ids and partner.state_id in self.exclude_state_ids:
            return False
            
        return has_match
