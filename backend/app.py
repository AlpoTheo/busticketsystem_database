# ============================================================================
# BUS TICKET SYSTEM - Flask API Application
# CENG 301 Database Systems Project
# ============================================================================
# This is the main Flask application that provides REST API endpoints
# for the Bus Ticket System frontend.
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
app.secret_key = 'bus_ticket_system_secret_key_2025'  # Change in production!
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Enable CORS for all routes
CORS(app, supports_credentials=True)

# Initialize database manager
db = DatabaseManager()

# ============================================================================
# AUTHENTICATION DECORATOR
# ============================================================================

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session and 'admin_id' not in session:
            return jsonify({'success': False, 'message': 'Please login first'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# STATIC FILE ROUTES (Serve HTML pages)
# ============================================================================

@app.route('/')
def index():
    """Serve main page"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)


# ============================================================================
# AUTH API ROUTES
# ============================================================================

@app.route('/api/register', methods=['POST'])
def register():
    """
    Register a new user
    
    Request JSON:
        {
            "first_name": "Ahmet",
            "last_name": "Yılmaz",
            "email": "ahmet@email.com",
            "phone": "0555 123 45 67",
            "password": "password123",
            "id_number": "12345678901"
        }
    """
    data = request.get_json()
    
    # Validate required fields
    required = ['first_name', 'last_name', 'email', 'phone', 'password', 'id_number']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field} is required'}), 400
    
    # Validate email
    valid, msg = validate_email(data['email'])
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    # Validate password
    valid, msg = validate_password(data['password'])
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    # Validate ID number
    valid, msg = validate_id_number(data['id_number'])
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    # Register user
    success, message, user_id = db.register_user(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        phone=data['phone'],
        password=data['password'],
        id_number=data['id_number']
    )
    
    if success:
        return jsonify({'success': True, 'message': message, 'user_id': user_id})
    else:
        return jsonify({'success': False, 'message': message}), 400


@app.route('/api/login', methods=['POST'])
def login():
    """
    Login user (handles both regular users and admins)
    
    Request JSON:
        {
            "email": "ahmet@email.com",
            "password": "password123"
        }
    """
    data = request.get_json()
    
    email = data.get('email', '')
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    # Try to login (works for both User and SystemAdmin)
    success, message, user_data = db.login_user(email, password)
    
    if success:
        session['user_id'] = user_data['user_id']
        session['user_data'] = user_data
        
        # Check role and set appropriate session data
        if user_data.get('role') == 'SystemAdmin':
            session['user_type'] = 'system_admin'
            session['admin_id'] = user_data['user_id']
        else:
            session['user_type'] = 'user'
        
        return jsonify({'success': True, 'message': message, 'user': user_data})
    
    # Try firm admin login as fallback
    success, message, admin_data = db.login_firm_admin(email, password)
    if success:
        session['admin_id'] = admin_data['admin_id']
        session['user_type'] = 'firm_admin'
        session['company_id'] = admin_data['company_id']
        session['admin_data'] = admin_data
        return jsonify({'success': True, 'message': message, 'user': admin_data})
    
    return jsonify({'success': False, 'message': 'Invalid email or password'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout current user"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@app.route('/api/session', methods=['GET'])
def get_session():
    """Get current session info"""
    if 'user_id' in session:
        # Refresh user data
        user = db.get_user_profile(session['user_id'])
        if user:
            session['user_data'] = user
            return jsonify({
                'logged_in': True,
                'user_type': 'user',
                'user': user
            })
    elif 'admin_id' in session:
        return jsonify({
            'logged_in': True,
            'user_type': session.get('user_type'),
            'admin': session.get('admin_data')
        })
    
    return jsonify({'logged_in': False})


# ============================================================================
# CITY API ROUTES
# ============================================================================

@app.route('/api/cities', methods=['GET'])
def get_cities():
    """Get all cities"""
    cities = db.get_all_cities()
    return jsonify({'success': True, 'cities': cities})


# ============================================================================
# TRIP API ROUTES
# ============================================================================

@app.route('/api/trips/search', methods=['GET'])
def search_trips():
    """
    Search for available trips
    
    Query Parameters:
        - from: Departure city ID
        - to: Arrival city ID
        - date: Travel date (YYYY-MM-DD)
        - sort_by: DepartureTime, Price, Duration (default: DepartureTime)
        - sort_order: ASC, DESC (default: ASC)
    """
    departure_city = request.args.get('from', type=int)
    arrival_city = request.args.get('to', type=int)
    travel_date = request.args.get('date')
    sort_by = request.args.get('sort_by', 'DepartureTime')
    sort_order = request.args.get('sort_order', 'ASC')
    
    if not all([departure_city, arrival_city, travel_date]):
        return jsonify({'success': False, 'message': 'Missing required parameters'}), 400
    
    try:
        travel_date = datetime.strptime(travel_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    trips = db.search_trips(departure_city, arrival_city, travel_date, sort_by, sort_order)
    
    # Format prices for display
    for trip in trips:
        trip['PriceFormatted'] = format_currency(trip.get('Price', 0))
        trip['DurationFormatted'] = format_duration(trip.get('DurationMinutes', 0))
    
    return jsonify({'success': True, 'trips': trips, 'count': len(trips)})


@app.route('/api/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    """Get trip details"""
    trip = db.get_trip_details(trip_id)
    
    if trip:
        trip['PriceFormatted'] = format_currency(trip.get('Price', 0))
        trip['DurationFormatted'] = format_duration(trip.get('DurationMinutes', 0))
        return jsonify({'success': True, 'trip': trip})
    
    return jsonify({'success': False, 'message': 'Trip not found'}), 404


@app.route('/api/trips/<int:trip_id>/seats', methods=['GET'])
def get_trip_seats(trip_id):
    """Get seat availability for a trip"""
    seats = db.get_trip_seat_status(trip_id)
    return jsonify({'success': True, 'seats': seats})


# ============================================================================
# TICKET API ROUTES
# ============================================================================

@app.route('/api/tickets/purchase', methods=['POST'])
@login_required
def purchase_ticket():
    """
    Purchase a ticket
    
    Request JSON:
        {
            "trip_id": 1,
            "seat_ids": [1, 2],
            "passenger_names": ["Ahmet Yılmaz", "Fatma Yılmaz"],
            "coupon_code": "DISCOUNT10"  // optional
        }
    """
    if session.get('user_type') != 'user':
        return jsonify({'success': False, 'message': 'Only users can purchase tickets'}), 403
    
    data = request.get_json()
    
    trip_id = data.get('trip_id')
    seat_ids = data.get('seat_ids', [])
    passenger_names = data.get('passenger_names', [])
    coupon_code = data.get('coupon_code')
    
    if not trip_id or not seat_ids or not passenger_names:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    if len(seat_ids) != len(passenger_names):
        return jsonify({'success': False, 'message': 'Number of seats must match passengers'}), 400
    
    user_id = session['user_id']
    
    success, message, ticket_id = db.purchase_ticket(
        user_id=user_id,
        trip_id=trip_id,
        seat_ids=seat_ids,
        passenger_names=passenger_names,
        coupon_code=coupon_code,
        use_credit=True
    )
    
    if success:
        # Update session with new credit balance
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


@app.route('/api/tickets', methods=['GET'])
@login_required
def get_user_tickets():
    """Get current user's tickets"""
    if session.get('user_type') != 'user':
        return jsonify({'success': False, 'message': 'Only users can view tickets'}), 403
    
    status_filter = request.args.get('status')
    user_id = session['user_id']
    
    tickets = db.get_user_tickets(user_id, status_filter)
    
    return jsonify({'success': True, 'tickets': tickets})


@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def get_ticket_details(ticket_id):
    """Get ticket details"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'User not found'}), 403
    
    ticket = db.get_ticket_details(ticket_id, user_id)
    
    if ticket:
        return jsonify({'success': True, 'ticket': ticket})
    
    return jsonify({'success': False, 'message': 'Ticket not found'}), 404


@app.route('/api/tickets/<int:ticket_id>/cancel', methods=['POST'])
@login_required
def cancel_ticket(ticket_id):
    """Cancel a ticket"""
    if session.get('user_type') != 'user':
        return jsonify({'success': False, 'message': 'Only users can cancel tickets'}), 403
    
    user_id = session['user_id']
    
    success, message = db.cancel_ticket(ticket_id, user_id)
    
    if success:
        # Update session with new credit balance
        user = db.get_user_profile(user_id)
        if user:
            session['user_data'] = user
        
        return jsonify({
            'success': True, 
            'message': message,
            'new_credit_balance': user.get('credit_balance', 0) if user else 0
        })
    
    return jsonify({'success': False, 'message': message}), 400


# ============================================================================
# COUPON API ROUTES
# ============================================================================

@app.route('/api/coupons/validate', methods=['POST'])
@login_required
def validate_coupon():
    """
    Validate a coupon code
    
    Request JSON:
        {
            "coupon_code": "DISCOUNT10"
        }
    """
    data = request.get_json()
    coupon_code = data.get('coupon_code', '')
    
    if not coupon_code:
        return jsonify({'success': False, 'message': 'Coupon code is required'}), 400
    
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


@app.route('/api/coupons', methods=['GET'])
@login_required
def get_user_coupons():
    """Get current user's available coupons"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not found'}), 403
    
    coupons = db.get_user_coupons(user_id)
    return jsonify({'success': True, 'coupons': coupons})


