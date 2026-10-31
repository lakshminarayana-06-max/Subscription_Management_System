# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo import fields
from dateutil.relativedelta import relativedelta


class TestBrightloopSubscriptionWorkflow(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.Product = self.env['product.product']
        self.Plan = self.env['brightloop.subscription.plan']
        self.Subscription = self.env['brightloop.subscription']
        self.Quotation = self.env['brightloop.quotation']
        self.Discount = self.env['brightloop.discount.rule']

        # Sample customer
        self.customer = self.Partner.create({
            'name': 'Test Tech Enterprise',
            'email': 'billing@testtech.com',
            'customer_rank': 1,
        })

        # Sample product
        self.product = self.Product.create({
            'name': 'Brightloop Cloud ERP Test',
            'lst_price': 1000.0,
            'is_subscription_product': True,
        })

        # Sample monthly plan
        self.plan = self.Plan.create({
            'name': 'Monthly Pro Test',
            'product_id': self.product.id,
            'billing_frequency': 'monthly',
            'price': 1000.0,
            'min_quantity': 1,
            'auto_close': True,
            'early_closure_allowed': True,
            'pause_allowed': True,
            'renewal_allowed': True,
        })

    def test_01_password_complexity(self):
        """Verify strict password rules: >8 chars, uppercase, lowercase, special char."""
        Users = self.env['res.users']
        # Valid password
        self.assertTrue(Users.validate_password_complexity('BrightLoop@2026!'))
        
        # Too short
        with self.assertRaises(ValidationError):
            Users.validate_password_complexity('Pass@1')
        
        # Missing uppercase
        with self.assertRaises(ValidationError):
            Users.validate_password_complexity('brightloop@2026')
            
        # Missing lowercase
        with self.assertRaises(ValidationError):
            Users.validate_password_complexity('BRIGHTLOOP@2026')
            
        # Missing special char
        with self.assertRaises(ValidationError):
            Users.validate_password_complexity('Brightloop2026')

    def test_02_plan_constraints(self):
        """Verify negative price and 0 quantity are rejected."""
        with self.assertRaises(ValidationError):
            self.Plan.create({
                'name': 'Invalid Negative Plan',
                'product_id': self.product.id,
                'billing_frequency': 'monthly',
                'price': -100.0,
                'min_quantity': 1,
            })
        with self.assertRaises(ValidationError):
            self.Plan.create({
                'name': 'Invalid Zero Qty Plan',
                'product_id': self.product.id,
                'billing_frequency': 'monthly',
                'price': 500.0,
                'min_quantity': 0,
            })

    def test_03_quotation_conversion_to_subscription(self):
        """Verify quotation creation and conversion to active subscription."""
        quote = self.Quotation.create({
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,
            'validity_days': 15,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 2.0,
                'unit_price': 1000.0,
            })]
        })
        self.assertEqual(quote.state, 'draft')
        quote.action_send_quotation()
        self.assertEqual(quote.state, 'quotation')
        quote.action_confirm()
        self.assertEqual(quote.state, 'confirmed')

        # Convert
        action = quote.action_convert_to_subscription()
        self.assertTrue(quote.subscription_id)
        sub = quote.subscription_id
        self.assertEqual(sub.state, 'active')
        self.assertEqual(sub.partner_id.id, self.customer.id)
        self.assertEqual(sub.amount_total, 2000.0)

    def test_04_recurring_billing_and_duplicate_prevention(self):
        """Verify invoice generation, date advancement and duplicate prevention."""
        today = fields.Date.context_today(self)
        sub = self.Subscription.create({
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'confirmed',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 1000.0,
            })]
        })
        sub.action_activate()
        self.assertEqual(sub.state, 'active')

        # First invoice generation
        inv = sub.action_generate_invoice()
        self.assertTrue(inv)
        self.assertEqual(inv.subscription_id.id, sub.id)
        self.assertEqual(sub.next_billing_date, today + relativedelta(months=1))

        # Attempting duplicate invoice for the same period should raise UserError
        sub.next_billing_date = today  # simulate reset
        with self.assertRaises(UserError):
            sub.action_generate_invoice()

    def test_05_pause_and_resume_lifecycle(self):
        """Verify pause, resume, and history tracking."""
        today = fields.Date.context_today(self)
        sub = self.Subscription.create({
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,
            'start_date': today,
            'next_billing_date': today,
            'state': 'active',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'unit_price': 1000.0,
            })]
        })
        sub.action_pause("Client requested vacation freeze")
        self.assertEqual(sub.state, 'paused')
        self.assertEqual(sub.pause_reason, "Client requested vacation freeze")
        
        # Resume
        sub.action_resume()
        self.assertEqual(sub.state, 'active')
        self.assertFalse(sub.pause_reason)

    def test_06_discount_rules(self):
        """Verify discount percentage and max usage limits."""
        disc = self.Discount.create({
            'name': 'Test 10% Off',
            'discount_type': 'percent',
            'value': 10.0,
            'min_purchase_amount': 500.0,
            'max_usage_count': 2,
            'current_usage_count': 0,
            'active': True,
        })
        # Calculate discount on ₹1000
        disc_val = disc.calculate_discount(1000.0)
        self.assertEqual(disc_val, 100.0)

        # Increment usage
        disc.increment_usage()
        self.assertEqual(disc.current_usage_count, 1)
        self.assertTrue(disc.active)

        disc.increment_usage()
        self.assertEqual(disc.current_usage_count, 2)
        self.assertFalse(disc.active)  # Automatically deactivated once max reached
