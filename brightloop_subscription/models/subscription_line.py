# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BrightloopSubscriptionLine(models.Model):
    _name = 'brightloop.subscription.line'
    _description = 'Brightloop Subscription Line'

    subscription_id = fields.Many2one(
        'brightloop.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        index=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    unit_price = fields.Float(string='Unit Price', required=True, default=0.0)
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    
    discount_id = fields.Many2one('brightloop.discount.rule', string='Applied Discount')
    discount_amount = fields.Float(string='Discount Amount (₹)', default=0.0)
    
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_totals',
        store=True
    )
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_totals',
        store=True
    )
    currency_id = fields.Many2one(
        related='subscription_id.currency_id',
        string='Currency',
        readonly=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.get_product_multiline_description_sale() if hasattr(self.product_id, 'get_product_multiline_description_sale') else self.product_id.name
            # If variant has brand price adjustment, get total calculated price
            if hasattr(self.product_id, 'final_variant_price') and self.product_id.final_variant_price:
                self.unit_price = self.product_id.final_variant_price
            else:
                self.unit_price = self.product_id.lst_price
            if self.product_id.taxes_id:
                self.tax_ids = self.product_id.taxes_id

    @api.depends('quantity', 'unit_price', 'discount_amount', 'tax_ids')
    def _compute_totals(self):
        for line in self:
            base_amount = (line.quantity * line.unit_price) - (line.discount_amount or 0.0)
            if base_amount < 0.0:
                base_amount = 0.0
            line.price_subtotal = base_amount
            
            tax_amount = 0.0
            if line.tax_ids and line.subscription_id.currency_id:
                taxes = line.tax_ids.compute_all(
                    line.unit_price,
                    line.subscription_id.currency_id,
                    line.quantity,
                    product=line.product_id,
                    partner=line.subscription_id.partner_id
                )
                tax_amount = sum(t['amount'] for t in taxes.get('taxes', []))
            line.price_total = base_amount + tax_amount

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("Line quantity must be strictly greater than 0."))
            if line.subscription_id.plan_id and line.quantity < line.subscription_id.plan_id.min_quantity:
                raise ValidationError(_("Quantity (%s) cannot be lower than the plan's minimum quantity (%s).",
                                      line.quantity, line.subscription_id.plan_id.min_quantity))
