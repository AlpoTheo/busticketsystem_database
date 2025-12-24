# ============================================================================
# BUS TICKET SYSTEM - Utility Functions
# CENG 301 Database Systems Term Project
# ============================================================================
# Common utility functions used throughout the application.
#
# WHY A SEPARATE UTILS FILE?
# Following the DRY (Don't Repeat Yourself) principle - these functions
# are used in multiple places (login, registration, etc.), so we put them
# in one place to avoid code duplication.
# ============================================================================

import hashlib
import re


def hash_password(password):
    """
    Hash a password using SHA256.
    
    WHY HASHING?
    We NEVER store passwords as plain text! If the database is compromised,
    attackers would get all user passwords. With hashing:
    - password123 -> ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f
    
    SHA256 is a one-way function - you can't reverse it to get the original.
    To verify login, we hash the entered password and compare hashes.
    
    NOTE: In production, use bcrypt or argon2 with salts. SHA256 is used here
    for simplicity and compatibility with the sample data in the SQL script.
    
    Args:
        password: Plain text password
        
    Returns:
        64-character hex string (SHA256 hash)
    """
    if not password:
        return ""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(stored_hash, provided_password):
    """
    Verify a password against a stored hash.
    
    This is used during login to check if the entered password matches.
    
    Args:
        stored_hash: The hash stored in database
        provided_password: The password user entered
        
    Returns:
        True if passwords match, False otherwise
    """
    if not stored_hash or not provided_password:
        return False
    return stored_hash == hash_password(provided_password)


def validate_email(email):
    """
    Validate email format using regex.
    
    WHY VALIDATE?
    - Prevent invalid data in database
    - Better user experience (catch typos early)
    - Security (reduce injection attack surface)
    
    Valid: user@example.com, user.name@domain.co.uk
    Invalid: user@, @domain.com, user@.com
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not email:
        return False, "E-posta adresi gerekli"  # "Email is required"
    
    # Standard email regex pattern
    # Matches: local-part@domain.tld
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email.strip()):
        return True, ""
    
    return False, "Geçersiz e-posta formatı"  # "Invalid email format"


def validate_phone(phone):
    """
    Validate Turkish phone number format.
    
    Accepted formats:
    - 05XX XXX XX XX
    - 5XX XXX XX XX
    - +905XXXXXXXXX
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not phone:
        return False, "Telefon numarası gerekli"  # "Phone number required"
    
    # Remove spaces, dashes, parentheses for validation
    cleaned = re.sub(r'[\s\-()]', '', phone)
    
    # Turkish mobile number patterns
    # Can start with 0, or without 0, or with +90
    pattern = r'^(0?5\d{9}|\+905\d{9})$'
    
    if re.match(pattern, cleaned):
        return True, ""
    
    return False, "Geçersiz telefon numarası"  # "Invalid phone number"


def validate_id_number(id_number):
    """
    Validate Turkish ID number (TC Kimlik No).
    
    Rules:
    - Exactly 11 digits
    - Cannot start with 0
    - Algorithm check (optional, not implemented for simplicity)
    
    Real TC numbers have a checksum algorithm, but we skip that
    for this project to allow test data.
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not id_number:
        return False, "TC kimlik numarası gerekli"  # "ID number required"
    
    # Remove any whitespace
    id_number = id_number.strip()
    
    # Must be exactly 11 digits
    if not id_number.isdigit() or len(id_number) != 11:
        return False, "TC kimlik numarası 11 haneli olmalı"  # "ID must be 11 digits"
    
    # Cannot start with 0
    if id_number[0] == '0':
        return False, "TC kimlik numarası 0 ile başlayamaz"  # "ID cannot start with 0"
    
    return True, ""


def validate_password(password):
    """
    Validate password requirements.
    
    Requirements (kept simple for demo):
    - At least 6 characters
    
    In production, you'd want:
    - Minimum 8 characters
    - At least one uppercase, lowercase, number
    - No common passwords
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not password:
        return False, "Şifre gerekli"  # "Password required"
    
    if len(password) < 6:
        return False, "Şifre en az 6 karakter olmalı"  # "Password must be at least 6 characters"
    
    return True, ""


