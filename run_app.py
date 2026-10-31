# -*- coding: utf-8 -*-
"""
Brightloop Software - Server Launcher
Runs the Live Interactive Subscription Management System on http://localhost:8069
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import uvicorn
from brightloop_app.db import init_db, get_db
from brightloop_app.seed_data import seed

def main():
    print("==================================================================")
    print("   BRIGHTLOOP SOFTWARE - SUBSCRIPTION MANAGEMENT SYSTEM (ODOO)   ")
    print("==================================================================")
    init_db()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM res_partner;")
            if cur.fetchone()[0] == 0:
                print("Database is empty. Populating demonstration dataset...")
                seed()
            else:
                print("PostgreSQL 18 database connected with demo records.")

    print("\nStarting Web Application Server on http://localhost:8069 ...")
    print("Login Roles available in the topbar:")
    print(" - Admin: admin@gmail.com (Full access)")
    print(" - Staff: staff@gmail.com (Operations & Billing)")
    print(" - Customer: cust@gmail.com (Self-Service Portal)")
    print("==================================================================\n")

    uvicorn.run("brightloop_app.app:app", host="127.0.0.1", port=8069, reload=False, log_level="info")

if __name__ == '__main__':
    main()
