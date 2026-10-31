# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    subscription_id = fields.Many2one(
        'brightloop.subscription',
        string='Originating Subscription',
        index=True,
        copy=False,
        help="Subscription from which this recurring invoice was generated"
    )
    is_subscription_invoice = fields.Boolean(
        string='Is Subscription Invoice',
        default=False,
        index=True
    )
    billing_period_start = fields.Date(string='Billing Period Start')
    billing_period_end = fields.Date(string='Billing Period End')
    
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        store=True,
        index=True
    )

    @api.depends('invoice_date_due', 'payment_state', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for move in self:
            if move.state == 'posted' and move.payment_state in ['not_paid', 'partial'] and move.invoice_date_due and move.invoice_date_due < today:
                move.is_overdue = True
            else:
                move.is_overdue = False

    @api.constrains('subscription_id', 'billing_period_start', 'state')
    def _check_duplicate_subscription_billing(self):
        for move in self:
            if move.subscription_id and move.billing_period_start and move.state != 'cancel':
                duplicates = self.search([
                    ('id', '!=', move.id),
                    ('subscription_id', '=', move.subscription_id.id),
                    ('billing_period_start', '=', move.billing_period_start),
                    ('state', '!=', 'cancel'),
                ])
                if duplicates:
                    raise ValidationError(_(
                        "Duplicate billing detected! An active invoice (%s) already exists for subscription %s covering period starting %s.",
                        duplicates[0].name, move.subscription_id.name, move.billing_period_start
                    ))
