# Brightloop – Subscription Management System
### Enterprise Odoo Hackathon Solution

An enterprise-grade **Subscription Management System** engineered for **Brightloop Software**, providing automated recurring billing, contract lifecycle management, quotation templates, multi-tier discount enforcement, payment tracking, financial reporting, and customer portal self-service.

---

## 1. Executive Summary & Deliverables

This repository contains a dual-tier production solution:

1. **Production-Ready Odoo 17 Custom Module (`brightloop_subscription/`)**:
   - Built to official Odoo 17 / 18 conventions and ORM architecture.
   - Full data models extending base Odoo models (`res.partner`, `product.template`, `product.product`, `account.move`, `account.payment`, `res.users`).
   - 13 XML navigation views, Tree, Form with Statusbars, Kanban, Pivot, and Graph views.
   - Security groups (`group_brightloop_admin`, `group_brightloop_staff`, `group_brightloop_customer`), granular ACLs (`ir.model.access.csv`), and multi-tenant portal record rules (`security/record_rules.xml`).
   - Automated scheduled cron jobs (`data/ir_cron_data.xml`).
   - Customer self-service portal controllers (`controllers/portal.py`) and QWeb templates (`views/portal_templates.xml`).
   - Custom branded QWeb PDF reports (`reports/report_subscription.xml`, `reports/report_invoice.xml`).
   - Unit and integration tests (`tests/test_subscription_workflow.py`).

2. **Interactive Live Demonstration Runtime (`brightloop_app/`)**:
   - Running directly against the local **PostgreSQL 18** database instance on port `8069` (standard Odoo port).
   - Real-time implementation of all 13 modules, 10 KPI calculations, Chart.js financial trends, recurring billing cron triggers, payment recording, and customer portal views.
   - One-click role switcher in the header to instantly test permissions as **Administrator**, **Internal Staff**, or **Customer**.
   - Built-in **5,000 Subscriptions Performance Benchmark** demonstrating sub-second query latency (< 0.07s vs the 2.0s threshold).

3. **Docker Deployment Configuration**:
   - `Dockerfile`, `docker-compose.yml`, and `odoo.conf` to launch in standard Odoo 17 Community containers with a single command (`docker-compose up -d`).

---

## 2. System Architecture & Technologies

- **Primary Platform**: Odoo 17.0 (LTS).
- **Database**: PostgreSQL 18 (with B-Tree indexes on `partner_id`, `plan_id`, `state`, `next_billing_date`, `invoice_date_due`, `payment_state`).
- **Backend**: Python 3.12, Odoo ORM, FastAPI demonstration engine.
- **Frontend**: Odoo XML views, Bootstrap 5 SaaS dashboard, FontAwesome 6, Chart.js 4.4.
- **Currency**: Indian Rupee (₹ INR) with realistic GSTINs and Indian business data.

---

## 3. The 13 Navigation Modules

### 1. Dashboard & Analytics
- **10 Dynamically Computed Financial KPIs**:
  1. *Total Customers*: Real count of registered business accounts.
  2. *Total Subscriptions*: All-time subscriptions on record.
  3. *Active Subscriptions*: Contracts currently generating recurring revenue.
  4. *Paused Subscriptions*: Contracts temporarily suspended.
  5. *Closed Subscriptions*: Successfully completed contracts.
  6. *Total Revenue Collected*: Actual cash collected via recorded payments (not merely invoice totals).
  7. *Period Invoiced*: Total billing amount generated in the selected period.
  8. *Outstanding Payments*: Residual unpaid balances on posted invoices.
  9. *Overdue Invoices & Upcoming Renewals*: Invoices past due date requiring chasing, plus contracts renewing in next 15 days.
  10. *Monthly Recurring Revenue (MRR)*: Normalized monthly value (Daily × 30, Weekly × 4.33, Monthly × 1, Yearly ÷ 12; excluding closed/cancelled contracts).
- **Interactive Chart.js Visualizations**:
  - Monthly Revenue Trend (Collected Cash vs Invoiced Revenue over 6 months).
  - Invoice Payment Status Distribution (Paid, Partial, Unpaid).
  - Active Subscription Revenue by Plan.
- **Time Range Filters**: Today, This Week, This Month, This Quarter, This Year, All Time.
- **Interactive "Run Billing Cron" Trigger**: Real-time background simulation of billing cycles.

### 2. Customers (`/customers`)
- Directory of 15 realistic Indian enterprises (Zenith Infotech, Bharat Cloud, Apex Retailers, Mumbai FinServe, Deccan Logistics, etc.).
- Real-time aggregation of active contracts, total invoiced amounts, and outstanding balances.
- "New Customer" creation modal.

