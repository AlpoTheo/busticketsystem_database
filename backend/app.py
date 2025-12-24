# =============================================================================
# BUS TICKET SYSTEM - Flask API
# Database Systems Course Project
# =============================================================================
# 
# This file is the main backend of our bus ticket system.
# I used Flask because its simple and we learned REST APIs in class.
#
# How it works:
#   Frontend (HTML/JS) --> Flask API (here) --> MSSQL Database
#
# I chose Flask because:
#   - Easy to learn (good documentation)
#   - @app.route decorator makes routing simple
#   - Works good with any database
# =============================================================================

import os
import sys
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
from utils import (
    validate_email, validate_phone, validate_id_number, 
    validate_password, format_currency, format_duration
)

# =============================================================================
# APP SETUP
# =============================================================================

app = Flask(__name__, static_folder='../frontend', static_url_path='')

# Secret key for session - in real app this should be environment variable
app.secret_key = 'bus_ticket_system_secret_key_2025'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# CORS lets frontend make API calls to backend
# supports_credentials=True needed for session cookies to work
CORS(app, supports_credentials=True)

# Singleton pattern - only one database connection for whole app
# This saves resources and prevents connection problems
db = DatabaseManager()


# =============================================================================
# DECORATORS FOR AUTHENTICATION
# =============================================================================
# Decorators are like "wrappers" - they run before the actual function
# We use them to check if user is logged in before accessing protected pages

def login_required(f):
    """
    Check if user logged in before accessing route.
    If not logged in, return 401 error.
    
    Usage: Put @login_required above any route that needs login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session for user_id or admin_id
        if 'user_id' not in session and 'admin_id' not in session:
            return jsonify({
                'success': False, 
                'message': 'Please login first'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Only admins can access this route.
    Returns 403 (Forbidden) if not admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({
                'success': False, 
                'message': 'Admin access required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# STATIC FILE ROUTES
# =============================================================================

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files like HTML, CSS, JS"""
    return send_from_directory(app.static_folder, filename)


# =============================================================================
# AUTH API - Login, Register, Logout
# =============================================================================

