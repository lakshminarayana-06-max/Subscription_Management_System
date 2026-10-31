# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    subscription_id = fields.Many2one(
        'brightloop.subscription',
        string='Related Subscription',
        index=True
    )
    custom_payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('upi', 'UPI'),
        ('other', 'Other'),
    ], string='Payment Method', default='upi', required=True)
    
    transaction_reference = fields.Char(string='Transaction Reference / UTR', copy=False)
    payment_notes = fields.Text(string='Payment Notes')

    invoice_id = fields.Many2one(
        'account.move',
        string='Target Invoice',
        domain="[('move_type', '=', 'out_invoice'), ('payment_state', 'in', ['not_paid', 'partial'])]"
    )

    @api.constrains('amount', 'invoice_id')
    def _check_payment_amount(self):
        for payment in self:
            if payment.amount <= 0.0:
                raise ValidationError(_("Payment amount must be greater than zero."))
            if payment.invoice_id:
                # Disallow payment exceeding residual amount
                if payment.amount > (payment.invoice_id.amount_residual + 0.01):
                    raise ValidationError(_(
                        "Payment amount (₹%s) cannot exceed the outstanding balance (₹%s) of invoice %s.",
                        payment.amount, payment.invoice_id.amount_residual, payment.invoice_id.name
                    ))
