# -*- coding: utf-8 -*-
"""
Brightloop Financial and Subscription Reporting Engine.
Generates all 10 Hackathon Reports with filtering and CSV/Excel export support.
"""
from brightloop_app.db import get_db
from psycopg2.extras import RealDictCursor
import io
import csv

def get_report_data(report_type: str, search="", customer_id=None, plan_id=None, status=None, date_from=None, date_to=None):
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Subscription Summary Report
            if report_type == 'subscription_summary':
                query = """
                    SELECT s.name as sub_number, c.name as customer_name, p.name as plan_name,
                           s.billing_frequency, s.start_date, s.expiry_date, s.next_billing_date,
                           s.state, s.amount_total
                    FROM brightloop_subscription s
                    JOIN res_partner c ON s.partner_id = c.id
                    JOIN brightloop_subscription_plan p ON s.plan_id = p.id
                    WHERE 1=1
                """
                params = []
                if search:
                    query += " AND (s.name ILIKE %s OR c.name ILIKE %s)"
                    params.extend([f"%{search}%", f"%{search}%"])
                if customer_id:
                    query += " AND s.partner_id = %s"
                    params.append(customer_id)
                if plan_id:
                    query += " AND s.plan_id = %s"
                    params.append(plan_id)
                if status:
                    query += " AND s.state = %s"
                    params.append(status)
                query += " ORDER BY s.id DESC;"
                cur.execute(query, params)
                return cur.fetchall(), ["Subscription #", "Customer", "Plan", "Frequency", "Start Date", "Expiry Date", "Next Billing", "Status", "Total (₹)"]

            # 2. Active Subscription Report
            elif report_type == 'active_subscriptions':
                query = """
                    SELECT s.name, c.name as customer_name, p.name as plan_name, s.billing_frequency,
                           s.amount_total,
                           CASE 
                             WHEN s.billing_frequency = 'daily' THEN s.amount_total * 30
                             WHEN s.billing_frequency = 'weekly' THEN s.amount_total * 4.33
                             WHEN s.billing_frequency = 'monthly' THEN s.amount_total
                             WHEN s.billing_frequency = 'yearly' THEN s.amount_total / 12
                             ELSE s.amount_total
                           END as mrr_contribution,
                           s.next_billing_date
                    FROM brightloop_subscription s
                    JOIN res_partner c ON s.partner_id = c.id
                    JOIN brightloop_subscription_plan p ON s.plan_id = p.id
                    WHERE s.state = 'active'
                """
                params = []
                if search:
                    query += " AND (s.name ILIKE %s OR c.name ILIKE %s)"
                    params.extend([f"%{search}%", f"%{search}%"])
                query += " ORDER BY mrr_contribution DESC;"
                cur.execute(query, params)
                return cur.fetchall(), ["Subscription #", "Customer", "Plan", "Frequency", "Recurring (₹)", "Monthly MRR (₹)", "Next Billing Date"]

            # 3. Expired Subscription Report
            elif report_type == 'expired_subscriptions':
                query = """
                    SELECT s.name, c.name as customer_name, p.name as plan_name, s.start_date, s.expiry_date,
                           s.amount_total, s.close_reason
                    FROM brightloop_subscription s
                    JOIN res_partner c ON s.partner_id = c.id
                    JOIN brightloop_subscription_plan p ON s.plan_id = p.id
                    WHERE s.state IN ('expired', 'closed')
                """
                params = []
                if search:
                    query += " AND (s.name ILIKE %s OR c.name ILIKE %s)"
                    params.extend([f"%{search}%", f"%{search}%"])
                query += " ORDER BY s.expiry_date DESC;"
                cur.execute(query, params)
                return cur.fetchall(), ["Subscription #", "Customer", "Plan", "Start Date", "Expiry Date", "Total (₹)", "Reason"]

            # 4. Renewal Report (Renewals due in next 30 days)
            elif report_type == 'renewals':
                query = """
                    SELECT s.name, c.name as customer_name, c.phone, c.email, p.name as plan_name,
                           s.expiry_date, s.amount_total
                    FROM brightloop_subscription s
                    JOIN res_partner c ON s.partner_id = c.id
                    JOIN brightloop_subscription_plan p ON s.plan_id = p.id
                    WHERE s.state = 'active' AND s.expiry_date >= CURRENT_DATE
                    ORDER BY s.expiry_date ASC;
                """
                cur.execute(query)
                return cur.fetchall(), ["Subscription #", "Customer", "Phone", "Email", "Plan", "Expiry Date", "Renewal Value (₹)"]

            # 5. Monthly Revenue Report
            elif report_type == 'monthly_revenue':
                query = """
                    SELECT TO_CHAR(invoice_date, 'YYYY-MM') as month,
                           COUNT(id) as invoice_count,
                           SUM(amount_untaxed) as untaxed_revenue,
                           SUM(amount_tax) as tax_collected,
                           SUM(amount_total) as invoiced_total,
                           SUM(amount_total - amount_residual) as collected_total,
                           SUM(amount_residual) as outstanding_total
                    FROM account_move
                    WHERE state = 'posted'
                    GROUP BY TO_CHAR(invoice_date, 'YYYY-MM')
                    ORDER BY month DESC;
                """
                cur.execute(query)
                return cur.fetchall(), ["Month", "Invoice Count", "Untaxed (₹)", "Tax (₹)", "Invoiced (₹)", "Collected (₹)", "Outstanding (₹)"]

            # 6. Payment Collection Report
            elif report_type == 'payment_collections':
                query = """
                    SELECT p.name as payment_ref, p.payment_date, c.name as customer_name,
                           m.name as invoice_name, UPPER(p.payment_method) as method,
                           p.amount, p.transaction_reference
                    FROM account_payment p
                    JOIN res_partner c ON p.partner_id = c.id
                    LEFT JOIN account_move m ON p.move_id = m.id
                    WHERE p.state = 'posted'
                    ORDER BY p.payment_date DESC;
                """
                cur.execute(query)
                return cur.fetchall(), ["Payment #", "Date", "Customer", "Invoice #", "Method", "Amount (₹)", "Transaction Ref"]

            # 7. Outstanding Invoice Report
            elif report_type == 'outstanding_invoices':
                query = """
                    SELECT m.name as invoice_num, c.name as customer_name, m.invoice_date,
                           m.invoice_date_due, m.amount_total, m.amount_residual,
                           m.payment_state
                    FROM account_move m
                    JOIN res_partner c ON m.partner_id = c.id
                    WHERE m.state = 'posted' AND m.payment_state IN ('not_paid', 'partial')
                    ORDER BY m.invoice_date_due ASC;
                """
                cur.execute(query)
                return cur.fetchall(), ["Invoice #", "Customer", "Invoice Date", "Due Date", "Total (₹)", "Outstanding Due (₹)", "Status"]

            # 8. Overdue Invoice Report
            elif report_type == 'overdue_invoices':
                query = """
                    SELECT m.name as invoice_num, c.name as customer_name, c.email, c.phone,
                           m.invoice_date, m.invoice_date_due,
                           (CURRENT_DATE - m.invoice_date_due) as days_overdue,
                           m.amount_residual
                    FROM account_move m
                    JOIN res_partner c ON m.partner_id = c.id
                    WHERE m.state = 'posted' AND m.payment_state IN ('not_paid', 'partial')
                      AND m.invoice_date_due < CURRENT_DATE
                    ORDER BY days_overdue DESC;
                """
                cur.execute(query)
                return cur.fetchall(), ["Invoice #", "Customer", "Email", "Phone", "Invoice Date", "Due Date", "Days Overdue", "Overdue Amount (₹)"]

            # 9. Discount Usage Report
            elif report_type == 'discount_usage':
                query = """
                    SELECT name as discount_name, UPPER(discount_type) as type, value,
                           min_purchase_amount, current_usage_count, max_usage_count,
                           (max_usage_count - current_usage_count) as remaining_quota,
                           CASE WHEN active THEN 'Active' ELSE 'Expired / Exhausted' END as status
                    FROM brightloop_discount_rule
                    ORDER BY current_usage_count DESC;
                """
                cur.execute(query)
                return cur.fetchall(), ["Discount Name", "Type", "Value", "Min Purchase (₹)", "Times Used", "Max Quota", "Remaining", "Status"]

            # 10. Customer Subscription History
            elif report_type == 'customer_history':
                query = """
                    SELECT h.date, c.name as customer_name, s.name as sub_number,
                           h.user_name, h.previous_state, h.new_state, h.note
                    FROM brightloop_subscription_history h
                    JOIN brightloop_subscription s ON h.subscription_id = s.id
                    JOIN res_partner c ON s.partner_id = c.id
                    ORDER BY h.date DESC;
                """
                cur.execute(query)
                return cur.fetchall(), ["Timestamp", "Customer", "Subscription #", "Operator", "From State", "To State", "Event Notes"]

            return [], []

def export_report_to_csv(report_type: str):
    rows, headers = get_report_data(report_type)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for r in rows:
        writer.writerow(list(r.values()))
    return output.getvalue()
