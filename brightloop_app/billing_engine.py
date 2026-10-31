# -*- coding: utf-8 -*-
"""
Brightloop Recurring Billing & Financial Automation Engine.
"""
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from brightloop_app.db import get_db
from psycopg2.extras import RealDictCursor
import logging

_logger = logging.getLogger("brightloop.billing")

def compute_next_date(frequency: str, from_date: date) -> date:
    if frequency == 'daily':
        return from_date + timedelta(days=1)
    elif frequency == 'weekly':
        return from_date + timedelta(weeks=1)
    elif frequency == 'monthly':
        return from_date + relativedelta(months=1)
    elif frequency == 'yearly':
        return from_date + relativedelta(years=1)
    return from_date + relativedelta(months=1)

def get_next_sequence(table_name: str, prefix: str, cur=None) -> str:
    year = date.today().year
    seq_name = f"seq_{table_name}"
    
    if cur:
        try:
            cur.execute(f"SELECT nextval('{seq_name}');")
            row = cur.fetchone()
            val = row[0] if isinstance(row, (tuple, list)) else (row.get('nextval') if isinstance(row, dict) else list(row.values())[0])
            return f"{prefix}/{year}/{str(val).zfill(5)}"
        except Exception:
            pass

    with get_db() as conn:
        with conn.cursor() as c:
            try:
                c.execute(f"SELECT nextval('{seq_name}');")
                val = c.fetchone()[0]
                return f"{prefix}/{year}/{str(val).zfill(5)}"
            except Exception:
                c.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table_name};")
                max_id = c.fetchone()[0]
                num = max_id + 1
                while True:
                    cand = f"{prefix}/{year}/{str(num).zfill(5)}"
                    c.execute(f"SELECT 1 FROM {table_name} WHERE name = %s;", (cand,))
                    if not c.fetchone():
                        return cand
                    num += 1

def run_recurring_billing_cron():
    """
    Core automated recurring billing job.
    Scans all active subscriptions due for billing, creates invoices,
    advances next billing dates, and prevents duplicate billing.
    """
    today = date.today()
    results = {
        'processed': 0,
        'invoices_created': 0,
        'skipped_duplicates': 0,
        'errors': []
    }

    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Fetch active subscriptions due for billing
            cur.execute("""
                SELECT s.*, p.name as plan_name, p.auto_close as plan_auto_close, p.end_date as plan_end_date
                FROM brightloop_subscription s
                JOIN brightloop_subscription_plan p ON s.plan_id = p.id
                WHERE s.state = 'active' AND s.next_billing_date <= %s
                ORDER BY s.id ASC;
            """, (today,))
            due_subs = cur.fetchall()
            results['processed'] = len(due_subs)

            for sub in due_subs:
                sub_id = sub['id']
                period_start = sub['next_billing_date']
                period_end = compute_next_date(sub['billing_frequency'], period_start) - timedelta(days=1)

                # Check for duplicate billing
                cur.execute("""
                    SELECT id, name FROM account_move
                    WHERE subscription_id = %s AND billing_period_start = %s AND state != 'cancel';
                """, (sub_id, period_start))
                existing = cur.fetchone()
                if existing:
                    results['skipped_duplicates'] += 1
                    continue

                cur.execute("SAVEPOINT sub_bill_sp;")
                try:
                    # Fetch subscription lines
                    cur.execute("""
                        SELECT * FROM brightloop_subscription_line WHERE subscription_id = %s;
                    """, (sub_id,))
                    lines = cur.fetchall()

                    inv_name = get_next_sequence('account_move', 'INV', cur=cur)
                    due_date = period_start + timedelta(days=15)
                    
                    untaxed_total = 0.0
                    tax_total = 0.0
                    discount_total = 0.0

                    # Process lines and discounts
                    prepared_lines = []
                    for line in lines:
                        qty = float(line['quantity'])
                        unit_price = float(line['unit_price'])
                        line_base = qty * unit_price
                        
                        # Check discount rules
                        cur.execute("""
                            SELECT * FROM brightloop_discount_rule
                            WHERE active = TRUE
                              AND (start_date IS NULL OR start_date <= %s)
                              AND (end_date IS NULL OR end_date >= %s)
                              AND current_usage_count < max_usage_count
                              AND min_purchase_amount <= %s
                              AND min_quantity <= %s
                            ORDER BY value DESC LIMIT 1;
                        """, (today, today, line_base, qty))
                        discount_rule = cur.fetchone()
                        
                        line_discount = 0.0
                        disc_pct = 0.0
                        if discount_rule:
                            if discount_rule['discount_type'] == 'percent':
                                disc_pct = float(discount_rule['value'])
                                line_discount = (line_base * disc_pct) / 100.0
                            else:
                                line_discount = min(float(discount_rule['value']), line_base)
                                disc_pct = (line_discount / line_base * 100.0) if line_base else 0.0
                            
                            # Increment discount usage
                            cur.execute("""
                                UPDATE brightloop_discount_rule
                                SET current_usage_count = current_usage_count + 1,
                                    active = CASE WHEN current_usage_count + 1 >= max_usage_count THEN FALSE ELSE active END
                                WHERE id = %s;
                            """, (discount_rule['id'],))

                        subtotal = line_base - line_discount
                        line_tax = subtotal * (float(line['tax_rate']) / 100.0)
                        
                        untaxed_total += subtotal
                        tax_total += line_tax
                        discount_total += line_discount

                        prepared_lines.append({
                            'product_id': line['product_id'],
                            'name': f"{line['name']} ({period_start} to {period_end})",
                            'quantity': qty,
                            'price_unit': unit_price,
                            'discount_percent': disc_pct,
                            'price_subtotal': subtotal
                        })

                    inv_total = untaxed_total + tax_total

                    # Insert account_move
                    cur.execute("""
                        INSERT INTO account_move (
                            name, partner_id, subscription_id, invoice_date, invoice_date_due,
                            billing_period_start, billing_period_end, state, payment_state,
                            amount_untaxed, amount_tax, amount_discount, amount_total, amount_residual,
                            is_subscription_invoice
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, 'posted', 'not_paid',
                            %s, %s, %s, %s, %s, TRUE
                        ) RETURNING id;
                    """, (
                        inv_name, sub['partner_id'], sub_id, today, due_date,
                        period_start, period_end, untaxed_total, tax_total, discount_total,
                        inv_total, inv_total
                    ))
                    inv_id = cur.fetchone()['id']

                    # Insert lines
                    for pline in prepared_lines:
                        cur.execute("""
                            INSERT INTO account_move_line (
                                move_id, product_id, name, quantity, price_unit, discount_percent, price_subtotal
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                        """, (
                            inv_id, pline['product_id'], pline['name'], pline['quantity'],
                            pline['price_unit'], pline['discount_percent'], pline['price_subtotal']
                        ))

                    # Advance next billing date
                    new_next_billing = compute_next_date(sub['billing_frequency'], period_start)
                    cur.execute("""
                        UPDATE brightloop_subscription
                        SET next_billing_date = %s
                        WHERE id = %s;
                    """, (new_next_billing, sub_id))

                    # Log audit history
                    cur.execute("""
                        INSERT INTO brightloop_subscription_history (
                            subscription_id, user_name, previous_state, new_state, note
                        ) VALUES (%s, 'System Automated Cron', 'active', 'active', %s);
                    """, (sub_id, f"Recurring invoice {inv_name} generated for period {period_start} to {period_end}"))

                    cur.execute("RELEASE SAVEPOINT sub_bill_sp;")
                    results['invoices_created'] += 1

                except Exception as err:
                    cur.execute("ROLLBACK TO SAVEPOINT sub_bill_sp;")
                    _logger.error(f"Error billing subscription {sub['name']}: {err}")
                    results['errors'].append(f"{sub['name']}: {str(err)}")

    return results

