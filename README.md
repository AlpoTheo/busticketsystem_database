# 🚌 Bus Ticket System - Database Design Documentation

## CENG 301 Database Systems Project - Phase 1

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Table Descriptions](#table-descriptions)
4. [Relationships & Foreign Keys](#relationships--foreign-keys)
5. [Stored Procedures](#stored-procedures)
6. [Normalization Analysis](#normalization-analysis)
7. [Sample Queries](#sample-queries)

---

## 🎯 System Overview

The Bus Ticket System is designed to manage:

| Module | Description |
|--------|-------------|
| **User Management** | Customer registration, login, profile, credit system |
| **Company Management** | Bus firms, their buses, and administrators |
| **Trip Management** | Scheduling trips with departure/arrival cities and times |
| **Ticket Booking** | Seat selection, purchase, cancellation |
| **Payment System** | Credit top-up, ticket payments, refunds |
| **Coupon System** | Discount coupons with usage limits and expiry |
| **Admin Panels** | System admin and Firm admin dashboards |

### User Roles

| Role | Permissions |
|------|-------------|
| **Customer (User)** | Search trips, buy tickets, manage profile, view history |
| **Firm Admin** | Manage company's trips, view tickets, generate reports |
| **System Admin** | Full access: manage firms, admins, coupons, users |

---

## 📊 Entity Relationship Diagram

```
                                    ┌─────────────────┐
                                    │  SystemAdmins   │
                                    │─────────────────│
                                    │ PK AdminID      │
                                    │ Username        │
                                    │ Email           │
                                    │ PasswordHash    │
                                    └─────────────────┘

┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│     Cities      │        │   Companies     │        │   FirmAdmins    │
│─────────────────│        │─────────────────│        │─────────────────│
│ PK CityID       │        │ PK CompanyID    │◄───────│ PK FirmAdminID  │
│ CityName        │        │ CompanyName     │   1:N  │ FK CompanyID    │
│ IsActive        │        │ Phone, Email    │        │ FirstName       │
└────────┬────────┘        │ Rating          │        │ LastName        │
         │                 └────────┬────────┘        │ Email, Phone    │
         │                          │                 └─────────────────┘
         │                          │
    ┌────┴────┐                     │ 1:N
    │         │                     │
    ▼         ▼                     ▼
┌───────┐ ┌───────┐        ┌─────────────────┐
│ From  │ │  To   │        │     Buses       │
│ City  │ │ City  │        │─────────────────│
└───┬───┘ └───┬───┘        │ PK BusID        │
    │         │            │ FK CompanyID    │
    │         │            │ PlateNumber     │
    │         │            │ TotalSeats      │
    │         │            │ HasWifi, etc.   │
    │         │            └────────┬────────┘
    │         │                     │
    │    ┌────┴─────────────────────┘
    │    │                          │
    │    │                          │ 1:N
    ▼    ▼                          ▼
┌─────────────────┐        ┌─────────────────┐
│     Trips       │        │     Seats       │
│─────────────────│        │─────────────────│
│ PK TripID       │        │ PK SeatID       │
│ TripCode        │        │ FK BusID        │
│ FK BusID        │        │ SeatNumber      │
│ FK DepartureCity│        │ SeatRow         │
│ FK ArrivalCity  │        │ SeatColumn      │
│ DepartureDate   │        └────────┬────────┘
│ DepartureTime   │                 │
│ ArrivalTime     │                 │
│ Price           │                 │
│ AvailableSeats  │                 │
└────────┬────────┘                 │
         │                          │
         │ 1:N                      │
         │                          │
         ▼                          │
┌─────────────────┐                 │
│    Tickets      │                 │
│─────────────────│                 │
│ PK TicketID     │                 │
│ TicketCode      │                 │
│ FK UserID       │◄────────┐      │
│ FK TripID       │         │      │
│ FK CouponID     │    ┌────┴──────┴──────┐
│ TotalPrice      │    │                  │
│ DiscountAmount  │    │  TicketSeats     │
│ FinalPrice      │    │──────────────────│
│ Status          │◄───│ PK TicketSeatID  │
└─────────────────┘    │ FK TicketID      │
                       │ FK SeatID        │
┌─────────────────┐    │ FK TripID        │
│     Users       │    │ PassengerName    │
│─────────────────│    └──────────────────┘
│ PK UserID       │
│ FirstName       │    ┌─────────────────┐
│ LastName        │    │    Coupons      │
│ Email           │    │─────────────────│
│ Phone           │    │ PK CouponID     │
│ PasswordHash    │    │ CouponCode      │
│ IDNumber        │    │ DiscountRate    │
│ CreditBalance   │    │ UsageLimit      │
│ IsActive        │    │ TimesUsed       │
└────────┬────────┘    │ ExpiryDate      │
         │             └────────┬────────┘
         │                      │
         │     ┌────────────────┘
         │     │
         ▼     ▼
┌─────────────────────────┐    ┌─────────────────┐
│     UserCoupons         │    │    Payments     │
│─────────────────────────│    │─────────────────│
│ PK UserCouponID         │    │ PK PaymentID    │
│ FK UserID               │    │ FK UserID       │
│ FK CouponID             │    │ FK TicketID     │
│ IsUsed                  │    │ Amount          │
│ UsedAt                  │    │ PaymentType     │
└─────────────────────────┘    │ PaymentMethod   │
                               │ Status          │
                               └─────────────────┘
```

---

## 📝 Table Descriptions

### 1. Cities
| Column | Type | Description |
|--------|------|-------------|
| CityID | INT (PK) | Unique identifier |
| CityName | NVARCHAR(100) | City name (unique) |
| IsActive | BIT | Active status |

### 2. Companies (Bus Firms)
| Column | Type | Description |
|--------|------|-------------|
| CompanyID | INT (PK) | Unique identifier |
| CompanyName | NVARCHAR(100) | Company name (unique) |
| Phone | NVARCHAR(20) | Contact phone |
| Email | NVARCHAR(100) | Contact email (unique) |
| Address | NVARCHAR(500) | Company address |
| Rating | DECIMAL(2,1) | Average rating (0-5) |
| TotalRatings | INT | Number of ratings |
| IsActive | BIT | Active status |

### 3. Users (Customers)
| Column | Type | Description |
|--------|------|-------------|
| UserID | INT (PK) | Unique identifier |
| FirstName | NVARCHAR(50) | First name |
| LastName | NVARCHAR(50) | Last name |
| Email | NVARCHAR(100) | Email (unique) |
| Phone | NVARCHAR(20) | Phone number |
| PasswordHash | NVARCHAR(256) | Hashed password |
| IDNumber | NVARCHAR(11) | Turkish ID (unique) |
| CreditBalance | DECIMAL(10,2) | Account balance |
| IsActive | BIT | Active status |

### 4. Buses
| Column | Type | Description |
|--------|------|-------------|
| BusID | INT (PK) | Unique identifier |
| CompanyID | INT (FK) | Owner company |
| PlateNumber | NVARCHAR(20) | License plate (unique) |
| TotalSeats | INT | Seat capacity (max 60) |
| HasWifi | BIT | WiFi available |
| HasTV | BIT | TV available |
| HasRefreshments | BIT | Refreshments available |
| HasPowerOutlet | BIT | Power outlets |
| HasEntertainment | BIT | Entertainment system |

### 5. Trips
| Column | Type | Description |
|--------|------|-------------|
| TripID | INT (PK) | Unique identifier |
| TripCode | NVARCHAR(20) | Trip code (unique) |
| BusID | INT (FK) | Assigned bus |
| DepartureCityID | INT (FK) | From city |
| ArrivalCityID | INT (FK) | To city |
| DepartureDate | DATE | Travel date |
| DepartureTime | TIME | Departure time |
| ArrivalTime | TIME | Estimated arrival |
| DurationMinutes | INT | Trip duration |
| Price | DECIMAL(10,2) | Ticket price |
| AvailableSeats | INT | Remaining seats |
| Status | NVARCHAR(20) | Active/Completed/Cancelled |

### 6. Tickets
| Column | Type | Description |
|--------|------|-------------|
| TicketID | INT (PK) | Unique identifier |
| TicketCode | NVARCHAR(20) | Ticket code (unique) |
| UserID | INT (FK) | Buyer |
| TripID | INT (FK) | Trip reference |
| CouponID | INT (FK) | Applied coupon (nullable) |
| TotalPrice | DECIMAL(10,2) | Price before discount |
| DiscountAmount | DECIMAL(10,2) | Discount applied |
| FinalPrice | DECIMAL(10,2) | Final amount paid |
| Status | NVARCHAR(20) | Active/Completed/Cancelled |

### 7. TicketSeats (Junction Table)
| Column | Type | Description |
|--------|------|-------------|
| TicketSeatID | INT (PK) | Unique identifier |
| TicketID | INT (FK) | Ticket reference |
| SeatID | INT (FK) | Seat reference |
| TripID | INT (FK) | Trip (denormalized) |
| PassengerName | NVARCHAR(100) | Passenger name |

### 8. Coupons
| Column | Type | Description |
|--------|------|-------------|
| CouponID | INT (PK) | Unique identifier |
| CouponCode | NVARCHAR(50) | Code (unique) |
| DiscountRate | DECIMAL(5,2) | Percentage (1-100) |
| UsageLimit | INT | Max usage count |
| TimesUsed | INT | Current usage |
| ExpiryDate | DATE | Expiration date |
| IsActive | BIT | Active status |

### 9. Payments
| Column | Type | Description |
|--------|------|-------------|
| PaymentID | INT (PK) | Unique identifier |
| UserID | INT (FK) | User reference |
| TicketID | INT (FK) | Ticket (nullable) |
| Amount | DECIMAL(10,2) | Payment amount |
| PaymentType | NVARCHAR(20) | Purchase/TopUp/Refund |
| PaymentMethod | NVARCHAR(20) | Card/Bank/Credit |
| Status | NVARCHAR(20) | Pending/Completed/Failed |

---

## 🔗 Relationships & Foreign Keys

| Table | Foreign Key | References | Relationship |
|-------|-------------|------------|--------------|
| FirmAdmins | CompanyID | Companies(CompanyID) | Many:1 |
| Buses | CompanyID | Companies(CompanyID) | Many:1 |
| Seats | BusID | Buses(BusID) | Many:1 |
| Trips | BusID | Buses(BusID) | Many:1 |
| Trips | DepartureCityID | Cities(CityID) | Many:1 |
| Trips | ArrivalCityID | Cities(CityID) | Many:1 |
| Tickets | UserID | Users(UserID) | Many:1 |
| Tickets | TripID | Trips(TripID) | Many:1 |
| Tickets | CouponID | Coupons(CouponID) | Many:1 |
| TicketSeats | TicketID | Tickets(TicketID) | Many:1 |
| TicketSeats | SeatID | Seats(SeatID) | Many:1 |
| UserCoupons | UserID | Users(UserID) | Many:Many |
| UserCoupons | CouponID | Coupons(CouponID) | Many:Many |
| Payments | UserID | Users(UserID) | Many:1 |
| Payments | TicketID | Tickets(TicketID) | Many:1 |

---

## ⚡ Stored Procedures

### 1. sp_SearchTrips (EFFICIENT QUERY EXAMPLE)
**Purpose:** Search available trips based on criteria

```sql
EXEC sp_SearchTrips 
    @DepartureCityID = 1,  -- Istanbul
    @ArrivalCityID = 2,     -- Ankara
    @DepartureDate = '2025-10-15',
    @SortBy = 'Price',
    @SortOrder = 'ASC';
```

**Why it's efficient:** Uses SQL JOINs and WHERE clauses instead of fetching all data to Python.

### 2. sp_PurchaseTicket (TRANSACTION EXAMPLE)
**Purpose:** Complete ticket purchase with seat reservation

```sql
DECLARE @TicketID INT, @Success BIT, @Message NVARCHAR(500);

EXEC sp_PurchaseTicket 
    @UserID = 1,
    @TripID = 1,
    @SeatIDs = '1,2',
    @CouponCode = 'DISCOUNT10',
    @PassengerNames = 'Ahmet Yilmaz,Fatma Yilmaz',
    @UseCredit = 1,
    @TicketID = @TicketID OUTPUT,
    @Success = @Success OUTPUT,
    @Message = @Message OUTPUT;

SELECT @TicketID, @Success, @Message;
```

**Features:**
- Transaction handling (BEGIN/COMMIT/ROLLBACK)
- Validates seat availability
- Applies coupon discounts
- Updates available seats
- Deducts user credit
- Records payment

### 3. sp_CancelTicket
**Purpose:** Cancel ticket with refund calculation

### 4. sp_GetUserTickets
**Purpose:** Get user's ticket history with filters

### 5. sp_AddUserCredit
**Purpose:** Top up user account balance

### 6. sp_GetDashboardStats
**Purpose:** Dashboard statistics for admins

### 7. sp_CreateTrip
**Purpose:** Firm admins create new trips

### 8. sp_ValidateCoupon
**Purpose:** Validate coupon before purchase

---

## 📐 Normalization Analysis

### First Normal Form (1NF) ✅
- All tables have atomic values
- No repeating groups
- Each column has unique name
- All entries in column are same type

### Second Normal Form (2NF) ✅
- Satisfies 1NF
- All non-key columns depend on entire primary key
- No partial dependencies

### Third Normal Form (3NF) ✅
- Satisfies 2NF
- No transitive dependencies
- Non-key columns depend only on primary key

**Example Analysis - Tickets Table:**
```
Tickets(TicketID, TicketCode, UserID, TripID, CouponID, 
        TotalPrice, DiscountAmount, FinalPrice, Status)

- Primary Key: TicketID
- All attributes depend on TicketID directly
- User info stored in Users table (no redundancy)
- Trip info stored in Trips table (no redundancy)
- No transitive dependencies
```

---

## 📊 Sample Queries

### 1. Find Top-Rated Companies
```sql
SELECT TOP 5 CompanyName, Rating, TotalRatings
FROM Companies
WHERE IsActive = 1
ORDER BY Rating DESC, TotalRatings DESC;
```
*Output: Returns oldest person without fetching all data*

### 2. Get Available Trips with Features
```sql
SELECT t.TripCode, c.CompanyName, 
       dep.CityName AS FromCity, arr.CityName AS ToCity,
       t.DepartureTime, t.Price, t.AvailableSeats,
       b.HasWifi, b.HasRefreshments
FROM Trips t
JOIN Buses b ON t.BusID = b.BusID
JOIN Companies c ON b.CompanyID = c.CompanyID
JOIN Cities dep ON t.DepartureCityID = dep.CityID
JOIN Cities arr ON t.ArrivalCityID = arr.CityID
WHERE t.DepartureDate = '2025-10-15'
  AND t.Status = 'Active'
ORDER BY t.DepartureTime;
```

### 3. Monthly Revenue Report
```sql
SELECT c.CompanyName,
       FORMAT(SUM(tk.FinalPrice), 'N2') AS Revenue,
       COUNT(tk.TicketID) AS TicketsSold
FROM Tickets tk
JOIN Trips t ON tk.TripID = t.TripID
JOIN Buses b ON t.BusID = b.BusID
JOIN Companies c ON b.CompanyID = c.CompanyID
WHERE tk.Status IN ('Active', 'Completed')
  AND MONTH(tk.PurchaseDate) = MONTH(GETDATE())
GROUP BY c.CompanyName
ORDER BY SUM(tk.FinalPrice) DESC;
```

### 4. Check Seat Availability (Using Stored Procedure)
```sql
EXEC sp_GetTripSeatStatus @TripID = 1;
```

---

## 🚀 Next Steps (Phase 2)

1. **Python Backend Development**
   - Create `DatabaseManager` class using `pyodbc`
   - Implement methods for all stored procedures
   - Handle connection pooling and error handling

2. **Frontend GUI Development**
   - Use CustomTkinter for modern UI
   - Implement all screens from HTML prototypes
   - Connect to DatabaseManager

---

## 📁 File Structure

```
busticketsystem_database/
├── database/
│   ├── BusTicketSystem_CreateDB.sql    # Main SQL script
│   └── README_Database_Design.md       # This documentation
├── frontend/
│   ├── index.html                      # Home page
│   ├── login.html                      # Login page
│   ├── register.html                   # Registration
│   ├── services.html                   # Trip listing
│   ├── chooseSeat.html                 # Seat selection
│   ├── MyTickets.html                  # User tickets
│   ├── adminPanel.html                 # System admin
│   └── firmAdminpanel.html             # Firm admin
├── backend/                            # (Phase 2)
│   ├── database_manager.py
│   └── ...
└── README.md
```

---

*Created for CENG 301 Database Systems Project - Fall 2025*
