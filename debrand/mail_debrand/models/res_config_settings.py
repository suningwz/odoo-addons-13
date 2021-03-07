###################################################################################
#
#    Copyright (c) 2017-today MuK IT GmbH.
#
#    This file is part of MuK Grid Snippets
#    (see https://mukit.at).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

import re
import uuid
import base64

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'
    
    old_mail_theme_primary = fields.Char(
        string="Previous Mail Brand Color", default="#875A7B"
    )
    mail_theme_primary = fields.Char(
        string="Mail Brand Color", default="#875A7B"
    )

    def create(self, values):
        # values.update({"old_mail_theme_primary": self.theme_color_brand})
        print("--------------------------------creater------------------------------------")
        print(values["mail_theme_primary"])
        print(self.mail_theme_primary)
        print("--------------------------------------------------------------------")
        res = super(ResConfigSettings, self).create(values)
        return res

    def write(self, values):
        # values.update({"old_mail_theme_primary": self.theme_color_brand})
        print("--------------------------------------------------------------------")
        print(values)
        print("--------------------------------------------------------------------")
        res = super(ResConfigSettings, self).write(values)
        return res
    
