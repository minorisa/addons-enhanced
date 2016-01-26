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
    "name": "List View Limit Options",
    "version": "1.0",
    "author": "Minorisa",
    "category": "Sales Management",
    "website": "http://www.minorisa.net/",
    "license": "GPL-3",
    "summary": "Enables you to set options in records per page drop-down.",
    "depends": ['website'],
    'data': [
        'list_view_limit_options.xml',
        'website_res_config_view.xml',
    ],
    "init_xml": [],
    "demo_xml": [],
    "installable": True,
    "active": False,
}
