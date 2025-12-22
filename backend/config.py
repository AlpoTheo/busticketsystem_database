# ============================================================================
# BUS TICKET SYSTEM - Configuration
# CENG 301 Database Systems Project
# ============================================================================
# Database and application configuration settings.
# UPDATE THESE VALUES FOR YOUR LOCAL ENVIRONMENT!
# ============================================================================


class Config:
    """Application configuration"""
    
    # =========================================================================
    # DATABASE SETTINGS
    # =========================================================================
    
    # SQL Server connection settings
    DB_SERVER = 'localhost'  # Or your SQL Server instance name (e.g., 'DESKTOP-ABC\\SQLEXPRESS')
    DB_DATABASE = 'BusTicketSystem'
    DB_USERNAME = ''  # Not needed for Windows Auth
    DB_PASSWORD = ''  # Not needed for Windows Auth
    
    # ODBC Driver - Try these in order if one doesn't work:
    # - '{ODBC Driver 17 for SQL Server}'
    # - '{ODBC Driver 18 for SQL Server}'  
    # - '{SQL Server}'
    DB_DRIVER = '{ODBC Driver 17 for SQL Server}'
    
    # =========================================================================
    # APPLICATION SETTINGS
    # =========================================================================
    
    # Flask secret key for session management
    SECRET_KEY = 'bus_ticket_system_secret_2025_change_in_production'
    
    # Session settings
    SESSION_LIFETIME_HOURS = 24
    
    # Business rules
    MAX_SEATS_PER_BOOKING = 5
    TICKET_CANCELLATION_HOURS_BEFORE = 1  # Can cancel up to 1 hour before departure
    MIN_PASSWORD_LENGTH = 6
    
    # =========================================================================
    # WINDOWS AUTHENTICATION
    # =========================================================================
    # Using Windows Authentication (Trusted Connection)
    USE_WINDOWS_AUTH = True
    
    @classmethod
    def get_connection_string(cls):
        """Build the connection string based on settings"""
        if cls.USE_WINDOWS_AUTH:
            return (
                f"DRIVER={cls.DB_DRIVER};"
                f"SERVER={cls.DB_SERVER};"
                f"DATABASE={cls.DB_DATABASE};"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes"
            )
        else:
            return (
                f"DRIVER={cls.DB_DRIVER};"
                f"SERVER={cls.DB_SERVER};"
                f"DATABASE={cls.DB_DATABASE};"
                f"UID={cls.DB_USERNAME};"
                f"PWD={cls.DB_PASSWORD};"
                "TrustServerCertificate=yes"
            )
