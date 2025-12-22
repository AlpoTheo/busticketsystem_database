# 🚌 Bus Ticket System
## CENG 301 Database Systems Project

A comprehensive bus ticket booking system built with **Python Flask** backend and **HTML/CSS/JavaScript** frontend, connected to **Microsoft SQL Server** database.

---

## 📋 Project Structure

```
busticketsystem_database/
├── backend/
│   ├── app.py              # Flask API server
│   ├── config.py           # Database configuration
│   ├── database_manager.py # Database operations
│   ├── utils.py            # Utility functions
│   └── requirements.txt    # Python dependencies
├── database/
│   └── BusTicketSystem_CreateDB.sql  # Database creation script
├── frontend/
│   ├── index.html          # Home page (search)
│   ├── login.html          # User login
│   ├── register.html       # User registration
│   ├── services.html       # Trip search results
│   ├── chooseSeat.html     # Seat selection
│   ├── MyTickets.html      # User dashboard
│   ├── adminPanel.html     # System admin panel
│   └── firmAdminpanel.html # Company admin panel
└── README.md
```

---

## 🚀 Setup Instructions

### Prerequisites

1. **Python 3.8+** - [Download](https://www.python.org/downloads/)
2. **Microsoft SQL Server** - [Download](https://www.microsoft.com/en-us/sql-server/sql-server-downloads)
3. **ODBC Driver for SQL Server** - [Download](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### Step 1: Create the Database

1. Open **SQL Server Management Studio (SSMS)**
2. Connect to your SQL Server instance
3. Open the file `database/BusTicketSystem_CreateDB.sql`
4. Execute the script (F5) to create:
   - Database
   - Tables (13 tables)
   - Stored Procedures (9 procedures)
   - Sample data

### Step 2: Configure Database Connection

1. Open `backend/config.py`
2. Update the following settings:

```python
# SQL Server connection settings
DB_SERVER = 'localhost'  # Your server name
DB_DATABASE = 'BusTicketSystem'
DB_USERNAME = 'sa'       # Your username
DB_PASSWORD = 'your_password'  # Your password

# ODBC Driver - Use one that's installed on your system
DB_DRIVER = '{ODBC Driver 17 for SQL Server}'
```

### Step 3: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
cd backend
python app.py
```

The server will start at: **http://localhost:5000**

---

## 🎯 Features

### User Features
- ✅ User registration and login
- ✅ Search trips by city and date
- ✅ View trip details and bus amenities
- ✅ Interactive seat selection
- ✅ Apply discount coupons
- ✅ Purchase tickets using credit
- ✅ View and cancel tickets
- ✅ Top up account credit
- ✅ View payment history

### Admin Features
- ✅ System dashboard with statistics
- ✅ Manage companies
- ✅ Manage users
- ✅ Create and manage coupons

### Company Admin Features
- ✅ Company dashboard
- ✅ Create and manage trips
- ✅ View ticket sales
- ✅ Manage buses

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Register new user |
| POST | `/api/login` | User login |
| POST | `/api/logout` | Logout |
| GET | `/api/session` | Get session info |

### Trips
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cities` | Get all cities |
| GET | `/api/trips/search` | Search trips |
| GET | `/api/trips/{id}` | Get trip details |
| GET | `/api/trips/{id}/seats` | Get seat status |

### Tickets
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tickets/purchase` | Purchase ticket |
| GET | `/api/tickets` | Get user tickets |
| POST | `/api/tickets/{id}/cancel` | Cancel ticket |

### Credit & Coupons
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/credit/add` | Add credit |
| GET | `/api/credit/balance` | Get balance |
| POST | `/api/coupons/validate` | Validate coupon |
| GET | `/api/coupons` | Get user coupons |

---

## 🗄️ Database Schema

### Main Tables
1. **Users** - User accounts
2. **Companies** - Bus companies
3. **Cities** - City list
4. **Buses** - Bus fleet
5. **Seats** - Bus seats
6. **Trips** - Trip schedules
7. **Tickets** - Purchased tickets
8. **Payments** - Payment transactions
9. **Coupons** - Discount coupons
10. **CouponUsage** - Coupon usage tracking
11. **FirmAdmins** - Company administrators

### Stored Procedures
- `sp_SearchTrips` - Search available trips
- `sp_GetTripSeatStatus` - Get seat availability
- `sp_PurchaseTicket` - Process ticket purchase
- `sp_CancelTicket` - Cancel ticket and refund
- `sp_GetUserTickets` - Get user's tickets
- `sp_AddUserCredit` - Add credit to account
- `sp_ValidateCoupon` - Validate discount code
- `sp_GetDashboardStats` - Admin dashboard stats
- `sp_CreateTrip` - Create new trip

---

## 🔐 Test Accounts

After running the database script, you can use these accounts:

| Type | Email | Password |
|------|-------|----------|
| User | ahmet.yilmaz@email.com | password123 |
| User | fatma.kaya@email.com | password123 |
| System Admin | admin@busticket.com | admin123 |

---

## 🛠️ Troubleshooting

### "Connection error" on startup
- Check if SQL Server is running
- Verify username/password in `config.py`
- Make sure ODBC driver is installed
- Try changing `DB_DRIVER` to `'{SQL Server}'`

### "No trips found"
- Make sure you've run the database script
- Check if sample data was inserted

### Windows Authentication
If you want to use Windows Authentication:
```python
USE_WINDOWS_AUTH = True
DB_USERNAME = ''
DB_PASSWORD = ''
```

---

## 📝 Project Requirements Met

✅ **ER Model** - Comprehensive entity-relationship design
✅ **Normalization** - Database normalized to 3NF
✅ **Stored Procedures** - 9 procedures for complex operations
✅ **Efficient Queries** - Database-side processing
✅ **User Interface** - Modern, responsive web UI
✅ **Python Backend** - Flask REST API
✅ **MSSQL Database** - Microsoft SQL Server

---

## 👨‍💻 Development

### Run in Debug Mode
```bash
python app.py
```
The Flask debug mode is enabled by default.

### Testing API Endpoints
Use tools like **Postman** or **curl** to test API endpoints.

---

## 📄 License

This project is created for educational purposes as part of CENG 301 Database Systems course.

