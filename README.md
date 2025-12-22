# 🚌 Bus Ticket System - Database Management System

## CENG 301 - Database Systems Term Project (Fall 2025)

---

### 👥 Project Team

| Name | Student ID |
|------|------------|
| **Alp Doruk Şengün** | 230444401 |
| **Zeynep Azra Doyğun** | 220444055 |
| **İdil Bilgen** | 220444402 |
| **Kübra Alkan** | 220444046 |

---

## 📋 Project Overview

This project implements a **Bus Ticket Booking System** as a comprehensive Database Management System (DBMS) solution. The system enables users to search for bus trips, book seats, manage tickets, and process payments - all powered by a well-designed relational database with **Microsoft SQL Server**.

### Technologies Used

| Component | Technology |
|-----------|------------|
| **Database** | Microsoft SQL Server (MSSQL) |
| **Backend** | Python 3.x + Flask |
| **Frontend** | HTML5, CSS3, JavaScript |
| **DB Connection** | pyodbc |

---

## 🗄️ DATABASE DESIGN

### Entity-Relationship (ER) Model

The database follows a normalized design (3NF) with the following main entities:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CITIES    │     │  COMPANIES  │     │    USERS    │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ CityID (PK) │     │CompanyID(PK)│     │ UserID (PK) │
│ CityName    │     │ CompanyName │     │ FirstName   │
│ IsActive    │     │ Phone       │     │ LastName    │
└─────────────┘     │ Email       │     │ Email       │
       │            │ Rating      │     │ PasswordHash│
       │            └─────────────┘     │ CreditBalance│
       │                   │            │ Role        │
       ▼                   ▼            └─────────────┘
┌─────────────┐     ┌─────────────┐            │
│   TRIPS     │◄────│    BUSES    │            │
├─────────────┤     ├─────────────┤            │
│ TripID (PK) │     │ BusID (PK)  │            │
│ BusID (FK)  │     │CompanyID(FK)│            │
│DepartureCityID(FK)│ PlateNumber │            │
│ArrivalCityID(FK)│ │ TotalSeats  │            │
│ DepartureDate│    │ HasWifi     │            │
│ DepartureTime│    │ HasTV       │            │
│ Price       │     └─────────────┘            │
│AvailableSeats│           │                   │
└─────────────┘            ▼                   │
       │            ┌─────────────┐            │
       │            │    SEATS    │            │
       │            ├─────────────┤            │
       │            │ SeatID (PK) │            │
       │            │ BusID (FK)  │            │
       │            │ SeatNumber  │            │
       │            │ SeatRow     │            │
       │            │ SeatColumn  │            │
       │            └─────────────┘            │
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────────────────────────────────────────┐
│                    TICKETS                        │
├──────────────────────────────────────────────────┤
│ TicketID (PK)                                    │
│ UserID (FK) ──────────────────────────────────►  │
│ TripID (FK) ◄────────────────────────────────    │
│ TotalPrice, DiscountAmount, FinalPrice           │
│ Status (Active/Completed/Cancelled)              │
└──────────────────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  TICKET_SEATS   │
              ├─────────────────┤
              │ TicketID (FK)   │
              │ SeatID (FK)     │
              │ TripID (FK)     │
              │ PassengerName   │
              └─────────────────┘