@app.route('/api/register', methods=['POST'])
def register():
    """
    Register new user.
    
    POST /api/register
    Body: {first_name, last_name, email, phone, password, id_number}
    
    We validate everything before inserting to database.
    This prevents bad data and SQL errors.
    """
    try:
        data = request.get_json()
        
        # Null check - important! If no JSON sent, data will be None
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
        # Check all required fields exist and not empty
        required_fields = ['first_name', 'last_name', 'email', 'phone', 'password', 'id_number']
        for field in required_fields:
            if not data.get(field) or not str(data.get(field)).strip():
                return jsonify({
                    'success': False, 
                    'message': f'{field} is required'
                }), 400
        
        # Validate email format with regex
        is_valid, error_msg = validate_email(data['email'])
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Check password length
        is_valid, error_msg = validate_password(data['password'])
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Turkish ID number validation (11 digits, cant start with 0)
        is_valid, error_msg = validate_id_number(data['id_number'])
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # All validation passed, now register user
        # .strip() removes extra spaces, .lower() makes email lowercase
        success, message, user_id = db.register_user(
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            email=data['email'].strip().lower(),
            phone=data['phone'].strip(),
            password=data['password'],
            id_number=data['id_number'].strip()
        )
        
        if success:
            return jsonify({'success': True, 'message': message, 'user_id': user_id})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        # Log error for debugging but dont show technical details to user
        print(f"[ERROR] Registration failed: {e}")
        return jsonify({'success': False, 'message': 'Registration failed'}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """
    Login user.
    
    POST /api/login
    Body: {email, password}
    
    The system checks Users table first, then FirmAdmins table.
    This way all user types can use same login form.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Basic check - both email and password needed
        if not email or not password:
            return jsonify({
                'success': False, 
                'message': 'Email and password required'
            }), 400
        
        # Try regular User/SystemAdmin login first
        success, message, user_data = db.login_user(email, password)
        
        if success and user_data:
            # Save user info in session (session is like temporary storage for logged in user)
            session['user_id'] = user_data['user_id']
            session['user_data'] = user_data
            session.permanent = True
            
            # Check if SystemAdmin
            if user_data.get('role') == 'SystemAdmin':
                session['user_type'] = 'system_admin'
                session['admin_id'] = user_data['user_id']
            else:
                session['user_type'] = 'user'
            
            return jsonify({'success': True, 'message': message, 'user': user_data})
        
        # If user login failed, try firm admin login
        success, message, admin_data = db.login_firm_admin(email, password)
        if success and admin_data:
            session['admin_id'] = admin_data['admin_id']
            session['user_type'] = 'firm_admin'
            session['company_id'] = admin_data['company_id']
            session['admin_data'] = admin_data
            session.permanent = True
            return jsonify({'success': True, 'message': message, 'user': admin_data})
        
        # Both failed
        return jsonify({
            'success': False, 
            'message': 'Invalid email or password'
        }), 401
        
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    """Clear session to logout user"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'})


@app.route('/api/session', methods=['GET'])
def get_session():
    """
    Check if user still logged in.
    Frontend calls this to verify session is valid.
    Also refreshes user data (like credit balance).
    """
    try:
        if 'user_id' in session:
            # Get fresh data from database (balance might have changed)
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


# =============================================================================
# CITY API
# =============================================================================

@app.route('/api/cities', methods=['GET'])
def get_cities():
    """
    Get all cities for dropdown menus.
    Public endpoint - no login needed because search form is on home page.
    """
    try:
        cities = db.get_all_cities()
        return jsonify({'success': True, 'cities': cities})
    except Exception as e:
        print(f"[ERROR] Get cities failed: {e}")
        return jsonify({'success': False, 'cities': [], 'message': 'Could not load cities'})


# =============================================================================
# TRIP API - Search and Details
# =============================================================================

@app.route('/api/trips/search', methods=['GET'])
def search_trips():
    """
    Search available trips.
    
    GET /api/trips/search?from=1&to=2&date=2025-12-25
    
    Uses stored procedure sp_SearchTrips for the query.
    Stored procedure is better because complex query logic stays in database.
    """
    try:
        # Get parameters from URL query string
        departure_city = request.args.get('from', type=int)
        arrival_city = request.args.get('to', type=int)
        travel_date_str = request.args.get('date')
        sort_by = request.args.get('sort_by', 'DepartureTime')
        sort_order = request.args.get('sort_order', 'ASC')
        
        # Check required parameters
        if not all([departure_city, arrival_city, travel_date_str]):
            return jsonify({
                'success': False, 
                'message': 'Missing parameters'
            }), 400
        
        # Parse date string to date object
        try:
            travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        
        # Dont allow past dates
        if travel_date < datetime.now().date():
            return jsonify({
                'success': False,
                'message': 'Cannot select past date'
            }), 400
        
        # Call database
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
            'message': 'Search failed'
        })


