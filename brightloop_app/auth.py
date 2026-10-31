# -*- coding: utf-8 -*-
"""
Authentication and Role-Based Access Control for Brightloop Software.
"""
import re
import hashlib
from brightloop_app.db import get_db
from psycopg2.extras import RealDictCursor

def validate_password_complexity(password: str):
    """
    Validates:
    - Length > 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 special character
    """
    if not password or len(password) <= 8:
        return False, "Password must be strictly longer than 8 characters."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Password must contain at least one special character (e.g. !@#$%^&*)."
    return True, ""

def hash_password(password: str) -> str:
    salt = "brightloop_secure_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def create_user(name, email, password, role="customer"):
    is_valid, msg = validate_password_complexity(password)
    if not is_valid:
        raise ValueError(msg)
    
    pwd_hash = hash_password(password)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM res_users WHERE LOWER(login) = LOWER(%s)", (email.strip(),))
            if cur.fetchone():
                raise ValueError(f"Email '{email}' is already registered.")
            
            cur.execute("""
                INSERT INTO res_users (name, login, password_hash, role)
                VALUES (%s, %s, %s, %s) RETURNING id;
            """, (name.strip(), email.strip().lower(), pwd_hash, role))
            user_id = cur.fetchone()[0]
            
            # If customer role, link or create res_partner
            if role == 'customer':
                cur.execute("SELECT id FROM res_partner WHERE LOWER(email) = LOWER(%s)", (email.strip(),))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO res_partner (name, email, customer_rank)
                        VALUES (%s, %s, 1);
                    """, (name.strip(), email.strip().lower()))
            return user_id

def authenticate_user(email, password):
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM res_users WHERE LOWER(login) = LOWER(%s) AND active = TRUE", (email.strip(),))
            user = cur.fetchone()
            if not user:
                return None
            if verify_password(password, user['password_hash']):
                return user
            return None
