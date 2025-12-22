# ============================================================================
# BUS TICKET SYSTEM - Utility Functions
# CENG 301 Database Systems Project
# ============================================================================
# Common utility functions used throughout the application.
# ============================================================================

import hashlib
import re


def hash_password(password):
    """
    Hash a password using SHA256.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(stored_hash, provided_password):
    """
    Verify a password against a stored hash.
    
    Args:
        stored_hash: The stored password hash
        provided_password: The password to verify
        
    Returns:
        True if passwords match, False otherwise
    """
    return stored_hash == hash_password(provided_password)


def validate_email(email):
    """
    Validate email format.
    
    Returns:
        (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, ""
    
    return False, "Invalid email format"


def validate_phone(phone):
    """
    Validate Turkish phone number format.
    
    Returns:
        (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-()]', '', phone)
    
    # Check if it's a valid Turkish phone number
    pattern = r'^(0?5\d{9}|\+905\d{9})$'
    if re.match(pattern, cleaned):
        return True, ""
    
    return False, "Invalid phone number format"


def validate_id_number(id_number):
    """
    Validate Turkish ID number (TC Kimlik No).
    Must be exactly 11 digits and not start with 0.
    
    Returns:
        (is_valid, error_message)
    """
    if not id_number:
        return False, "ID number is required"
    
    # Must be exactly 11 digits
    if not id_number.isdigit() or len(id_number) != 11:
        return False, "ID number must be 11 digits"
    
    # Cannot start with 0
    if id_number[0] == '0':
        return False, "ID number cannot start with 0"
    
    return True, ""


def validate_password(password):
    """
    Validate password requirements.
    
    Returns:
        (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    return True, ""


def format_currency(amount):
    """
    Format amount as Turkish Lira.
    
    Args:
        amount: Numeric amount
        
    Returns:
        Formatted string (e.g., "1,250 TL")
    """
    try:
        return f"{int(amount):,} TL".replace(",", ".")
    except (TypeError, ValueError):
        return "0 TL"


def format_duration(minutes):
    """
    Format duration in minutes to human readable format.
    
    Args:
        minutes: Duration in minutes
        
    Returns:
        Formatted string (e.g., "5 hours 30 min")
    """
    if not minutes:
        return "-"
    
    try:
        hours = int(minutes) // 60
        mins = int(minutes) % 60
        
        if hours > 0 and mins > 0:
            return f"{hours} hours {mins} min"
        elif hours > 0:
            return f"{hours} hours"
        else:
            return f"{mins} min"
    except (TypeError, ValueError):
        return "-"


def format_date(date_obj):
    """
    Format date object to string.
    
    Args:
        date_obj: Date or datetime object
        
    Returns:
        Formatted string (e.g., "December 25, 2025")
    """
    if not date_obj:
        return "-"
    
    try:
        if hasattr(date_obj, 'strftime'):
            return date_obj.strftime("%B %d, %Y")
        return str(date_obj)
    except Exception:
        return str(date_obj)


def format_time(time_obj):
    """
    Format time object to HH:MM string.
    
    Args:
        time_obj: Time or datetime object
        
    Returns:
        Formatted string (e.g., "09:30")
    """
    if not time_obj:
        return "-"
    
    try:
        if hasattr(time_obj, 'strftime'):
            return time_obj.strftime("%H:%M")
        return str(time_obj)[:5]
    except Exception:
        return str(time_obj)


def sanitize_input(text):
    """
    Sanitize user input to prevent SQL injection.
    Note: This is a basic sanitization - parameterized queries are used
    for actual database operations.
    
    Args:
        text: Input text
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove or escape dangerous characters
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_"]
    result = str(text)
    
    for char in dangerous_chars:
        result = result.replace(char, "")
    
    return result.strip()
