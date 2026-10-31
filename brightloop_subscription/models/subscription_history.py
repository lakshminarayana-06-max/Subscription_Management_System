# -*- coding: utf-8 -*-
from odoo import models, fields


class BrightloopSubscriptionHistory(models.Model):
    _name = 'brightloop.subscription.history'
    _description = 'Subscription Status Audit Trail'
    _order = 'create_date desc'

    subscription_id = fields.Many2one('brightloop.subscription', string='Subscription', required=True, ondelete='cascade', index=True)
    date = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True)
    user_id = fields.Many2one('res.users', string='Changed By', default=lambda self: self.env.user)
    previous_state = fields.Char(string='From State')
    new_state = fields.Char(string='To State', required=True)
    note = fields.Text(string='Reason / Details')