@app.route('/api/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    """Get details for single trip - used on seat selection page"""
    try:
        trip = db.get_trip_details(trip_id)
        
        if trip:
            trip['PriceFormatted'] = format_currency(trip.get('Price', 0))
            trip['DurationFormatted'] = format_duration(trip.get('DurationMinutes', 0))
            return jsonify({'success': True, 'trip': trip})
        
        return jsonify({'success': False, 'message': 'Trip not found'}), 404
        
    except Exception as e:
        print(f"[ERROR] Get trip failed: {e}")
        return jsonify({'success': False, 'message': 'Could not get trip info'}), 500


@app.route('/api/trips/<int:trip_id>/seats', methods=['GET'])
def get_trip_seats(trip_id):
    """
    Get seat status for trip.
    Returns all seats with status (Available or Occupied).
    Frontend uses this to draw the seat grid.
    """
    try:
        seats = db.get_trip_seat_status(trip_id)
        return jsonify({'success': True, 'seats': seats})
    except Exception as e:
        print(f"[ERROR] Get seats failed: {e}")
        return jsonify({
            'success': False, 
            'seats': [],
            'message': 'Could not get seat info'
        })


# =============================================================================
# TICKET API - Purchase and Cancel
# =============================================================================

@app.route('/api/tickets/purchase', methods=['POST'])
@login_required
def purchase_ticket():
    """
    Purchase ticket - THIS IS THE MAIN TRANSACTION!
    
    POST /api/tickets/purchase
    Body: {trip_id, seat_ids, passenger_names, coupon_code}
    
    Why stored procedure (sp_PurchaseTicket)?
    Because buying ticket needs multiple steps:
      1. Check seats available
      2. Validate coupon
      3. Calculate price with discount
      4. Check user has enough money
      5. Create ticket record
      6. Create seat assignments
      7. Update available seats
      8. Deduct money from user
      9. Record payment
    
    If ANY step fails, ALL changes must rollback.
    This is ACID - we learned this in class.
    Transaction keeps database consistent.
    """
    try:
        # Only users can buy tickets (not admins)
        if session.get('user_type') != 'user':
            return jsonify({
                'success': False, 
                'message': 'Only users can buy tickets'
            }), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
        trip_id = data.get('trip_id')
        seat_ids = data.get('seat_ids', [])
        passenger_names = data.get('passenger_names', [])
        coupon_code = data.get('coupon_code')
        
        # Validation
        if not trip_id:
            return jsonify({'success': False, 'message': 'No trip selected'}), 400
        
        if not seat_ids or len(seat_ids) == 0:
            return jsonify({'success': False, 'message': 'No seat selected'}), 400
        
        if not passenger_names or len(passenger_names) == 0:
            return jsonify({'success': False, 'message': 'Passenger name required'}), 400
        
        # Seat count must match passenger count
        if len(seat_ids) != len(passenger_names):
            return jsonify({
                'success': False, 
                'message': 'Seat and passenger count dont match'
            }), 400
        
        # Business rule: max 5 seats per booking
        if len(seat_ids) > 5:
            return jsonify({
                'success': False, 
                'message': 'Maximum 5 seats per booking'
            }), 400
        
        user_id = session['user_id']
        
        # Call stored procedure
        success, message, ticket_id = db.purchase_ticket(
            user_id=user_id,
            trip_id=trip_id,
            seat_ids=seat_ids,
            passenger_names=passenger_names,
            coupon_code=coupon_code,
            use_credit=True
        )
        
        if success:
            # Refresh user data (balance changed)
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
            'message': 'Ticket purchase failed'
        }), 500


@app.route('/api/tickets', methods=['GET'])
@login_required
def get_user_tickets():
    """
    Get users tickets.
    Can filter by status: Active, Completed, Cancelled
    """
    try:
        if session.get('user_type') != 'user':
            return jsonify({
                'success': False, 
                'message': 'Only users can view tickets'
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
            'message': 'Could not load tickets'
        })


@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def get_ticket_details(ticket_id):
    """Get single ticket details"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'}), 403
        
        ticket = db.get_ticket_details(ticket_id, user_id)
        
        if ticket:
            return jsonify({'success': True, 'ticket': ticket})
        
        return jsonify({'success': False, 'message': 'Ticket not found'}), 404
        
    except Exception as e:
        print(f"[ERROR] Get ticket details failed: {e}")
        return jsonify({'success': False, 'message': 'Could not get ticket info'}), 500


@app.route('/api/tickets/<int:ticket_id>/cancel', methods=['POST'])
@login_required
def cancel_ticket(ticket_id):
    """
    Cancel ticket and get refund.
    
    Uses sp_CancelTicket stored procedure.
    Similar to purchase - needs transaction because:
      1. Verify ticket belongs to user
      2. Calculate refund
      3. Update ticket status
      4. Release seats
      5. Refund money to user
      6. Record refund payment
    
    All steps must succeed or all fail (ACID).
    """
    try:
        if session.get('user_type') != 'user':
            return jsonify({
                'success': False, 
                'message': 'Only users can cancel tickets'
            }), 403
        
        user_id = session['user_id']
        
        success, message = db.cancel_ticket(ticket_id, user_id)
        
        if success:
            # Refresh user data (balance changed after refund)
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
            'message': 'Cancellation failed'
        }), 500


# =============================================================================
# COUPON API
# =============================================================================

@app.route('/api/coupons/validate', methods=['POST'])
@login_required
def validate_coupon():
    """
    Check if coupon is valid before purchase.
    Returns discount rate if valid.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
        coupon_code = data.get('coupon_code', '').strip().upper()
        
        if not coupon_code:
            return jsonify({
                'success': False, 
                'message': 'Coupon code required'
            }), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'}), 403
        
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
            'message': 'Coupon validation failed'
        })