# ============================================================================
# CREDIT API ROUTES
# ============================================================================

@app.route('/api/credit/add', methods=['POST'])
@login_required
def add_credit():
    """
    Add credit to user account
    
    Request JSON:
        {
            "amount": 100,
            "payment_method": "CreditCard"
        }
    """
    if session.get('user_type') != 'user':
        return jsonify({'success': False, 'message': 'Only users can add credit'}), 403
    
    data = request.get_json()
    amount = data.get('amount', 0)
    payment_method = data.get('payment_method', 'CreditCard')
    
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Amount must be positive'}), 400
    
    if payment_method not in ['CreditCard', 'BankTransfer']:
        return jsonify({'success': False, 'message': 'Invalid payment method'}), 400
    
    user_id = session['user_id']
    success, message = db.add_user_credit(user_id, amount, payment_method)
    
    if success:
        # Update session with new credit balance
        user = db.get_user_profile(user_id)
        if user:
            session['user_data'] = user
        
        return jsonify({
            'success': True,
            'message': message,
            'new_credit_balance': user.get('credit_balance', 0) if user else 0
        })
    
    return jsonify({'success': False, 'message': message}), 400


@app.route('/api/credit/balance', methods=['GET'])
@login_required
def get_credit_balance():
    """Get current user's credit balance"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not found'}), 403
    
    balance = db.get_user_credit(user_id)
    return jsonify({'success': True, 'balance': balance, 'formatted': format_currency(balance)})


@app.route('/api/payments', methods=['GET'])
@login_required
def get_payment_history():
    """Get payment history"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not found'}), 403
    
    payments = db.get_payment_history(user_id)
    return jsonify({'success': True, 'payments': payments})


