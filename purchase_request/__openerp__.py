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

{
    "name": "Purchase Request",
    "version": "1.0",
    "author": "Minorisa",
    "category": "Purchases Management",
    "website": "http://www.minorisa.net/",
    "license": "GPL-3",
    "summary": "Purchase Request Module",
    "depends": [
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'purchase_request_wkf.xml',
        'purchase_request_sequence.xml',
        'purchase_request_view.xml',
        'purchase_request_data.xml',
        'purchase_order_view.xml',
        'purchase_request_type_view.xml',
    ],
    "init_xml": [],
    "test": [],
    "demo_xml": [],
    "installable": True,
    "active": False,
}