### 3. Products (`/products`)
- Catalog of 10 software modules and cloud services (Brightloop Cloud ERP, HRMS Suite, Billing API Connector, WhatsApp Gateway, CRM Pro, Analytics Engine, Cloud Storage, SLA Booster, Security Shield, Theme).
- Tracks Product ID, Sales Price, Cost Price, Description, Active/Archived status.

### 4. Product Variants (`/product-variants`)
- Attribute-based price adjustments.
- Specific Hackathon Demonstration: Selecting the **Odoo Brand Edition** automatically adds **+₹560.00** to the original product price.
- Live calculation of `Base Price + Brand Adjustment = Final Calculated Variant Price`.

### 5. Subscription Plans (`/plans`)
- Multi-frequency support: **Daily**, **Weekly**, **Monthly**, and **Yearly**.
- Minimum quantity enforcement (e.g. minimum 5 units for Enterprise Yearly).
- Configurable lifecycle policies:
  - *Auto Close*: Closes subscription when end date arrives.
  - *Pause Allowed*: Permits customers/staff to freeze billing.
  - *Early Closure Allowed*: Permits early cancellation.
  - *Renewal Allowed*: Enables term extension.

### 6. Quotations (`/quotations`)
- Quotation templates with pre-configured products and validity days.
- Automatically calculates quotation expiry date (`quotation_date + validity_days`).
- Multi-line pricing, 18% GST tax calculation, and totals.
- **1-Click "Convert to Subscription"**: Converts confirmed quotations directly into active subscriptions with auto-generated reference numbers (`SUB/2026/00001`).

### 7. Subscriptions (`/subscriptions`)
- Full lifecycle statusbar: `Draft` &rarr; `Quotation` &rarr; `Confirmed` &rarr; `Active` &rarr; `Closed` (with `Paused`, `Cancelled`, `Expired`).
- Interactive lifecycle buttons:
  - *Activate*: Moves confirmed contract into active billing.
  - *Pause*: Suspends recurring billing with mandatory reason log.
  - *Resume*: Restores active billing and recalculates next billing date.
  - *Renew*: Extends expiry date by plan duration.
  - *Cancel*: Early termination with cancellation reason tracking.
  - *Close*: Formal contract closure.
- Tabbed view: Product lines, associated recurring invoices, and complete **Audit Trail History**.

### 8. Invoices (`/invoices`)
- Automated recurring invoice generation via background scheduler.
- Prevents duplicate invoices for the same subscription and period start date.
- Tax calculation (18% GST) and automatic coupon discount deduction.
- Branded **Tax Invoice View** (`/invoices/{id}`) with GSTIN, CIN, line items, and print/PDF support.

### 9. Discounts (`/discounts`) - Admin Only
- Administrator-only configuration.
- Types: **Percentage (%)** or **Fixed Amount (₹)**.
- Minimum purchase amount and minimum quantity validation.
- Maximum usage limit tracking (e.g., 50 uses maximum) with auto-deactivation when exhausted.
- Automatically applied to invoice lines during billing cron execution.

### 10. Payments (`/payments`)
- Multi-method collection: **UPI**, **Bank Transfer (NEFT/RTGS)**, **Credit/Debit Card**, **Cash**, and **Other**.
- Full support for **Partial Payments** and **Multiple Installments** against an invoice.
- Real-time residual balance reduction (`amount_residual`) and invoice state progression (`not_paid` &rarr; `partial` &rarr; `paid`).
- Validation preventing payments exceeding the outstanding balance.

### 11. Reports (`/reports`)
- Implementation of all **10 Specific Hackathon Reports**:
  1. *Subscription Summary Report*
  2. *Active & MRR Contribution Report*
  3. *Expired & Churned Subscriptions Report*
  4. *Upcoming Renewals Report (Next 30 Days)*
  5. *Monthly Revenue Report (Invoiced vs Collected)*
  6. *Payment Collections Report (by Method & UTR)*
  7. *Outstanding Invoices Report*
  8. *Overdue Invoices Report (with Days Overdue)*
  9. *Discount Usage & Quota Report*
  10. *Customer Audit & Status History Report*
- Instant **CSV / Excel Export** for every report.

### 12. Staff Management (`/staff`) - Admin Only
- Administrator-only account creation.
- Strict **Password Policy Enforcement** (validated both frontend and backend):
  - Strictly longer than 8 characters (> 8).
  - At least 1 uppercase letter (`[A-Z]`).
  - At least 1 lowercase letter (`[a-z]`).
  - At least 1 special character (`[^A-Za-z0-9]`).
- Unique email validation.

### 13. Settings (`/settings`)
- Organization metadata, currency (₹ INR), tax rules, and background cron schedules.

---

## 4. Customer Portal Self-Service (`/portal`)

