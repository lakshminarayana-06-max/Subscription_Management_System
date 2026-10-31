# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BrightloopDiscountRule(models.Model):
    _name = 'brightloop.discount.rule'
    _description = 'Brightloop Discount Rule'
    _order = 'id desc'

    name = fields.Char(string='Discount Name', required=True)
    discount_type = fields.Selection([
        ('percent', 'Percentage (%)'),
        ('fixed', 'Fixed Amount (₹)'),
    ], string='Discount Type', required=True, default='percent')
    value = fields.Float(string='Discount Value', required=True, default=0.0)

    min_purchase_amount = fields.Float(string='Minimum Purchase Amount (₹)', default=0.0)
    min_quantity = fields.Float(string='Minimum Quantity', default=1.0)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    max_usage_count = fields.Integer(string='Maximum Usage Limit', default=100)
    current_usage_count = fields.Integer(string='Times Used', default=0, readonly=True)

    applicable_product_ids = fields.Many2many(
        'product.product',
        'brightloop_discount_product_rel',
        'discount_id',
        'product_id',
        string='Applicable Products',
        help="Leave blank to apply across all products on eligible subscriptions"
    )
    applicable_plan_ids = fields.Many2many(
        'brightloop.subscription.plan',
        'brightloop_discount_plan_rel',
        'discount_id',
        'plan_id',
        string='Applicable Subscription Plans',
        help="Leave blank to apply across all plans"
    )
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('value', 'discount_type', 'start_date', 'end_date', 'max_usage_count')
    def _check_discount_constraints(self):
        for rule in self:
            if rule.value <= 0:
                raise ValidationError(_("Discount value must be greater than zero."))
            if rule.discount_type == 'percent' and rule.value > 100.0:
                raise ValidationError(_("Percentage discount cannot exceed 100%."))
            if rule.start_date and rule.end_date and rule.end_date < rule.start_date:
                raise ValidationError(_("End Date cannot be earlier than Start Date."))
            if rule.max_usage_count < 1:
                raise ValidationError(_("Maximum usage count must be at least 1."))

    @api.model
    def get_applicable_discount(self, product=None, plan=None, amount=0.0, quantity=1.0, date=None):
        """Finds the most advantageous active discount rule matching criteria."""
        today = date or fields.Date.context_today(self)
        rules = self.search([
            ('active', '=', True),
            '|', ('start_date', '=', False), ('start_date', '<=', today),
            '|', ('end_date', '=', False), ('end_date', '>=', today),
        ])
        for rule in rules:
            if rule.current_usage_count >= rule.max_usage_count:
                continue
            if rule.min_purchase_amount and amount < rule.min_purchase_amount:
                continue
            if rule.min_quantity and quantity < rule.min_quantity:
                continue
            if rule.applicable_product_ids and product and product.id not in rule.applicable_product_ids.ids:
                continue
            if rule.applicable_plan_ids and plan and plan.id not in rule.applicable_plan_ids.ids:
                continue
            return rule
        return None

    def calculate_discount(self, base_amount):
        """Calculates discount amount in currency value."""
        self.ensure_one()
        if self.discount_type == 'percent':
            return (base_amount * self.value) / 100.0
        elif self.discount_type == 'fixed':
            return min(self.value, base_amount)
        return 0.0

    def increment_usage(self):
        """Increments current usage count and archives if max is reached."""
        for rule in self:
            rule.current_usage_count += 1
            if rule.current_usage_count >= rule.max_usage_count:
                rule.active = False

    @api.model
    def cron_check_discount_expiry(self):
        """Disables discounts past their validity date or usage limits."""
        today = fields.Date.context_today(self)
        expired = self.search([
            ('active', '=', True),
            '|',
            '&', ('end_date', '!=', False), ('end_date', '<', today),
            ('current_usage_count', '>=', 'max_usage_count')
        ])
        for rule in expired:
            rule.active = False
