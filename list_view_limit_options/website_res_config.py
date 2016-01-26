# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2011-TODAY MINORISA (http://www.minorisa.net)
#                             All Rights Reserved.
#                             Minorisa <contact@minorisa.net>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    default_limit_stops = fields.Char(string="Limit Stops",
                                      default_model="list.view.limit.options")
    default_hide_unlimited = fields.Boolean(
        string="Hide Unlimited Option",
        default_model="list.view.limit.options")


    @api.onchange('default_limit_stops')
    def onchangelimitstops(self):
        dls = self.default_limit_stops
        if dls and len(dls) > 0:
            arr = dls.split(',') or []
            new_arr = []
            for a in arr:
                try:
                    v = int(a)
                except:
                    v = False
            if v:
                new_arr.append(str(v))
        if len(new_arr) > 0:
            self.default_limit_stops = ",".join(new_arr)
        else:
            self.default_limit_stops = ""
