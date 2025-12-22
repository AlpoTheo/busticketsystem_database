# ============================================================================
# BUS TICKET SYSTEM - Database Manager
# CENG 301 Database Systems Project
# ============================================================================
# This module handles all database operations using pyodbc and stored procedures.
# Implements Singleton pattern for connection management.
# ============================================================================

import pyodbc
from datetime import datetime, date
from config import Config
from utils import hash_password


class DatabaseManager:
    """
    Singleton Database Manager class for handling all MSSQL operations.
    Uses stored procedures for complex operations as required by project guidelines.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            # Build connection string based on authentication method
            if Config.USE_WINDOWS_AUTH:
                cls._instance._connection_string = (
                    f"DRIVER={Config.DB_DRIVER};"
                    f"SERVER={Config.DB_SERVER};"
                    f"DATABASE={Config.DB_DATABASE};"
                    "Trusted_Connection=yes;"
                    "TrustServerCertificate=yes"
                )
            else:
                cls._instance._connection_string = (
                    f"DRIVER={Config.DB_DRIVER};"
                    f"SERVER={Config.DB_SERVER};"
                    f"DATABASE={Config.DB_DATABASE};"
                    f"UID={Config.DB_USERNAME};"
                    f"PWD={Config.DB_PASSWORD};"
                    "TrustServerCertificate=yes"
                )
            cls._instance._conn = None
        return cls._instance
    
    # =========================================================================
    # CONNECTION MANAGEMENT
    # =========================================================================
    
    def connect(self):
        """Establish database connection"""
        try:
            if self._conn is None:
                self._conn = pyodbc.connect(self._connection_string, autocommit=False)
            return True
        except pyodbc.Error as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def test_connection(self):
        """Test if database connection works"""
        try:
            if self.connect():
                cursor = self._conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                return True
        except Exception as e:
            print(f"Connection test failed: {e}")
        return False
    
    def _execute(self, query, params=None, fetch_all=False, fetch_one=False, commit=False):
        """Execute a query and return results"""
        self.connect()
        cursor = self._conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch_all:
                columns = [column[0] for column in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            elif fetch_one:
                columns = [column[0] for column in cursor.description] if cursor.description else []
                row = cursor.fetchone()
                return dict(zip(columns, row)) if row else None
            
            if commit:
                self._conn.commit()
            
            return cursor.rowcount
        except pyodbc.Error as e:
            self._conn.rollback()
            print(f"Query error: {e}")
            raise
        finally:
            cursor.close()
    
    # =========================================================================
    # USER AUTHENTICATION
    # =========================================================================
    
    def register_user(self, first_name, last_name, email, phone, password, id_number):
        """
        Register a new user
        Returns: (success, message, user_id)
        """
        try:
            # Check if email exists
            existing = self._execute(
                "SELECT UserID FROM Users WHERE Email = ?",
                (email,), fetch_one=True
            )
            if existing:
                return False, "Email already registered", None
            
            # Check if ID number exists
            existing = self._execute(
                "SELECT UserID FROM Users WHERE IDNumber = ?",
                (id_number,), fetch_one=True
            )
            if existing:
                return False, "ID number already registered", None
            
            # Hash password and insert
            password_hash = hash_password(password)
            
            query = """
                INSERT INTO Users (FirstName, LastName, Email, Phone, PasswordHash, IDNumber, Role, IsActive, CreditBalance, CreatedAt)
                OUTPUT INSERTED.UserID
                VALUES (?, ?, ?, ?, ?, ?, 'User', 1, 0, GETDATE())
            """
            result = self._execute(query, (first_name, last_name, email, phone, password_hash, id_number), fetch_one=True)
            self._conn.commit()
            
            return True, "Registration successful", result['UserID'] if result else None
            
        except Exception as e:
            return False, f"Registration failed: {str(e)}", None
    
    def login_user(self, email, password):
        """
        Login a user (both regular users and system admins)
        Returns: (success, message, user_data)
        """
        try:
            password_hash = hash_password(password)
            
            # Allow both User and SystemAdmin to login
            query = """
                SELECT UserID, FirstName, LastName, Email, Phone, CreditBalance, Role
                FROM Users 
                WHERE Email = ? AND PasswordHash = ? AND IsActive = 1
            """
            user = self._execute(query, (email, password_hash), fetch_one=True)
            
            if user:
                return True, "Login successful", {
                    'user_id': user['UserID'],
                    'first_name': user['FirstName'],
                    'last_name': user['LastName'],
                    'email': user['Email'],
                    'phone': user['Phone'],
                    'credit_balance': float(user['CreditBalance'] or 0),
                    'role': user['Role']
                }
            
            return False, "Invalid email or password", None
            
        except Exception as e:
            return False, f"Login error: {str(e)}", None
    
    def login_firm_admin(self, email, password):
        """Login a firm admin"""
        try:
            password_hash = hash_password(password)
            
            query = """
                SELECT fa.AdminID, fa.CompanyID, fa.FirstName, fa.LastName, fa.Email, c.CompanyName
                FROM FirmAdmins fa
                JOIN Companies c ON fa.CompanyID = c.CompanyID
                WHERE fa.Email = ? AND fa.PasswordHash = ? AND fa.IsActive = 1
            """
            admin = self._execute(query, (email, password_hash), fetch_one=True)
            
            if admin:
                return True, "Login successful", {
                    'admin_id': admin['AdminID'],
                    'company_id': admin['CompanyID'],
                    'first_name': admin['FirstName'],
                    'last_name': admin['LastName'],
                    'email': admin['Email'],
                    'company_name': admin['CompanyName']
                }
            
            return False, "Invalid credentials", None
            
        except Exception as e:
            return False, f"Login error: {str(e)}", None
    
    def login_system_admin(self, email, password):
        """Login a system admin"""
        try:
            password_hash = hash_password(password)
            
            query = """
                SELECT UserID, FirstName, LastName, Email, Role
                FROM Users 
                WHERE Email = ? AND PasswordHash = ? AND IsActive = 1 AND Role = 'SystemAdmin'
            """
            admin = self._execute(query, (email, password_hash), fetch_one=True)
            
            if admin:
                return True, "Login successful", {
                    'admin_id': admin['UserID'],
                    'first_name': admin['FirstName'],
                    'last_name': admin['LastName'],
                    'email': admin['Email'],
                    'role': admin['Role']
                }
            
            return False, "Invalid credentials", None
            
        except Exception as e:
            return False, f"Login error: {str(e)}", None
    
    # =========================================================================
    # USER PROFILE
    # =========================================================================
    
    def get_user_profile(self, user_id):
        """Get user profile data"""
        query = """
            SELECT UserID, FirstName, LastName, Email, Phone, CreditBalance, Role, CreatedAt
            FROM Users WHERE UserID = ?
        """
        user = self._execute(query, (user_id,), fetch_one=True)
        
        if user:
            return {
                'user_id': user['UserID'],
                'first_name': user['FirstName'],
                'last_name': user['LastName'],
                'email': user['Email'],
                'phone': user['Phone'],
                'credit_balance': float(user['CreditBalance'] or 0),
                'role': user['Role']
            }
        return None
    
    def update_user_profile(self, user_id, **kwargs):
        """Update user profile"""
        try:
            updates = []
            params = []
            
            if 'first_name' in kwargs and kwargs['first_name']:
                updates.append("FirstName = ?")
                params.append(kwargs['first_name'])
            if 'last_name' in kwargs and kwargs['last_name']:
                updates.append("LastName = ?")
                params.append(kwargs['last_name'])
            if 'phone' in kwargs and kwargs['phone']:
                updates.append("Phone = ?")
                params.append(kwargs['phone'])
            
            if not updates:
                return False, "No fields to update"
            
            params.append(user_id)
            query = f"UPDATE Users SET {', '.join(updates)} WHERE UserID = ?"
            
            self._execute(query, tuple(params), commit=True)
            return True, "Profile updated successfully"
            
        except Exception as e:
            return False, f"Update failed: {str(e)}"
    
    # =========================================================================
    # CITIES
    # =========================================================================
    
    def get_all_cities(self):
        """Get all cities"""
        query = "SELECT CityID, CityName FROM Cities ORDER BY CityName"
        cities = self._execute(query, fetch_all=True)
        return [{'city_id': c['CityID'], 'city_name': c['CityName']} for c in cities]
    
    # =========================================================================
    # TRIPS (Using Stored Procedures)
    # =========================================================================
    
    def search_trips(self, departure_city_id, arrival_city_id, travel_date, sort_by='DepartureTime', sort_order='ASC'):
        """
        Search trips using sp_SearchTrips stored procedure
        """
        try:
            query = "EXEC sp_SearchTrips @DepartureCityID=?, @ArrivalCityID=?, @DepartureDate=?"
            trips = self._execute(query, (departure_city_id, arrival_city_id, travel_date), fetch_all=True)
            
            # Convert to proper format
            result = []
            for t in trips:
                result.append({
                    'TripID': t.get('TripID'),
                    'CompanyName': t.get('CompanyName'),
                    'CompanyRating': float(t.get('CompanyRating') or 4.5),
                    'DepartureCity': t.get('DepartureCity'),
                    'ArrivalCity': t.get('ArrivalCity'),
                    'DepartureDate': str(t.get('DepartureDate', '')),
                    'DepartureTime': str(t.get('DepartureTime', '')),
                    'ArrivalTime': str(t.get('ArrivalTime', '')),
                    'DurationMinutes': t.get('DurationMinutes', 0),
                    'Price': float(t.get('Price', 0)),
                    'AvailableSeats': t.get('AvailableSeats', 0),
                    'TotalSeats': t.get('TotalSeats', 40),
                    'HasWifi': t.get('HasWifi', False),
                    'HasRefreshments': t.get('HasRefreshments', False),
                    'HasTV': t.get('HasTV', False),
                    'HasPowerOutlet': t.get('HasPowerOutlet', False),
                    'HasEntertainment': t.get('HasEntertainment', False)
                })
            
            return result
            
        except Exception as e:
            print(f"Search trips error: {e}")
            return []
    
    def get_trip_details(self, trip_id):
        """Get single trip details"""
        query = """
            SELECT t.TripID, t.Price, t.DepartureTime, t.ArrivalTime, t.DurationMinutes,
                   t.DepartureDate, c.CompanyName, c.Rating as CompanyRating,
                   dc.CityName as DepartureCity, ac.CityName as ArrivalCity,
                   b.TotalSeats, b.HasWifi, b.HasRefreshments, b.HasTV, b.HasPowerOutlet, b.HasEntertainment
            FROM Trips t
            JOIN Buses b ON t.BusID = b.BusID
            JOIN Companies c ON b.CompanyID = c.CompanyID
            JOIN Cities dc ON t.DepartureCityID = dc.CityID
            JOIN Cities ac ON t.ArrivalCityID = ac.CityID
            WHERE t.TripID = ?
        """
        trip = self._execute(query, (trip_id,), fetch_one=True)
        
        if trip:
            return {
                'TripID': trip['TripID'],
                'CompanyName': trip['CompanyName'],
                'CompanyRating': float(trip['CompanyRating'] or 4.5),
                'DepartureCity': trip['DepartureCity'],
                'ArrivalCity': trip['ArrivalCity'],
                'DepartureDate': str(trip['DepartureDate']),
                'DepartureTime': str(trip['DepartureTime']),
                'ArrivalTime': str(trip['ArrivalTime']),
                'DurationMinutes': trip['DurationMinutes'],
                'Price': float(trip['Price']),
                'TotalSeats': trip['TotalSeats'],
                'HasWifi': trip['HasWifi'],
                'HasRefreshments': trip['HasRefreshments'],
                'HasTV': trip['HasTV'],
                'HasPowerOutlet': trip['HasPowerOutlet'],
                'HasEntertainment': trip['HasEntertainment']
            }
        return None
    
    def get_trip_seat_status(self, trip_id):
        """
        Get seat status for a trip using sp_GetTripSeatStatus
        """
        try:
            query = "EXEC sp_GetTripSeatStatus @TripID=?"
            seats = self._execute(query, (trip_id,), fetch_all=True)
            
            result = []
            for s in seats:
                result.append({
                    'SeatID': s.get('SeatID'),
                    'SeatNumber': s.get('SeatNumber'),
                    'SeatRow': s.get('SeatRow'),
                    'SeatColumn': s.get('SeatColumn'),
                    'SeatStatus': s.get('SeatStatus', 'Available')
                })
            
            return result
            
        except Exception as e:
            print(f"Get seat status error: {e}")
            return []
    
    # =========================================================================
    # TICKETS (Using Stored Procedures)
    # =========================================================================
    
    def purchase_ticket(self, user_id, trip_id, seat_ids, passenger_names, coupon_code=None, use_credit=True):
        """
        Purchase ticket(s) using sp_PurchaseTicket stored procedure
        Returns: (success, message, ticket_id)
        """
        try:
            # Convert lists to comma-separated strings for the SP
            seat_ids_str = ','.join(map(str, seat_ids))
            passenger_names_str = '|'.join(passenger_names)  # Use | as separator
            
            query = "EXEC sp_PurchaseTicket @UserID=?, @TripID=?, @SeatIDs=?, @PassengerNames=?, @CouponCode=?"
            
            self.connect()
            cursor = self._conn.cursor()
            cursor.execute(query, (user_id, trip_id, seat_ids_str, passenger_names_str, coupon_code or ''))
            
            # Get the result
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = row[0]
                message = row[1]
                ticket_id = row[2] if len(row) > 2 else None
                return success == 1, message, ticket_id
            
            return False, "Purchase failed", None
            
        except Exception as e:
            self._conn.rollback()
            print(f"Purchase error: {e}")
            return False, f"Purchase error: {str(e)}", None
    
    def get_user_tickets(self, user_id, status_filter=None):
        """
        Get user's tickets using sp_GetUserTickets
        """
        try:
            query = "EXEC sp_GetUserTickets @UserID=?, @StatusFilter=?"
            tickets = self._execute(query, (user_id, status_filter or ''), fetch_all=True)
            
            result = []
            for t in tickets:
                result.append({
                    'TicketID': t.get('TicketID'),
                    'TripID': t.get('TripID'),
                    'CompanyName': t.get('CompanyName'),
                    'DepartureCity': t.get('DepartureCity'),
                    'ArrivalCity': t.get('ArrivalCity'),
                    'DepartureDate': str(t.get('DepartureDate', '')),
                    'DepartureTime': str(t.get('DepartureTime', '')),
                    'ArrivalTime': str(t.get('ArrivalTime', '')),
                    'DurationMinutes': t.get('DurationMinutes', 0),
                    'SeatNumber': t.get('SeatNumber'),
                    'PassengerName': t.get('PassengerName'),
                    'PaidAmount': float(t.get('PaidAmount', 0)),
                    'Status': t.get('Status', 'Active'),
                    'PurchasedAt': str(t.get('PurchasedAt', ''))
                })
            
            return result
            
        except Exception as e:
            print(f"Get tickets error: {e}")
            return []
    
    def get_ticket_details(self, ticket_id, user_id):
        """Get ticket details for a specific user"""
        query = """
            SELECT tk.*, t.DepartureDate, t.DepartureTime, t.ArrivalTime, t.DurationMinutes, t.Price,
                   c.CompanyName, dc.CityName as DepartureCity, ac.CityName as ArrivalCity,
                   s.SeatNumber
            FROM Tickets tk
            JOIN Trips t ON tk.TripID = t.TripID
            JOIN Buses b ON t.BusID = b.BusID
            JOIN Companies c ON b.CompanyID = c.CompanyID
            JOIN Cities dc ON t.DepartureCityID = dc.CityID
            JOIN Cities ac ON t.ArrivalCityID = ac.CityID
            JOIN Seats s ON tk.SeatID = s.SeatID
            WHERE tk.TicketID = ? AND tk.UserID = ?
        """
        return self._execute(query, (ticket_id, user_id), fetch_one=True)
    
    def cancel_ticket(self, ticket_id, user_id):
        """
        Cancel a ticket using sp_CancelTicket
        Returns: (success, message)
        """
        try:
            query = "EXEC sp_CancelTicket @TicketID=?, @UserID=?"
            
            self.connect()
            cursor = self._conn.cursor()
            cursor.execute(query, (ticket_id, user_id))
            
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = row[0]
                message = row[1]
                return success == 1, message
            
            return False, "Cancellation failed"
            
        except Exception as e:
            self._conn.rollback()
            print(f"Cancel error: {e}")
            return False, f"Cancel error: {str(e)}"
    
    # =========================================================================
    # COUPONS
    # =========================================================================
    
    def validate_coupon(self, coupon_code, user_id):
        """
        Validate a coupon using sp_ValidateCoupon
        Returns: (is_valid, discount_rate, message)
        """
        try:
            query = "EXEC sp_ValidateCoupon @CouponCode=?, @UserID=?"
            
            self.connect()
            cursor = self._conn.cursor()
            cursor.execute(query, (coupon_code, user_id))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                is_valid = row[0]
                discount_rate = row[1] if len(row) > 1 else 0
                message = row[2] if len(row) > 2 else ''
                return is_valid == 1, float(discount_rate or 0), message
            
            return False, 0, "Invalid coupon"
            
        except Exception as e:
            print(f"Coupon validation error: {e}")
            return False, 0, f"Validation error: {str(e)}"
    
    def get_user_coupons(self, user_id):
        """Get available coupons for a user"""
        query = """
            SELECT c.CouponID, c.CouponCode, c.DiscountRate, c.ExpiryDate, c.Description,
                   CASE WHEN uc.UsageID IS NOT NULL THEN 1 ELSE 0 END as IsUsed
            FROM Coupons c
            LEFT JOIN CouponUsage uc ON c.CouponID = uc.CouponID AND uc.UserID = ?
            WHERE c.IsActive = 1
            ORDER BY c.ExpiryDate
        """
        return self._execute(query, (user_id,), fetch_all=True)
    
    def get_all_coupons(self):
        """Get all coupons (admin)"""
        query = """
            SELECT CouponID, CouponCode, DiscountRate, UsageLimit, UsageCount, 
                   ExpiryDate, IsActive, Description
            FROM Coupons ORDER BY CreatedAt DESC
        """
        return self._execute(query, fetch_all=True)
    
    def create_coupon(self, coupon_code, discount_rate, usage_limit, expiry_date, description=''):
        """Create a new coupon"""
        try:
            query = """
                INSERT INTO Coupons (CouponCode, DiscountRate, UsageLimit, UsageCount, ExpiryDate, IsActive, Description, CreatedAt)
                VALUES (?, ?, ?, 0, ?, 1, ?, GETDATE())
            """
            self._execute(query, (coupon_code, discount_rate, usage_limit, expiry_date, description), commit=True)
            return True, "Coupon created successfully"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # =========================================================================
    # CREDIT MANAGEMENT
    # =========================================================================
    
    def add_user_credit(self, user_id, amount, payment_method='CreditCard'):
        """
        Add credit to user account using sp_AddUserCredit
        Returns: (success, message)
        """
        try:
            query = "EXEC sp_AddUserCredit @UserID=?, @Amount=?, @PaymentMethod=?"
            
            self.connect()
            cursor = self._conn.cursor()
            cursor.execute(query, (user_id, amount, payment_method))
            
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = row[0]
                message = row[1]
                return success == 1, message
            
            return True, f"{amount} TL added successfully"
            
        except Exception as e:
            self._conn.rollback()
            print(f"Add credit error: {e}")
            return False, f"Error: {str(e)}"
    
    def get_user_credit(self, user_id):
        """Get user's credit balance"""
        query = "SELECT CreditBalance FROM Users WHERE UserID = ?"
        result = self._execute(query, (user_id,), fetch_one=True)
        return float(result['CreditBalance']) if result else 0
    
    def get_payment_history(self, user_id):
        """Get user's payment history"""
        query = """
            SELECT PaymentID, Amount, PaymentMethod, PaymentStatus, PaymentDate, TransactionType
            FROM Payments WHERE UserID = ?
            ORDER BY PaymentDate DESC
        """
        return self._execute(query, (user_id,), fetch_all=True)
    
    # =========================================================================
    # ADMIN DASHBOARD
    # =========================================================================
    
    def get_dashboard_stats(self, company_id=None):
        """
        Get dashboard statistics using sp_GetDashboardStats
        """
        try:
            query = "EXEC sp_GetDashboardStats @CompanyID=?"
            
            self.connect()
            cursor = self._conn.cursor()
            cursor.execute(query, (company_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    'total_users': row[0] if len(row) > 0 else 0,
                    'total_trips': row[1] if len(row) > 1 else 0,
                    'total_tickets': row[2] if len(row) > 2 else 0,
                    'total_revenue': float(row[3]) if len(row) > 3 else 0,
                    'active_trips': row[4] if len(row) > 4 else 0
                }
            
            return {}
            
        except Exception as e:
            print(f"Dashboard stats error: {e}")
            return {}
    
    def get_all_companies(self):
        """Get all companies"""
        query = """
            SELECT CompanyID, CompanyName, ContactEmail, ContactPhone, Rating, IsActive, CreatedAt
            FROM Companies ORDER BY CompanyName
        """
        return self._execute(query, fetch_all=True)
    
    def get_all_users(self):
        """Get all users"""
        query = """
            SELECT UserID, FirstName, LastName, Email, Phone, CreditBalance, Role, IsActive, CreatedAt
            FROM Users WHERE Role = 'User'
            ORDER BY CreatedAt DESC
        """
        return self._execute(query, fetch_all=True)
    
    # =========================================================================
    # FIRM ADMIN OPERATIONS
    # =========================================================================
    
    def get_company_trips(self, company_id, status=None):
        """Get trips for a company"""
        query = """
            SELECT t.TripID, t.DepartureDate, t.DepartureTime, t.ArrivalTime, t.DurationMinutes,
                   t.Price, t.Status, b.PlateNumber,
                   dc.CityName as DepartureCity, ac.CityName as ArrivalCity,
                   (SELECT COUNT(*) FROM Tickets tk WHERE tk.TripID = t.TripID AND tk.Status = 'Active') as SoldSeats
            FROM Trips t
            JOIN Buses b ON t.BusID = b.BusID
            JOIN Cities dc ON t.DepartureCityID = dc.CityID
            JOIN Cities ac ON t.ArrivalCityID = ac.CityID
            WHERE b.CompanyID = ?
        """
        if status:
            query += " AND t.Status = ?"
            return self._execute(query, (company_id, status), fetch_all=True)
        
        query += " ORDER BY t.DepartureDate DESC"
        return self._execute(query, (company_id,), fetch_all=True)
    
    def get_company_buses(self, company_id):
        """Get buses for a company"""
        query = """
            SELECT BusID, PlateNumber, TotalSeats, BusType, HasWifi, HasRefreshments, 
                   HasTV, HasPowerOutlet, HasEntertainment, IsActive
            FROM Buses WHERE CompanyID = ? AND IsActive = 1
        """
        return self._execute(query, (company_id,), fetch_all=True)
    
    def create_trip(self, bus_id, departure_city_id, arrival_city_id, departure_date, 
                    departure_time, arrival_time, duration_minutes, price, created_by_admin_id):
        """
        Create a new trip using sp_CreateTrip
        Returns: (success, message, trip_id)
        """
        try:
            query = """
                EXEC sp_CreateTrip @BusID=?, @DepartureCityID=?, @ArrivalCityID=?, 
                @DepartureDate=?, @DepartureTime=?, @ArrivalTime=?, @DurationMinutes=?, 
                @Price=?, @CreatedByAdminID=?
            """
            
            self.connect()
            cursor = self._conn.cursor()
            cursor.execute(query, (
                bus_id, departure_city_id, arrival_city_id, departure_date,
                departure_time, arrival_time, duration_minutes, price, created_by_admin_id
            ))
            
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = row[0]
                message = row[1]
                trip_id = row[2] if len(row) > 2 else None
                return success == 1, message, trip_id
            
            return False, "Failed to create trip", None
            
        except Exception as e:
            self._conn.rollback()
            print(f"Create trip error: {e}")
            return False, f"Error: {str(e)}", None
