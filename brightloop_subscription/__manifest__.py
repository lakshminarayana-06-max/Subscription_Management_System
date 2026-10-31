# -*- coding: utf-8 -*-
{
    'name': 'Brightloop Subscription Management System',
    'version': '17.0.1.0.0',
    'summary': 'Enterprise Recurring Billing, Subscription Lifecycle, Plans, Quotations, Discounts & Financial Analytics',
    'sequence': 10,
    'description': """
Brightloop Subscription Management System
==========================================
A unified recurring billing and subscription lifecycle management platform for Brightloop Software.

Features:
---------
* Multi-frequency Subscription Plans (Daily, Weekly, Monthly, Yearly)
* Product & Brand Variant Management with Price Adjustments (e.g., Odoo Brand +₹560)
* Quotations & Quotation Templates with Expiry Tracking and 1-Click Conversion
* Automated Recurring Billing Engine (Odoo account.move integration)
* Duplicate Billing Prevention & Transaction Safety
* Multi-Tier Discount Rules (Fixed & Percentage, Max Usage, Min Purchases)
* Payment Tracking with Partial & Multi-Payment Support (account.payment)
* Role-based Permissions (Admin, Internal Staff, Customer Portal)
* Strict Password Policy & Email Validation
* Financial Analytics Dashboard (10 KPIs, MRR, Revenue Trend, Outstanding vs Collected)
* 10 Comprehensive Reports with Excel/CSV & PDF Export
* Customer Self-Service Portal (/my/subscriptions)
* Automated Scheduled Cron Operations (Renewals, Billing, Expiry, Overdue Checks)
    """,
    'category': 'Sales/Subscriptions',
    'author': 'Brightloop Software',
    'website': 'https://www.brightloopsoftware.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'account',
        'portal',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/ir_cron_data.xml',
        'reports/report_subscription.xml',
        'reports/report_invoice.xml',
        'views/menus.xml',
        'views/subscription_plan_views.xml',
        'views/subscription_views.xml',
        'views/quotation_template_views.xml',
        'views/quotation_views.xml',
        'views/discount_rule_views.xml',
        'views/product_views.xml',
        'views/invoice_views.xml',
        'views/payment_views.xml',
        'views/customer_views.xml',
        'views/staff_views.xml',
        'views/dashboard_views.xml',
        'views/portal_templates.xml',
    ],
    'demo': [
        'data/brightloop_demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'brightloop_subscription/static/src/css/dashboard.css',
            'brightloop_subscription/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