```

---

### 📊 Database Tables (11 Tables)

#### 1. Cities
Stores all available cities for bus routes.

```sql
CREATE TABLE Cities (
    CityID INT IDENTITY(1,1) PRIMARY KEY,
    CityName NVARCHAR(100) NOT NULL UNIQUE,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE()
);
```

#### 2. Companies
Stores bus company information.

```sql
CREATE TABLE Companies (
    CompanyID INT IDENTITY(1,1) PRIMARY KEY,
    CompanyName NVARCHAR(100) NOT NULL UNIQUE,
    Phone NVARCHAR(20) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    Rating DECIMAL(2,1) DEFAULT 0.0 CHECK (Rating >= 0 AND Rating <= 5),
    IsActive BIT DEFAULT 1
);
```

#### 3. Users
Stores customer and admin accounts.

```sql
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    Phone NVARCHAR(20) NOT NULL,
    PasswordHash NVARCHAR(256) NOT NULL,
    IDNumber NVARCHAR(11) NOT NULL UNIQUE,  -- Turkish ID (TC Kimlik No)
    Role NVARCHAR(20) DEFAULT 'User' CHECK (Role IN ('User', 'SystemAdmin')),
    CreditBalance DECIMAL(10,2) DEFAULT 0.00 CHECK (CreditBalance >= 0),
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE()
);
```

#### 4. Buses
Stores physical bus information with amenities.

```sql
CREATE TABLE Buses (
    BusID INT IDENTITY(1,1) PRIMARY KEY,
    CompanyID INT NOT NULL FOREIGN KEY REFERENCES Companies(CompanyID),
    PlateNumber NVARCHAR(20) NOT NULL UNIQUE,
    TotalSeats INT NOT NULL DEFAULT 40 CHECK (TotalSeats > 0 AND TotalSeats <= 60),
    HasWifi BIT DEFAULT 0,
    HasTV BIT DEFAULT 0,
    HasRefreshments BIT DEFAULT 0,
    HasPowerOutlet BIT DEFAULT 0,
    HasEntertainment BIT DEFAULT 0
);
```

#### 5. Seats
Stores seat layout for each bus (2+2 configuration).

```sql
CREATE TABLE Seats (
    SeatID INT IDENTITY(1,1) PRIMARY KEY,
    BusID INT NOT NULL FOREIGN KEY REFERENCES Buses(BusID),
    SeatNumber INT NOT NULL CHECK (SeatNumber > 0),
    SeatRow INT NOT NULL,
    SeatColumn NVARCHAR(1) NOT NULL,  -- A, B (left) | C, D (right)
    CONSTRAINT UQ_Seats_BusSeat UNIQUE (BusID, SeatNumber)
);
```

#### 6. Trips
Stores scheduled bus trips.

```sql
CREATE TABLE Trips (
    TripID INT IDENTITY(1,1) PRIMARY KEY,
    TripCode NVARCHAR(20) NOT NULL UNIQUE,
    BusID INT NOT NULL FOREIGN KEY REFERENCES Buses(BusID),
    DepartureCityID INT NOT NULL FOREIGN KEY REFERENCES Cities(CityID),
    ArrivalCityID INT NOT NULL FOREIGN KEY REFERENCES Cities(CityID),
    DepartureDate DATE NOT NULL,
    DepartureTime TIME NOT NULL,
    ArrivalTime TIME NOT NULL,
    DurationMinutes INT NOT NULL CHECK (DurationMinutes > 0),
    Price DECIMAL(10,2) NOT NULL CHECK (Price > 0),
    AvailableSeats INT NOT NULL,
    Status NVARCHAR(20) DEFAULT 'Active' CHECK (Status IN ('Active', 'Completed', 'Cancelled')),
    CONSTRAINT CK_Trips_DifferentCities CHECK (DepartureCityID <> ArrivalCityID)
);
```

#### 7. Coupons
Stores discount coupons with usage limits.

```sql
CREATE TABLE Coupons (
    CouponID INT IDENTITY(1,1) PRIMARY KEY,
    CouponCode NVARCHAR(50) NOT NULL UNIQUE,
    DiscountRate DECIMAL(5,2) NOT NULL CHECK (DiscountRate > 0 AND DiscountRate <= 100),
    UsageLimit INT NOT NULL CHECK (UsageLimit > 0),
    TimesUsed INT DEFAULT 0,
    ExpiryDate DATE NOT NULL,
    IsActive BIT DEFAULT 1
);
```

#### 8. Tickets
Stores purchased tickets with pricing.

```sql
CREATE TABLE Tickets (
    TicketID INT IDENTITY(1,1) PRIMARY KEY,
    TicketCode NVARCHAR(20) NOT NULL UNIQUE,
    UserID INT NOT NULL FOREIGN KEY REFERENCES Users(UserID),
    TripID INT NOT NULL FOREIGN KEY REFERENCES Trips(TripID),
    CouponID INT NULL FOREIGN KEY REFERENCES Coupons(CouponID),
    TotalPrice DECIMAL(10,2) NOT NULL,
    DiscountAmount DECIMAL(10,2) DEFAULT 0.00,
    FinalPrice DECIMAL(10,2) NOT NULL,
    Status NVARCHAR(20) DEFAULT 'Active' CHECK (Status IN ('Active', 'Completed', 'Cancelled')),
    PurchaseDate DATETIME DEFAULT GETDATE()
);
```

#### 9. TicketSeats
Many-to-many relationship between tickets and seats.

```sql
CREATE TABLE TicketSeats (
    TicketSeatID INT IDENTITY(1,1) PRIMARY KEY,
    TicketID INT NOT NULL FOREIGN KEY REFERENCES Tickets(TicketID),
    SeatID INT NOT NULL FOREIGN KEY REFERENCES Seats(SeatID),
    TripID INT NOT NULL FOREIGN KEY REFERENCES Trips(TripID),
    PassengerName NVARCHAR(100) NOT NULL,
    CONSTRAINT UQ_TicketSeats_TripSeat UNIQUE (TripID, SeatID)
);
```

#### 10. Payments
Stores all payment transactions.

```sql
CREATE TABLE Payments (
    PaymentID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL FOREIGN KEY REFERENCES Users(UserID),
    TicketID INT NULL FOREIGN KEY REFERENCES Tickets(TicketID),
    Amount DECIMAL(10,2) NOT NULL,
    PaymentType NVARCHAR(20) NOT NULL CHECK (PaymentType IN ('TicketPurchase', 'CreditTopUp', 'Refund')),
    PaymentMethod NVARCHAR(20) NOT NULL CHECK (PaymentMethod IN ('CreditCard', 'BankTransfer', 'UserCredit')),
    Status NVARCHAR(20) DEFAULT 'Completed',
    CreatedAt DATETIME DEFAULT GETDATE()
);
```

#### 11. UserCoupons
Tracks coupon assignments and usage per user.

```sql
CREATE TABLE UserCoupons (
    UserCouponID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL FOREIGN KEY REFERENCES Users(UserID),
    CouponID INT NOT NULL FOREIGN KEY REFERENCES Coupons(CouponID),
    IsUsed BIT DEFAULT 0,
    UsedAt DATETIME NULL,
    CONSTRAINT UQ_UserCoupons UNIQUE (UserID, CouponID)
);
```

---

## ⚡ STORED PROCEDURES

The system uses **stored procedures** for all complex database operations, ensuring efficient server-side processing and better security.

### 1. sp_SearchTrips
Searches for available trips based on route and date.

```sql
CREATE PROCEDURE sp_SearchTrips
    @DepartureCityID INT,
    @ArrivalCityID INT,
    @DepartureDate DATE
