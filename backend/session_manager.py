# ============================================================================
# BUS TICKET SYSTEM - Session Manager
# CENG 301 Database Systems Project
# ============================================================================
# This module manages user sessions for the application.
# ============================================================================

from typing import Optional, Dict
from enum import Enum


class UserRole(Enum):
    """Enum for user roles"""
    GUEST = "guest"
    USER = "user"
    FIRM_ADMIN = "firm_admin"
    SYSTEM_ADMIN = "system_admin"


class SessionManager:
    """
    Singleton class to manage user sessions.
    
    Stores the currently logged-in user's information and provides
    methods to check authentication status.
    """
    
    _instance = None
    
    def __new__(cls):
        """Ensure only one instance exists (Singleton pattern)"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize session manager"""
        if self._initialized:
            return
        
        self._current_user: Optional[Dict] = None
        self._user_role: UserRole = UserRole.GUEST
        self._initialized = True
    
    # =========================================================================
    # LOGIN/LOGOUT METHODS
    # =========================================================================
    
    def login_user(self, user_data: Dict) -> None:
        """
        Set the current logged-in user.
        
        Args:
            user_data: Dictionary containing user information
        """
        self._current_user = user_data
        self._user_role = UserRole.USER
    
    def login_firm_admin(self, admin_data: Dict) -> None:
        """
        Set the current logged-in firm admin.
        
        Args:
            admin_data: Dictionary containing admin information
        """
        self._current_user = admin_data
        self._user_role = UserRole.FIRM_ADMIN
    
    def login_system_admin(self, admin_data: Dict) -> None:
        """
        Set the current logged-in system admin.
        
        Args:
            admin_data: Dictionary containing admin information
        """
        self._current_user = admin_data
        self._user_role = UserRole.SYSTEM_ADMIN
    
    def logout(self) -> None:
        """Clear the current session"""
        self._current_user = None
        self._user_role = UserRole.GUEST
    
    # =========================================================================
    # SESSION PROPERTIES
    # =========================================================================
    
    @property
    def is_logged_in(self) -> bool:
        """Check if any user is logged in"""
        return self._current_user is not None
    
    @property
    def is_user(self) -> bool:
        """Check if logged in as regular user"""
        return self._user_role == UserRole.USER
    
    @property
    def is_firm_admin(self) -> bool:
        """Check if logged in as firm admin"""
        return self._user_role == UserRole.FIRM_ADMIN
    
    @property
    def is_system_admin(self) -> bool:
        """Check if logged in as system admin"""
        return self._user_role == UserRole.SYSTEM_ADMIN
    
    @property
    def user_role(self) -> UserRole:
        """Get current user role"""
        return self._user_role
    
    @property
    def current_user(self) -> Optional[Dict]:
        """Get current user data"""
        return self._current_user
    
    # =========================================================================
    # USER DATA GETTERS
    # =========================================================================
    
    def get_user_id(self) -> Optional[int]:
        """Get current user's ID"""
        if self._current_user:
            return self._current_user.get('user_id') or self._current_user.get('admin_id')
        return None
    
    def get_user_name(self) -> str:
        """Get current user's full name"""
        if self._current_user:
            first = self._current_user.get('first_name', '')
            last = self._current_user.get('last_name', '')
            return f"{first} {last}".strip()
        return "Guest"
    
    def get_user_email(self) -> Optional[str]:
        """Get current user's email"""
        if self._current_user:
            return self._current_user.get('email')
        return None
    
    def get_credit_balance(self) -> float:
        """Get current user's credit balance (for regular users)"""
        if self._current_user and self._user_role == UserRole.USER:
            return self._current_user.get('credit_balance', 0.0)
        return 0.0
    
    def update_credit_balance(self, new_balance: float) -> None:
        """Update the cached credit balance"""
        if self._current_user and self._user_role == UserRole.USER:
            self._current_user['credit_balance'] = new_balance
    
    def get_company_id(self) -> Optional[int]:
        """Get firm admin's company ID"""
        if self._current_user and self._user_role == UserRole.FIRM_ADMIN:
            return self._current_user.get('company_id')
        return None
    
    def get_company_name(self) -> Optional[str]:
        """Get firm admin's company name"""
        if self._current_user and self._user_role == UserRole.FIRM_ADMIN:
            return self._current_user.get('company_name')
        return None
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def refresh_user_data(self, user_data: Dict) -> None:
        """
        Refresh the current user's data (e.g., after profile update).
        
        Args:
            user_data: Updated user data dictionary
        """
        if self._current_user:
            self._current_user.update(user_data)
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary (for debugging)"""
        return {
            'is_logged_in': self.is_logged_in,
            'role': self._user_role.value,
            'user_id': self.get_user_id(),
            'user_name': self.get_user_name(),
            'email': self.get_user_email(),
        }


# Global session instance
session = SessionManager()

