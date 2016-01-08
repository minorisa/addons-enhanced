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
    """Tests cases for Purchase Request module"""

    def test_purchase_request_type(self):
        prtobj = self.registry('purchase.request.type')
        prt = prtobj.create(self.cr, self.uid,
                            {'name': 'Test Purchase Request Type'})
        self.assertIsNotNone(
            prt,
            'Purchase Request Type should has not been created.')