def run_expiry_and_auto_close_cron():
    """Daily check for expired subscriptions and auto-closing plans."""
    today = date.today()
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Subscriptions past expiry date
            cur.execute("""
                UPDATE brightloop_subscription
                SET state = 'expired'
                WHERE state = 'active' AND expiry_date IS NOT NULL AND expiry_date < %s;
            """, (today,))

            # 2. Plans past end date
            cur.execute("""
                UPDATE brightloop_subscription_plan
                SET active = FALSE
                WHERE active = TRUE AND end_date IS NOT NULL AND end_date < %s AND auto_close = TRUE;
            """, (today,))

def record_invoice_payment(invoice_id: int, amount: float, method: str, ref: str, notes: str, user_name="Staff"):
    """Records full or partial payment against an invoice."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM account_move WHERE id = %s", (invoice_id,))
            inv = cur.fetchone()
            if not inv:
                raise ValueError("Invoice not found.")
            
            amount_residual = float(inv['amount_residual'])
            if amount <= 0:
                raise ValueError("Payment amount must be greater than zero.")
            if amount > amount_residual + 0.01:
                raise ValueError(f"Payment (₹{amount}) cannot exceed outstanding balance (₹{amount_residual}).")

            pay_name = get_next_sequence('account_payment', 'PAY')
            new_residual = max(0.0, amount_residual - amount)
            new_payment_state = 'paid' if new_residual <= 0.01 else 'partial'

            # Insert payment
            cur.execute("""
                INSERT INTO account_payment (
                    name, partner_id, move_id, subscription_id, payment_method, amount,
                    payment_date, transaction_reference, notes, state
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'posted') RETURNING id;
            """, (
                pay_name, inv['partner_id'], invoice_id, inv['subscription_id'],
                method, amount, date.today(), ref, notes
            ))
            pay_id = cur.fetchone()['id']

            # Update invoice
            cur.execute("""
                UPDATE account_move
                SET amount_residual = %s, payment_state = %s
                WHERE id = %s;
            """, (new_residual, new_payment_state, invoice_id))

            # Audit log on subscription if linked
            if inv['subscription_id']:
                cur.execute("""
                    INSERT INTO brightloop_subscription_history (
                        subscription_id, user_name, previous_state, new_state, note
                    ) VALUES (%s, %s, 'active', 'active', %s);
                """, (inv['subscription_id'], user_name, f"Recorded payment {pay_name} of ₹{amount:,.2f} via {method.upper()} for invoice {inv['name']}"))

            return {
                'payment_id': pay_id,
                'payment_name': pay_name,
                'new_residual': new_residual,
                'payment_state': new_payment_state
            }