# ============================================================================
# USER PROFILE API ROUTES
# ============================================================================

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user's profile"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not found'}), 403
    
    profile = db.get_user_profile(user_id)
    if profile:
        return jsonify({'success': True, 'profile': profile})
    
    return jsonify({'success': False, 'message': 'Profile not found'}), 404


@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    """
    Update user profile
    
    Request JSON (all optional):
        {
            "first_name": "Ahmet",
            "last_name": "Yılmaz",
            "phone": "0555 123 45 67",
            "address": "Istanbul, Turkey"
        }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not found'}), 403
    
    data = request.get_json()
    
    success, message = db.update_user_profile(user_id, **data)
    
    if success:
        # Update session
        user = db.get_user_profile(user_id)
        if user:
            session['user_data'] = user
        
        return jsonify({'success': True, 'message': message, 'profile': user})
    
    return jsonify({'success': False, 'message': message}), 400


# ============================================================================
# ADMIN API ROUTES
# ============================================================================

@app.route('/api/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    """Get dashboard statistics"""
    company_id = session.get('company_id') if session.get('user_type') == 'firm_admin' else None
    stats = db.get_dashboard_stats(company_id)
    return jsonify({'success': True, 'stats': stats})


@app.route('/api/admin/companies', methods=['GET'])
@admin_required
def get_companies():
    """Get all companies (System Admin only)"""
    if session.get('user_type') != 'system_admin':
        return jsonify({'success': False, 'message': 'System admin access required'}), 403
    
    companies = db.get_all_companies()
    return jsonify({'success': True, 'companies': companies})


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users (System Admin only)"""
    if session.get('user_type') != 'system_admin':
        return jsonify({'success': False, 'message': 'System admin access required'}), 403
    
    users = db.get_all_users()
    return jsonify({'success': True, 'users': users})