@app.route('/api/coupons', methods=['GET'])
@login_required
def get_user_coupons():
    """Get users available coupons"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'}), 403
        
        coupons = db.get_user_coupons(user_id)
        return jsonify({'success': True, 'coupons': coupons})
        
    except Exception as e:
        print(f"[ERROR] Get coupons failed: {e}")
        return jsonify({'success': False, 'coupons': []})


# =============================================================================
# CREDIT API - Add money to account
# =============================================================================

@app.route('/api/credit/add', methods=['POST'])
@login_required
def add_credit():
    """
    Add credit to user account.
    
    POST /api/credit/add
    Body: {amount, payment_method}
    
    In real app this would connect to payment gateway.
    For demo we just simulate successful payment.
    """
    try:
        if session.get('user_type') != 'user':
            return jsonify({
                'success': False, 
                'message': 'Only users can add credit'
            }), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
        amount = data.get('amount', 0)
        payment_method = data.get('payment_method', 'CreditCard')
        
        # Validate amount is number
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return jsonify({
                'success': False, 
                'message': 'Invalid amount'
            }), 400
        
        # Amount must be positive
        if amount <= 0:
            return jsonify({
                'success': False, 
                'message': 'Amount must be positive'
            }), 400
        
        # Max limit for security
        if amount > 50000:
            return jsonify({
                'success': False, 
                'message': 'Maximum 50,000 TL allowed'
            }), 400
        
        # Validate payment method
        if payment_method not in ['CreditCard', 'BankTransfer']:
            return jsonify({
                'success': False, 
                'message': 'Invalid payment method'
            }), 400
        
        user_id = session['user_id']
        
        success, message = db.add_user_credit(user_id, amount, payment_method)
        
        if success:
            # Refresh user data
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
            'message': 'Credit top-up failed'
        }), 500


@app.route('/api/credit/balance', methods=['GET'])
@login_required
def get_credit_balance():
    """Get current credit balance"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'}), 403
        
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
    """Get users payment history"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'}), 403
        
        payments = db.get_payment_history(user_id)
        return jsonify({'success': True, 'payments': payments})
        
    except Exception as e:
        print(f"[ERROR] Get payment history failed: {e}")
        return jsonify({'success': False, 'payments': []})


# =============================================================================
# USER PROFILE API
# =============================================================================

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'}), 403
        
        profile = db.get_user_profile(user_id)
        if profile:
            return jsonify({'success': True, 'profile': profile})
        
        return jsonify({'success': False, 'message': 'Profile not found'}), 404
        
    except Exception as e:
        print(f"[ERROR] Get profile failed: {e}")
        return jsonify({'success': False, 'message': 'Could not load profile'}), 500


@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    """
    Update user profile.
    Only updates fields that are sent in request.
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User not found'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
        success, message = db.update_user_profile(user_id, **data)
        
        if success:
            # Refresh session data
            user = db.get_user_profile(user_id)
            if user:
                session['user_data'] = user
            
            return jsonify({'success': True, 'message': message, 'profile': user})
        
        return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"[ERROR] Update profile failed: {e}")
        return jsonify({
            'success': False, 
            'message': 'Could not update profile'
        }), 500


# =============================================================================
# ADMIN API
# =============================================================================

