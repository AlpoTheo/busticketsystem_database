# =============================================================================
# BUS TICKET SYSTEM - Utility Functions
# Database Systems Course Project
# =============================================================================
# 
# Helper functions used in different parts of the app.
# I put them here because DRY principle - Dont Repeat Yourself.
# Instead of writing same code in many places, write once and import.
# =============================================================================

import hashlib
import re


def hash_password(password):
    """
    Hash password using SHA256.
    
    WHY HASH PASSWORDS?
    We NEVER store passwords as plain text!
    
    If someone hacks the database and sees:
      Plain: password123
    They can use it immediately.
    
    But if they see:
      Hash: ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f
    They cant reverse it to get original password.
    
    SHA256 is one-way function - you can hash but cant un-hash.
    
    To check login: hash the entered password and compare hashes.
    If hashes match, password is correct.
    
    Note: In real production apps use bcrypt or argon2 with salt.
    SHA256 is simpler and works for this project.
    """
    if not password:
        return ""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(stored_hash, provided_password):
    """
    Check if password matches stored hash.
    Used during login.
    """
    if not stored_hash or not provided_password:
        return False
    return stored_hash == hash_password(provided_password)


def validate_email(email):
    """
    Check email format using regex (regular expression).
    
    Why validate?
    - Prevent bad data in database
    - Give quick feedback to user
    - Reduce errors
    
    Good: user@example.com, user.name@domain.co.uk
    Bad: user@, @domain.com, no-at-sign
    
    Returns: (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Regex pattern for email
    # ^ = start, $ = end
    # [a-zA-Z0-9._%+-]+ = letters, numbers, dots etc (one or more)
    # @ = the @ symbol
    # [a-zA-Z0-9.-]+ = domain name
    # \. = literal dot
    # [a-zA-Z]{2,} = at least 2 letters for TLD (com, org, etc)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email.strip()):
        return True, ""
    
    return False, "Invalid email format"


def validate_phone(phone):
    """
    Validate Turkish phone number.
    
    Accepted formats:
    - 05XX XXX XX XX
    - 5XX XXX XX XX  
    - +905XXXXXXXXX
    
    Returns: (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number required"
    
    # Remove spaces and dashes for checking
    cleaned = re.sub(r'[\s\-()]', '', phone)
    
    # Turkish mobile starts with 05 or 5 or +905
    # Then 9 more digits
    pattern = r'^(0?5\d{9}|\+905\d{9})$'
    
    if re.match(pattern, cleaned):
        return True, ""
    
    return False, "Invalid phone number"


def validate_id_number(id_number):
    """
    Validate Turkish ID number (TC Kimlik No).
    
    Rules:
    - Must be exactly 11 digits
    - Cannot start with 0
    
    Real TC numbers have checksum algorithm but we skip that
    to allow test data.
    
    Returns: (is_valid, error_message)
    """
    if not id_number:
        return False, "ID number required"
    
    id_number = id_number.strip()
    
    # Check 11 digits
    if not id_number.isdigit() or len(id_number) != 11:
        return False, "ID number must be 11 digits"
    
    # Cannot start with 0
    if id_number[0] == '0':
        return False, "ID number cannot start with 0"
    
    return True, ""


def validate_password(password):
    """
    Check password requirements.
    
    For this project: minimum 6 characters.
    
    In real app you would want:
    - Min 8 characters
    - At least 1 uppercase, 1 lowercase, 1 number
    - Not a common password like "123456"
    
    Returns: (is_valid, error_message)
    """
    if not password:
        return False, "Password required"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    return True, ""


def format_currency(amount):
    """
    Format number as Turkish Lira.
    
    Examples:
      1250 -> "1.250 TL"
      350.50 -> "351 TL"
    
    Uses dot as thousands separator (Turkish style).
    """
    try:
        value = int(round(float(amount)))
        formatted = f"{value:,}".replace(",", ".")
        return f"{formatted} TL"
    except (TypeError, ValueError):
        return "0 TL"


def format_duration(minutes):
    """
    Format minutes to readable text.
    
    Examples:
      330 -> "5h 30m"
      60 -> "1h"
      45 -> "45m"
    """
    if not minutes:
        return "-"
    
    try:
        minutes = int(minutes)
        hours = minutes // 60
        mins = minutes % 60
        
        if hours > 0 and mins > 0:
            return f"{hours}h {mins}m"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{mins}m"
    except (TypeError, ValueError):
        return "-"


def format_date(date_obj):
    """
    Format date to readable string.
    
    Example: 2025-12-25 -> "25 December 2025"
    """
    if not date_obj:
        return "-"
    
    months = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April',
        5: 'May', 6: 'June', 7: 'July', 8: 'August',
        9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }
    
    try:
        if hasattr(date_obj, 'day'):
            month_name = months.get(date_obj.month, str(date_obj.month))
            return f"{date_obj.day} {month_name} {date_obj.year}"
        return str(date_obj)
    except Exception:
        return str(date_obj)


def format_time(time_obj):
    """
    Format time to HH:MM string.
    
    Example: 09:30:00 -> "09:30"
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
    Basic input cleaning.
    
    IMPORTANT: This is NOT enough for SQL injection protection!
    We use parameterized queries (? placeholders) in database_manager.py
    That is the proper way to prevent SQL injection.
    
    This function just removes some obvious bad patterns as extra safety.
    """
    if not text:
        return ""
    
    result = str(text)
    
    # Remove dangerous SQL patterns
    # Note: parameterized queries already protect us
    dangerous = [
        "'--",      # SQL comment
        "'; --",    # injection attempt  
        "/*",       # block comment
        "*/",
        "xp_",      # SQL Server commands
        "EXEC(",
        "DROP ",
    ]
    
    for pattern in dangerous:
        result = result.replace(pattern, "")
    
    return result.strip()


def truncate_string(text, max_length, suffix="..."):
    """
    Cut string if too long.
    
    Useful for displaying long text in UI.
    
    Example: truncate_string("Hello World", 8) -> "Hello..."
    """
    if not text:
        return ""
    
    text = str(text)
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
