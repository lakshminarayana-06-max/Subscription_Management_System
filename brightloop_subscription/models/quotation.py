# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BrightloopQuotation(models.Model):
    _name = 'brightloop.quotation'
    _description = 'Brightloop Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Quotation Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    template_id = fields.Many2one('brightloop.quotation.template', string='Quotation Template')
    plan_id = fields.Many2one('brightloop.subscription.plan', string='Subscription Plan', required=True, tracking=True)
    quotation_date = fields.Date(string='Quotation Date', default=fields.Date.context_today, required=True)
    validity_days = fields.Integer(string='Validity (Days)', default=30, required=True)
    validity_date = fields.Date(string='Expiry Date', compute='_compute_validity_date', store=True, readonly=False)
    payment_terms_id = fields.Many2one('account.payment.term', string='Payment Terms')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('quotation', 'Quotation Sent'),
        ('confirmed', 'Confirmed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    line_ids = fields.One2many('brightloop.quotation.line', 'quotation_id', string='Product Lines', copy=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)
    
    amount_untaxed = fields.Monetary(string='Untaxed Amount', compute='_compute_amounts', store=True)
    amount_tax = fields.Monetary(string='Taxes', compute='_compute_amounts', store=True)
    amount_total = fields.Monetary(string='Total', compute='_compute_amounts', store=True)

    subscription_id = fields.Many2one('brightloop.subscription', string='Generated Subscription', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('brightloop.quotation') or _('New')
                if seq == _('New'):
                    last_id = self.search([], order='id desc', limit=1).id or 0
                    seq = f"QT/2026/{str(last_id + 1).zfill(5)}"
                vals['name'] = seq
        return super().create(vals_list)

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.plan_id = self.template_id.plan_id
            self.validity_days = self.template_id.validity_days
            new_lines = []
            for t_line in self.template_id.line_ids:
                new_lines.append((0, 0, {
                    'product_id': t_line.product_id.id,
                    'name': t_line.product_id.name,
                    'quantity': t_line.quantity,
                    'unit_price': t_line.unit_price,
                    'tax_ids': [(6, 0, t_line.product_id.taxes_id.ids)],
                }))
            self.line_ids = False
            self.line_ids = new_lines

    @api.depends('quotation_date', 'validity_days')
    def _compute_validity_date(self):
        for q in self:
            if q.quotation_date and q.validity_days:
                q.validity_date = q.quotation_date + relativedelta(days=q.validity_days)

    @api.depends('line_ids.price_subtotal', 'line_ids.tax_ids')
    def _compute_amounts(self):
        for q in self:
            untaxed = sum(l.price_subtotal for l in q.line_ids)
            tax = 0.0
            for l in q.line_ids:
                if l.tax_ids and q.currency_id:
                    taxes = l.tax_ids.compute_all(l.unit_price, q.currency_id, l.quantity, product=l.product_id, partner=q.partner_id)
                    tax += sum(t['amount'] for t in taxes.get('taxes', []))
            q.amount_untaxed = untaxed
            q.amount_tax = tax
            q.amount_total = untaxed + tax

    def action_send_quotation(self):
        for q in self:
            q.write({'state': 'quotation'})

    def action_confirm(self):
        for q in self:
            today = fields.Date.context_today(self)
            if q.validity_date and q.validity_date < today:
                q.write({'state': 'expired'})
                raise UserError(_("Cannot confirm this quotation because it expired on %s.", q.validity_date))
            q.write({'state': 'confirmed'})

    def action_cancel(self):
        for q in self:
            q.write({'state': 'cancelled'})

    def action_convert_to_subscription(self):
        """Converts accepted quotation into an active subscription."""
        self.ensure_one()
        if self.state not in ['confirmed', 'quotation']:
            raise UserError(_("Only confirmed or sent quotations can be converted to subscriptions."))
        if self.subscription_id:
            raise UserError(_("Quotation has already been converted to subscription %s.", self.subscription_id.name))
        
        today = fields.Date.context_today(self)
        if self.validity_date and self.validity_date < today:
            self.write({'state': 'expired'})
            raise UserError(_("This quotation expired on %s and cannot be converted.", self.validity_date))

        # Check plan availability
        if self.plan_id.end_date and self.plan_id.end_date < today:
            raise UserError(_("The plan '%s' is no longer available (ended %s).", self.plan_id.name, self.plan_id.end_date))

        expiry = self.plan_id.compute_next_billing_date(today)
        sub_vals = {
            'partner_id': self.partner_id.id,
            'plan_id': self.plan_id.id,
            'quotation_id': self.id,
            'start_date': today,
            'expiry_date': expiry,
            'next_billing_date': today,
            'payment_terms_id': self.payment_terms_id.id if self.payment_terms_id else False,
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.quantity,
                'unit_price': line.unit_price,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
            }) for line in self.line_ids]
        }
        subscription = self.env['brightloop.subscription'].create(sub_vals)
        subscription.action_activate()
        self.write({'subscription_id': subscription.id, 'state': 'confirmed'})

        return {
            'name': _('Subscription Created'),
            'type': 'ir.actions.act_window',
            'res_model': 'brightloop.subscription',
            'res_id': subscription.id,
            'view_mode': 'form',
            'target': 'current',
        }


class BrightloopQuotationLine(models.Model):
    _name = 'brightloop.quotation.line'
    _description = 'Quotation Line'

    quotation_id = fields.Many2one('brightloop.quotation', string='Quotation', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    unit_price = fields.Float(string='Unit Price', required=True, default=0.0)
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one(related='quotation_id.currency_id', string='Currency', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            if hasattr(self.product_id, 'final_variant_price') and self.product_id.final_variant_price:
                self.unit_price = self.product_id.final_variant_price
            else:
                self.unit_price = self.product_id.lst_price
            if self.product_id.taxes_id:
                self.tax_ids = self.product_id.taxes_id

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.unit_price
