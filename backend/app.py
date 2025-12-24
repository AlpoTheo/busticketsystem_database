# ============================================================================
# BUS TICKET SYSTEM - Flask API Application
# CENG 301 Database Systems Term Project
# ============================================================================
# 
# This is the main Flask application that provides REST API endpoints
# for the Bus Ticket System frontend.
#
# ARCHITECTURE OVERVIEW:
# Frontend (HTML/JS) <--HTTP--> Flask API (this file) <--ODBC--> MSSQL Database
#
# WHY FLASK?
# - Simple and lightweight (good for a term project)
# - Easy to understand routing (@app.route decorators)
# - Good documentation and community support
# - Works well with any database via Python libraries
#
# API DESIGN:
# - RESTful endpoints (GET for retrieval, POST for actions)
# - JSON responses with consistent format {success, message, data}
# - Session-based authentication (stored server-side)
# ============================================================================

import os
import sys
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
from utils import (
    validate_email, validate_phone, validate_id_number, 
    validate_password, format_currency, format_duration
)

# ============================================================================
# APP CONFIGURATION
# ============================================================================

app = Flask(__name__, static_folder='../frontend', static_url_path='')

# Secret key for session encryption - in production this would be an environment variable
app.secret_key = 'bus_ticket_system_secret_key_2025'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Enable CORS for all routes (allows frontend to make API calls)
# supports_credentials=True needed for session cookies
CORS(app, supports_credentials=True)

# Initialize database manager (Singleton - only one instance created)
db = DatabaseManager()


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================
# These are "decorators" - a Python feature that wraps functions
# We use them to check if user is logged in before accessing protected routes

def login_required(f):
    """
    Decorator to require login for routes.
    If user is not logged in, returns 401 Unauthorized.
    
    Usage:
        @app.route('/api/protected')
        @login_required
        def protected_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if any type of user is in session
        if 'user_id' not in session and 'admin_id' not in session:
            return jsonify({
                'success': False, 
                'message': 'Lütfen önce giriş yapın'  # "Please login first"
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin (system or firm) login.
    Returns 403 Forbidden if not an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({
                'success': False, 
                'message': 'Admin yetkisi gerekli'  # "Admin access required"
            }), 403
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# ERROR HANDLING HELPERS
# ============================================================================

def handle_db_error(operation_name):
    """
    Wrapper for database operations to provide consistent error handling.
    Logs error and returns user-friendly message.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                # Log the error for debugging
                print(f"[ERROR] {operation_name} failed: {str(e)}")
                # Return user-friendly error (don't expose technical details)
                return jsonify({
                    'success': False,
                    'message': 'Bir hata oluştu. Lütfen tekrar deneyin.'  # "An error occurred. Please try again."
                }), 500
        return wrapper
    return decorator


# ============================================================================
# STATIC FILE ROUTES (Serve HTML pages)
# ============================================================================

@app.route('/')
def index():
    """Serve main page"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (HTML, CSS, JS, images)"""
    return send_from_directory(app.static_folder, filename)


# ============================================================================
# AUTH API ROUTES
# ============================================================================