@app.route('/api/admin/coupons', methods=['GET'])
@admin_required
def get_all_coupons():
    """Get all coupons (System Admin only)"""
    if session.get('user_type') != 'system_admin':
        return jsonify({'success': False, 'message': 'System admin access required'}), 403
    
    coupons = db.get_all_coupons()
    return jsonify({'success': True, 'coupons': coupons})


@app.route('/api/admin/coupons', methods=['POST'])
@admin_required
def create_coupon():
    """
    Create a new coupon (System Admin only)
    
    Request JSON:
        {
            "coupon_code": "NEWCODE",
            "discount_rate": 15,
            "usage_limit": 100,
            "expiry_date": "2025-12-31",
            "description": "New coupon description"
        }
    """
    if session.get('user_type') != 'system_admin':
        return jsonify({'success': False, 'message': 'System admin access required'}), 403
    
    data = request.get_json()
    
    required = ['coupon_code', 'discount_rate', 'usage_limit', 'expiry_date']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field} is required'}), 400
    
    try:
        expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    
    success, message = db.create_coupon(
        coupon_code=data['coupon_code'],
        discount_rate=float(data['discount_rate']),
        usage_limit=int(data['usage_limit']),
        expiry_date=expiry_date,
        description=data.get('description', '')
    )
    
    if success:
        return jsonify({'success': True, 'message': message})
    
    return jsonify({'success': False, 'message': message}), 400


# ============================================================================
# FIRM ADMIN API ROUTES
# ============================================================================

@app.route('/api/firm/trips', methods=['GET'])
@admin_required
def get_firm_trips():
    """Get company's trips (Firm Admin only)"""
    if session.get('user_type') != 'firm_admin':
        return jsonify({'success': False, 'message': 'Firm admin access required'}), 403
    
    company_id = session['company_id']
    status = request.args.get('status')
    
    trips = db.get_company_trips(company_id, status)
    return jsonify({'success': True, 'trips': trips})


@app.route('/api/firm/trips', methods=['POST'])
@admin_required
def create_firm_trip():
    """
    Create a new trip (Firm Admin only)
    
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
    if session.get('user_type') != 'firm_admin':
        return jsonify({'success': False, 'message': 'Firm admin access required'}), 403
    
    data = request.get_json()
    
    required = ['bus_id', 'departure_city_id', 'arrival_city_id', 'departure_date',
                'departure_time', 'arrival_time', 'duration_minutes', 'price']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'message': f'{field} is required'}), 400
    
    try:
        departure_date = datetime.strptime(data['departure_date'], '%Y-%m-%d').date()
        departure_time = datetime.strptime(data['departure_time'], '%H:%M').time()
        arrival_time = datetime.strptime(data['arrival_time'], '%H:%M').time()
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date/time format'}), 400
    
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


@app.route('/api/firm/buses', methods=['GET'])
@admin_required
def get_firm_buses():
    """Get company's buses (Firm Admin only)"""
    if session.get('user_type') != 'firm_admin':
        return jsonify({'success': False, 'message': 'Firm admin access required'}), 403
    
    company_id = session['company_id']
    buses = db.get_company_buses(company_id)
    return jsonify({'success': True, 'buses': buses})


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚌 BUS TICKET SYSTEM - Flask API Server")
    print("=" * 60)
    
    # Test database connection
    if db.test_connection():
        print("✓ Database connection successful!")
        print()
        print("Starting server...")
        print("Open http://localhost:5000 in your browser")
        print()
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("✗ Database connection failed!")
        print("Please run the SQL script first: database/BusTicketSystem_CreateDB.sql")