AS
BEGIN
    SELECT 
        t.TripID, t.TripCode, c.CompanyName, c.Rating AS CompanyRating,
        dep.CityName AS DepartureCity, arr.CityName AS ArrivalCity,
        t.DepartureDate, t.DepartureTime, t.ArrivalTime,
        t.DurationMinutes, t.Price, t.AvailableSeats,
        b.HasWifi, b.HasTV, b.HasRefreshments
    FROM Trips t
    INNER JOIN Buses b ON t.BusID = b.BusID
    INNER JOIN Companies c ON b.CompanyID = c.CompanyID
    INNER JOIN Cities dep ON t.DepartureCityID = dep.CityID
    INNER JOIN Cities arr ON t.ArrivalCityID = arr.CityID
    WHERE t.DepartureCityID = @DepartureCityID
      AND t.ArrivalCityID = @ArrivalCityID
      AND t.DepartureDate = @DepartureDate
      AND t.Status = 'Active'
      AND t.AvailableSeats > 0
    ORDER BY t.DepartureTime;
END
```

### 2. sp_GetTripSeatStatus
Returns seat availability for a specific trip.

```sql
CREATE PROCEDURE sp_GetTripSeatStatus
    @TripID INT
AS
BEGIN
    SELECT 
        s.SeatID, s.SeatNumber, s.SeatRow, s.SeatColumn,
        CASE 
            WHEN ts.TicketSeatID IS NOT NULL THEN 'Occupied'
            ELSE 'Available'
        END AS SeatStatus
    FROM Trips t
    INNER JOIN Buses b ON t.BusID = b.BusID
    INNER JOIN Seats s ON b.BusID = s.BusID
    LEFT JOIN TicketSeats ts ON s.SeatID = ts.SeatID AND ts.TripID = @TripID
    WHERE t.TripID = @TripID
    ORDER BY s.SeatRow, s.SeatColumn;