@app.route('/api/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Endpoint: POST /api/register
    
    Request JSON:
        {
            "first_name": "Ahmet",
            "last_name": "Yılmaz",
            "email": "ahmet@email.com",
            "phone": "0555 123 45 67",
            "password": "password123",
            "id_number": "12345678901"
        }
    
    Response JSON:
        {
            "success": true/false,
            "message": "...",
            "user_id": 123 (on success)
        }
    """
    try:
        data = request.get_json()
        
        # Null check - make sure we got JSON data
        if not data:
            return jsonify({
                'success': False, 
                'message': 'Geçersiz istek'  # "Invalid request"
            }), 400
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'phone', 'password', 'id_number']
        for field in required_fields:
            if not data.get(field) or not str(data.get(field)).strip():
                return jsonify({
                    'success': False, 
                    'message': f'{field} alanı gerekli'  # "field is required"
                }), 400
        
        # Validate email format
        is_valid, error_msg = validate_email(data['email'])
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Validate password strength
        is_valid, error_msg = validate_password(data['password'])
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Validate Turkish ID number format
        is_valid, error_msg = validate_id_number(data['id_number'])
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Register user in database
        success, message, user_id = db.register_user(
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            email=data['email'].strip().lower(),  # Normalize email to lowercase
            phone=data['phone'].strip(),
            password=data['password'],
            id_number=data['id_number'].strip()
        )
        
        if success:
            return jsonify({'success': True, 'message': message, 'user_id': user_id})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        print(f"[ERROR] Registration failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Kayıt işlemi başarısız'  # "Registration failed"
        }), 500


@app.route('/api/login', methods=['POST'])
def login():
    """
    Login user (handles both regular users, system admins, and firm admins).
    
    Endpoint: POST /api/login
    
    The system checks:
    1. First, tries to login as User/SystemAdmin (Users table)
    2. If that fails, tries FirmAdmin (FirmAdmins table)
    
    This allows all user types to use the same login form.
    """
    try:
        data = request.get_json()
        
        # Null check
        if not data:
            return jsonify({
                'success': False, 
                'message': 'Geçersiz istek'
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Basic validation
        if not email or not password:
            return jsonify({
                'success': False, 
                'message': 'E-posta ve şifre gerekli'  # "Email and password required"
            }), 400
        
        # STEP 1: Try to login as regular User or SystemAdmin
        success, message, user_data = db.login_user(email, password)
        
        if success and user_data:
            # Store user info in session
            session['user_id'] = user_data['user_id']
            session['user_data'] = user_data
            session.permanent = True  # Use the permanent session lifetime
            
            # Check role and set appropriate session data
            if user_data.get('role') == 'SystemAdmin':
                session['user_type'] = 'system_admin'
                session['admin_id'] = user_data['user_id']
            else:
                session['user_type'] = 'user'
            
            return jsonify({'success': True, 'message': message, 'user': user_data})
        
        # STEP 2: Try firm admin login as fallback
        success, message, admin_data = db.login_firm_admin(email, password)
        if success and admin_data:
            session['admin_id'] = admin_data['admin_id']
            session['user_type'] = 'firm_admin'
            session['company_id'] = admin_data['company_id']
            session['admin_data'] = admin_data
            session.permanent = True
            return jsonify({'success': True, 'message': message, 'user': admin_data})
        
        # Both attempts failed
        return jsonify({
            'success': False, 
            'message': 'Geçersiz e-posta veya şifre'  # "Invalid email or password"
        }), 401
        
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Giriş işlemi başarısız'  # "Login failed"
        }), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    """
    Logout current user by clearing session.
    
    Endpoint: POST /api/logout
    """
    session.clear()
    return jsonify({'success': True, 'message': 'Çıkış yapıldı'})  # "Logged out"


@app.route('/api/session', methods=['GET'])
def get_session():
    """
    Get current session info.
    
    Endpoint: GET /api/session
    
    Used by frontend to check if user is still logged in
    and get updated user data (like credit balance).
    """
    try:
        if 'user_id' in session:
            # Refresh user data from database (in case balance changed)
            user = db.get_user_profile(session['user_id'])
            if user:
                session['user_data'] = user
                return jsonify({
                    'logged_in': True,
                    'user_type': session.get('user_type', 'user'),
                    'user': user
                })
        
        if 'admin_id' in session:
            return jsonify({
                'logged_in': True,
                'user_type': session.get('user_type'),
                'admin': session.get('admin_data')
            })
        
        return jsonify({'logged_in': False})
        
    except Exception as e:
        print(f"[ERROR] Session check failed: {e}")
        return jsonify({'logged_in': False})


# ============================================================================
# CITY API ROUTES
# ============================================================================

@app.route('/api/cities', methods=['GET'])
def get_cities():
    """
    Get all active cities for dropdown selection.
    
    Endpoint: GET /api/cities
    
    This is a public endpoint (no login required) because
    we need to show cities on the home page search form.
    """
    try:
        cities = db.get_all_cities()
        return jsonify({'success': True, 'cities': cities})
    except Exception as e:
        print(f"[ERROR] Get cities failed: {e}")
        return jsonify({'success': False, 'cities': [], 'message': 'Şehirler yüklenemedi'})


# ============================================================================
# TRIP API ROUTES
# ============================================================================

@app.route('/api/trips/search', methods=['GET'])
def search_trips():
    """
    Search for available trips.
    
    Endpoint: GET /api/trips/search
    
    Query Parameters:
        - from: Departure city ID (required)
        - to: Arrival city ID (required)
        - date: Travel date YYYY-MM-DD (required)
        - sort_by: DepartureTime, Price, Duration (default: DepartureTime)
        - sort_order: ASC, DESC (default: ASC)
    
    Example: /api/trips/search?from=1&to=2&date=2025-12-25
    """
    try:
        # Get and validate parameters
        departure_city = request.args.get('from', type=int)
        arrival_city = request.args.get('to', type=int)
        travel_date_str = request.args.get('date')
        sort_by = request.args.get('sort_by', 'DepartureTime')
        sort_order = request.args.get('sort_order', 'ASC')
        
        # Validate required parameters
        if not all([departure_city, arrival_city, travel_date_str]):
            return jsonify({
                'success': False, 
                'message': 'Eksik parametre'  # "Missing parameters"
            }), 400
        
        # Parse and validate date
        try:
            travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Geçersiz tarih formatı. YYYY-MM-DD kullanın'  # "Invalid date format"
            }), 400
        
        # Check date is not in past
        if travel_date < datetime.now().date():
            return jsonify({
                'success': False,
                'message': 'Geçmiş tarih seçilemez'  # "Cannot select past date"
            }), 400
        
        # Search trips
        trips = db.search_trips(departure_city, arrival_city, travel_date, sort_by, sort_order)
        
        # Format prices and duration for display
        for trip in trips:
            trip['PriceFormatted'] = format_currency(trip.get('Price', 0))
            trip['DurationFormatted'] = format_duration(trip.get('DurationMinutes', 0))
        
        return jsonify({'success': True, 'trips': trips, 'count': len(trips)})
        
    except Exception as e:
        print(f"[ERROR] Trip search failed: {e}")
        return jsonify({
            'success': False, 
            'trips': [],
            'message': 'Sefer araması başarısız'  # "Trip search failed"
        })


@app.route('/api/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    """
    Get single trip details.
    
    Endpoint: GET /api/trips/<trip_id>
    
    Used on seat selection page to show trip information.
    """
    try:
        trip = db.get_trip_details(trip_id)
        
        if trip:
            trip['PriceFormatted'] = format_currency(trip.get('Price', 0))
            trip['DurationFormatted'] = format_duration(trip.get('DurationMinutes', 0))
            return jsonify({'success': True, 'trip': trip})
        
        return jsonify({
            'success': False, 
            'message': 'Sefer bulunamadı'  # "Trip not found"
        }), 404
        
    except Exception as e:
        print(f"[ERROR] Get trip failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Sefer bilgisi alınamadı'  # "Could not get trip info"
        }), 500


@app.route('/api/trips/<int:trip_id>/seats', methods=['GET'])
def get_trip_seats(trip_id):
    """
    Get seat availability for a trip.
    
    Endpoint: GET /api/trips/<trip_id>/seats
    
    Returns list of all seats with their status (Available/Occupied).
    This is used to render the seat selection grid.
    """
    try:
        seats = db.get_trip_seat_status(trip_id)
        return jsonify({'success': True, 'seats': seats})
    except Exception as e:
        print(f"[ERROR] Get seats failed: {e}")
        return jsonify({
            'success': False, 
            'seats': [],
            'message': 'Koltuk bilgisi alınamadı'  # "Could not get seat info"
        })


# ============================================================================
# TICKET API ROUTES
# ============================================================================

@app.route('/api/tickets/purchase', methods=['POST'])
@login_required
def purchase_ticket():
    """
    Purchase ticket(s).
    
    Endpoint: POST /api/tickets/purchase
    
    This is the MAIN TRANSACTION of the system!
    
    Request JSON:
        {
            "trip_id": 1,
            "seat_ids": [1, 2],              // List of seat IDs to book
            "passenger_names": ["Ahmet Y", "Fatma Y"],  // One name per seat
            "coupon_code": "DISCOUNT10"      // Optional discount coupon
        }
    
    The stored procedure handles:
    - Checking seat availability (prevents double-booking)
    - Validating coupon
    - Calculating price with discount
    - Checking user has enough credit
    - Creating ticket and seat records
    - Deducting credit from user
    - Recording payment
    
    All in a TRANSACTION (either all succeed or all fail).
    """
    try:
        # Only regular users can purchase tickets
        if session.get('user_type') != 'user':
            return jsonify({
                'success': False, 
                'message': 'Sadece kullanıcılar bilet alabilir'  # "Only users can buy tickets"
            }), 403
        
        data = request.get_json()
        
        # Null check
        if not data:
            return jsonify({'success': False, 'message': 'Geçersiz istek'}), 400
        
        # Extract and validate parameters
        trip_id = data.get('trip_id')
        seat_ids = data.get('seat_ids', [])
        passenger_names = data.get('passenger_names', [])
        coupon_code = data.get('coupon_code')
        
        # Basic validation
        if not trip_id:
            return jsonify({'success': False, 'message': 'Sefer seçilmedi'}), 400
        
        if not seat_ids or len(seat_ids) == 0:
            return jsonify({'success': False, 'message': 'Koltuk seçilmedi'}), 400
        
        if not passenger_names or len(passenger_names) == 0:
            return jsonify({'success': False, 'message': 'Yolcu adı gerekli'}), 400
        
        # Number of seats must match number of passengers
        if len(seat_ids) != len(passenger_names):
            return jsonify({
                'success': False, 
                'message': 'Koltuk ve yolcu sayısı eşleşmiyor'  # "Seat and passenger count don't match"
            }), 400
        
        # Maximum 5 seats per booking (business rule)
        if len(seat_ids) > 5:
            return jsonify({
                'success': False, 
                'message': 'Tek seferde en fazla 5 koltuk alınabilir'  # "Max 5 seats per booking"
            }), 400
        
        user_id = session['user_id']
        
        # Call the stored procedure for purchase
        success, message, ticket_id = db.purchase_ticket(
            user_id=user_id,
            trip_id=trip_id,
            seat_ids=seat_ids,
            passenger_names=passenger_names,
            coupon_code=coupon_code,
            use_credit=True
        )
        
        if success:
            # Refresh user data in session (credit balance changed)
            user = db.get_user_profile(user_id)
            if user:
                session['user_data'] = user
            
            return jsonify({
                'success': True, 
                'message': message, 
                'ticket_id': ticket_id,
                'new_credit_balance': user.get('credit_balance', 0) if user else 0
            })
        
        return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"[ERROR] Ticket purchase failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Bilet satın alma başarısız'  # "Ticket purchase failed"
        }), 500


@app.route('/api/tickets', methods=['GET'])
@login_required
def get_user_tickets():
    """
    Get current user's tickets.
    
    Endpoint: GET /api/tickets
    
    Query Parameters:
        - status: Filter by status (Active, Completed, Cancelled) - optional
    """
    try:
        if session.get('user_type') != 'user':
            return jsonify({
                'success': False, 
                'message': 'Sadece kullanıcılar biletlerini görebilir'
            }), 403
        
        status_filter = request.args.get('status')
        user_id = session['user_id']
        
        tickets = db.get_user_tickets(user_id, status_filter)
        
        return jsonify({'success': True, 'tickets': tickets})
        
    except Exception as e:
        print(f"[ERROR] Get tickets failed: {e}")
        return jsonify({
            'success': False, 
            'tickets': [],
            'message': 'Biletler yüklenemedi'  # "Could not load tickets"
        })


@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def get_ticket_details(ticket_id):
    """
    Get detailed information for a specific ticket.
    
    Endpoint: GET /api/tickets/<ticket_id>
    """
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Kullanıcı bulunamadı'}), 403
        
        ticket = db.get_ticket_details(ticket_id, user_id)
        
        if ticket:
            return jsonify({'success': True, 'ticket': ticket})
        
        return jsonify({
            'success': False, 
            'message': 'Bilet bulunamadı'  # "Ticket not found"
        }), 404
        
    except Exception as e:
        print(f"[ERROR] Get ticket details failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Bilet bilgisi alınamadı'
        }), 500


@app.route('/api/tickets/<int:ticket_id>/cancel', methods=['POST'])
@login_required
def cancel_ticket(ticket_id):
    """
    Cancel a ticket and get refund.
    
    Endpoint: POST /api/tickets/<ticket_id>/cancel
    
    Cancellation process:
    1. Verify ticket belongs to user and is cancellable
    2. Calculate refund amount
    3. Update ticket status to 'Cancelled'
    4. Release seats (update trip's AvailableSeats)
    5. Refund credit to user account
    6. Record refund payment
    """
    try:
        if session.get('user_type') != 'user':
            return jsonify({
                'success': False, 
                'message': 'Sadece kullanıcılar bilet iptal edebilir'
            }), 403
        
        user_id = session['user_id']
        
        # Call stored procedure for cancellation
        success, message = db.cancel_ticket(ticket_id, user_id)
        
        if success:
            # Refresh user data in session (credit balance changed)
            user = db.get_user_profile(user_id)
            if user:
                session['user_data'] = user
            
            return jsonify({
                'success': True, 
                'message': message,
                'new_credit_balance': user.get('credit_balance', 0) if user else 0
            })
        
        return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"[ERROR] Ticket cancellation failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'İptal işlemi başarısız'  # "Cancellation failed"
        }), 500


# ============================================================================
# COUPON API ROUTES
# ============================================================================

@app.route('/api/coupons/validate', methods=['POST'])
@login_required
def validate_coupon():
    """
    Validate a coupon code before purchase.
    
    Endpoint: POST /api/coupons/validate
    
    Request JSON:
        {"coupon_code": "DISCOUNT10"}
    
    Response includes discount_rate if valid.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Geçersiz istek'}), 400
        
        coupon_code = data.get('coupon_code', '').strip().upper()
        
        if not coupon_code:
            return jsonify({
                'success': False, 
                'message': 'Kupon kodu gerekli'  # "Coupon code required"
            }), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Kullanıcı bulunamadı'}), 403
        
        is_valid, discount_rate, message = db.validate_coupon(coupon_code, user_id)
        
        return jsonify({
            'success': is_valid,
            'valid': is_valid,
            'discount_rate': discount_rate,
            'message': message
        })
        
    except Exception as e:
        print(f"[ERROR] Coupon validation failed: {e}")
        return jsonify({
            'success': False,
            'valid': False,
            'discount_rate': 0,
            'message': 'Kupon doğrulama başarısız'
        })


@app.route('/api/coupons', methods=['GET'])
@login_required
def get_user_coupons():
    """
    Get current user's available coupons.
    
    Endpoint: GET /api/coupons
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Kullanıcı bulunamadı'}), 403
        
        coupons = db.get_user_coupons(user_id)
        return jsonify({'success': True, 'coupons': coupons})
        
    except Exception as e:
        print(f"[ERROR] Get coupons failed: {e}")
        return jsonify({'success': False, 'coupons': []})


# ============================================================================
# CREDIT API ROUTES
# ============================================================================

@app.route('/api/credit/add', methods=['POST'])
@login_required
def add_credit():
    """
    Add credit to user account.
    
    Endpoint: POST /api/credit/add
    
    Request JSON:
        {
            "amount": 100,
            "payment_method": "CreditCard"  // or "BankTransfer"
        }
    
    Note: In a real application, this would integrate with a payment gateway.
    For this project, we simulate successful payment.
    """
    try:
        if session.get('user_type') != 'user':
            return jsonify({
                'success': False, 
                'message': 'Sadece kullanıcılar bakiye yükleyebilir'
            }), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Geçersiz istek'}), 400
        
        amount = data.get('amount', 0)
        payment_method = data.get('payment_method', 'CreditCard')
        
        # Validate amount
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return jsonify({
                'success': False, 
                'message': 'Geçersiz miktar'  # "Invalid amount"
            }), 400
        
        if amount <= 0:
            return jsonify({
                'success': False, 
                'message': 'Miktar pozitif olmalı'  # "Amount must be positive"
            }), 400
        
        if amount > 10000:
            return jsonify({
                'success': False, 
                'message': 'Maksimum 10.000 TL yüklenebilir'  # "Max 10,000 TL"
            }), 400
        
        # Validate payment method
        if payment_method not in ['CreditCard', 'BankTransfer']:
            return jsonify({
                'success': False, 
                'message': 'Geçersiz ödeme yöntemi'  # "Invalid payment method"
            }), 400
        
        user_id = session['user_id']
        
        # Add credit via stored procedure
        success, message = db.add_user_credit(user_id, amount, payment_method)
        
        if success:
            # Refresh user data in session
            user = db.get_user_profile(user_id)
            if user:
                session['user_data'] = user
            
            return jsonify({
                'success': True,
                'message': message,
                'new_credit_balance': user.get('credit_balance', 0) if user else 0
            })
        
        return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"[ERROR] Add credit failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Bakiye yükleme başarısız'  # "Credit top-up failed"
        }), 500


@app.route('/api/credit/balance', methods=['GET'])
@login_required
def get_credit_balance():
    """
    Get current user's credit balance.
    
    Endpoint: GET /api/credit/balance
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Kullanıcı bulunamadı'}), 403
        
        balance = db.get_user_credit(user_id)
        return jsonify({
            'success': True, 
            'balance': balance, 
            'formatted': format_currency(balance)
        })
        
    except Exception as e:
        print(f"[ERROR] Get balance failed: {e}")
        return jsonify({'success': False, 'balance': 0})


@app.route('/api/payments', methods=['GET'])
@login_required
def get_payment_history():
    """
    Get user's payment history.
    
    Endpoint: GET /api/payments
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Kullanıcı bulunamadı'}), 403
        
        payments = db.get_payment_history(user_id)
        return jsonify({'success': True, 'payments': payments})
        
    except Exception as e:
        print(f"[ERROR] Get payment history failed: {e}")
        return jsonify({'success': False, 'payments': []})


# ============================================================================
# USER PROFILE API ROUTES
# ============================================================================

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """
    Get current user's profile.
    
    Endpoint: GET /api/profile
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Kullanıcı bulunamadı'}), 403
        
        profile = db.get_user_profile(user_id)
        if profile:
            return jsonify({'success': True, 'profile': profile})
        
        return jsonify({
            'success': False, 
            'message': 'Profil bulunamadı'  # "Profile not found"
        }), 404
        
    except Exception as e:
        print(f"[ERROR] Get profile failed: {e}")
        return jsonify({'success': False, 'message': 'Profil yüklenemedi'}), 500


@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    """
    Update user profile.
    
    Endpoint: PUT /api/profile
    
    Request JSON (all optional):
        {
            "first_name": "Ahmet",
            "last_name": "Yılmaz",
            "phone": "0555 123 45 67",
            "address": "Istanbul, Turkey"
        }
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Kullanıcı bulunamadı'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Geçersiz istek'}), 400
        
        success, message = db.update_user_profile(user_id, **data)
        
        if success:
            # Refresh session with updated data
            user = db.get_user_profile(user_id)
            if user:
                session['user_data'] = user
            
            return jsonify({'success': True, 'message': message, 'profile': user})
        
        return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"[ERROR] Update profile failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Profil güncellenemedi'  # "Could not update profile"
        }), 500


# ============================================================================
# ADMIN API ROUTES
# ============================================================================

@app.route('/api/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    """
    Get dashboard statistics for admin panel.
    
    Endpoint: GET /api/admin/dashboard
    
    Returns key metrics: total users, trips, tickets, revenue
    """
    try:
        # For firm admins, only show their company's stats
        company_id = session.get('company_id') if session.get('user_type') == 'firm_admin' else None
        stats = db.get_dashboard_stats(company_id)
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        print(f"[ERROR] Dashboard stats failed: {e}")
        return jsonify({'success': False, 'stats': {}})


@app.route('/api/admin/companies', methods=['GET'])
@admin_required
def get_companies():
    """
    Get all companies (System Admin only).
    
    Endpoint: GET /api/admin/companies
    """
    try:
        if session.get('user_type') != 'system_admin':
            return jsonify({
                'success': False, 
                'message': 'Sistem admin yetkisi gerekli'
            }), 403
        
        companies = db.get_all_companies()
        return jsonify({'success': True, 'companies': companies})
        
    except Exception as e:
        print(f"[ERROR] Get companies failed: {e}")
        return jsonify({'success': False, 'companies': []})


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """
    Get all users (System Admin only).
    
    Endpoint: GET /api/admin/users
    """
    try:
        if session.get('user_type') != 'system_admin':
            return jsonify({
                'success': False, 
                'message': 'Sistem admin yetkisi gerekli'
            }), 403
        
        users = db.get_all_users()
        return jsonify({'success': True, 'users': users})
        
    except Exception as e:
        print(f"[ERROR] Get users failed: {e}")
        return jsonify({'success': False, 'users': []})


@app.route('/api/admin/coupons', methods=['GET'])
@admin_required
def get_all_coupons():
    """
    Get all coupons (System Admin only).
    
    Endpoint: GET /api/admin/coupons
    """
    try:
        if session.get('user_type') != 'system_admin':
            return jsonify({
                'success': False, 
                'message': 'Sistem admin yetkisi gerekli'
            }), 403
        
        coupons = db.get_all_coupons()
        return jsonify({'success': True, 'coupons': coupons})
        
    except Exception as e:
        print(f"[ERROR] Get coupons failed: {e}")
        return jsonify({'success': False, 'coupons': []})


@app.route('/api/admin/coupons', methods=['POST'])
@admin_required
def create_coupon():
    """
    Create a new coupon (System Admin only).
    
    Endpoint: POST /api/admin/coupons
    
    Request JSON:
        {
            "coupon_code": "NEWCODE",
            "discount_rate": 15,
            "usage_limit": 100,
            "expiry_date": "2025-12-31",
            "description": "New coupon description"
        }
    """
    try:
        if session.get('user_type') != 'system_admin':
            return jsonify({
                'success': False, 
                'message': 'Sistem admin yetkisi gerekli'
            }), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Geçersiz istek'}), 400
        
        # Validate required fields
        required = ['coupon_code', 'discount_rate', 'usage_limit', 'expiry_date']
        for field in required:
            if not data.get(field):
                return jsonify({
                    'success': False, 
                    'message': f'{field} alanı gerekli'
                }), 400
        
        # Parse expiry date
        try:
            expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Geçersiz tarih formatı'
            }), 400
        
        success, message = db.create_coupon(
            coupon_code=data['coupon_code'].upper().strip(),
            discount_rate=float(data['discount_rate']),
            usage_limit=int(data['usage_limit']),
            expiry_date=expiry_date,
            description=data.get('description', '')
        )
        
        if success:
            return jsonify({'success': True, 'message': message})
        
        return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"[ERROR] Create coupon failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Kupon oluşturulamadı'  # "Could not create coupon"
        }), 500


# ============================================================================
# FIRM ADMIN API ROUTES
# ============================================================================

@app.route('/api/firm/trips', methods=['GET'])
@admin_required
def get_firm_trips():
    """
    Get company's trips (Firm Admin only).
    
    Endpoint: GET /api/firm/trips
    
    Query Parameters:
        - status: Filter by status (Active, Completed, Cancelled) - optional
    """
    try:
        if session.get('user_type') != 'firm_admin':
            return jsonify({
                'success': False, 
                'message': 'Firma admin yetkisi gerekli'
            }), 403
        
        company_id = session['company_id']
        status = request.args.get('status')
        
        trips = db.get_company_trips(company_id, status)
        return jsonify({'success': True, 'trips': trips})
        
    except Exception as e:
        print(f"[ERROR] Get firm trips failed: {e}")
        return jsonify({'success': False, 'trips': []})


@app.route('/api/firm/trips', methods=['POST'])
@admin_required
def create_firm_trip():
    """
    Create a new trip (Firm Admin only).
    
    Endpoint: POST /api/firm/trips
    
    Request JSON:
        {
            "bus_id": 1,
            "departure_city_id": 1,
            "arrival_city_id": 2,
            "departure_date": "2025-10-15",
            "departure_time": "09:00",
            "arrival_time": "14:30",
            "duration_minutes": 330,
            "price": 350
        }
    """
    try:
        if session.get('user_type') != 'firm_admin':
            return jsonify({
                'success': False, 
                'message': 'Firma admin yetkisi gerekli'
            }), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Geçersiz istek'}), 400
        
        # Validate required fields
        required = ['bus_id', 'departure_city_id', 'arrival_city_id', 'departure_date',
                    'departure_time', 'arrival_time', 'duration_minutes', 'price']
        for field in required:
            if field not in data:
                return jsonify({
                    'success': False, 
                    'message': f'{field} alanı gerekli'
                }), 400
        
        # Parse date/time values
        try:
            departure_date = datetime.strptime(data['departure_date'], '%Y-%m-%d').date()
            departure_time = datetime.strptime(data['departure_time'], '%H:%M').time()
            arrival_time = datetime.strptime(data['arrival_time'], '%H:%M').time()
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Geçersiz tarih/saat formatı'
            }), 400
        
        admin_id = session['admin_id']
        
        success, message, trip_id = db.create_trip(
            bus_id=data['bus_id'],
            departure_city_id=data['departure_city_id'],
            arrival_city_id=data['arrival_city_id'],
            departure_date=departure_date,
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration_minutes=data['duration_minutes'],
            price=float(data['price']),
            created_by_admin_id=admin_id
        )
        
        if success:
            return jsonify({'success': True, 'message': message, 'trip_id': trip_id})
        
        return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"[ERROR] Create trip failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Sefer oluşturulamadı'  # "Could not create trip"
        }), 500


@app.route('/api/firm/buses', methods=['GET'])
@admin_required
def get_firm_buses():
    """
    Get company's buses (Firm Admin only).
    
    Endpoint: GET /api/firm/buses
    """
    try:
        if session.get('user_type') != 'firm_admin':
            return jsonify({
                'success': False, 
                'message': 'Firma admin yetkisi gerekli'
            }), 403
        
        company_id = session['company_id']
        buses = db.get_company_buses(company_id)
        return jsonify({'success': True, 'buses': buses})
        
    except Exception as e:
        print(f"[ERROR] Get buses failed: {e}")
        return jsonify({'success': False, 'buses': []})


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False, 
        'message': 'Sayfa bulunamadı'  # "Page not found"
    }), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return jsonify({
        'success': False, 
        'message': 'Sunucu hatası'  # "Server error"
    }), 500


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors (wrong HTTP method)"""
    return jsonify({
        'success': False, 
        'message': 'Bu işlem desteklenmiyor'  # "Method not allowed"
    }), 405


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚌 BUS TICKET SYSTEM - Flask API Server")
    print("=" * 60)
    print()
    
    # Test database connection before starting
    print("Testing database connection...")
    if db.test_connection():
        print("✓ Database connection successful!")
        print()
        print("Starting server...")
        print("=" * 60)
        print("Open http://localhost:5000 in your browser")
        print("=" * 60)
        print()
        print("Test Accounts:")
        print("  User:  ahmet.yilmaz@email.com / password123")
        print("  Admin: admin@busticket.com / password123")
        print("=" * 60)
        
        # Run Flask development server
        # debug=True enables auto-reload on code changes
        # host='0.0.0.0' allows access from other devices on network
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("✗ Database connection failed!")
        print()
        print("Please make sure:")
        print("1. SQL Server is running")
        print("2. The database exists (run BusTicketSystem_CreateDB.sql)")
        print("3. Check config.py for correct connection settings")
        print()
