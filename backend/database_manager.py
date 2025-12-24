# =============================================================================
# BUS TICKET SYSTEM - Database Manager
# Database Systems Course Project
# =============================================================================
# 
# This file handles all database operations.
# I used pyodbc library to connect to MSSQL Server.
#
# SINGLETON PATTERN:
# We only need ONE database connection for whole app.
# Creating many connections wastes resources and can cause problems.
# Singleton makes sure only one instance of this class exists.
#
# WHY STORED PROCEDURES?
# Teacher said use stored procedures for complex operations.
# Benefits:
#   - Transaction control (ACID)
#   - Business logic stays in database
#   - Better performance (query plan cached)
#   - Security (less SQL injection risk)
# =============================================================================

import pyodbc
from datetime import datetime, date
from config import Config
from utils import hash_password


class DatabaseManager:
    """
    Database manager with Singleton pattern.
    
    Only one instance created, all parts of app use same connection.
    This is better than creating new connection for each request.
    """
    _instance = None
    
    def __new__(cls):
        # Singleton: if instance exists, return it. Otherwise create new one.
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize_connection_string()
            cls._instance._conn = None
        return cls._instance
    
    def _initialize_connection_string(self):
        """
        Build connection string based on auth method.
        Windows Auth: no password needed (uses Windows login)
        SQL Auth: needs username and password
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
    # CONNECTION METHODS
    # =========================================================================
    
    def connect(self):
        """
        Connect to database.
        Returns True if connected, False if failed.
        """
        try:
            if self._conn is None:
                # autocommit=False means we control transactions manually
                # This is important for ACID - we decide when to commit or rollback
                self._conn = pyodbc.connect(self._connection_string, autocommit=False)
            return True
        except pyodbc.Error as e:
            print(f"[DB ERROR] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close connection safely"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass  # Ignore errors on close
            finally:
                self._conn = None
    
    def test_connection(self):
        """Test if database is reachable - used at app startup"""
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
        Main query execution method.
        
        All other methods use this one.
        
        Why parameterized queries (? placeholders)?
        PREVENTS SQL INJECTION! This is very important for security.
        Instead of putting values directly in query, we use ? and pass values separately.
        
        Example:
          BAD:  "SELECT * FROM Users WHERE Email = '" + email + "'"
          GOOD: "SELECT * FROM Users WHERE Email = ?", (email,)
        
        The bad way allows hackers to inject SQL code.
        The good way treats input as data, not code.
        """
        if not self.connect():
            raise Exception("Database connection failed")
        
        cursor = self._conn.cursor()
        try:
            # Execute with or without parameters
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Return results based on what caller needs
            if fetch_all:
                # Get column names and all rows, return as list of dicts
                columns = [column[0] for column in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            elif fetch_one:
                # Get column names and one row, return as dict
                columns = [column[0] for column in cursor.description] if cursor.description else []
                row = cursor.fetchone()
                return dict(zip(columns, row)) if row else None
            
            if commit:
                self._conn.commit()
            
            return cursor.rowcount
            
        except pyodbc.Error as e:
            # ROLLBACK on error - this is part of ACID
            # If something fails, undo all changes from this transaction
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
        Register new user.
        
        Steps:
        1. Check email not already used (UNIQUE constraint)
        2. Check ID number not already used (UNIQUE constraint)
        3. Hash password (NEVER store plain text!)
        4. Insert user with default values
        
        Returns tuple: (success, message, user_id)
        """
        try:
            # Check for duplicate email
            existing = self._execute(
                "SELECT UserID FROM Users WHERE Email = ?",
                (email,), fetch_one=True
            )
            if existing:
                return False, "This email is already registered", None
            
            # Check for duplicate ID number
            existing = self._execute(
                "SELECT UserID FROM Users WHERE IDNumber = ?",
                (id_number,), fetch_one=True
            )
            if existing:
                return False, "This ID number is already registered", None
            
            # Hash password using SHA256
            # We NEVER store plain passwords - if database is hacked,
            # attacker cant see real passwords
            password_hash = hash_password(password)
            
            # Insert user
            # OUTPUT INSERTED.UserID returns the auto-generated ID immediately
            # This is better than doing separate SELECT to get ID
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
            
            return True, "Registration successful!", result['UserID'] if result else None
            
        except Exception as e:
            return False, f"Registration error: {str(e)}", None
    
    def login_user(self, email, password):
        """
        Login user.
        
        Security:
        - Hash entered password and compare with stored hash
        - Check IsActive (allows us to ban/suspend users)
        - Return role to know if regular user or admin
        """
        try:
            password_hash = hash_password(password)
            
            query = """
                SELECT UserID, FirstName, LastName, Email, Phone, CreditBalance, Role
                FROM Users 
                WHERE Email = ? AND PasswordHash = ? AND IsActive = 1
            """
            user = self._execute(query, (email, password_hash), fetch_one=True)
            
            if user:
                # Update last login time for security tracking
                self._execute(
                    "UPDATE Users SET LastLoginAt = GETDATE() WHERE UserID = ?",
                    (user['UserID'],), commit=True
                )
                
                return True, "Login successful!", {
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
        """
        Login firm admin (company staff).
        Firm admins manage trips for their company.
        """
        try:
            password_hash = hash_password(password)
            
            # JOIN with Companies to get company name
            query = """
                SELECT fa.FirmAdminID, fa.CompanyID, fa.FirstName, fa.LastName, fa.Email, c.CompanyName
                FROM FirmAdmins fa
                INNER JOIN Companies c ON fa.CompanyID = c.CompanyID
                WHERE fa.Email = ? AND fa.PasswordHash = ? AND fa.IsActive = 1 AND c.IsActive = 1
            """
            admin = self._execute(query, (email, password_hash), fetch_one=True)
            
            if admin:
                self._execute(
                    "UPDATE FirmAdmins SET LastLoginAt = GETDATE() WHERE FirmAdminID = ?",
                    (admin['FirmAdminID'],), commit=True
                )
                
                return True, "Login successful!", {
                    'admin_id': admin['FirmAdminID'],
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
        """Login system admin (full platform access)"""
        try:
            password_hash = hash_password(password)
            
            query = """
                SELECT UserID, FirstName, LastName, Email, Role
                FROM Users 
                WHERE Email = ? AND PasswordHash = ? AND IsActive = 1 AND Role = 'SystemAdmin'
            """
            admin = self._execute(query, (email, password_hash), fetch_one=True)
            
            if admin:
                return True, "Login successful!", {
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
        Update user profile.
        Only updates fields that are provided.
        **kwargs lets us accept any fields without listing them all.
        """
        if not user_id:
            return False, "User not found"
            
        try:
            updates = []
            params = []
            
            # Build dynamic UPDATE query
            # Only add fields that were actually sent
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
                return False, "No fields to update"
            
            updates.append("UpdatedAt = GETDATE()")
            params.append(user_id)
            
            query = f"UPDATE Users SET {', '.join(updates)} WHERE UserID = ?"
            self._execute(query, tuple(params), commit=True)
            
            return True, "Profile updated"
            
        except Exception as e:
            return False, f"Update error: {str(e)}"
    
    # =========================================================================
    # CITIES
    # =========================================================================
    
    def get_all_cities(self):
        """Get all active cities for dropdowns"""
        try:
            query = "SELECT CityID, CityName FROM Cities WHERE IsActive = 1 ORDER BY CityName"
            cities = self._execute(query, fetch_all=True)
            return [{'city_id': c['CityID'], 'city_name': c['CityName']} for c in cities]
        except Exception as e:
            print(f"[DB ERROR] Get cities failed: {e}")
            return []
    
    # =========================================================================
    # TRIPS - Using Stored Procedures
    # =========================================================================
    
    def search_trips(self, departure_city_id, arrival_city_id, travel_date, sort_by='DepartureTime', sort_order='ASC'):
        """
        Search trips using sp_SearchTrips stored procedure.
        
        Why stored procedure here?
        Search query has many JOINs and filters.
        Keeping it in database:
          - Easier to optimize (DBA can tune it)
          - Query plan is cached (faster)
          - Can change query without redeploying app
        """
        try:
            query = "EXEC sp_SearchTrips @DepartureCityID=?, @ArrivalCityID=?, @DepartureDate=?, @SortBy=?, @SortOrder=?"
            trips = self._execute(
                query, 
                (departure_city_id, arrival_city_id, travel_date, sort_by, sort_order), 
                fetch_all=True
            )
            
            # Transform to consistent format for frontend
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
        """Get single trip details for seat selection page"""
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
        Get seat status for trip using sp_GetTripSeatStatus.
        
        This query needs to:
        1. Get all seats from the bus
        2. Check which are already booked (from TicketSeats)
        3. Only count active tickets (not cancelled)
        
        Stored procedure handles this complex logic.
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
    # TICKETS - The main transaction!
    # =========================================================================
    
    def purchase_ticket(self, user_id, trip_id, seat_ids, passenger_names, coupon_code=None, use_credit=True):
        """
        Purchase ticket using sp_PurchaseTicket.
        
        THIS IS THE MOST IMPORTANT FUNCTION!
        
        Why stored procedure with TRANSACTION?
        Buying ticket needs many steps that MUST all succeed together:
        
        1. Check trip is available
        2. Check seats not already booked (prevent double booking!)
        3. Validate coupon if used
        4. Calculate price with discount
        5. Check user has enough money
        6. Create ticket record
        7. Create seat assignments in TicketSeats
        8. Update AvailableSeats on trip
        9. Deduct money from user
        10. Record payment
        11. Mark coupon as used
        
        If ANY step fails, ALL changes rollback.
        This is ACID compliance - we learned in class:
          A - Atomicity: all or nothing
          C - Consistency: database stays valid
          I - Isolation: transactions dont interfere
          D - Durability: committed changes persist
        
        Example problem without transaction:
        User pays but ticket not created = user loses money!
        
        With transaction, if ticket creation fails, payment also rolls back.
        """
        if not user_id or not trip_id or not seat_ids or not passenger_names:
            return False, "Missing information", None
        
        try:
            # Convert lists to strings for stored procedure
            # SP uses STRING_SPLIT to parse these
            seat_ids_str = ','.join(map(str, seat_ids))
            passenger_names_str = '|'.join(passenger_names)  # | because names might have commas
            
            query = "EXEC sp_PurchaseTicket @UserID=?, @TripID=?, @SeatIDs=?, @PassengerNames=?, @CouponCode=?"
            
            if not self.connect():
                return False, "Database connection error", None
            
            cursor = self._conn.cursor()
            cursor.execute(query, (user_id, trip_id, seat_ids_str, passenger_names_str, coupon_code or ''))
            
            # SP returns: Success (bit), Message (nvarchar), TicketID (int)
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = bool(row[0])
                message = row[1]
                ticket_id = row[2] if len(row) > 2 else None
                return success, message, ticket_id
            
            return False, "Ticket purchase failed", None
            
        except Exception as e:
            # ALWAYS rollback on error
            if self._conn:
                try:
                    self._conn.rollback()
                except:
                    pass
            print(f"[DB ERROR] Purchase failed: {e}")
            return False, f"Purchase error: {str(e)}", None
    
    def get_user_tickets(self, user_id, status_filter=None):
        """Get user's tickets, can filter by status"""
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
        Get ticket details.
        User ID check makes sure users can only see their own tickets.
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
        Cancel ticket using sp_CancelTicket.
        
        Similar to purchase - needs transaction because:
        1. Check ticket belongs to user
        2. Check ticket is cancellable (not already cancelled, trip not passed)
        3. Calculate refund
        4. Update ticket status
        5. Release seats (update trip AvailableSeats)
        6. Refund money to user
        7. Record refund payment
        
        All must succeed or all fail.
        """
        if not ticket_id or not user_id:
            return False, "Missing information"
            
        try:
            query = "EXEC sp_CancelTicket @TicketID=?, @UserID=?"
            
            if not self.connect():
                return False, "Database connection error"
            
            cursor = self._conn.cursor()
            cursor.execute(query, (ticket_id, user_id))
            
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = bool(row[0])
                message = row[1]
                return success, message
            
            return False, "Cancellation failed"
            
        except Exception as e:
            if self._conn:
                try:
                    self._conn.rollback()
                except:
                    pass
            print(f"[DB ERROR] Cancel failed: {e}")
            return False, f"Cancel error: {str(e)}"
    
    # =========================================================================
    # COUPONS
    # =========================================================================
    
    def validate_coupon(self, coupon_code, user_id):
        """
        Validate coupon using sp_ValidateCoupon.
        
        Checks:
        - Coupon exists and active
        - Not expired
        - Usage limit not reached
        - User hasnt used it before
        """
        if not coupon_code or not user_id:
            return False, 0, "Missing information"
            
        try:
            query = "EXEC sp_ValidateCoupon @CouponCode=?, @UserID=?"
            
            if not self.connect():
                return False, 0, "Database connection error"
            
            cursor = self._conn.cursor()
            cursor.execute(query, (coupon_code, user_id))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                is_valid = bool(row[0])
                discount_rate = float(row[1]) if len(row) > 1 else 0
                message = row[2] if len(row) > 2 else ''
                return is_valid, discount_rate, message
            
            return False, 0, "Invalid coupon"
            
        except Exception as e:
            print(f"[DB ERROR] Coupon validation failed: {e}")
            return False, 0, f"Validation error: {str(e)}"
    
    def get_user_coupons(self, user_id):
        """Get coupons assigned to user"""
        if not user_id:
            return []
            
        try:
            # UserCoupons table links users to their coupons
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
        """Get all coupons for admin view"""
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
        """Create new coupon (admin function)"""
        try:
            # Check if code already exists
            existing = self._execute(
                "SELECT CouponID FROM Coupons WHERE CouponCode = ?",
                (coupon_code,), fetch_one=True
            )
            if existing:
                return False, "This coupon code already exists"
            
            query = """
                INSERT INTO Coupons (CouponCode, DiscountRate, UsageLimit, TimesUsed, ExpiryDate, IsActive, Description, CreatedAt)
                VALUES (?, ?, ?, 0, ?, 1, ?, GETDATE())
            """
            self._execute(query, (coupon_code, discount_rate, usage_limit, expiry_date, description), commit=True)
            return True, "Coupon created"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # =========================================================================
    # CREDIT MANAGEMENT
    # =========================================================================
    
    def add_user_credit(self, user_id, amount, payment_method='CreditCard'):
        """
        Add credit to user using sp_AddUserCredit.
        
        Steps:
        1. Validate amount
        2. Update user balance
        3. Record payment for history/audit
        """
        if not user_id or not amount:
            return False, "Missing information"
            
        try:
            query = "EXEC sp_AddUserCredit @UserID=?, @Amount=?, @PaymentMethod=?"
            
            if not self.connect():
                return False, "Database connection error"
            
            cursor = self._conn.cursor()
            cursor.execute(query, (user_id, amount, payment_method))
            
            row = cursor.fetchone()
            self._conn.commit()
            cursor.close()
            
            if row:
                success = bool(row[0])
                message = row[1]
                return success, message
            
            return True, f"{amount} TL added successfully"
            
        except Exception as e:
            if self._conn:
                try:
                    self._conn.rollback()
                except:
                    pass
            print(f"[DB ERROR] Add credit failed: {e}")
            return False, f"Error: {str(e)}"
    
    def get_user_credit(self, user_id):
        """Get user's credit balance"""
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
        """Get user's payment history"""
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
    # ADMIN FUNCTIONS
    # =========================================================================
    
    def get_dashboard_stats(self, company_id=None):
        """Get dashboard stats using sp_GetDashboardStats"""
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
        """Get all companies for admin view"""
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
        """Get all regular users for admin view"""
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
    # FIRM ADMIN FUNCTIONS
    # =========================================================================
    
    def get_company_trips(self, company_id, status=None):
        """Get trips for a company"""
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
        """Get buses for a company"""
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
        Create new trip.
        Uses direct INSERT because sp_CreateTrip doesnt exist in our schema.
        """
        try:
            # Validate bus exists
            bus = self._execute(
                "SELECT BusID, TotalSeats, CompanyID FROM Buses WHERE BusID = ? AND IsActive = 1",
                (bus_id,), fetch_one=True
            )
            if not bus:
                return False, "Bus not found", None
            
            # Cities must be different
            if departure_city_id == arrival_city_id:
                return False, "Departure and arrival city cannot be same", None
            
            # Generate trip code
            trip_code = f"TRP-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M%S')}"
            
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
                return True, f"Trip created: {trip_code}", result['TripID']
            
            return False, "Could not create trip", None
            
        except Exception as e:
            if self._conn:
                try:
                    self._conn.rollback()
                except:
                    pass
            print(f"[DB ERROR] Create trip failed: {e}")
            return False, f"Error: {str(e)}", None
