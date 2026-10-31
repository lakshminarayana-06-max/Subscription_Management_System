# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BrightloopSubscriptionPlan(models.Model):
    _name = 'brightloop.subscription.plan'
    _description = 'Brightloop Subscription Plan'
    _order = 'name asc'

    name = fields.Char(string='Plan Name', required=True, index=True)
    code = fields.Char(string='Plan Code', copy=False)
    product_id = fields.Many2one(
        'product.product',
        string='Related Product',
        required=True,
        domain="[('is_subscription_product', '=', True)]",
        help="Base service or product tied to this recurring plan"
    )
    billing_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], string='Billing Frequency', required=True, default='monthly')

    price = fields.Float(string='Plan Price', required=True, default=0.0)
    min_quantity = fields.Integer(string='Minimum Quantity', default=1, required=True)
    start_date = fields.Date(string='Start Availability Date', default=fields.Date.context_today)
    end_date = fields.Date(string='End Availability Date')
    
    auto_close = fields.Boolean(string='Auto Close on Expiry', default=True,
                               help="Automatically mark subscriptions as Closed when plan availability or subscription period ends")
    early_closure_allowed = fields.Boolean(string='Early Closure Allowed', default=True,
                                         help="Permits customer or staff to cancel before term completes")
    pause_allowed = fields.Boolean(string='Pause Allowed', default=True,
                                  help="Allows temporarily suspending recurring billing")
    renewal_allowed = fields.Boolean(string='Renewal Allowed', default=True,
                                    help="Permits extending term when expiry date arrives")
    
    description = fields.Html(string='Plan Description')
    active = fields.Boolean(string='Active', default=True)

    subscription_count = fields.Integer(
        string='Subscriptions',
        compute='_compute_subscription_count'
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Plan Name must be unique!'),
    ]

    @api.constrains('price', 'min_quantity', 'start_date', 'end_date')
    def _check_plan_constraints(self):
        for plan in self:
            if plan.price < 0.0:
                raise ValidationError(_("Plan price cannot be negative."))
            if plan.min_quantity < 1:
                raise ValidationError(_("Minimum quantity must be at least 1."))
            if plan.start_date and plan.end_date and plan.end_date < plan.start_date:
                raise ValidationError(_("End Availability Date cannot be earlier than Start Availability Date."))

    def _compute_subscription_count(self):
        subscription_obj = self.env['brightloop.subscription']
        for plan in self:
            plan.subscription_count = subscription_obj.search_count([('plan_id', '=', plan.id)])

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'name': _('Subscriptions - %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'brightloop.subscription',
            'view_mode': 'tree,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }

    def compute_next_billing_date(self, from_date):
        """Calculates the subsequent billing date according to frequency."""
        self.ensure_one()
        if not from_date:
            from_date = fields.Date.context_today(self)
        if self.billing_frequency == 'daily':
            return from_date + relativedelta(days=1)
        elif self.billing_frequency == 'weekly':
            return from_date + relativedelta(weeks=1)
        elif self.billing_frequency == 'monthly':
            return from_date + relativedelta(months=1)
        elif self.billing_frequency == 'yearly':
            return from_date + relativedelta(years=1)
        return from_date + relativedelta(months=1)

    @api.model
    def cron_auto_close_plans(self):
        """Scheduled task to close plans whose end availability date has passed."""
        today = fields.Date.context_today(self)
        expired_plans = self.search([
            ('active', '=', True),
            ('end_date', '!=', False),
            ('end_date', '<', today),
            ('auto_close', '=', True)
        ])
        for plan in expired_plans:
            plan.active = False
            # Close active subscriptions on this auto-closing plan
            subs = self.env['brightloop.subscription'].search([
                ('plan_id', '=', plan.id),
                ('state', 'in', ['active', 'paused'])
            ])
            for sub in subs:
                sub.action_close(reason=_("Plan reached configured end availability date: %s", plan.end_date))
