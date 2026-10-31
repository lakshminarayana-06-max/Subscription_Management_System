# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BrightloopQuotationTemplate(models.Model):
    _name = 'brightloop.quotation.template'
    _description = 'Brightloop Quotation Template'

    name = fields.Char(string='Template Name', required=True)
    validity_days = fields.Integer(string='Quotation Validity (Days)', default=30, required=True)
    plan_id = fields.Many2one('brightloop.subscription.plan', string='Subscription Plan', required=True)
    line_ids = fields.One2many('brightloop.quotation.template.line', 'template_id', string='Products & Variants', copy=True)
    note = fields.Html(string='Terms & Conditions / Notes')
    active = fields.Boolean(string='Active', default=True)


class BrightloopQuotationTemplateLine(models.Model):
    _name = 'brightloop.quotation.template.line'
    _description = 'Quotation Template Line'

    template_id = fields.Many2one('brightloop.quotation.template', string='Template', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Default Quantity', default=1.0, required=True)
    unit_price = fields.Float(string='Unit Price', required=True, default=0.0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if hasattr(self.product_id, 'final_variant_price') and self.product_id.final_variant_price:
                self.unit_price = self.product_id.final_variant_price
            else:
                self.unit_price = self.product_id.lst_price
