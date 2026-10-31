# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    subscription_ids = fields.One2many(
        'brightloop.subscription',
        'partner_id',
        string='Subscriptions'
    )
    subscription_count = fields.Integer(
        string='Total Subscriptions',
        compute='_compute_subscription_stats'
    )
    active_subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_subscription_stats'
    )
    total_invoiced_amount = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_financial_stats',
        currency_field='currency_id'
    )
    total_paid_amount = fields.Monetary(
        string='Total Paid',
        compute='_compute_financial_stats',
        currency_field='currency_id'
    )
    total_outstanding_amount = fields.Monetary(
        string='Total Outstanding',
        compute='_compute_financial_stats',
        currency_field='currency_id'
    )

    def _compute_subscription_stats(self):
        sub_obj = self.env['brightloop.subscription']
        for partner in self:
            partner.subscription_count = sub_obj.search_count([('partner_id', '=', partner.id)])
            partner.active_subscription_count = sub_obj.search_count([
                ('partner_id', '=', partner.id),
                ('state', '=', 'active')
            ])

    def _compute_financial_stats(self):
        for partner in self:
            invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted')
            ])
            invoiced = sum(inv.amount_total for inv in invoices)
            outstanding = sum(inv.amount_residual for inv in invoices)
            partner.total_invoiced_amount = invoiced
            partner.total_outstanding_amount = outstanding
            partner.total_paid_amount = invoiced - outstanding

    def action_view_customer_subscriptions(self):
        self.ensure_one()
        return {
            'name': _('Subscriptions - %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'brightloop.subscription',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
