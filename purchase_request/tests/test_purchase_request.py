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

from openerp.tests.common import TransactionCase


class TestPurchaseRequest(TransactionCase):

    def test_purchase_request_type(self):
        """ Testing Purchase Request Type creation... """
        prtobj = self.registry('purchase.request.type')
        prt = prtobj.create(self.cr, self.uid,
                            {'name': 'Test Purchase Request Type'})
        self.assertIsNotNone(prt, 'Error creating Request Type.')

    def test_purchase_request(self):
        """ Testing Purchase Request creation... """
        probj = self.registry('purchase.request')
        prtobj = self.registry('purchase.request.type')
        prlobj = self.registry('purchase.request.line')
        mcmobj = self.registry('mail.compose.message')
        poobj = self.registry('purchase.order')
        cr = self.cr
        uid = self.uid

        # Create Purchase Request Type
        idprt = prtobj.create(cr, uid,
                              {'name': 'Test Purchase Request Type'})

        # Create admin user
        admin = self.browse_ref('base.user_root')

        # Create Purchase Request
        vals = {
            'partner_id': self.ref('base.res_partner_18'),
            'description': 'Test Description',
            'employee_id': admin.id,
            'validator_id': admin.id,
            'request_type': idprt,
            'fiscal_position_id': False,
        }
        idpr = probj.create(cr, uid, vals)
        pr = probj.browse(cr, uid, [idpr])

        self.assertIsNotNone(pr, 'Error creating Purchase Request.')
        self.assertRegexpMatches(pr.name,
                                 'PR[0-9]+',
                                 "Error assigning name sequence.")

        # Create a couple of Purchase Request Lines
        line_vals = {
            'purchase_request_id': pr.id,
            'product_qty': 10,
            'price_unit': 10.0,
            'product_uom': self.ref('product.product_uom_unit'),
            'product_id': self.ref('product.product_product_0'),
        }
        idprl1 = prlobj.create(cr, uid, line_vals)
        prl1 = prlobj.browse(cr, uid, [idprl1])
        line_vals['product_qty'] = 20
        line_vals['price_unit'] = 5.0
        prlobj.create(cr, uid, line_vals)

        # Check if sum calculations are correctly computed
        self.assertEqual(prl1.price_subtotal,
                         100.0,
                         'Error computing line price subtotal.')
        self.assertEqual(pr.amount_total,
                         200.0,
                         'Error computing request total amount.')

        # Send purchase_request and check if state is correct
        context = {
            'default_composition_mode': 'comment',
            'default_use_template': False,
            'default_model': 'purchase.request',
            'mark_so_as_sent': True,
            'default_res_id': pr.id,
        }
        idmcm = mcmobj.create(cr, uid, {
            'subject': 'Hola',
            'body': 'Hola',
        }, context=context)
        mcm = mcmobj.browse(cr, uid, [idmcm], context=context)
        mcm.send_mail()

        # Check whether PR state is 'pending'
        self.assertEqual(pr.state, 'pending', "PR state should be 'pending'")

        # Approve Purchase Request & Check whether state is 'approved'
        pr.signal_workflow('approve')
        self.assertEqual(pr.state, 'approved', "State should be 'approved'")

        # Create PO
        podict = pr.button_create_po()
        poid = podict.get('res_id', False)
        self.assertTrue(poid, 'Error creating associated PO.')
        self.assertEqual(pr.state,
                         'po_created',
                         "Error setting state to 'po_created'.")
        po = poobj.browse(cr, uid, [poid])
        po.button_cancel()
        po.unlink()
        self.assertEqual(pr.state,
                         'approved',
                         "Purchase Request state should be 'approved'")