END
```

### 3. sp_PurchaseTicket (Transaction Example)
Handles complete ticket purchase with **ACID transaction**.

```sql
CREATE PROCEDURE sp_PurchaseTicket
    @UserID INT,
    @TripID INT,
    @SeatIDs NVARCHAR(MAX),      -- Comma-separated: '1,2,3'
    @PassengerNames NVARCHAR(MAX), -- Pipe-separated: 'Name1|Name2|Name3'
    @CouponCode NVARCHAR(50) = NULL
AS
BEGIN
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;
    
    -- 1. Validate trip availability
    -- 2. Check seat availability
    -- 3. Validate coupon (if provided)
    -- 4. Calculate total price with discount
    -- 5. Check user credit balance
    -- 6. Create ticket record
    -- 7. Create ticket-seat relationships
    -- 8. Update available seats count
    -- 9. Deduct user credit
    -- 10. Record payment transaction
    -- 11. Update coupon usage
    
    COMMIT TRANSACTION;
END
```

### 4. sp_CancelTicket
Cancels ticket and processes refund.

```sql
CREATE PROCEDURE sp_CancelTicket
    @TicketID INT,
    @UserID INT
AS
BEGIN
    BEGIN TRANSACTION;
    
    -- 1. Validate ticket ownership
    -- 2. Check if ticket is active
    -- 3. Calculate refund amount
    -- 4. Update ticket status to 'Cancelled'
    -- 5. Release seats (update trip available seats)
    -- 6. Refund to user credit balance
    -- 7. Record refund payment
    
    COMMIT TRANSACTION;
END
```

### 5. sp_GetUserTickets
Retrieves all tickets for a user with details.

```sql
CREATE PROCEDURE sp_GetUserTickets
    @UserID INT,
    @StatusFilter NVARCHAR(20) = NULL
AS
BEGIN
    SELECT 
        t.TicketID, t.TicketCode, c.CompanyName,
        dep.CityName AS DepartureCity, arr.CityName AS ArrivalCity,
        tr.DepartureDate, tr.DepartureTime, tr.ArrivalTime,
        t.FinalPrice, t.Status,
        STRING_AGG(s.SeatNumber, ', ') AS SeatNumbers
    FROM Tickets t
    INNER JOIN Trips tr ON t.TripID = tr.TripID
    -- ... joins ...
    WHERE t.UserID = @UserID
      AND (@StatusFilter IS NULL OR t.Status = @StatusFilter)
    GROUP BY t.TicketID, ...
    ORDER BY t.PurchaseDate DESC;
END
```

### 6. sp_ValidateCoupon
Validates coupon code for a user.

```sql
CREATE PROCEDURE sp_ValidateCoupon
    @CouponCode NVARCHAR(50),
    @UserID INT
AS
BEGIN
    -- Check: exists, active, not expired, usage limit, user hasn't used
    SELECT 
        CASE WHEN valid THEN 1 ELSE 0 END AS IsValid,
        DiscountRate,
        Message
    FROM Coupons
    WHERE CouponCode = @CouponCode
      AND IsActive = 1
      AND ExpiryDate >= GETDATE()
      AND TimesUsed < UsageLimit;
END
```

### 7. sp_AddUserCredit
Adds credit to user account.

```sql
CREATE PROCEDURE sp_AddUserCredit
    @UserID INT,
    @Amount DECIMAL(10,2),
    @PaymentMethod NVARCHAR(20)
AS
BEGIN
    BEGIN TRANSACTION;
    
    UPDATE Users SET CreditBalance = CreditBalance + @Amount WHERE UserID = @UserID;
    
    INSERT INTO Payments (UserID, Amount, PaymentType, PaymentMethod, Status)
    VALUES (@UserID, @Amount, 'CreditTopUp', @PaymentMethod, 'Completed');
    
    COMMIT TRANSACTION;
END
```

---

## 📈 Performance Optimization

### Indexes

```sql
-- Trip search optimization
CREATE INDEX IX_Trips_Search ON Trips(DepartureCityID, ArrivalCityID, DepartureDate, Status);
CREATE INDEX IX_Trips_DepartureDate ON Trips(DepartureDate);

-- Ticket lookup optimization
CREATE INDEX IX_Tickets_UserID ON Tickets(UserID);
CREATE INDEX IX_Tickets_Status ON Tickets(Status);

-- Seat availability optimization
CREATE INDEX IX_TicketSeats_TripID ON TicketSeats(TripID);

