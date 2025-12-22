# ============================================================================
# BUS TICKET SYSTEM - Main Entry Point
# CENG 301 Database Systems Project
# ============================================================================
# This is the main entry point for the application.
# Run this file to start the Bus Ticket System.
# ============================================================================

import sys
import os

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
from session_manager import session


def check_database_connection():
    """Check if database connection is working"""
    print("=" * 60)
    print("🚌 BUS TICKET SYSTEM")
    print("CENG 301 Database Systems Project")
    print("=" * 60)
    print()
    print("Checking database connection...")
    
    db = DatabaseManager()
    
    if db.test_connection():
        print("✓ Database connection successful!")
        print()
        
        # Show some statistics
        stats = db.get_dashboard_stats()
        if stats:
            print("📊 Database Statistics:")
            print(f"   • Total Companies: {stats.get('TotalCompanies', 0)}")
            print(f"   • Total Users: {stats.get('TotalUsers', 0)}")
            print(f"   • Active Trips: {stats.get('ActiveTrips', 0)}")
            print(f"   • Active Coupons: {stats.get('ActiveCoupons', 0)}")
        
        return True
    else:
        print("✗ Database connection failed!")
        print()
        print("Please make sure:")
        print("  1. SQL Server is running")
        print("  2. Database 'BusTicketSystem' has been created")
        print("     (Run the SQL script: database/BusTicketSystem_CreateDB.sql)")
        print("  3. Connection settings in config.py are correct")
        print()
        return False


def run_console_demo():
    """Run a console demo of the database operations"""
    db = DatabaseManager()
    
    print()
    print("=" * 60)
    print("CONSOLE DEMO")
    print("=" * 60)
    
    # 1. Get cities
    print("\n📍 Available Cities:")
    cities = db.get_all_cities()
    for city in cities[:5]:
        print(f"   • {city['city_name']}")
    if len(cities) > 5:
        print(f"   ... and {len(cities) - 5} more")
    
    # 2. Search trips (Istanbul -> Ankara)
    print("\n🚍 Sample Trip Search (Istanbul -> Ankara):")
    from datetime import date, timedelta
    tomorrow = date.today() + timedelta(days=1)
    trips = db.search_trips(1, 2, tomorrow)  # Istanbul=1, Ankara=2
    
    if trips:
        for trip in trips[:3]:
            print(f"   • {trip.get('CompanyName')}: {trip.get('DepartureTime')} - {trip.get('Price')} TL")
            print(f"     Available seats: {trip.get('AvailableSeats')}")
    else:
        print("   No trips found for this date")
    
    # 3. Get companies
    print("\n🏢 Bus Companies:")
    companies = db.get_all_companies()
    for company in companies[:4]:
        print(f"   • {company['company_name']} (Rating: {company['rating']}⭐)")
    
    # 4. Test user registration
    print("\n👤 User Registration Test:")
    success, message, user_id = db.register_user(
        first_name="Test",
        last_name="User",
        email="test.user@example.com",
        phone="0555 123 45 67",
        password="test123",
        id_number="12345678901"
    )
    print(f"   Result: {message}")
    
    print()
    print("=" * 60)
    print("Demo completed! Ready for GUI application.")
    print("=" * 60)


def main():
    """Main entry point"""
    # Check database connection first
    if not check_database_connection():
        input("\nPress Enter to exit...")
        return
    
    print()
    choice = input("Run console demo? (y/n): ").strip().lower()
    
    if choice == 'y':
        run_console_demo()
    
    print()
    print("To start the GUI application, run:")
    print("  python gui/app.py")
    print()
    print("(GUI will be created in Phase 3)")


if __name__ == "__main__":
    main()

