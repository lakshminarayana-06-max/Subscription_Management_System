# -*- coding: utf-8 -*-
"""
Database Management & PostgreSQL Connection Pool for Brightloop Software.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging

_logger = logging.getLogger("brightloop.db")

DB_CONFIG = {
    'dbname': 'brightloop_db',
    'user': 'postgres',
    'password': '1234',
    'host': 'localhost',
    'port': 5432
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initializes tables, constraints, foreign keys, and indexes."""
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Users Table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS res_users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                login VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'customer',
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 2. Partners / Customers Table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS res_partner (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                email VARCHAR(100) UNIQUE,
                phone VARCHAR(30),
                street VARCHAR(255),
                city VARCHAR(100),
                vat VARCHAR(50),
                customer_rank INT DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 3. Product Template
            cur.execute("""
            CREATE TABLE IF NOT EXISTS product_template (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                default_code VARCHAR(50),
                type VARCHAR(20) DEFAULT 'service',
                list_price NUMERIC(12,2) DEFAULT 0.00,
                standard_price NUMERIC(12,2) DEFAULT 0.00,
                description TEXT,
                is_subscription_product BOOLEAN DEFAULT TRUE,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 4. Product Variants (Brand Edition adjustments)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS product_product (
                id SERIAL PRIMARY KEY,
                template_id INT REFERENCES product_template(id) ON DELETE CASCADE,
                brand_name VARCHAR(100) NOT NULL,
                brand_price_extra NUMERIC(12,2) DEFAULT 0.00,
                final_price NUMERIC(12,2) DEFAULT 0.00,
                active BOOLEAN DEFAULT TRUE
            );
            """)

            # 5. Subscription Plan
            cur.execute("""
            CREATE TABLE IF NOT EXISTS brightloop_subscription_plan (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) UNIQUE NOT NULL,
                code VARCHAR(50),
                product_id INT REFERENCES product_template(id),
                billing_frequency VARCHAR(20) NOT NULL,
                price NUMERIC(12,2) NOT NULL,
                min_quantity INT DEFAULT 1,
                start_date DATE,
                end_date DATE,
                auto_close BOOLEAN DEFAULT TRUE,
                early_closure_allowed BOOLEAN DEFAULT TRUE,
                pause_allowed BOOLEAN DEFAULT TRUE,
                renewal_allowed BOOLEAN DEFAULT TRUE,
                description TEXT,
                active BOOLEAN DEFAULT TRUE
            );
            """)

            # 6. Quotation Template
            cur.execute("""
            CREATE TABLE IF NOT EXISTS brightloop_quotation_template (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                validity_days INT DEFAULT 30,
                plan_id INT REFERENCES brightloop_subscription_plan(id),
                note TEXT,
                active BOOLEAN DEFAULT TRUE
            );
            """)

            # 7. Quotation Template Line
            cur.execute("""
            CREATE TABLE IF NOT EXISTS brightloop_quotation_template_line (
                id SERIAL PRIMARY KEY,
                template_id INT REFERENCES brightloop_quotation_template(id) ON DELETE CASCADE,
                product_id INT REFERENCES product_template(id),
                quantity NUMERIC(10,2) DEFAULT 1.00,
                unit_price NUMERIC(12,2) DEFAULT 0.00
            );
            """)

            # 8. Discount Rules
            cur.execute("""
            CREATE TABLE IF NOT EXISTS brightloop_discount_rule (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                discount_type VARCHAR(20) NOT NULL, -- 'percent' or 'fixed'
                value NUMERIC(10,2) NOT NULL,
                min_purchase_amount NUMERIC(12,2) DEFAULT 0.00,
                min_quantity NUMERIC(10,2) DEFAULT 1.00,
                start_date DATE,
                end_date DATE,
                max_usage_count INT DEFAULT 100,
                current_usage_count INT DEFAULT 0,
                applicable_products TEXT,
                active BOOLEAN DEFAULT TRUE
            );
            """)

            # 9. Subscriptions
            cur.execute("""
            CREATE TABLE IF NOT EXISTS brightloop_subscription (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                partner_id INT REFERENCES res_partner(id),
                plan_id INT REFERENCES brightloop_subscription_plan(id),
                billing_frequency VARCHAR(20) NOT NULL,
                start_date DATE NOT NULL,
                expiry_date DATE,
                next_billing_date DATE NOT NULL,
                payment_terms VARCHAR(100) DEFAULT 'Immediate Payment',
                state VARCHAR(20) DEFAULT 'draft',
                amount_untaxed NUMERIC(12,2) DEFAULT 0.00,
                amount_tax NUMERIC(12,2) DEFAULT 0.00,
                amount_discount NUMERIC(12,2) DEFAULT 0.00,
                amount_total NUMERIC(12,2) DEFAULT 0.00,
                pause_reason TEXT,
                close_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 10. Subscription Lines
            cur.execute("""
            CREATE TABLE IF NOT EXISTS brightloop_subscription_line (
                id SERIAL PRIMARY KEY,
                subscription_id INT REFERENCES brightloop_subscription(id) ON DELETE CASCADE,
                product_id INT REFERENCES product_template(id),
                name VARCHAR(255) NOT NULL,
                quantity NUMERIC(10,2) DEFAULT 1.00,
                unit_price NUMERIC(12,2) DEFAULT 0.00,
                tax_rate NUMERIC(5,2) DEFAULT 18.00,
                discount_amount NUMERIC(12,2) DEFAULT 0.00,
                price_subtotal NUMERIC(12,2) DEFAULT 0.00,
                price_total NUMERIC(12,2) DEFAULT 0.00
            );
            """)

            # 11. Subscription History (Audit Trail)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS brightloop_subscription_history (
                id SERIAL PRIMARY KEY,
                subscription_id INT REFERENCES brightloop_subscription(id) ON DELETE CASCADE,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_name VARCHAR(100),
                previous_state VARCHAR(20),
                new_state VARCHAR(20) NOT NULL,
                note TEXT
            );
            """)

            # 12. Quotations
            cur.execute("""
            CREATE TABLE IF NOT EXISTS brightloop_quotation (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                partner_id INT REFERENCES res_partner(id),
                template_id INT REFERENCES brightloop_quotation_template(id),
                plan_id INT REFERENCES brightloop_subscription_plan(id),
                quotation_date DATE DEFAULT CURRENT_DATE,
                validity_days INT DEFAULT 30,
                validity_date DATE,
                state VARCHAR(20) DEFAULT 'draft',
                amount_untaxed NUMERIC(12,2) DEFAULT 0.00,
                amount_tax NUMERIC(12,2) DEFAULT 0.00,
                amount_total NUMERIC(12,2) DEFAULT 0.00,
                subscription_id INT REFERENCES brightloop_subscription(id)
            );
            """)

            # 13. Quotation Lines
            cur.execute("""
            CREATE TABLE IF NOT EXISTS brightloop_quotation_line (
                id SERIAL PRIMARY KEY,
                quotation_id INT REFERENCES brightloop_quotation(id) ON DELETE CASCADE,
                product_id INT REFERENCES product_template(id),
                name VARCHAR(255) NOT NULL,
                quantity NUMERIC(10,2) DEFAULT 1.00,
                unit_price NUMERIC(12,2) DEFAULT 0.00,
                tax_rate NUMERIC(5,2) DEFAULT 18.00,
                price_subtotal NUMERIC(12,2) DEFAULT 0.00
            );
            """)

            # 14. Invoices (Account Move)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS account_move (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                partner_id INT REFERENCES res_partner(id),
                subscription_id INT REFERENCES brightloop_subscription(id),
                invoice_date DATE DEFAULT CURRENT_DATE,
                invoice_date_due DATE,
                billing_period_start DATE,
                billing_period_end DATE,
                state VARCHAR(20) DEFAULT 'draft', -- 'draft', 'posted', 'cancel'
                payment_state VARCHAR(20) DEFAULT 'not_paid', -- 'not_paid', 'partial', 'paid'
                amount_untaxed NUMERIC(12,2) DEFAULT 0.00,
                amount_tax NUMERIC(12,2) DEFAULT 0.00,
                amount_discount NUMERIC(12,2) DEFAULT 0.00,
                amount_total NUMERIC(12,2) DEFAULT 0.00,
                amount_residual NUMERIC(12,2) DEFAULT 0.00,
                is_subscription_invoice BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 15. Invoice Lines
            cur.execute("""
            CREATE TABLE IF NOT EXISTS account_move_line (
                id SERIAL PRIMARY KEY,
                move_id INT REFERENCES account_move(id) ON DELETE CASCADE,
                product_id INT REFERENCES product_template(id),
                name VARCHAR(255) NOT NULL,
                quantity NUMERIC(10,2) DEFAULT 1.00,
                price_unit NUMERIC(12,2) DEFAULT 0.00,
                discount_percent NUMERIC(5,2) DEFAULT 0.00,
                price_subtotal NUMERIC(12,2) DEFAULT 0.00
            );
            """)

            # 16. Payments
            cur.execute("""
            CREATE TABLE IF NOT EXISTS account_payment (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                partner_id INT REFERENCES res_partner(id),
                move_id INT REFERENCES account_move(id),
                subscription_id INT REFERENCES brightloop_subscription(id),
                payment_method VARCHAR(20) DEFAULT 'upi', -- 'cash', 'bank', 'credit_card', 'upi', 'other'
                amount NUMERIC(12,2) NOT NULL,
                payment_date DATE DEFAULT CURRENT_DATE,
                transaction_reference VARCHAR(100),
                notes TEXT,
                state VARCHAR(20) DEFAULT 'posted',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 17. High Performance Database Indexes (< 2.0s response time requirement)
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sub_partner ON brightloop_subscription(partner_id);
            CREATE INDEX IF NOT EXISTS idx_sub_plan ON brightloop_subscription(plan_id);
            CREATE INDEX IF NOT EXISTS idx_sub_state ON brightloop_subscription(state);
            CREATE INDEX IF NOT EXISTS idx_sub_next_billing ON brightloop_subscription(next_billing_date);
            CREATE INDEX IF NOT EXISTS idx_sub_expiry ON brightloop_subscription(expiry_date);
            
            CREATE INDEX IF NOT EXISTS idx_move_partner ON account_move(partner_id);
            CREATE INDEX IF NOT EXISTS idx_move_sub ON account_move(subscription_id);
            CREATE INDEX IF NOT EXISTS idx_move_state ON account_move(state);
            CREATE INDEX IF NOT EXISTS idx_pay_move ON account_payment(move_id);
            CREATE INDEX IF NOT EXISTS idx_pay_date ON account_payment(payment_date);

            CREATE SEQUENCE IF NOT EXISTS seq_brightloop_subscription START 1;
            CREATE SEQUENCE IF NOT EXISTS seq_brightloop_quotation START 1;
            CREATE SEQUENCE IF NOT EXISTS seq_account_move START 1;
            CREATE SEQUENCE IF NOT EXISTS seq_account_payment START 1;
            """)
    print("PostgreSQL brightloop_db schema & indexes initialized successfully!")

if __name__ == '__main__':
    init_db()
