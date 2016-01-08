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


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_request_id = fields.Many2one('purchase.request',
                                          string="Associated Purchase Request")

    @api.multi
    def unlink(self):
        prs = self.env['purchase.request']
        for po in self:
            prs |= po.purchase_request_id
        res = super(PurchaseOrder, self).unlink()
        prs.write({
            'state': 'approved',
            'purchase_order_id': False,
        })
        prs.signal_workflow('delete_po')
        return res