def format_currency(amount):
    """
    Format amount as Turkish Lira for display.
    
    Examples:
        1250 -> "1.250 TL"
        350.50 -> "351 TL" (rounded)
    
    Uses dot as thousands separator (Turkish convention).
    
    Args:
        amount: Numeric amount
        
    Returns:
        Formatted string
    """
    try:
        # Round to nearest integer for display
        value = int(round(float(amount)))
        # Format with dots as thousands separator
        formatted = f"{value:,}".replace(",", ".")
        return f"{formatted} TL"
    except (TypeError, ValueError):
        return "0 TL"


def format_duration(minutes):
    """
    Format duration in minutes to human readable format.
    
    Examples:
        330 -> "5 saat 30 dk"
        60 -> "1 saat"
        45 -> "45 dk"
    
    Args:
        minutes: Duration in minutes
        
    Returns:
        Formatted string
    """
    if not minutes:
        return "-"
    
    try:
        minutes = int(minutes)
        hours = minutes // 60
        mins = minutes % 60
        
        if hours > 0 and mins > 0:
            return f"{hours} saat {mins} dk"  # "X hours Y min"
        elif hours > 0:
            return f"{hours} saat"  # "X hours"
        else:
            return f"{mins} dk"  # "X min"
    except (TypeError, ValueError):
        return "-"


def format_date(date_obj):
    """
    Format date object to Turkish locale string.
    
    Example: 2025-12-25 -> "25 Aralık 2025"
    
    Args:
        date_obj: Date or datetime object
        
    Returns:
        Formatted string
    """
    if not date_obj:
        return "-"
    
    # Turkish month names
    months_turkish = {
        1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan',
        5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos',
        9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
    }
    
    try:
        if hasattr(date_obj, 'day'):
            month_name = months_turkish.get(date_obj.month, str(date_obj.month))
            return f"{date_obj.day} {month_name} {date_obj.year}"
        return str(date_obj)
    except Exception:
        return str(date_obj)


def format_time(time_obj):
    """
    Format time object to HH:MM string.
    
    Example: 09:30:00 -> "09:30"
    
    Args:
        time_obj: Time or datetime object
        
    Returns:
        Formatted string (HH:MM)
    """
    if not time_obj:
        return "-"
    
    try:
        if hasattr(time_obj, 'strftime'):
            return time_obj.strftime("%H:%M")
        # If it's a string, just take first 5 characters (HH:MM)
        return str(time_obj)[:5]
    except Exception:
        return str(time_obj)


def sanitize_input(text):
    """
    Basic input sanitization.
    
    NOTE: This is NOT sufficient for SQL injection prevention!
    We use parameterized queries (? placeholders) in database_manager.py
    which is the proper way to prevent SQL injection.
    
    This function is just an extra layer for removing obviously dangerous patterns.
    
    Args:
        text: Input text
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Convert to string
    result = str(text)
    
    # Remove some dangerous patterns
    # Note: parameterized queries already protect against SQL injection
    dangerous_patterns = [
        "'--",      # SQL comment
        "'; --",    # SQL injection attempt
        "/*",       # SQL block comment start
        "*/",       # SQL block comment end
        "xp_",      # SQL Server extended stored procedures
        "EXEC(",    # Execute command
        "DROP ",    # Drop table/database
    ]
    
    for pattern in dangerous_patterns:
        result = result.replace(pattern, "")
    
    return result.strip()


def truncate_string(text, max_length, suffix="..."):
    """
    Truncate a string to maximum length.
    
    Useful for displaying long text in UI.
    
    Example: truncate_string("Hello World", 8) -> "Hello..."
    
    Args:
        text: Input text
        max_length: Maximum length including suffix
        suffix: String to append when truncated
        
    Returns:
        Truncated string
    """
    if not text:
        return ""
    
    text = str(text)
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