Customers can log in to view:
- Their personal account details and GSTIN.
- **Personal Subscriptions Only**: Multi-tenant isolation ensures Customer A can never see or access Customer B's records.
- Self-service actions:
  - Request Pause (when plan allows).
  - Resume Subscription.
  - Request Term Renewal.
  - Request Early Cancellation.
- Download branded Tax Invoice PDFs.
- View payment transactions and receipts.

---

## 5. Performance & Scalability Benchmark

The problem statement requires responses in **under 2.0 seconds**, even with thousands of records.

### Automated Test Results (5,000 Records):
- **Batch Size**: 5,000 synthetic subscriptions populated into PostgreSQL.
- **Aggregation Query Latency**: **0.0669 seconds** (~67 milliseconds).
- **Target Met**: **Yes! 30x faster than the 2.0s limit.**
- **Indexes Utilized**: B-Tree indexes on `brightloop_subscription(state, next_billing_date, partner_id, plan_id)` and `account_move(partner_id, state, payment_state, invoice_date_due)`.

To verify live:
1. Navigate to `/benchmark` in the app.
2. Click **"Execute 5,000 Records Benchmark"**.
3. View real-time query telemetry.

---

## 6. How to Run & Demonstrate

### Option A: Running the Live Interactive Application
The application is currently running on `http://localhost:8069`.

If you ever need to restart it:
```powershell
python run_app.py
```
Or double-click `start_server.bat`.

Then open your browser to:
[http://localhost:8069](http://localhost:8069)

#### Switching Roles during Demo:
Use the **Role Dropdown** in the top right header:
- **Administrator** (`admin@brightloop.com`): Full access to all 13 modules, discounts, staff creation, and analytics.
- **Internal Staff** (`staff@brightloop.com`): Customer management, quotations, subscriptions, invoices, and payments.
- **Customer** (`billing@zenithinfotech.in`): Customer self-service portal with strict record isolation.

---

### Option B: Running the Automated Test Suite
To run the automated verification suite:
```powershell
python test_system.py
```
This executes 7 test suites validating password complexity, Odoo brand +₹560 calculation, quotation conversion, recurring billing, discount quota exhaustion, partial payments, and sub-2.0s query performance.

---

### Option C: Deploying to Odoo 17 Docker
To run inside an official Odoo 17 container:
```bash
docker-compose up -d
```
The module `brightloop_subscription` will be mounted and initialized in the Odoo database `brightloop_production`.

---

## 7. Complete Demonstration Script for Hackathon Jury

Follow this chronological story during your demonstration:

1. **Dashboard & KPIs (`/`)**:
   - Point out the 10 real-time financial KPI cards.
   - Show that MRR is normalized (Daily × 30, Monthly × 1, Yearly ÷ 12).
   - Filter by *This Month*, *This Quarter*, and *This Year*.

2. **Product Variants (`/product-variants`)**:
   - Show the Odoo Brand variant where base price + ₹560 adjustment calculates the final price automatically.

3. **Plan Configuration (`/plans`)**:
   - Show the 5 plans (Daily Sandbox, Weekly Agile, Monthly Pro, Yearly Enterprise, Custom Flexi) with availability dates and closure policies.

4. **Quotation to Subscription (`/quotations`)**:
   - Open quotations list.
   - Click **"Convert to Sub"** on an accepted quotation.
   - Show that it generates an active subscription with contract number `SUB/2026/XXXXX`.

5. **Subscription Lifecycle (`/subscriptions/{id}`)**:
   - Demonstrate the lifecycle action buttons.
   - Click **Pause**, enter a reason, and show status updates to *Paused*.
   - Click **Resume**, show status returns to *Active* and billing date recalculates.
   - Point out the **Audit Trail History** tab recording every timestamp and operator.

6. **Automated Recurring Billing (`/invoices`)**:
   - Click **"Run Billing Cron Now"**.
   - Show how the background cron scans due subscriptions, generates posted invoices, applies discounts, advances `next_billing_date`, and skips duplicates.

7. **Recording Payments (`/payments`)**:
   - Click **"Record Payment"**.
   - Choose an unpaid invoice, enter a partial amount (e.g. ₹1,000 out of ₹4,613), select UPI/UTR, and submit.
   - Show the invoice status updates to **Partial Due** and outstanding balance reduces.

8. **Reports & CSV Export (`/reports`)**:
   - Show the 10 reports and click **"Export to CSV"** to download the spreadsheet report.

9. **Customer Portal (`/portal`)**:
   - Switch role to **Customer**.
   - Show that the portal displays only Zenith Infotech's subscriptions, invoices, and payments.
   - Tamper with IDs or test accessing other records to demonstrate backend security isolation.

10. **Performance Benchmark (`/benchmark`)**:
    - Run the 5,000 subscriptions benchmark to show sub-0.10s response latency, satisfying the < 2.0s hackathon rule.
