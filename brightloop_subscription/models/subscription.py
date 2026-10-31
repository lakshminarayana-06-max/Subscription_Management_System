# -*- coding: utf-8 -*-
import logging
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BrightloopSubscription(models.Model):
    _name = 'brightloop.subscription'
    _description = 'Brightloop Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Subscription Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        index=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        index=True
    )
    plan_id = fields.Many2one(
        'brightloop.subscription.plan',
        string='Subscription Plan',
        required=True,
        tracking=True,
        index=True
    )
    billing_frequency = fields.Selection(
        related='plan_id.billing_frequency',
        string='Billing Frequency',
        store=True,
        readonly=True
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        tracking=True,
        help="Date on which this subscription term ends"
    )
    next_billing_date = fields.Date(
        string='Next Billing Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True
    )
    payment_terms_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms'
    )
    quotation_id = fields.Many2one(
        'brightloop.quotation',
        string='Source Quotation',
        copy=False,
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('quotation', 'Quotation'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)

    line_ids = fields.One2many(
        'brightloop.subscription.line',
        'subscription_id',
        string='Subscription Lines',
        copy=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )
    amount_tax = fields.Monetary(
        string='Taxes',
        compute='_compute_amounts',
        store=True
    )
    amount_discount = fields.Monetary(
        string='Discount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )
    amount_total = fields.Monetary(
        string='Total Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )

    invoice_ids = fields.One2many(
        'account.move',
        'subscription_id',
        string='Invoices'
    )
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_count'
    )

    history_ids = fields.One2many(
        'brightloop.subscription.history',
        'subscription_id',
        string='Status History',
        readonly=True
    )

    pause_reason = fields.Char(string='Pause Reason', tracking=True)
    close_reason = fields.Char(string='Closure / Cancellation Reason', tracking=True)
    active = fields.Boolean(string='Active Record', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('brightloop.subscription') or _('New')
                if seq == _('New'):
                    # Fallback sequence generation if ir.sequence not yet installed
                    last_id = self.search([], order='id desc', limit=1).id or 0
                    seq = f"SUB/2026/{str(last_id + 1).zfill(5)}"
                vals['name'] = seq
        records = super().create(vals_list)
        for record in records:
            record._log_history(False, record.state, _("Subscription created"))
        return records

    def _log_history(self, from_state, to_state, note=''):
        self.env['brightloop.subscription.history'].create({
            'subscription_id': self.id,
            'previous_state': from_state,
            'new_state': to_state,
            'note': note,
            'user_id': self.env.user.id,
        })

    @api.depends('line_ids.price_subtotal', 'line_ids.tax_ids', 'line_ids.discount_amount')
    def _compute_amounts(self):
        for sub in self:
            untaxed = 0.0
            tax_amount = 0.0
            discount_amount = 0.0
            for line in sub.line_ids:
                untaxed += line.price_subtotal
                discount_amount += (line.discount_amount or 0.0)
                # Compute tax for line
                if line.tax_ids:
                    taxes = line.tax_ids.compute_all(
                        line.unit_price,
                        sub.currency_id,
                        line.quantity,
                        product=line.product_id,
                        partner=sub.partner_id
                    )
                    tax_amount += sum(t['amount'] for t in taxes.get('taxes', []))
            sub.amount_untaxed = untaxed
            sub.amount_tax = tax_amount
            sub.amount_discount = discount_amount
            sub.amount_total = untaxed + tax_amount

    def _compute_invoice_count(self):
        for sub in self:
            sub.invoice_count = len(sub.invoice_ids)

    def action_confirm(self):
        for sub in self:
            if not sub.line_ids:
                raise UserError(_("Cannot confirm a subscription with no product lines."))
            old = sub.state
            sub.write({'state': 'confirmed'})
            sub._log_history(old, 'confirmed', _("Quotation accepted & confirmed"))

    def action_activate(self):
        for sub in self:
            old = sub.state
            if not sub.next_billing_date:
                sub.next_billing_date = sub.start_date or fields.Date.context_today(self)
            sub.write({'state': 'active'})
            sub._log_history(old, 'active', _("Subscription officially activated"))

    def action_pause(self, reason=None):
        for sub in self:
            if not sub.plan_id.pause_allowed:
                raise UserError(_("The plan '%s' does not permit pausing.", sub.plan_id.name))
            old = sub.state
            sub.write({
                'state': 'paused',
                'pause_reason': reason or _("Suspended by user request")
            })
            sub._log_history(old, 'paused', sub.pause_reason)

    def action_resume(self):
        for sub in self:
            if sub.state != 'paused':
                raise UserError(_("Only paused subscriptions can be resumed."))
            old = sub.state
            today = fields.Date.context_today(self)
            # Recompute next billing date if paused past the original billing date
            next_bill = sub.next_billing_date
            if next_bill and next_bill < today:
                next_bill = sub.plan_id.compute_next_billing_date(today)
            sub.write({
                'state': 'active',
                'pause_reason': False,
                'next_billing_date': next_bill
            })
            sub._log_history(old, 'active', _("Subscription resumed from pause"))

    def action_renew(self):
        for sub in self:
            if not sub.plan_id.renewal_allowed:
                raise UserError(_("The plan '%s' does not allow renewals.", sub.plan_id.name))
            old = sub.state
            today = fields.Date.context_today(self)
            base_date = sub.expiry_date if (sub.expiry_date and sub.expiry_date >= today) else today
            new_expiry = sub.plan_id.compute_next_billing_date(base_date)
            sub.write({
                'state': 'active',
                'expiry_date': new_expiry,
                'next_billing_date': sub.plan_id.compute_next_billing_date(today) if sub.next_billing_date < today else sub.next_billing_date
            })
            sub._log_history(old, 'active', _("Subscription renewed until %s", new_expiry))

    def action_cancel(self, reason=None):
        for sub in self:
            is_admin = self.env.user.has_group('brightloop_subscription.group_brightloop_admin')
            if not sub.plan_id.early_closure_allowed and not is_admin:
                raise UserError(_("This plan does not permit early closure without administrator privileges."))
            old = sub.state
            sub.write({
                'state': 'cancelled',
                'close_reason': reason or _("Cancelled before term completion")
            })
            sub._log_history(old, 'cancelled', sub.close_reason)

    def action_close(self, reason=None):
        for sub in self:
            old = sub.state
            sub.write({
                'state': 'closed',
                'close_reason': reason or _("Term completed or closed as per plan rules")
            })
            sub._log_history(old, 'closed', sub.close_reason)

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Invoices for %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {
                'default_move_type': 'out_invoice',
                'default_partner_id': self.partner_id.id,
                'default_subscription_id': self.id
            },
        }

    def action_generate_invoice(self):
        """Generates the recurring invoice for this subscription."""
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_("Cannot generate recurring invoice for a non-active subscription."))
        
        # Check for duplicate billing in the current period
        period_start = self.next_billing_date or fields.Date.context_today(self)
        period_end = self.plan_id.compute_next_billing_date(period_start) - relativedelta(days=1)
        
        existing_invoice = self.env['account.move'].search([
            ('subscription_id', '=', self.id),
            ('billing_period_start', '=', period_start),
            ('state', '!=', 'cancel')
        ], limit=1)
        if existing_invoice:
            raise UserError(_("An invoice (%s) has already been generated for period %s to %s.",
                             existing_invoice.name, period_start, period_end))

        invoice_vals = self._prepare_invoice_vals(period_start, period_end)
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Advance next billing date
        new_billing_date = self.plan_id.compute_next_billing_date(period_start)
        self.write({'next_billing_date': new_billing_date})
        
        self._log_history(self.state, self.state, _("Generated recurring invoice %s for period %s - %s",
                                                    invoice.name or 'Draft', period_start, period_end))
        return invoice

    def _prepare_invoice_vals(self, period_start, period_end):
        self.ensure_one()
        invoice_lines = []
        for line in self.line_ids:
            line_vals = {
                'product_id': line.product_id.id,
                'name': f"{line.name} ({period_start} to {period_end})",
                'quantity': line.quantity,
                'price_unit': line.unit_price,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'discount': 0.0,
            }
            # Check applicable discount rules
            applicable_discount = self.env['brightloop.discount.rule'].get_applicable_discount(
                product=line.product_id,
                plan=self.plan_id,
                amount=line.unit_price * line.quantity,
                quantity=line.quantity,
                date=period_start
            )
            if applicable_discount:
                disc_amount = applicable_discount.calculate_discount(line.unit_price * line.quantity)
                line_vals['discount'] = (disc_amount / (line.unit_price * line.quantity)) * 100 if line.unit_price * line.quantity else 0.0
                applicable_discount.increment_usage()

            invoice_lines.append((0, 0, line_vals))

        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'subscription_id': self.id,
            'is_subscription_invoice': True,
            'invoice_date': fields.Date.context_today(self),
            'invoice_date_due': period_start + relativedelta(days=15),
            'billing_period_start': period_start,
            'billing_period_end': period_end,
            'invoice_payment_term_id': self.payment_terms_id.id if self.payment_terms_id else False,
            'invoice_line_ids': invoice_lines,
        }

    # ==========================================
    # CRON / SCHEDULED ACTIONS
    # ==========================================
    @api.model
    def cron_recurring_billing(self):
        """Scans all active subscriptions due for billing and generates invoices automatically."""
        today = fields.Date.context_today(self)
        due_subscriptions = self.search([
            ('state', '=', 'active'),
            ('next_billing_date', '<=', today),
        ])
        _logger.info("Found %s subscriptions due for recurring billing on %s", len(due_subscriptions), today)
        generated_count = 0
        for sub in due_subscriptions:
            try:
                # Check plan availability
                if sub.plan_id.end_date and sub.plan_id.end_date < today and sub.plan_id.auto_close:
                    sub.action_close(reason=_("Plan reached configured end date %s", sub.plan_id.end_date))
                    continue
                # Check subscription expiry
                if sub.expiry_date and sub.expiry_date < today:
                    sub.write({'state': 'expired'})
                    sub._log_history('active', 'expired', _("Subscription expired on %s", sub.expiry_date))
                    continue
                
                sub.action_generate_invoice()
                generated_count += 1
            except Exception as e:
                _logger.error("Failed recurring invoice generation for subscription %s: %s", sub.name, str(e))
        _logger.info("Recurring billing cron complete: Generated %s invoices", generated_count)

    @api.model
    def cron_check_expiries(self):
        """Identifies expired subscriptions and marks them Expired or Closed."""
        today = fields.Date.context_today(self)
        expired = self.search([
            ('state', 'in', ['active', 'paused']),
            ('expiry_date', '!=', False),
            ('expiry_date', '<', today),
        ])
        for sub in expired:
            if sub.plan_id.auto_close:
                sub.action_close(reason=_("Automatic expiry on %s", sub.expiry_date))
            else:
                sub.write({'state': 'expired'})
                sub._log_history('active', 'expired', _("Term expired on %s", sub.expiry_date))

    @api.model
    def cron_renewal_reminders(self):
        """Alerts staff and customers of upcoming renewals within 7 days."""
        today = fields.Date.context_today(self)
        alert_window = today + relativedelta(days=7)
        upcoming_renewals = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '>=', today),
            ('expiry_date', '<=', alert_window),
        ])
        for sub in upcoming_renewals:
            # Schedule activity for responsible staff
            sub.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_("Upcoming Subscription Renewal for %s", sub.partner_id.name),
                note=_("Subscription %s is expiring on %s. Reach out for renewal.", sub.name, sub.expiry_date),
                date_deadline=sub.expiry_date,
                user_id=sub.create_uid.id or self.env.user.id
            )
