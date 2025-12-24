# ============================================================================
# BUS TICKET SYSTEM - Database Manager
# CENG 301 Database Systems Term Project
# ============================================================================
# This module handles all database operations using pyodbc.
# 
# WHY SINGLETON PATTERN?
# We use Singleton here because we only need ONE database connection
# throughout the application. Creating multiple connections would waste
# resources and could cause issues with transactions.
#
# WHY STORED PROCEDURES?
# The project requirements specify using SPs for complex operations.
# This also demonstrates understanding of:
#   - ACID transactions (ticket purchase)
#   - Data integrity (seat availability checks)
#   - Separation of concerns (business logic in DB layer)
# ============================================================================

import pyodbc
from datetime import datetime, date
from config import Config
from utils import hash_password


class DatabaseManager:
    """
    Singleton Database Manager class for handling all MSSQL operations.
    
    This class manages:
    - Connection pooling (single connection instance)
    - Query execution with proper error handling
    - Stored procedure calls for complex transactions
    """
    _instance = None
    
    def __new__(cls):
        # Singleton pattern: ensure only one instance exists
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize_connection_string()
            cls._instance._conn = None
        return cls._instance
    
    def _initialize_connection_string(self):
        """
        Build the connection string based on authentication method.
        Windows Auth is used for local development (no password needed).
        SQL Auth would be used in production with proper credentials.
        """
        if Config.USE_WINDOWS_AUTH:
            self._connection_string = (
                f"DRIVER={Config.DB_DRIVER};"
                f"SERVER={Config.DB_SERVER};"
                f"DATABASE={Config.DB_DATABASE};"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes"
            )
        else:
            self._connection_string = (
                f"DRIVER={Config.DB_DRIVER};"
                f"SERVER={Config.DB_SERVER};"
                f"DATABASE={Config.DB_DATABASE};"
                f"UID={Config.DB_USERNAME};"
                f"PWD={Config.DB_PASSWORD};"
                "TrustServerCertificate=yes"
            )
    
    # =========================================================================
    # CONNECTION MANAGEMENT
    # =========================================================================
    
    def connect(self):
        """
        Establish database connection.
        Returns True if successful, False otherwise.
        
        We check if connection exists first to avoid creating multiple connections.
        """
        try:
            if self._conn is None:
                self._conn = pyodbc.connect(self._connection_string, autocommit=False)
            return True
        except pyodbc.Error as e:
            # Log error for debugging but don't crash
            print(f"[DB ERROR] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection safely"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass  # Ignore errors on close
            finally:
                self._conn = None
    
    def test_connection(self):
        """
        Test if database connection works.
        Used at startup to verify the database is accessible.
        """
        try:
            if self.connect():
                cursor = self._conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                return True
        except Exception as e:
            print(f"[DB ERROR] Connection test failed: {e}")
        return False
    
    def _execute(self, query, params=None, fetch_all=False, fetch_one=False, commit=False):
        """
        Execute a query and return results.
        
        This is the core method that all other methods use.
        It handles:
        - Connection management
        - Parameter binding (prevents SQL injection)
        - Result fetching
        - Error handling with rollback
        
        Args:
            query: SQL query string
            params: Tuple of parameters for parameterized query
            fetch_all: Return all rows as list of dicts
            fetch_one: Return single row as dict
            commit: Commit transaction after execution
        """
        # Make sure we're connected before executing
        if not self.connect():
            raise Exception("Veritabanı bağlantısı kurulamadı")  # Turkish: "Database connection failed"
        
        cursor = self._conn.cursor()
        try:
            # Execute with or without parameters
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Fetch results if requested
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
            # Rollback on error to maintain data integrity
            if self._conn:
                self._conn.rollback()
            print(f"[DB ERROR] Query failed: {e}")
            raise
        finally:
            cursor.close()
    
    # =========================================================================
    # USER AUTHENTICATION
    # =========================================================================
    
    def register_user(self, first_name, last_name, email, phone, password, id_number):
        """
        Register a new user in the system.
        
        Validation flow:
        1. Check if email already exists (UNIQUE constraint)
        2. Check if ID number already exists (UNIQUE constraint)
        3. Hash the password (never store plain text!)
        4. Insert the user
        
        Returns: (success: bool, message: str, user_id: int or None)
        """
        try:
            # Step 1: Check for duplicate email
            existing = self._execute(
                "SELECT UserID FROM Users WHERE Email = ?",
                (email,), fetch_one=True
            )
            if existing:
                return False, "Bu e-posta adresi zaten kayıtlı", None  # "This email is already registered"
            
            # Step 2: Check for duplicate ID number
            existing = self._execute(
                "SELECT UserID FROM Users WHERE IDNumber = ?",
                (id_number,), fetch_one=True
            )
            if existing:
                return False, "Bu TC kimlik numarası zaten kayıtlı", None  # "This ID number is already registered"
            
            # Step 3: Hash the password using SHA256
            password_hash = hash_password(password)
            
            # Step 4: Insert the new user
            # OUTPUT INSERTED.UserID gives us the auto-generated ID immediately
            query = """
                INSERT INTO Users (FirstName, LastName, Email, Phone, PasswordHash, IDNumber, Role, IsActive, CreditBalance, CreatedAt)
                OUTPUT INSERTED.UserID
                VALUES (?, ?, ?, ?, ?, ?, 'User', 1, 0, GETDATE())
            """
            result = self._execute(
                query, 
                (first_name, last_name, email, phone, password_hash, id_number), 
                fetch_one=True
            )
            self._conn.commit()
            
            return True, "Kayıt başarılı!", result['UserID'] if result else None  # "Registration successful!"
            
        except Exception as e:
            return False, f"Kayıt hatası: {str(e)}", None  # "Registration error"
    
    def login_user(self, email, password):
        """
        Login a user (both regular users and system admins).
        
        Security notes:
        - We hash the password and compare hashes, never plain text
        - We check IsActive to allow account suspension feature
        - We return role to determine redirect (user vs admin panel)
        
        Returns: (success: bool, message: str, user_data: dict or None)
        """
        try:
            password_hash = hash_password(password)
            
            # Query allows both User and SystemAdmin roles to login
            query = """
                SELECT UserID, FirstName, LastName, Email, Phone, CreditBalance, Role
                FROM Users 
                WHERE Email = ? AND PasswordHash = ? AND IsActive = 1
            """
            user = self._execute(query, (email, password_hash), fetch_one=True)
            
            if user:
                # Update last login time (good for tracking/security)
                self._execute(
                    "UPDATE Users SET LastLoginAt = GETDATE() WHERE UserID = ?",
                    (user['UserID'],), commit=True
                )
                
                return True, "Giriş başarılı!", {  # "Login successful!"
                    'user_id': user['UserID'],
                    'first_name': user['FirstName'],
                    'last_name': user['LastName'],
                    'email': user['Email'],
                    'phone': user['Phone'],
                    'credit_balance': float(user['CreditBalance'] or 0),
                    'role': user['Role']
                }
            
            return False, "Geçersiz e-posta veya şifre", None  # "Invalid email or password"
            
        except Exception as e:
            return False, f"Giriş hatası: {str(e)}", None  # "Login error"
    
    def login_firm_admin(self, email, password):
        """
        Login a firm admin (company staff who manage trips).
        
        Firm admins have different privileges than regular users:
        - They can create/edit trips for their company
        - They can view their company's sales statistics
        """
        try:
            password_hash = hash_password(password)
            
            # Join with Companies to get company name for display
            query = """
                SELECT fa.FirmAdminID, fa.CompanyID, fa.FirstName, fa.LastName, fa.Email, c.CompanyName
                FROM FirmAdmins fa
                INNER JOIN Companies c ON fa.CompanyID = c.CompanyID
                WHERE fa.Email = ? AND fa.PasswordHash = ? AND fa.IsActive = 1 AND c.IsActive = 1
            """
            admin = self._execute(query, (email, password_hash), fetch_one=True)
            
            if admin:
                # Update last login
                self._execute(
                    "UPDATE FirmAdmins SET LastLoginAt = GETDATE() WHERE FirmAdminID = ?",
                    (admin['FirmAdminID'],), commit=True
                )
                
                return True, "Giriş başarılı!", {
                    'admin_id': admin['FirmAdminID'],
                    'company_id': admin['CompanyID'],
                    'first_name': admin['FirstName'],
                    'last_name': admin['LastName'],
                    'email': admin['Email'],
                    'company_name': admin['CompanyName']
                }
            
            return False, "Geçersiz kimlik bilgileri", None  # "Invalid credentials"
            
        except Exception as e:
            return False, f"Giriş hatası: {str(e)}", None
    
    def login_system_admin(self, email, password):
        """Login a system admin (full platform access)"""
        try:
            password_hash = hash_password(password)
            
            query = """
                SELECT UserID, FirstName, LastName, Email, Role
                FROM Users 
                WHERE Email = ? AND PasswordHash = ? AND IsActive = 1 AND Role = 'SystemAdmin'
            """
            admin = self._execute(query, (email, password_hash), fetch_one=True)
            
            if admin:
                return True, "Giriş başarılı!", {
                    'admin_id': admin['UserID'],
                    'first_name': admin['FirstName'],
                    'last_name': admin['LastName'],
                    'email': admin['Email'],
                    'role': admin['Role']
                }
            
            return False, "Geçersiz kimlik bilgileri", None
            
        except Exception as e:
            return False, f"Giriş hatası: {str(e)}", None
    
    # =========================================================================
    # USER PROFILE
    # =========================================================================
    
    def get_user_profile(self, user_id):
        """
        Get user profile data for display.
        Used in session refresh and profile page.
        """
        if not user_id:
            return None
            
        try:
            query = """
                SELECT UserID, FirstName, LastName, Email, Phone, CreditBalance, Role, CreatedAt
                FROM Users WHERE UserID = ? AND IsActive = 1
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
            
        except Exception as e:
            print(f"[DB ERROR] Get profile failed: {e}")
            return None
    
    def update_user_profile(self, user_id, **kwargs):
        """
        Update user profile fields.
        Only updates fields that are provided (not None/empty).
        """
        if not user_id:
            return False, "Kullanıcı bulunamadı"  # "User not found"
            
        try:
            updates = []
            params = []
            
            # Build dynamic UPDATE query based on provided fields
            if kwargs.get('first_name'):
                updates.append("FirstName = ?")
                params.append(kwargs['first_name'])
            if kwargs.get('last_name'):
                updates.append("LastName = ?")
                params.append(kwargs['last_name'])
            if kwargs.get('phone'):
                updates.append("Phone = ?")
                params.append(kwargs['phone'])
            if kwargs.get('address'):
                updates.append("Address = ?")
                params.append(kwargs['address'])
            
            if not updates:
                return False, "Güncellenecek alan yok"  # "No fields to update"
            
            # Always update UpdatedAt timestamp
            updates.append("UpdatedAt = GETDATE()")
            params.append(user_id)
            
            query = f"UPDATE Users SET {', '.join(updates)} WHERE UserID = ?"
            self._execute(query, tuple(params), commit=True)
            
            return True, "Profil güncellendi"  # "Profile updated"
            
        except Exception as e:
            return False, f"Güncelleme hatası: {str(e)}"  # "Update error"
    
    # =========================================================================
    # CITIES
    # =========================================================================
    
    def get_all_cities(self):
        """
        Get all active cities for dropdowns.
        Ordered alphabetically for better UX.
        """
        try:
            query = "SELECT CityID, CityName FROM Cities WHERE IsActive = 1 ORDER BY CityName"
            cities = self._execute(query, fetch_all=True)
            return [{'city_id': c['CityID'], 'city_name': c['CityName']} for c in cities]
        except Exception as e:
            print(f"[DB ERROR] Get cities failed: {e}")
            return []
    
    # =========================================================================
    # TRIPS (Using Stored Procedures)
    # =========================================================================
    
    def search_trips(self, departure_city_id, arrival_city_id, travel_date, sort_by='DepartureTime', sort_order='ASC'):
        """
        Search trips using sp_SearchTrips stored procedure.
        
        WHY STORED PROCEDURE?
        The search involves multiple JOINs and filtering logic.
        Using SP keeps this complex query in the database layer,
        making it easier to optimize and modify without touching app code.
        """
        try:
            # Call the stored procedure with parameters
            query = "EXEC sp_SearchTrips @DepartureCityID=?, @ArrivalCityID=?, @DepartureDate=?, @SortBy=?, @SortOrder=?"
            trips = self._execute(
                query, 
                (departure_city_id, arrival_city_id, travel_date, sort_by, sort_order), 
                fetch_all=True
            )
            
            # Transform results to consistent format for frontend
            result = []
            for t in trips:
                result.append({
                    'TripID': t.get('TripID'),
                    'TripCode': t.get('TripCode'),
                    'CompanyName': t.get('CompanyName'),
                    'CompanyRating': float(t.get('CompanyRating') or 0),
                    'DepartureCity': t.get('DepartureCity'),
                    'ArrivalCity': t.get('ArrivalCity'),
                    'DepartureDate': str(t.get('DepartureDate', '')),
                    'DepartureTime': str(t.get('DepartureTime', '')),
                    'ArrivalTime': str(t.get('ArrivalTime', '')),
                    'DurationMinutes': t.get('DurationMinutes', 0),
                    'Price': float(t.get('Price', 0)),
                    'AvailableSeats': t.get('AvailableSeats', 0),
                    'TotalSeats': t.get('TotalSeats', 40),
                    'HasWifi': bool(t.get('HasWifi')),
                    'HasRefreshments': bool(t.get('HasRefreshments')),
                    'HasTV': bool(t.get('HasTV')),
                    'HasPowerOutlet': bool(t.get('HasPowerOutlet')),
                    'HasEntertainment': bool(t.get('HasEntertainment'))
                })
            
            return result
            
        except Exception as e:
            print(f"[DB ERROR] Search trips failed: {e}")
            return []
    
    def get_trip_details(self, trip_id):
        """
        Get detailed information for a single trip.
        Used on the seat selection page.
        """
        if not trip_id:
            return None
            
        try:
            query = """
                SELECT 
                    t.TripID, t.TripCode, t.Price, t.DepartureTime, t.ArrivalTime, 
                    t.DurationMinutes, t.DepartureDate, t.AvailableSeats, t.Status,
                    c.CompanyName, c.Rating as CompanyRating,
                    dc.CityName as DepartureCity, ac.CityName as ArrivalCity,
                    b.TotalSeats, b.HasWifi, b.HasRefreshments, b.HasTV, 
                    b.HasPowerOutlet, b.HasEntertainment
                FROM Trips t
                INNER JOIN Buses b ON t.BusID = b.BusID
                INNER JOIN Companies c ON b.CompanyID = c.CompanyID
                INNER JOIN Cities dc ON t.DepartureCityID = dc.CityID
                INNER JOIN Cities ac ON t.ArrivalCityID = ac.CityID
                WHERE t.TripID = ?
            """
            trip = self._execute(query, (trip_id,), fetch_one=True)
            
            if trip:
                return {
                    'TripID': trip['TripID'],
                    'TripCode': trip['TripCode'],
                    'CompanyName': trip['CompanyName'],
                    'CompanyRating': float(trip['CompanyRating'] or 0),
                    'DepartureCity': trip['DepartureCity'],
                    'ArrivalCity': trip['ArrivalCity'],
                    'DepartureDate': str(trip['DepartureDate']),
                    'DepartureTime': str(trip['DepartureTime']),
                    'ArrivalTime': str(trip['ArrivalTime']),
                    'DurationMinutes': trip['DurationMinutes'],
                    'Price': float(trip['Price']),
                    'AvailableSeats': trip['AvailableSeats'],
                    'TotalSeats': trip['TotalSeats'],
                    'Status': trip['Status'],
                    'HasWifi': bool(trip['HasWifi']),
                    'HasRefreshments': bool(trip['HasRefreshments']),
                    'HasTV': bool(trip['HasTV']),
                    'HasPowerOutlet': bool(trip['HasPowerOutlet']),
                    'HasEntertainment': bool(trip['HasEntertainment'])
                }
            return None
            
        except Exception as e:
            print(f"[DB ERROR] Get trip details failed: {e}")
            return None
    
    def get_trip_seat_status(self, trip_id):
        """
        Get seat status for a trip using sp_GetTripSeatStatus.
        
        WHY STORED PROCEDURE?
        This query needs to:
        1. Get all seats for the bus assigned to this trip
        2. Check which seats are already booked (via TicketSeats)
        3. Only consider active/completed tickets (not cancelled)
        
        The SP encapsulates this complex logic and ensures consistency.
        """
        if not trip_id:
            return []
            
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
            print(f"[DB ERROR] Get seat status failed: {e}")
            return []
    
    # =========================================================================
    # TICKETS (Using Stored Procedures)
    # =========================================================================
    
    def purchase_ticket(self, user_id, trip_id, seat_ids, passenger_names, coupon_code=None, use_credit=True):
        """
        Purchase ticket(s) using sp_PurchaseTicket stored procedure.
        
        THIS IS THE MOST IMPORTANT FUNCTION IN THE SYSTEM!
        
        WHY STORED PROCEDURE WITH TRANSACTION?
        The ticket purchase involves multiple operations that MUST succeed together:
        1. Validate trip is still available
        2. Check seats aren't already booked (prevent double-booking)
        3. Validate coupon if provided
        4. Calculate final price with discount
        5. Check user has enough credit
        6. Create ticket record
        7. Create seat assignments (TicketSeats)
        8. Update available seat count on trip
        9. Deduct money from user
        10. Record payment
        11. Mark coupon as used
        
        If ANY step fails, ALL changes are rolled back (ACID compliance).
        This prevents issues like:
        - User charged but ticket not created
        - Seat shown as available but already sold
        - Coupon used but discount not applied
        
        Returns: (success: bool, message: str, ticket_id: int or None)
        """
        if not user_id or not trip_id or not seat_ids or not passenger_names:
            return False, "Eksik bilgi", None  # "Missing information"
        
        try:
            # Convert lists to comma-separated strings for the SP
            # The SP uses STRING_SPLIT to parse these
            seat_ids_str = ','.join(map(str, seat_ids))
            passenger_names_str = '|'.join(passenger_names)  # Use | as separator (names might have commas)
            
            query = "EXEC sp_PurchaseTicket @UserID=?, @TripID=?, @SeatIDs=?, @PassengerNames=?, @CouponCode=?"
            
            # Ensure connection is established
            if not self.connect():
                return False, "Veritabanı bağlantı hatası", None
            
            cursor = self._conn.cursor()
            cursor.execute(query, (user_id, trip_id, seat_ids_str, passenger_names_str, coupon_code or ''))
            
            # SP returns: Success (bit), Message (nvarchar), TicketID (int)
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = bool(row[0])  # Convert bit to boolean
                message = row[1]
                ticket_id = row[2] if len(row) > 2 else None
                return success, message, ticket_id
            
            return False, "Bilet satın alma başarısız", None  # "Ticket purchase failed"
            
        except Exception as e:
            # Always rollback on error
            if self._conn:
                try:
                    self._conn.rollback()
                except:
                    pass
            print(f"[DB ERROR] Purchase failed: {e}")
            return False, f"Satın alma hatası: {str(e)}", None  # "Purchase error"
    
    def get_user_tickets(self, user_id, status_filter=None):
        """
        Get user's tickets using sp_GetUserTickets.
        Can filter by status (Active, Completed, Cancelled).
        """
        if not user_id:
            return []
            
        try:
            query = "EXEC sp_GetUserTickets @UserID=?, @StatusFilter=?"
            tickets = self._execute(query, (user_id, status_filter or ''), fetch_all=True)
            
            result = []
            for t in tickets:
                result.append({
                    'TicketID': t.get('TicketID'),
                    'TicketCode': t.get('TicketCode'),
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
                    'PurchaseDate': str(t.get('PurchaseDate', ''))
                })
            
            return result
            
        except Exception as e:
            print(f"[DB ERROR] Get tickets failed: {e}")
            return []
    
    def get_ticket_details(self, ticket_id, user_id):
        """
        Get ticket details for a specific user.
        User ID check ensures users can only see their own tickets.
        """
        if not ticket_id or not user_id:
            return None
            
        try:
            query = """
                SELECT 
                    tk.TicketID, tk.TicketCode, tk.TotalPrice, tk.DiscountAmount, 
                    tk.FinalPrice, tk.Status, tk.PurchaseDate,
                    tr.DepartureDate, tr.DepartureTime, tr.ArrivalTime, tr.DurationMinutes, tr.Price,
                    c.CompanyName, dc.CityName as DepartureCity, ac.CityName as ArrivalCity,
                    STRING_AGG(CAST(s.SeatNumber AS NVARCHAR), ', ') as SeatNumbers,
                    STRING_AGG(ts.PassengerName, ', ') as PassengerNames
                FROM Tickets tk
                INNER JOIN Trips tr ON tk.TripID = tr.TripID
                INNER JOIN Buses b ON tr.BusID = b.BusID
                INNER JOIN Companies c ON b.CompanyID = c.CompanyID
                INNER JOIN Cities dc ON tr.DepartureCityID = dc.CityID
                INNER JOIN Cities ac ON tr.ArrivalCityID = ac.CityID
                LEFT JOIN TicketSeats ts ON tk.TicketID = ts.TicketID
                LEFT JOIN Seats s ON ts.SeatID = s.SeatID
                WHERE tk.TicketID = ? AND tk.UserID = ?
                GROUP BY tk.TicketID, tk.TicketCode, tk.TotalPrice, tk.DiscountAmount,
                         tk.FinalPrice, tk.Status, tk.PurchaseDate,
                         tr.DepartureDate, tr.DepartureTime, tr.ArrivalTime, tr.DurationMinutes, tr.Price,
                         c.CompanyName, dc.CityName, ac.CityName
            """
            return self._execute(query, (ticket_id, user_id), fetch_one=True)
            
        except Exception as e:
            print(f"[DB ERROR] Get ticket details failed: {e}")
            return None
    
    def cancel_ticket(self, ticket_id, user_id):
        """
        Cancel a ticket using sp_CancelTicket.
        
        WHY STORED PROCEDURE?
        Cancellation involves:
        1. Verify ticket belongs to user and is cancellable
        2. Calculate refund amount
        3. Update ticket status
        4. Release seats (update trip's AvailableSeats)
        5. Refund credit to user
        6. Record refund payment
        
        All must succeed together (transaction).
        
        Returns: (success: bool, message: str)
        """
        if not ticket_id or not user_id:
            return False, "Eksik bilgi"
            
        try:
            query = "EXEC sp_CancelTicket @TicketID=?, @UserID=?"
            
            if not self.connect():
                return False, "Veritabanı bağlantı hatası"
            
            cursor = self._conn.cursor()
            cursor.execute(query, (ticket_id, user_id))
            
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = bool(row[0])
                message = row[1]
                return success, message
            
            return False, "İptal işlemi başarısız"  # "Cancellation failed"
            
        except Exception as e:
            if self._conn:
                try:
                    self._conn.rollback()
                except:
                    pass
            print(f"[DB ERROR] Cancel failed: {e}")
            return False, f"İptal hatası: {str(e)}"  # "Cancellation error"
    
    # =========================================================================
    # COUPONS
    # =========================================================================
    
    def validate_coupon(self, coupon_code, user_id):
        """
        Validate a coupon using sp_ValidateCoupon.
        
        Checks:
        - Coupon exists and is active
        - Coupon hasn't expired
        - Usage limit not reached
        - User hasn't already used this coupon
        
        Returns: (is_valid: bool, discount_rate: float, message: str)
        """
        if not coupon_code or not user_id:
            return False, 0, "Eksik bilgi"
            
        try:
            query = "EXEC sp_ValidateCoupon @CouponCode=?, @UserID=?"
            
            if not self.connect():
                return False, 0, "Veritabanı bağlantı hatası"
            
            cursor = self._conn.cursor()
            cursor.execute(query, (coupon_code, user_id))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                is_valid = bool(row[0])
                discount_rate = float(row[1]) if len(row) > 1 else 0
                message = row[2] if len(row) > 2 else ''
                return is_valid, discount_rate, message
            
            return False, 0, "Geçersiz kupon"  # "Invalid coupon"
            
        except Exception as e:
            print(f"[DB ERROR] Coupon validation failed: {e}")
            return False, 0, f"Doğrulama hatası: {str(e)}"  # "Validation error"
    
    def get_user_coupons(self, user_id):
        """
        Get available coupons for a user.
        Shows all coupons assigned to user via UserCoupons table.
        
        NOTE: Table is UserCoupons, not CouponUsage (fixed from original code)
        """
        if not user_id:
            return []
            
        try:
            # Using UserCoupons table (correct table name from schema)
            query = """
                SELECT 
                    c.CouponID, c.CouponCode, c.DiscountRate, c.ExpiryDate, c.Description,
                    uc.IsUsed
                FROM UserCoupons uc
                INNER JOIN Coupons c ON uc.CouponID = c.CouponID
                WHERE uc.UserID = ? AND c.IsActive = 1
                ORDER BY c.ExpiryDate
            """
            coupons = self._execute(query, (user_id,), fetch_all=True)
            
            return [{
                'CouponID': c['CouponID'],
                'CouponCode': c['CouponCode'],
                'DiscountRate': float(c['DiscountRate']),
                'ExpiryDate': str(c['ExpiryDate']),
                'Description': c['Description'],
                'IsUsed': bool(c['IsUsed'])
            } for c in coupons]
            
        except Exception as e:
            print(f"[DB ERROR] Get coupons failed: {e}")
            return []
    
    def get_all_coupons(self):
        """
        Get all coupons (admin view).
        
        NOTE: Using correct column names from schema:
        - TimesUsed (not UsageCount)
        """
        try:
            query = """
                SELECT CouponID, CouponCode, DiscountRate, UsageLimit, TimesUsed, 
                       ExpiryDate, IsActive, Description, CreatedAt
                FROM Coupons 
                ORDER BY CreatedAt DESC
            """
            return self._execute(query, fetch_all=True)
            
        except Exception as e:
            print(f"[DB ERROR] Get all coupons failed: {e}")
            return []
    
    def create_coupon(self, coupon_code, discount_rate, usage_limit, expiry_date, description=''):
        """Create a new coupon (admin function)"""
        try:
            # Check if coupon code already exists
            existing = self._execute(
                "SELECT CouponID FROM Coupons WHERE CouponCode = ?",
                (coupon_code,), fetch_one=True
            )
            if existing:
                return False, "Bu kupon kodu zaten mevcut"  # "This coupon code already exists"
            
            query = """
                INSERT INTO Coupons (CouponCode, DiscountRate, UsageLimit, TimesUsed, ExpiryDate, IsActive, Description, CreatedAt)
                VALUES (?, ?, ?, 0, ?, 1, ?, GETDATE())
            """
            self._execute(query, (coupon_code, discount_rate, usage_limit, expiry_date, description), commit=True)
            return True, "Kupon oluşturuldu"  # "Coupon created"
            
        except Exception as e:
            return False, f"Hata: {str(e)}"  # "Error"
    
    # =========================================================================
    # CREDIT MANAGEMENT
    # =========================================================================
    
    def add_user_credit(self, user_id, amount, payment_method='CreditCard'):
        """
        Add credit to user account using sp_AddUserCredit.
        
        WHY STORED PROCEDURE?
        Credit operations need:
        1. Validate amount (positive, within limits)
        2. Update user balance
        3. Record payment for audit trail
        
        Returns: (success: bool, message: str)
        """
        if not user_id or not amount:
            return False, "Eksik bilgi"
            
        try:
            query = "EXEC sp_AddUserCredit @UserID=?, @Amount=?, @PaymentMethod=?"
            
            if not self.connect():
                return False, "Veritabanı bağlantı hatası"
            
            cursor = self._conn.cursor()
            cursor.execute(query, (user_id, amount, payment_method))
            
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = bool(row[0])
                message = row[1]
                return success, message
            
            return True, f"{amount} TL başarıyla eklendi"  # "TL added successfully"
            
        except Exception as e:
            if self._conn:
                try:
                    self._conn.rollback()
                except:
                    pass
            print(f"[DB ERROR] Add credit failed: {e}")
            return False, f"Hata: {str(e)}"
    
    def get_user_credit(self, user_id):
        """Get user's current credit balance"""
        if not user_id:
            return 0
            
        try:
            query = "SELECT CreditBalance FROM Users WHERE UserID = ?"
            result = self._execute(query, (user_id,), fetch_one=True)
            return float(result['CreditBalance']) if result else 0
            
        except Exception as e:
            print(f"[DB ERROR] Get credit failed: {e}")
            return 0
    
    def get_payment_history(self, user_id):
        """
        Get user's payment history.
        
        NOTE: Using correct column names from Payments table:
        - Status (not PaymentStatus)
        - CreatedAt (not PaymentDate)
        - PaymentType (for transaction type)
        """
        if not user_id:
            return []
            
        try:
            query = """
                SELECT PaymentID, Amount, PaymentMethod, Status, CreatedAt, PaymentType
                FROM Payments 
                WHERE UserID = ?
                ORDER BY CreatedAt DESC
            """
            return self._execute(query, (user_id,), fetch_all=True)
            
        except Exception as e:
            print(f"[DB ERROR] Get payment history failed: {e}")
            return []
    
    # =========================================================================
    # ADMIN DASHBOARD
    # =========================================================================
    
    def get_dashboard_stats(self, company_id=None):
        """
        Get dashboard statistics using sp_GetDashboardStats.
        Returns key metrics for admin panels.
        """
        try:
            query = "EXEC sp_GetDashboardStats @CompanyID=?"
            
            if not self.connect():
                return {}
            
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
            print(f"[DB ERROR] Dashboard stats failed: {e}")
            return {}
    
    def get_all_companies(self):
        """
        Get all companies (System Admin view).
        
        NOTE: Using correct column names from Companies table:
        - Email (not ContactEmail)
        - Phone (not ContactPhone)
        """
        try:
            query = """
                SELECT CompanyID, CompanyName, Email, Phone, Rating, TotalRatings, IsActive, CreatedAt
                FROM Companies 
                ORDER BY CompanyName
            """
            return self._execute(query, fetch_all=True)
            
        except Exception as e:
            print(f"[DB ERROR] Get companies failed: {e}")
            return []
    
    def get_all_users(self):
        """Get all regular users (admin view)"""
        try:
            query = """
                SELECT UserID, FirstName, LastName, Email, Phone, CreditBalance, Role, IsActive, CreatedAt
                FROM Users 
                WHERE Role = 'User'
                ORDER BY CreatedAt DESC
            """
            return self._execute(query, fetch_all=True)
            
        except Exception as e:
            print(f"[DB ERROR] Get users failed: {e}")
            return []
    
    # =========================================================================
    # FIRM ADMIN OPERATIONS
    # =========================================================================
    
    def get_company_trips(self, company_id, status=None):
        """
        Get trips for a specific company (Firm Admin view).
        Used to show company's trips and their booking status.
        """
        if not company_id:
            return []
            
        try:
            query = """
                SELECT 
                    t.TripID, t.TripCode, t.DepartureDate, t.DepartureTime, t.ArrivalTime, 
                    t.DurationMinutes, t.Price, t.AvailableSeats, t.Status, 
                    b.PlateNumber, b.TotalSeats,
                    dc.CityName as DepartureCity, ac.CityName as ArrivalCity,
                    (b.TotalSeats - t.AvailableSeats) as SoldSeats
                FROM Trips t
                INNER JOIN Buses b ON t.BusID = b.BusID
                INNER JOIN Cities dc ON t.DepartureCityID = dc.CityID
                INNER JOIN Cities ac ON t.ArrivalCityID = ac.CityID
                WHERE b.CompanyID = ?
            """
            params = [company_id]
            
            if status:
                query += " AND t.Status = ?"
                params.append(status)
            
            query += " ORDER BY t.DepartureDate DESC, t.DepartureTime DESC"
            
            return self._execute(query, tuple(params), fetch_all=True)
            
        except Exception as e:
            print(f"[DB ERROR] Get company trips failed: {e}")
            return []
    
    def get_company_buses(self, company_id):
        """
        Get buses for a company.
        
        NOTE: Removed BusType column (doesn't exist in schema).
        The amenities (HasWifi, etc.) indicate bus type implicitly.
        """
        if not company_id:
            return []
            
        try:
            query = """
                SELECT BusID, PlateNumber, TotalSeats, HasWifi, HasRefreshments, 
                       HasTV, HasPowerOutlet, HasEntertainment, IsActive
                FROM Buses 
                WHERE CompanyID = ? AND IsActive = 1
                ORDER BY PlateNumber
            """
            return self._execute(query, (company_id,), fetch_all=True)
            
        except Exception as e:
            print(f"[DB ERROR] Get buses failed: {e}")
            return []
    
    def create_trip(self, bus_id, departure_city_id, arrival_city_id, departure_date, 
                    departure_time, arrival_time, duration_minutes, price, created_by_admin_id):
        """
        Create a new trip.
        
        NOTE: The original code called sp_CreateTrip which doesn't exist.
        We'll use a direct INSERT instead with proper validation.
        
        Returns: (success: bool, message: str, trip_id: int or None)
        """
        try:
            # Validate bus exists and get seat count
            bus = self._execute(
                "SELECT BusID, TotalSeats, CompanyID FROM Buses WHERE BusID = ? AND IsActive = 1",
                (bus_id,), fetch_one=True
            )
            if not bus:
                return False, "Otobüs bulunamadı", None  # "Bus not found"
            
            # Validate cities are different
            if departure_city_id == arrival_city_id:
                return False, "Kalkış ve varış şehri aynı olamaz", None  # "Departure and arrival city cannot be same"
            
            # Generate trip code
            trip_code = f"TRP-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M%S')}"
            
            # Insert the trip
            query = """
                INSERT INTO Trips (
                    TripCode, BusID, DepartureCityID, ArrivalCityID, 
                    DepartureDate, DepartureTime, ArrivalTime, DurationMinutes, 
                    Price, AvailableSeats, Status, CreatedAt
                )
                OUTPUT INSERTED.TripID
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', GETDATE())
            """
            result = self._execute(
                query,
                (trip_code, bus_id, departure_city_id, arrival_city_id,
                 departure_date, departure_time, arrival_time, duration_minutes,
                 price, bus['TotalSeats']),
                fetch_one=True
            )
            self._conn.commit()
            
            if result:
                return True, f"Sefer oluşturuldu: {trip_code}", result['TripID']  # "Trip created"
            
            return False, "Sefer oluşturulamadı", None  # "Could not create trip"
            
        except Exception as e:
            if self._conn:
                try:
                    self._conn.rollback()
                except:
                    pass
            print(f"[DB ERROR] Create trip failed: {e}")
            return False, f"Hata: {str(e)}", None