@app.route('/api/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    """
    Get dashboard statistics.
    Shows total users, trips, tickets, revenue etc.
    """
    try:
        # Firm admin only sees their company stats
        company_id = session.get('company_id') if session.get('user_type') == 'firm_admin' else None
        stats = db.get_dashboard_stats(company_id)
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        print(f"[ERROR] Dashboard stats failed: {e}")
        return jsonify({'success': False, 'stats': {}})


@app.route('/api/admin/companies', methods=['GET'])
@admin_required
def get_companies():
    """Get all companies - System Admin only"""
    try:
        if session.get('user_type') != 'system_admin':
            return jsonify({
                'success': False, 
                'message': 'System admin access required'
            }), 403
        
        companies = db.get_all_companies()
        return jsonify({'success': True, 'companies': companies})
        
    except Exception as e:
        print(f"[ERROR] Get companies failed: {e}")
        return jsonify({'success': False, 'companies': []})


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users - System Admin only"""
    try:
        if session.get('user_type') != 'system_admin':
            return jsonify({
                'success': False, 
                'message': 'System admin access required'
            }), 403
        
        users = db.get_all_users()
        return jsonify({'success': True, 'users': users})
        
    except Exception as e:
        print(f"[ERROR] Get users failed: {e}")
        return jsonify({'success': False, 'users': []})


@app.route('/api/admin/coupons', methods=['GET'])
@admin_required
def get_all_coupons():
    """Get all coupons - System Admin only"""
    try:
        if session.get('user_type') != 'system_admin':
            return jsonify({
                'success': False, 
                'message': 'System admin access required'
            }), 403
        
        coupons = db.get_all_coupons()
        return jsonify({'success': True, 'coupons': coupons})
        
    except Exception as e:
        print(f"[ERROR] Get coupons failed: {e}")
        return jsonify({'success': False, 'coupons': []})


@app.route('/api/admin/coupons', methods=['POST'])
@admin_required
def create_coupon():
    """Create new coupon - System Admin only"""
    try:
        if session.get('user_type') != 'system_admin':
            return jsonify({
                'success': False, 
                'message': 'System admin access required'
            }), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
        # Check required fields
        required = ['coupon_code', 'discount_rate', 'usage_limit', 'expiry_date']
        for field in required:
            if not data.get(field):
                return jsonify({
                    'success': False, 
                    'message': f'{field} is required'
                }), 400
        
        # Parse date
        try:
            expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Invalid date format'
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
            'message': 'Could not create coupon'
        }), 500


# =============================================================================
# FIRM ADMIN API
# =============================================================================

@app.route('/api/firm/trips', methods=['GET'])
@admin_required
def get_firm_trips():
    """Get companys trips - Firm Admin only"""
    try:
        if session.get('user_type') != 'firm_admin':
            return jsonify({
                'success': False, 
                'message': 'Firm admin access required'
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
    """Create new trip - Firm Admin only"""
    try:
        if session.get('user_type') != 'firm_admin':
            return jsonify({
                'success': False, 
                'message': 'Firm admin access required'
            }), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
        # Check required fields
        required = ['bus_id', 'departure_city_id', 'arrival_city_id', 'departure_date',
                    'departure_time', 'arrival_time', 'duration_minutes', 'price']
        for field in required:
            if field not in data:
                return jsonify({
                    'success': False, 
                    'message': f'{field} is required'
                }), 400
        
        # Parse date and time
        try:
            departure_date = datetime.strptime(data['departure_date'], '%Y-%m-%d').date()
            departure_time = datetime.strptime(data['departure_time'], '%H:%M').time()
            arrival_time = datetime.strptime(data['arrival_time'], '%H:%M').time()
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Invalid date/time format'
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
            'message': 'Could not create trip'
        }), 500


@app.route('/api/firm/buses', methods=['GET'])
@admin_required
def get_firm_buses():
    """Get companys buses - Firm Admin only"""
    try:
        if session.get('user_type') != 'firm_admin':
            return jsonify({
                'success': False, 
                'message': 'Firm admin access required'
            }), 403
        
        company_id = session['company_id']
        buses = db.get_company_buses(company_id)
        return jsonify({'success': True, 'buses': buses})
        
    except Exception as e:
        print(f"[ERROR] Get buses failed: {e}")
        return jsonify({'success': False, 'buses': []})


# =============================================================================
# ERROR HANDLERS
# =============================================================================
# These catch errors that arent handled by try-catch blocks
# Important for demo - prevents ugly error pages

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Page not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'success': False, 'message': 'Server error'}), 500


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'success': False, 'message': 'Method not allowed'}), 405


# =============================================================================
# MAIN - Start the server
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("BUS TICKET SYSTEM - Flask API Server")
    print("=" * 60)
    print()
    
    # Test database before starting
    print("Testing database connection...")
    if db.test_connection():
        print("Database connection OK!")
        print()
        print("Starting server...")
        print("=" * 60)
        print("Open http://localhost:5000 in browser")
        print("=" * 60)
        print()
        print("Test Accounts:")
        print("  User:  ahmet.yilmaz@email.com / password123")
        print("  Admin: admin@busticket.com / password123")
        print("=" * 60)
        
        # debug=True auto-reloads when code changes (useful for development)
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Database connection FAILED!")
        print()
        print("Check:")
        print("1. SQL Server is running")
        print("2. Database exists (run BusTicketSystem_CreateDB.sql)")
        print("3. Connection settings in config.py")
        print()
