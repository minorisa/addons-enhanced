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

import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, _
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

    @api.depends('purchase_line.price_total')
    def _amount_all(self):
        for request in self:
            amount_untaxed = amount_tax = 0.0
            for line in request.purchase_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            request.update({
                'amount_untaxed': request.currency_id.round(amount_untaxed),
                'amount_tax': request.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.depends('employee_id')
    def _is_employee(self):
        for e in self:
            e.is_employee = e.employee_id == self.env.user

    @api.depends('validator_id')
    def _is_validator(self):
        for v in self:
            v.is_validator = v.validator_id == self.env.user

    name = fields.Char(
            string="Purchase Request",
            required=True, select=True, copy=False,
            default=lambda a: '/', states=READONLY_STATES,
            help="Unique number of the purchase request, \
            computed automatically when the purchase request is created.")
    partner_id = fields.Many2one(
            'res.partner',
            string="Supplier Reference", copy=True,
            help="Supplier", states=READONLY_STATES)
    description = fields.Char(
            string="Purchase Description", states=READONLY_STATES)
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
    employee_id = fields.Many2one('res.users',
                                  string="Requested By",
                                  required=True, copy=True,
                                  default=lambda s: s.env.user,
                                  states=READONLY_STATES)
    is_employee = fields.Boolean(string="Is Employee Responsible",
                                 compute='_is_employee', store=True)
    validator_id = fields.Many2one(
            'res.users', string="Validated by", copy=False)
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
    fiscal_position_id = fields.Many2one(
            'account.fiscal.position', string='Fiscal Position',
            oldname='fiscal_position')
    company_id = fields.Many2one(
            'res.company', string="Company", required=True, states=READONLY_STATES,
            default=lambda s: s.env.user.company_id)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.fiscal_position_id = False
            self.currency_id = False
        else:
            afpobj = self.env['account.fiscal.position']
            self.fiscal_position_id = afpobj.get_fiscal_position(
                    self.partner_id.id)
            ppc = self.partner_id.property_purchase_currency_id.id
            self.currency_id = ppc or self.env.user.company_id.currency_id.id
        return {}

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
        # po_obj = self.env['purchase.order']
        po_vals = {
            'origin': self.name,
            'partner_ref': self.description,
            'date_order': self.date_request,
            'partner_id': self.partner_id.id,
            'dest_address_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'validator': self.validator_id.id,
            'notes': self.notes,
            'fiscal_position': self.fiscal_position_id.id or False,
        }
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
                'product_qty': line.product_qty,
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

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(
                    line.price_unit, line.purchase_request_id.currency_id,
                    line.product_qty, product=line.product_id,
                    partner=line.purchase_request_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    purchase_request_id = fields.Many2one('purchase.request')
    product_id = fields.Many2one(
            'product.product', string="Product",
            domain=[('purchase_ok', '=', True)],
            change_default=True, required=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes')
    product_uom = fields.Many2one(
            'product.uom', string='Product Unit of Measure', required=True)
    description = fields.Char(string="Description")
    product_qty = fields.Float(
            string='Quantity',
            digits_compute=dp.get_precision('Product Unit of Measure'),
            required=True, default=1.0)
    price_unit = fields.Float(
            string='Unit Price',
            required=True, digits_compute=dp.get_precision('Product Price'))
    price_subtotal = fields.Monetary(
            compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(
            compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Monetary(
            compute='_compute_amount', string='Tax', store=True)
    partner_id = fields.Many2one(
            'res.partner', related='purchase_request_id.partner_id',
            string='Partner', readonly=True, store=True)
    currency_id = fields.Many2one(
            related='purchase_request_id.currency_id', store=True,
            string='Currency', readonly=True)
    date_request = fields.Datetime(
            related='purchase_request_id.date_request',
            string='Purchase Request Date', readonly=True)

    @api.onchange('product_id', 'product_qty', 'product_uom')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return {}

        if self.product_id.uom_id.category_id.id != \
                self.product_uom.category_id.id:
            self.product_uom = self.product_id.uom_po_id
        result['domain'] = {
            'product_uom': [('category_id', '=',
                             self.product_id.uom_id.category_id.id)]}

        prdate = self.purchase_request_id.date_request
        seller = self.product_id._select_seller(
                self.product_id,
                partner_id=self.partner_id,
                quantity=self.product_qty,
                date=prdate and prdate[:10],
                uom_id=self.product_uom)

        price_unit = seller.price if seller else 0.0
        if price_unit and seller and self.purchase_request_id.currency_id \
                and seller.currency_id != self.purchase_request_id.currency_id:
            price_unit = seller.currency_id.compute(
                    price_unit, self.purchase_request_id.currency_id)
        self.price_unit = price_unit

        product_lang = self.product_id.with_context({
            'lang': self.partner_id.lang,
            'partner_id': self.partner_id.id,
        })
        self.description = product_lang.display_name
        if product_lang.description_purchase:
            self.description += '\n' + product_lang.description_purchase

        taxes = self.product_id.supplier_taxes_id
        fpos = self.purchase_request_id.fiscal_position_id
        if fpos:
            self.taxes_id = fpos.map_tax(taxes)

        result['value'] = {
            'description': self.description,
            'product_uom': self.product_uom.id,
            'product_qty': self.product_qty,
            'taxes_id': self.taxes_id.ids,
            'price_unit': self.price_unit,
        }

        return result


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
        return super(MailComposeMessage, self).send_mail()
