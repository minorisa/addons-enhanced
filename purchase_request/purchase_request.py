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

import logging

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('pending', 'Approval Pending'),
    ('approved', 'Approved'),
    ('denied', 'Denied'),
    ('po_created', 'PO Created'),
]

READONLY_STATES = {
    'pending': [('readonly', True)],
    'approved': [('readonly', True)],
    'denied': [('readonly', True)],
    'po_created': [('readonly', True)],
}


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _order = 'date_request desc, id desc'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _track = {
        'state': {
            'purchase_request.mt_request_sent':
                lambda self, cr, uid, obj, ctx=None: obj.state in ['pending']
        },
    }

    @api.model
    def default_get(self, field_list):
        res = super(PurchaseRequest, self).default_get(field_list)

        if 'employee' not in res:
            employee_obj = self.env['hr.employee']

            domain = [('user_id', '=', self.env.user.id)]
            employee_ids = employee_obj.search(domain, limit=1)
            if employee_ids:
                employee_id = employee_ids[0].id

                res.update({'employee': employee_id})
        return res

    @api.depends('purchase_line')
    def _amount_all(self):
        company_id = self.env.user.company_id
        partner_id = company_id.partner_id
        currency = partner_id.property_product_pricelist_purchase.currency_id
        for p in self:
            val = val1 = 0.0
            for line in p.purchase_line:
                val1 += line.price_subtotal
                for c in line.taxes_id.compute_all(
                        line.price_unit,
                        line.quantity,
                        line.product_id,
                        self.env.user.company_id.partner_id)['taxes']:
                    val += c.get('amount', 0.0)
            p.amount_tax = currency.round(val)
            p.amount_untaxed = currency.round(val1)
            p.amount_total = p.amount_untaxed + p.amount_tax

    @api.depends('employee')
    def _is_employee(self):
        for e in self:
            employee_obj = self.env['hr.employee']

            domain = [('user_id', '=', self.env.user.id)]
            employee_ids = employee_obj.search(domain, limit=1)
            if employee_ids:
                employee_id = employee_ids[0].id

            e.is_employee = e.employee.id == employee_id

    @api.depends('validator')
    def _is_validator(self):
        for v in self:

            employee_obj = self.env['hr.employee']

            domain = [('user_id', '=', self.env.user.id)]
            employee_ids = employee_obj.search(domain, limit=1)
            if employee_ids:
                employee_id = employee_ids[0].id

            v.is_validator = v.validator.id == employee_id

    name = fields.Char(
            string="Purchase Request",
            required=True, select=True, copy=False,
            default=lambda a: '/', states=READONLY_STATES,
            help="Unique number of the purchase request, \
            computed automatically when the purchase request is created.")
    supplier = fields.Many2one(
            'res.partner',
            string="Supplier Reference", copy=True,
            help="Supplier", states=READONLY_STATES, required=True)
    description = fields.Char(string="Description", states=READONLY_STATES)
    date_request = fields.Datetime(string="Request Date", required=True,
                                   copy=True, default=fields.Datetime.now(),
                                   states=READONLY_STATES)
    currency_id = fields.Many2one(
            'res.currency', string="Currency",
            required=True, states=READONLY_STATES,
            default=lambda s: s.env.user.company_id.currency_id.id)
    state = fields.Selection(selection=STATE_SELECTION, string="Status",
                             readonly=True, help="Status",
                             select=True, copy=False, default="draft")
    purchase_line = fields.One2many(
            'purchase.request.line',
            'purchase_request_id',
            'Request Lines',
            states=READONLY_STATES,
            copy=True)
    employee = fields.Many2one('hr.employee',
                               string="Requested By",
                               required=True, copy=True,
                               # default=lambda s: s.env.user,
                               states=READONLY_STATES)
    is_employee = fields.Boolean(string="Is Employee Responsible",
                                 compute='_is_employee', store=True)
    validator = fields.Many2one('hr.employee', string="Validated by",
                                copy=False)

    is_validator = fields.Boolean(string="Is Validator Responsible",
                                  compute='_is_validator', store=True)
    notes = fields.Text('Terms and Conditions')
    request_type = fields.Many2one('purchase.request.type',
                                   string="Purchase Request Type",
                                   required=True, states=READONLY_STATES)
    purchase_order_id = fields.Many2one('purchase.order',
                                        string="Related PO", readonly=True)
    amount_untaxed = fields.Float(compute='_amount_all',
                                  digits_compute=dp.get_precision('Account'),
                                  string="Untaxed Amount")
    amount_tax = fields.Float(compute='_amount_all',
                              digits_compute=dp.get_precision('Account'),
                              string="Taxes")
    amount_total = fields.Float(compute='_amount_all',
                                digits_compute=dp.get_precision('Account'),
                                string="Total")

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            ir = self.env['ir.sequence']
            vals['name'] = ir.next_by_code('purchase.request') or '/'
        purchase = super(PurchaseRequest, self).create(vals)
        return purchase

    @api.multi
    def unlink(self):
        unlink_ids = self.env['purchase.request']
        for s in self:
            if s.state in ['draft']:
                unlink_ids |= s
            else:
                raise ValidationError(
                        _("In order to delete a purchase request, \
                        it must be in Draft state."))

        return super(PurchaseRequest, unlink_ids).unlink()

    @api.multi
    def button_send(self):
        # Send Email
        '''
        This function opens a window to compose an email,
        with the purchase request template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference(
                    'purchase_request',
                    'purchase_request_template')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(
                    'mail',
                    'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'purchase.request',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def _get_po_vals(self):
        po_obj = self.env['purchase.order']
        po_vals = {
            'origin': self.name,
            'partner_ref': self.description,
            'date_order': self.date_request,
            'partner_id': self.supplier.id,
            'dest_address_id': self.supplier.id,
            'currency_id': self.currency_id.id,
            'validator': self.validator.id,
            'notes': self.notes,
        }
        merge_vals = po_obj.onchange_partner_id(self.supplier.id)
        po_vals.update(merge_vals['value'])
        po_vals['fiscal_position'] = po_vals['fiscal_position'].id or False
        merge_vals = po_obj.onchange_dest_address_id(po_vals['partner_id'])
        po_vals.update(merge_vals['value'])
        return po_vals

    @api.model
    def _get_po_line_vals(self, po_id):
        lines = []
        for line in self.purchase_line:
            lines.append({
                'order_id': po_id,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'name': line.description or '',
                'product_qty': line.quantity,
                'price_unit': line.price_unit,
                'taxes_id': [(6, 0, [t.id for t in line.taxes_id])],
                'date_planned': fields.Date.today(),
            })
        return lines

    @api.multi
    def button_create_po(self):
        # Create PO
        self.ensure_one()
        pol_obj = self.env['purchase.order.line']
        po_vals = self._get_po_vals()
        po = self.env['purchase.order'].create(po_vals)
        po.write({'purchase_request_id': self.id})
        po_line_vals = self._get_po_line_vals(po.id)
        for line_val in po_line_vals:
            pol_obj.create(line_val)
        self.signal_workflow('create_po')
        self.write({
            'purchase_order_id': po.id,
            'state': 'po_created',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [[False, 'form']],
            'res_id': po.id,
        }


class PurchaseRequestType(models.Model):
    _name = 'purchase.request.type'
    _order = 'name'

    name = fields.Char(string="Request Type Name", required=True)


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'

    @api.depends('price_unit', 'quantity', 'product_id')
    def _amount_line(self):
        partner_id = self.env.user.company_id.partner_id.id
        for line in self:
            taxes = line.taxes_id.compute_all(
                    line.price_unit,
                    line.quantity,
                    line.product_id, partner_id)
            cur = line.purchase_request_id.currency_id
            line.price_subtotal = cur.round(taxes['total'])
        return True

    def _get_uom_id(self):
        try:
            proxy = self.env['ir.model.data']
            result = proxy.get_object_reference('product', 'product_uom_unit')
            return result[1]
        except Exception:
            return False

    purchase_request_id = fields.Many2one('purchase.request')
    product_id = fields.Many2one('product.product',
                                 string="Product", required=True)
    taxes_id = fields.Many2many('account.tax',
                                'purchase_request_taxe',
                                'ord_id', 'tax_id', string="Taxes")
    product_uom = fields.Many2one('product.uom',
                                  string="Product Unit of Measure",
                                  required=True, default=_get_uom_id)
    description = fields.Char(string="Description", required=True)
    currency_id = fields.Many2one('res.currency',
                                  string="Currency",
                                  related='purchase_request_id.currency_id')
    quantity = fields.Float(
            string="Quantity",
            digits_compute=dp.get_precision('Product Unit of Measure'),
            required=True, default=1.0)
    price_unit = fields.Float(string="Unit Price",
                              required=True,
                              digits_compute=dp.get_precision('Product Price'))
    price_subtotal = fields.Float(compute='_amount_line',
                                  string="Subtotal",
                                  digits_compute=dp.get_precision('Account'))

    @api.onchange('product_id', 'product_uom')
    def onchange_product(self):
        if not self.product_id:
            if not self.product_uom:
                uom_id = self.default_get(['product_uom']).get('product_uom',
                                                               False)
                if uom_id:
                    self.product_uom = self.env['product.uom'].browse(uom_id)
            return False

        if not self.description:
            # The 'or not uom_id' part of the above condition can be removed
            # in master. See commit message of the rev. introducing this line.
            dummy, name = self.product_id.name_get()[0]
            if self.product_id.description_purchase:
                name += '\n' + self.product_id.description_purchase
            self.description = name

        self.price_unit = self.product_id.standard_price or 0.0

        taxes = self.env['account.tax'].browse(
                map(lambda x: x.id, self.product_id.supplier_taxes_id))
        taxes_ids = self.env['account.fiscal.position'].map_tax(taxes)
        self.taxes_id = taxes_ids
        return False


class MailComposeMessage(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        context = dict(self._context)
        if context.get('default_model') == 'purchase.request' \
                and context.get('default_res_id') \
                and context.get('mark_so_as_sent'):
            pr = self.env['purchase.request']
            pr.browse(context['default_res_id']).signal_workflow('send')
        return super(MailComposeMessage, self).send_mail(context=context)
