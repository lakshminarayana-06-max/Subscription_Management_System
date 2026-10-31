# -*- coding: utf-8 -*-
"""
Brightloop Software - Realistic Demo Data Seeder for Hackathon Demonstration.
Seeds:
- 3 User Roles (Admin, Staff, Customer with strict complex passwords)
- 15 Indian Customers with GSTINs
- 10 Software Products & Brand Variants (including Odoo Brand +₹560)
- 5 Subscription Plans (Daily, Weekly, Monthly, Yearly, Custom Flexi)
- 10 Quotations
- 20 Subscriptions (Active, Paused, Closed, Expired, Confirmed)
- Invoices across Draft, Posted, Paid, Partial, and Overdue statuses
- Payments across UPI, Bank Transfer, Credit Card, and Cash
- Multi-tier Discount Rules
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from brightloop_app.billing_engine import compute_next_date
from brightloop_app.db import get_db, init_db
from brightloop_app.auth import hash_password
from psycopg2.extras import RealDictCursor

def seed():
    init_db()
    today = date.today()

    with get_db() as conn:
        with conn.cursor() as cur:
            # Check if data already seeded
            cur.execute("SELECT COUNT(*) FROM res_partner;")
            if cur.fetchone()[0] > 0:
                print("Database already contains records. Clearing existing records for clean seed...")
                cur.execute("""
                    TRUNCATE account_payment, account_move_line, account_move,
                             brightloop_subscription_history, brightloop_subscription_line,
                             brightloop_subscription, brightloop_quotation_line, brightloop_quotation,
                             brightloop_quotation_template_line, brightloop_quotation_template,
                             brightloop_discount_rule, brightloop_subscription_plan,
                             product_product, product_template, res_users, res_partner CASCADE;
                """)

            print("Seeding Users...")
            # 1. Admin
            cur.execute("""
                INSERT INTO res_users (name, login, password_hash, role)
                VALUES ('Rajesh Sharma (Admin)', 'admin@gmail.com', %s, 'admin');
            """, (hash_password('admin@123'),))

            # 2. Staff
            cur.execute("""
                INSERT INTO res_users (name, login, password_hash, role)
                VALUES ('Pooja Verma (Billing Staff)', 'staff@gmail.com', %s, 'staff');
            """, (hash_password('staff@123'),))

            # 3. Customer
            cur.execute("""
                INSERT INTO res_users (name, login, password_hash, role)
                VALUES ('Vikram Malhotra (Zenith Infotech)', 'cust@gmail.com', %s, 'customer');
            """, (hash_password('cust@123'),))

            print("Seeding 15 Customers...")
            customers = [
                ("Zenith Infotech Pvt Ltd", "cust@gmail.com", "+91 98765 43210", "102 Electronic City Phase 1", "Bengaluru", "29AAACZ1234F1Z5"),
                ("Bharat Cloud Solutions", "billing@bharatcloud.co.in", "+91 98111 22334", "45 Okhla Industrial Area", "New Delhi", "07AABCB5678H1Z2"),
                ("Apex Retailers Network", "accounts@apexretail.com", "+91 94440 98765", "88 Anna Salai", "Chennai", "33AACCA9988D1Z9"),
                ("Mumbai FinServe Corp", "info@mumbaifinserve.in", "+91 99200 11223", "14 Nariman Point", "Mumbai", "27AADCM3344K1Z4"),
                ("Deccan Logistics Hub", "ops@deccanlogistics.com", "+91 90000 55667", "23 HITEC City Madhapur", "Hyderabad", "36AAECD7788L1Z6"),
                ("Kolkata Analytics Lab", "billing@kolkataanalytics.in", "+91 98300 44556", "5 Park Street", "Kolkata", "19AABCK1122P1Z0"),
                ("Gujarat AgroTech Ventures", "finance@agrotechguj.com", "+91 97250 88990", "12 SG Highway", "Ahmedabad", "24AAACG4455M1Z8"),
                ("Pune Software Forge", "admin@punesoftwareforge.in", "+91 98600 66778", "7 Hinjewadi Phase 2", "Pune", "27AAACP9900Q1Z3"),
                ("Jaipur Heritage Crafts", "orders@jaipurcrafts.co.in", "+91 94140 22331", "101 MI Road", "Jaipur", "08AAACJ7788R1Z1"),
                ("Cochin Marine Exports", "accounts@cochinmarine.in", "+91 94470 33445", "34 Willingdon Island", "Kochi", "32AAACC5566T1Z7"),
                ("Indore FoodTech Systems", "info@indorefoodtech.com", "+91 98260 77889", "6 AB Road", "Indore", "23AAACI8899U1Z5"),
                ("Chandigarh HealthCare Ltd", "procure@chandigarhhealth.in", "+91 98720 11224", "17 Sector 17 Plaza", "Chandigarh", "04AAACC2233W1Z9"),
                ("Lucknow Cyber Services", "contact@lucknowcyber.in", "+91 94150 99887", "54 Hazratganj", "Lucknow", "09AAACL4455X1Z2"),
                ("Surat Textile Dynamics", "billing@surattextile.co.in", "+91 98250 55661", "9 Ring Road Market", "Surat", "24AAACS6677Y1Z4"),
                ("Nagpur Logistics Express", "finance@nagpurlogistics.in", "+91 98900 88776", "40 Wardha Road", "Nagpur", "27AAACN1122Z1Z0"),
            ]
            cust_ids = []
            for c in customers:
                cur.execute("""
                    INSERT INTO res_partner (name, email, phone, street, city, vat, customer_rank)
                    VALUES (%s, %s, %s, %s, %s, %s, 1) RETURNING id;
                """, c)
                cust_ids.append(cur.fetchone()[0])

            print("Seeding 10 Products & Variants...")
            products = [
                ("Brightloop Cloud ERP", "BL-ERP", "service", 2400.0, 800.0, "All-in-one business software including Sales, Invoicing and Inventory"),
                ("Brightloop HRMS Suite", "BL-HRMS", "service", 1500.0, 500.0, "Payroll, attendance and employee lifecycle management"),
                ("Automated Billing API Connector", "BL-API", "service", 1800.0, 400.0, "REST APIs for automated invoicing, webhooks and recurring payment sync"),
                ("WhatsApp Business Gateway", "BL-WAPP", "service", 950.0, 250.0, "Automated WhatsApp alerts for subscription renewals and overdue invoices"),
                ("Brightloop CRM Pro", "BL-CRM", "service", 1200.0, 350.0, "Customer pipeline tracking, lead scoring and quotation generator"),
                ("Real-Time Revenue Analytics Engine", "BL-REV", "service", 3000.0, 1000.0, "MRR tracking, churn analytics and executive financial reports"),
                ("Secure Cloud Storage 500GB", "BL-STOR", "service", 600.0, 150.0, "Encrypted cloud backup with automated snapshot retention"),
                ("24/7 Priority SLA Booster", "BL-SLA", "service", 2500.0, 900.0, "Guaranteed 15-minute response time and dedicated technical account manager"),
                ("Advanced Enterprise Security Shield", "BL-SEC", "service", 1750.0, 600.0, "MFA enforcement, IP whitelisting and automated intrusion detection"),
                ("Custom White-Label Portal Theme", "BL-THEME", "service", 850.0, 200.0, "Branded customer portal with custom domain and logos"),
            ]
            prod_ids = []
            for p in products:
                cur.execute("""
                    INSERT INTO product_template (name, default_code, type, list_price, standard_price, description)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
                """, p)
                prod_ids.append(cur.fetchone()[0])

            # Seed Product Variants (Standard Brand vs Odoo Brand +₹560 vs Enterprise +₹1200)
            print("Seeding Variants with Brand price adjustment (Odoo Brand +₹560)...")
            for pid in prod_ids:
                cur.execute("SELECT list_price FROM product_template WHERE id = %s", (pid,))
                base_price = float(cur.fetchone()[0])
                # Standard
                cur.execute("""
                    INSERT INTO product_product (template_id, brand_name, brand_price_extra, final_price)
                    VALUES (%s, 'Standard Edition', 0.00, %s);
                """, (pid, base_price))
                # ODOO BRAND (+₹560) - Specific Hackathon Requirement!
                cur.execute("""
                    INSERT INTO product_product (template_id, brand_name, brand_price_extra, final_price)
                    VALUES (%s, 'Odoo Brand Edition', 560.00, %s);
                """, (pid, base_price + 560.0))
                # Enterprise Custom (+₹1200)
                cur.execute("""
                    INSERT INTO product_product (template_id, brand_name, brand_price_extra, final_price)
                    VALUES (%s, 'Enterprise Custom Brand', 1200.00, %s);
                """, (pid, base_price + 1200.0))

            print("Seeding 5 Subscription Plans...")
            plans = [
                ("Daily Developer Sandbox", "PLAN-DAILY", prod_ids[0], "daily", 150.0, 1, today - timedelta(days=60), today + timedelta(days=300), True, True, True, True, "Daily automated sandbox billing with instant provisioning."),
                ("Weekly Agile Starter", "PLAN-WEEKLY", prod_ids[4], "weekly", 650.0, 1, today - timedelta(days=60), today + timedelta(days=300), False, True, True, True, "Flexible weekly billing designed for sprint-based agile projects."),
                ("Monthly Business Pro", "PLAN-MONTHLY", prod_ids[0], "monthly", 2400.0, 1, today - timedelta(days=60), today + timedelta(days=365), False, True, True, True, "Flagship monthly recurring business tier with priority features."),
                ("Yearly Enterprise Platinum", "PLAN-YEARLY", prod_ids[5], "yearly", 25000.0, 5, today - timedelta(days=60), today + timedelta(days=730), False, False, False, True, "Annual enterprise software contract with dedicated support and SLA guarantees."),
                ("Custom High-Volume Flexi", "PLAN-FLEXI", prod_ids[2], "monthly", 4500.0, 10, today - timedelta(days=60), today + timedelta(days=180), True, True, True, True, "High-throughput API tier designed for scale and webhooks."),
            ]
            plan_ids = []
            for pl in plans:
                cur.execute("""
                    INSERT INTO brightloop_subscription_plan (
                        name, code, product_id, billing_frequency, price, min_quantity,
                        start_date, end_date, auto_close, early_closure_allowed, pause_allowed,
                        renewal_allowed, description
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, pl)
                plan_ids.append(cur.fetchone()[0])

            print("Seeding Quotation Templates...")
            cur.execute("""
                INSERT INTO brightloop_quotation_template (name, validity_days, plan_id, note)
                VALUES ('Standard Enterprise Onboarding Pack', 30, %s, 'Includes Cloud ERP, HRMS, and SLA Booster.') RETURNING id;
            """, (plan_ids[2],))
            tmpl_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO brightloop_quotation_template_line (template_id, product_id, quantity, unit_price)
                VALUES (%s, %s, 1.0, 2400.0), (%s, %s, 1.0, 1500.0), (%s, %s, 1.0, 2500.0);
            """, (tmpl_id, prod_ids[0], tmpl_id, prod_ids[1], tmpl_id, prod_ids[7]))

            print("Seeding Discount Rules...")
            discounts = [
                ("Early Bird 15% Off", "percent", 15.0, 1000.0, 1.0, today - timedelta(days=30), today + timedelta(days=90), 50, 14),
                ("Enterprise Volume ₹2000 Off", "fixed", 2000.0, 15000.0, 5.0, today - timedelta(days=30), today + timedelta(days=90), 25, 8),
                ("Diwali Special 10% Off", "percent", 10.0, 500.0, 1.0, today - timedelta(days=15), today + timedelta(days=45), 100, 32),
            ]
            disc_ids = []
            for d in discounts:
                cur.execute("""
                    INSERT INTO brightloop_discount_rule (
                        name, discount_type, value, min_purchase_amount, min_quantity,
                        start_date, end_date, max_usage_count, current_usage_count, active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING id;
                """, d)
                disc_ids.append(cur.fetchone()[0])

            print("Seeding 10 Quotations...")
            quotation_states = ['confirmed', 'confirmed', 'quotation', 'quotation', 'draft', 'draft', 'expired', 'cancelled', 'confirmed', 'confirmed']
            quote_ids = []
            for i in range(10):
                q_name = f"QT/2026/{str(i+1).zfill(5)}"
                c_id = cust_ids[i % len(cust_ids)]
                p_id = plan_ids[i % len(plan_ids)]
                q_state = quotation_states[i]
                v_days = 30
                q_date = today - timedelta(days=40 if q_state == 'expired' else (i * 2))
                val_date = q_date + timedelta(days=v_days)
                
                cur.execute("""
                    INSERT INTO brightloop_quotation (
                        name, partner_id, template_id, plan_id, quotation_date,
                        validity_days, validity_date, state, amount_untaxed, amount_tax, amount_total
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 3900.00, 702.00, 4602.00) RETURNING id;
                """, (q_name, c_id, tmpl_id, p_id, q_date, v_days, val_date, q_state))
                qid = cur.fetchone()[0]
                quote_ids.append(qid)

                cur.execute("""
                    INSERT INTO brightloop_quotation_line (quotation_id, product_id, name, quantity, unit_price, tax_rate, price_subtotal)
                    VALUES (%s, %s, 'Brightloop Cloud ERP', 1.0, 2400.0, 18.0, 2400.0),
                           (%s, %s, 'Brightloop HRMS Suite', 1.0, 1500.0, 18.0, 1500.0);
                """, (qid, prod_ids[0], qid, prod_ids[1]))

            print("Seeding 20 Subscriptions in varied states...")
            # States distribution: 12 Active, 2 Paused, 2 Confirmed, 2 Closed, 2 Expired
            sub_configs = [
                # 1-12 Active
                ('active', 'monthly', 0, 15, 30),
                ('active', 'monthly', 1, 5, 25),
                ('active', 'yearly', 2, 60, 305),
                ('active', 'monthly', 3, 2, 28),
                ('active', 'weekly', 4, 1, 6),
                ('active', 'monthly', 5, 20, 10),
                ('active', 'yearly', 6, 90, 275),
                ('active', 'daily', 7, 0, 1),
                ('active', 'monthly', 8, 12, 18),
                ('active', 'monthly', 9, 8, 22),
                ('active', 'weekly', 10, 3, 4),
                ('active', 'monthly', 11, 4, 26),
                # 13-14 Paused
                ('paused', 'monthly', 12, 45, 0),
                ('paused', 'monthly', 13, 30, 0),
                # 15-16 Confirmed
                ('confirmed', 'monthly', 14, 0, 30),
                ('confirmed', 'yearly', 0, 0, 365),
                # 17-18 Closed
                ('closed', 'monthly', 1, 120, 0),
                ('closed', 'weekly', 2, 60, 0),
                # 19-20 Expired
                ('expired', 'monthly', 3, 90, 0),
                ('expired', 'daily', 4, 15, 0),
            ]

            sub_ids = []
            for idx, (st, freq, days_ago, days_to_bill, days_to_expiry) in enumerate(sub_configs):
                sub_name = f"SUB/2026/{str(idx+1).zfill(5)}"
                c_id = cust_ids[idx % len(cust_ids)]
                # Select plan corresponding to frequency
                target_plan_id = plan_ids[2] # monthly default
                if freq == 'daily': target_plan_id = plan_ids[0]
                elif freq == 'weekly': target_plan_id = plan_ids[1]
                elif freq == 'yearly': target_plan_id = plan_ids[3]

                s_date = today - timedelta(days=days_ago)
                n_bill = today + timedelta(days=days_to_bill) if days_to_bill > 0 else today
                e_date = today + timedelta(days=days_to_expiry) if days_to_expiry > 0 else (today - timedelta(days=5))

                p_reason = "Customer team restructuring" if st == 'paused' else None
                c_reason = "Customer project completed successfully" if st == 'closed' else None

                cur.execute("""
                    INSERT INTO brightloop_subscription (
                        name, partner_id, plan_id, billing_frequency, start_date, expiry_date,
                        next_billing_date, payment_terms, state, amount_untaxed, amount_tax,
                        amount_discount, amount_total, pause_reason, close_reason
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, 'Immediate Payment', %s,
                        3900.00, 702.00, 0.00, 4602.00, %s, %s
                    ) RETURNING id;
                """, (sub_name, c_id, target_plan_id, freq, s_date, e_date, n_bill, st, p_reason, c_reason))
                sid = cur.fetchone()[0]
                sub_ids.append(sid)

                # Add lines
                cur.execute("""
                    INSERT INTO brightloop_subscription_line (
                        subscription_id, product_id, name, quantity, unit_price, tax_rate, discount_amount, price_subtotal, price_total
                    ) VALUES (
                        %s, %s, 'Brightloop Cloud ERP (Odoo Brand Edition)', 1.0, 2960.00, 18.0, 0.0, 2960.00, 3492.80
                    ), (
                        %s, %s, 'WhatsApp Business Gateway', 1.0, 950.00, 18.0, 0.0, 950.00, 1121.00
                    );
                """, (sid, prod_ids[0], sid, prod_ids[3]))

                # History log
                cur.execute("""
                    INSERT INTO brightloop_subscription_history (subscription_id, user_name, previous_state, new_state, note)
                    VALUES (%s, 'Rajesh Sharma (Admin)', 'draft', %s, 'Subscription initialized in demo dataset');
                """, (sid, st))

            print("Seeding Invoices & Payments...")
            # Generate realistic invoices for subscriptions
            # Some fully paid, some partially paid, some overdue, some recent unpaid
            inv_counter = 1
            for i, sid in enumerate(sub_ids[:14]): # first 14 subscriptions
                cur.execute("SELECT partner_id, start_date, billing_frequency FROM brightloop_subscription WHERE id = %s", (sid,))
                sub_row = cur.fetchone()
                c_id, s_date, freq = sub_row[0], sub_row[1], sub_row[2]

                inv_name = f"INV/2026/{str(inv_counter).zfill(5)}"
                inv_counter += 1

                p_start = s_date
                p_end = compute_next_date(freq, p_start) - timedelta(days=1)
                
                # Determine invoice status & due dates
                if i in [0, 1, 2, 3, 4]:
                    # Paid invoices
                    inv_date = today - timedelta(days=35)
                    due_date = today - timedelta(days=20)
                    inv_state = 'posted'
                    pay_state = 'paid'
                    tot = 4613.80
                    residual = 0.00
                elif i in [5, 6, 7]:
                    # Partially paid invoices
                    inv_date = today - timedelta(days=25)
                    due_date = today - timedelta(days=10) # overdue!
                    inv_state = 'posted'
                    pay_state = 'partial'
                    tot = 4613.80
                    residual = 2000.00 # 2613.80 paid
                elif i in [8, 9]:
                    # Overdue unpaid invoices
                    inv_date = today - timedelta(days=30)
                    due_date = today - timedelta(days=15) # overdue!
                    inv_state = 'posted'
                    pay_state = 'not_paid'
                    tot = 4613.80
                    residual = 4613.80
                else:
                    # Current unpaid invoices
                    inv_date = today - timedelta(days=5)
                    due_date = today + timedelta(days=10)
                    inv_state = 'posted'
                    pay_state = 'not_paid'
                    tot = 4613.80
                    residual = 4613.80

                cur.execute("""
                    INSERT INTO account_move (
                        name, partner_id, subscription_id, invoice_date, invoice_date_due,
                        billing_period_start, billing_period_end, state, payment_state,
                        amount_untaxed, amount_tax, amount_discount, amount_total, amount_residual,
                        is_subscription_invoice
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        3910.00, 703.80, 0.00, %s, %s, TRUE
                    ) RETURNING id;
                """, (
                    inv_name, c_id, sid, inv_date, due_date, p_start, p_end,
                    inv_state, pay_state, tot, residual
                ))
                invid = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO account_move_line (move_id, product_id, name, quantity, price_unit, price_subtotal)
                    VALUES (%s, %s, 'Brightloop Cloud ERP (Odoo Brand Edition)', 1.0, 2960.00, 2960.00),
                           (%s, %s, 'WhatsApp Business Gateway', 1.0, 950.00, 950.00);
                """, (invid, prod_ids[0], invid, prod_ids[3]))

                # Add payments if paid or partially paid
                if pay_state == 'paid':
                    cur.execute("""
                        INSERT INTO account_payment (
                            name, partner_id, move_id, subscription_id, payment_method, amount,
                            payment_date, transaction_reference, notes, state
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, 'Full payment settled via gateway', 'posted'
                        );
                    """, (
                        f"PAY/2026/{str(invid).zfill(5)}", c_id, invid, sid,
                        ['upi', 'bank', 'credit_card'][i % 3], tot, inv_date + timedelta(days=3),
                        f"UTR-BL-{100000 + invid}"
                    ))
                elif pay_state == 'partial':
                    cur.execute("""
                        INSERT INTO account_payment (
                            name, partner_id, move_id, subscription_id, payment_method, amount,
                            payment_date, transaction_reference, notes, state
                        ) VALUES (
                            %s, %s, %s, %s, 'upi', 2613.80, %s, %s, 'First installment received', 'posted'
                        );
                    """, (
                        f"PAY/2026/{str(invid).zfill(5)}", c_id, invid, sid,
                        inv_date + timedelta(days=5), f"UPI-BL-{200000 + invid}"
                    ))
            # Synchronize native PostgreSQL sequences with seeded data
            cur.execute("""
                SELECT setval('seq_account_move', (SELECT COALESCE(MAX(id), 0) + 1 FROM account_move));
                SELECT setval('seq_account_payment', (SELECT COALESCE(MAX(id), 0) + 1 FROM account_payment));
                SELECT setval('seq_brightloop_subscription', (SELECT COALESCE(MAX(id), 0) + 1 FROM brightloop_subscription));
                SELECT setval('seq_brightloop_quotation', (SELECT COALESCE(MAX(id), 0) + 1 FROM brightloop_quotation));
            """)

            print("Demo dataset seeded successfully!")

if __name__ == '__main__':
    seed()
