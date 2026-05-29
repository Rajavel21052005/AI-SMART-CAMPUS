# ============================================================
# utils/validators.py — Input validation helpers
# ============================================================
import re


def is_valid_email(email: str) -> bool:
    pattern = r'^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_phone(phone: str) -> bool:
    return bool(re.match(r'^\+?[\d\s\-]{7,15}$', phone))


def is_strong_password(password: str) -> tuple:
    """
    Returns (is_valid: bool, message: str).
    Password must be 8+ chars, contain upper, lower, digit.
    """
    if len(password) < 8:
        return False, 'Password must be at least 8 characters.'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter.'
    if not re.search(r'\d', password):
        return False, 'Password must contain at least one digit.'
    return True, 'OK'


def is_valid_reg_number(reg: str) -> bool:
    """e.g. 22CS101 — 2-digit year + 2 letter dept + 3 digits."""
    return bool(re.match(r'^\d{2}[A-Z]{2,4}\d{3,5}$', reg))
