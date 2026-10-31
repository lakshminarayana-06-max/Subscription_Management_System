# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_subscription_product = fields.Boolean(
        string='Available for Subscriptions',
        default=True,
        help="Check this box if this product or software service can be billed as part of a recurring subscription plan."
    )
    brand_attribute_id = fields.Many2one(
        'product.attribute',
        string='Brand Attribute',
        help="Brand configuration attribute for this product"
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    brand_name = fields.Char(
        string='Brand / Edition',
        compute='_compute_brand_info',
        store=True
    )
    brand_price_adjustment = fields.Float(
        string='Brand Price Adjustment (₹)',
        compute='_compute_brand_info',
        store=True,
        help="Specific price addition, e.g., Odoo brand adds ₹560 to base price."
    )
    final_variant_price = fields.Float(
        string='Final Variant Price (₹)',
        compute='_compute_final_variant_price',
        store=True,
        help="Base Sales Price + Attribute & Brand Price Adjustments"
    )

    @api.depends('product_template_attribute_value_ids', 'lst_price')
    def _compute_brand_info(self):
        for product in self:
            brand_val = ""
            adjustment = 0.0
            for ptav in product.product_template_attribute_value_ids:
                if 'brand' in ptav.attribute_id.name.lower():
                    brand_val = ptav.name
                    adjustment += ptav.price_extra
            product.brand_name = brand_val
            product.brand_price_adjustment = adjustment

    @api.depends('lst_price', 'brand_price_adjustment', 'product_template_attribute_value_ids.price_extra')
    def _compute_final_variant_price(self):
        for product in self:
            total_extra = sum(ptav.price_extra for ptav in product.product_template_attribute_value_ids)
            product.final_variant_price = product.lst_price + total_extra