-- User authentication optimization
CREATE INDEX IX_Users_Email ON Users(Email);
```

### Sequences

```sql
-- Auto-generate unique ticket codes: TKT-2025-000001
CREATE SEQUENCE TicketSequence START WITH 1000 INCREMENT BY 1;

-- Auto-generate unique trip codes: TRP-2025-000001
CREATE SEQUENCE TripSequence START WITH 100 INCREMENT BY 1;
```

---

## 🔐 Security Features

1. **Password Hashing**: SHA-256 algorithm
2. **Parameterized Queries**: Prevents SQL injection
3. **Role-Based Access**: User vs SystemAdmin
4. **Transaction Integrity**: ACID compliance for critical operations
5. **Constraint Validation**: CHECK constraints on all tables

---

## 📁 Project Structure

```
busticketsystem_database/
│
├── database/
│   └── BusTicketSystem_CreateDB.sql   # Complete SQL script
│
├── backend/
│   ├── app.py                # Flask REST API
│   ├── database_manager.py   # Database operations (pyodbc)
│   ├── config.py             # Configuration settings
│   ├── utils.py              # Helper functions
│   └── requirements.txt      # Python dependencies
│
├── frontend/
│   ├── index.html            # Home page - Trip search
│   ├── login.html            # User login
│   ├── register.html         # User registration
│   ├── services.html         # Trip results
│   ├── chooseSeat.html       # Seat selection
│   ├── MyTickets.html        # User dashboard
│   └── adminPanel.html       # Admin panel
│
└── README.md
```

---

## 🚀 Installation & Setup

### 1. Database Setup (MSSQL)

```sql
-- Run in SQL Server Management Studio (SSMS)
-- Open and execute: database/BusTicketSystem_CreateDB.sql
```

### 2. Backend Setup (Python)

```bash
cd backend
pip install -r requirements.txt

# Configure database connection in config.py
# Set DB_SERVER, DB_DATABASE, USE_WINDOWS_AUTH

python app.py
```

### 3. Access the Application

Open browser: `http://localhost:5000`

---

## 👤 Test Accounts

| Role | Email | Password |
|------|-------|----------|
| User | ahmet.yilmaz@email.com | password123 |
| Admin | admin@busticket.com | password123 |

---

## 📊 Sample Data

The database includes sample data for testing:

- **15 Cities**: Istanbul, Ankara, Izmir, Antalya, Bursa...
- **3 Companies**: Metro Turizm, Pamukkale, Kamil Koç
- **6 Buses**: With various amenities
- **10+ Trips**: Different routes and dates
- **4 Coupons**: DISCOUNT10, DISCOUNT20, SUMMER25, WELCOME50
- **4 Users**: Including 1 admin account

---

## 📝 SQL Query Examples

### Find most popular routes:
```sql
SELECT 
    dep.CityName AS FromCity,
    arr.CityName AS ToCity,
    COUNT(*) AS TripCount
FROM Trips t
JOIN Cities dep ON t.DepartureCityID = dep.CityID
JOIN Cities arr ON t.ArrivalCityID = arr.CityID
GROUP BY dep.CityName, arr.CityName
ORDER BY TripCount DESC;
```

### Monthly revenue report:
```sql
SELECT 
    YEAR(PurchaseDate) AS Year,
    MONTH(PurchaseDate) AS Month,
    COUNT(*) AS TicketsSold,
    SUM(FinalPrice) AS TotalRevenue
FROM Tickets
WHERE Status IN ('Active', 'Completed')
GROUP BY YEAR(PurchaseDate), MONTH(PurchaseDate)
ORDER BY Year DESC, Month DESC;
```

### Company performance:
```sql
SELECT 
    c.CompanyName,
    COUNT(DISTINCT t.TripID) AS TotalTrips,
    COUNT(tk.TicketID) AS TicketsSold,
    SUM(tk.FinalPrice) AS Revenue
FROM Companies c
LEFT JOIN Buses b ON c.CompanyID = b.CompanyID
LEFT JOIN Trips t ON b.BusID = t.BusID
LEFT JOIN Tickets tk ON t.TripID = tk.TripID
GROUP BY c.CompanyID, c.CompanyName
ORDER BY Revenue DESC;
```

---

## 📄 License

This project was developed for **CENG 301 - Database Systems** course at [University Name], Fall 2025.

---

**© 2025 Bus Ticket System Project Team**
