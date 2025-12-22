-- ============================================================================
-- BUS TICKET SYSTEM - DATABASE CREATION SCRIPT
-- CENG 301 Database Systems Project
-- Microsoft SQL Server (MSSQL)
-- ============================================================================
-- Description: This script creates the complete database schema for a
--              Bus Ticket Management System including tables, relationships,
--              constraints, stored procedures, and sample data.
-- ============================================================================

-- ============================================================================
-- SECTION 1: DATABASE CREATION
-- ============================================================================

-- Create Database
USE master;
GO

-- Drop database if exists (for development purposes)
IF EXISTS (SELECT name FROM sys.databases WHERE name = N'BusTicketSystem')
BEGIN
    ALTER DATABASE BusTicketSystem SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE BusTicketSystem;
END
GO

CREATE DATABASE BusTicketSystem;
GO

USE BusTicketSystem;
GO

-- ============================================================================
-- SECTION 2: TABLE CREATION
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: Cities
-- Description: Stores all cities available for bus routes
-- ----------------------------------------------------------------------------
CREATE TABLE Cities (
    CityID INT IDENTITY(1,1) PRIMARY KEY,
    CityName NVARCHAR(100) NOT NULL UNIQUE,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE()
);
GO

-- ----------------------------------------------------------------------------
-- Table: SystemAdmins
-- Description: Stores system-wide administrators
-- ----------------------------------------------------------------------------
CREATE TABLE SystemAdmins (
    AdminID INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(50) NOT NULL UNIQUE,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    PasswordHash NVARCHAR(256) NOT NULL,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE(),
    LastLoginAt DATETIME NULL
);
GO

-- ----------------------------------------------------------------------------
-- Table: Companies (Bus Firms)
-- Description: Stores bus company/firm information
-- ----------------------------------------------------------------------------
CREATE TABLE Companies (
    CompanyID INT IDENTITY(1,1) PRIMARY KEY,
    CompanyName NVARCHAR(100) NOT NULL UNIQUE,
    Phone NVARCHAR(20) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    Address NVARCHAR(500) NULL,
    Rating DECIMAL(2,1) DEFAULT 0.0 CHECK (Rating >= 0 AND Rating <= 5),
    TotalRatings INT DEFAULT 0,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME NULL
);
GO

-- ----------------------------------------------------------------------------
-- Table: FirmAdmins
-- Description: Stores administrators for each bus company
-- ----------------------------------------------------------------------------
CREATE TABLE FirmAdmins (
    FirmAdminID INT IDENTITY(1,1) PRIMARY KEY,
    CompanyID INT NOT NULL,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    Phone NVARCHAR(20) NOT NULL,
    PasswordHash NVARCHAR(256) NOT NULL,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE(),
    LastLoginAt DATETIME NULL,
    CONSTRAINT FK_FirmAdmins_Companies FOREIGN KEY (CompanyID) 
        REFERENCES Companies(CompanyID) ON DELETE CASCADE
);
GO

-- ----------------------------------------------------------------------------
-- Table: Users
-- Description: Stores customer/passenger information
-- ----------------------------------------------------------------------------
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    Phone NVARCHAR(20) NOT NULL,
    PasswordHash NVARCHAR(256) NOT NULL,
    IDNumber NVARCHAR(11) NOT NULL UNIQUE, -- Turkish ID number (11 digits)
    CreditBalance DECIMAL(10,2) DEFAULT 0.00 CHECK (CreditBalance >= 0),
    BirthDate DATE NULL,
    Address NVARCHAR(500) NULL,
    IsActive BIT DEFAULT 1,
    EmailNotifications BIT DEFAULT 1,
    SMSNotifications BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME NULL,
    LastLoginAt DATETIME NULL
);
GO

-- ----------------------------------------------------------------------------
-- Table: Buses
-- Description: Stores physical bus information for each company
-- ----------------------------------------------------------------------------
CREATE TABLE Buses (
    BusID INT IDENTITY(1,1) PRIMARY KEY,
    CompanyID INT NOT NULL,
    PlateNumber NVARCHAR(20) NOT NULL UNIQUE,
    TotalSeats INT NOT NULL DEFAULT 40 CHECK (TotalSeats > 0 AND TotalSeats <= 60),
    HasWifi BIT DEFAULT 0,
    HasTV BIT DEFAULT 0,
    HasRefreshments BIT DEFAULT 0,
    HasPowerOutlet BIT DEFAULT 0,
    HasEntertainment BIT DEFAULT 0,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Buses_Companies FOREIGN KEY (CompanyID) 
        REFERENCES Companies(CompanyID) ON DELETE CASCADE
);
GO

-- ----------------------------------------------------------------------------
-- Table: Seats
-- Description: Stores seat information for each bus
-- ----------------------------------------------------------------------------
CREATE TABLE Seats (
    SeatID INT IDENTITY(1,1) PRIMARY KEY,
    BusID INT NOT NULL,
    SeatNumber INT NOT NULL CHECK (SeatNumber > 0),
    SeatRow INT NOT NULL,
    SeatColumn NVARCHAR(1) NOT NULL, -- A, B, C, D (A-B left side, C-D right side)
    IsActive BIT DEFAULT 1,
    CONSTRAINT FK_Seats_Buses FOREIGN KEY (BusID) 
        REFERENCES Buses(BusID) ON DELETE CASCADE,
    CONSTRAINT UQ_Seats_BusSeat UNIQUE (BusID, SeatNumber)
);
GO

-- ----------------------------------------------------------------------------
-- Table: Trips
-- Description: Stores scheduled bus trips
-- ----------------------------------------------------------------------------
CREATE TABLE Trips (
    TripID INT IDENTITY(1,1) PRIMARY KEY,
    TripCode NVARCHAR(20) NOT NULL UNIQUE,
    BusID INT NOT NULL,
    DepartureCityID INT NOT NULL,
    ArrivalCityID INT NOT NULL,
    DepartureDate DATE NOT NULL,
    DepartureTime TIME NOT NULL,
    ArrivalTime TIME NOT NULL,
    DurationMinutes INT NOT NULL CHECK (DurationMinutes > 0),
    Price DECIMAL(10,2) NOT NULL CHECK (Price > 0),
    AvailableSeats INT NOT NULL,
    Status NVARCHAR(20) DEFAULT 'Active' 
        CHECK (Status IN ('Active', 'Completed', 'Cancelled', 'Delayed')),
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME NULL,
    CONSTRAINT FK_Trips_Buses FOREIGN KEY (BusID) 
        REFERENCES Buses(BusID),
    CONSTRAINT FK_Trips_DepartureCity FOREIGN KEY (DepartureCityID) 
        REFERENCES Cities(CityID),
    CONSTRAINT FK_Trips_ArrivalCity FOREIGN KEY (ArrivalCityID) 
        REFERENCES Cities(CityID),
    CONSTRAINT CK_Trips_DifferentCities CHECK (DepartureCityID <> ArrivalCityID)
);
GO

-- ----------------------------------------------------------------------------
-- Table: Coupons
-- Description: Stores discount coupons
-- ----------------------------------------------------------------------------
CREATE TABLE Coupons (
    CouponID INT IDENTITY(1,1) PRIMARY KEY,
    CouponCode NVARCHAR(50) NOT NULL UNIQUE,
    DiscountRate DECIMAL(5,2) NOT NULL CHECK (DiscountRate > 0 AND DiscountRate <= 100),
    UsageLimit INT NOT NULL CHECK (UsageLimit > 0),
    TimesUsed INT DEFAULT 0,
    Description NVARCHAR(500) NULL,
    ExpiryDate DATE NOT NULL,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE(),
    CreatedBy INT NULL -- SystemAdminID
);
GO

-- ----------------------------------------------------------------------------
-- Table: UserCoupons
-- Description: Tracks coupons assigned to users
-- ----------------------------------------------------------------------------
CREATE TABLE UserCoupons (
    UserCouponID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL,
    CouponID INT NOT NULL,
    IsUsed BIT DEFAULT 0,
    UsedAt DATETIME NULL,
    AssignedAt DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_UserCoupons_Users FOREIGN KEY (UserID) 
        REFERENCES Users(UserID) ON DELETE CASCADE,
    CONSTRAINT FK_UserCoupons_Coupons FOREIGN KEY (CouponID) 
        REFERENCES Coupons(CouponID) ON DELETE CASCADE,
    CONSTRAINT UQ_UserCoupons UNIQUE (UserID, CouponID)
);
GO

-- ----------------------------------------------------------------------------
-- Table: Tickets
-- Description: Stores purchased tickets
-- ----------------------------------------------------------------------------
CREATE TABLE Tickets (
    TicketID INT IDENTITY(1,1) PRIMARY KEY,
    TicketCode NVARCHAR(20) NOT NULL UNIQUE,
    UserID INT NOT NULL,
    TripID INT NOT NULL,
    CouponID INT NULL,
    TotalPrice DECIMAL(10,2) NOT NULL,
    DiscountAmount DECIMAL(10,2) DEFAULT 0.00,
    FinalPrice DECIMAL(10,2) NOT NULL,
    Status NVARCHAR(20) DEFAULT 'Active' 
        CHECK (Status IN ('Active', 'Completed', 'Cancelled', 'Refunded')),
    PurchaseDate DATETIME DEFAULT GETDATE(),
    CancellationDate DATETIME NULL,
    RefundAmount DECIMAL(10,2) NULL,
    CONSTRAINT FK_Tickets_Users FOREIGN KEY (UserID) 
        REFERENCES Users(UserID),
    CONSTRAINT FK_Tickets_Trips FOREIGN KEY (TripID) 
        REFERENCES Trips(TripID),
    CONSTRAINT FK_Tickets_Coupons FOREIGN KEY (CouponID) 
        REFERENCES Coupons(CouponID)
);
GO

-- ----------------------------------------------------------------------------
-- Table: TicketSeats
-- Description: Many-to-many relationship between tickets and seats
-- ----------------------------------------------------------------------------
CREATE TABLE TicketSeats (
    TicketSeatID INT IDENTITY(1,1) PRIMARY KEY,
    TicketID INT NOT NULL,
    SeatID INT NOT NULL,
    TripID INT NOT NULL, -- Denormalized for query performance
    PassengerName NVARCHAR(100) NOT NULL,
    PassengerIDNumber NVARCHAR(11) NULL,
    CONSTRAINT FK_TicketSeats_Tickets FOREIGN KEY (TicketID) 
        REFERENCES Tickets(TicketID) ON DELETE CASCADE,
    CONSTRAINT FK_TicketSeats_Seats FOREIGN KEY (SeatID) 
        REFERENCES Seats(SeatID),
    CONSTRAINT FK_TicketSeats_Trips FOREIGN KEY (TripID) 
        REFERENCES Trips(TripID),
    CONSTRAINT UQ_TicketSeats_TripSeat UNIQUE (TripID, SeatID)
);
GO

-- ----------------------------------------------------------------------------
-- Table: Payments
-- Description: Stores all payment transactions
-- ----------------------------------------------------------------------------
CREATE TABLE Payments (
    PaymentID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL,
    TicketID INT NULL, -- NULL for credit top-up payments
    Amount DECIMAL(10,2) NOT NULL,
    PaymentType NVARCHAR(20) NOT NULL 
        CHECK (PaymentType IN ('TicketPurchase', 'CreditTopUp', 'Refund')),
    PaymentMethod NVARCHAR(20) NOT NULL 
        CHECK (PaymentMethod IN ('CreditCard', 'BankTransfer', 'UserCredit')),
    Status NVARCHAR(20) DEFAULT 'Completed' 
        CHECK (Status IN ('Pending', 'Completed', 'Failed', 'Refunded')),
    TransactionReference NVARCHAR(100) NULL,
    CreatedAt DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Payments_Users FOREIGN KEY (UserID) 
        REFERENCES Users(UserID),
    CONSTRAINT FK_Payments_Tickets FOREIGN KEY (TicketID) 
        REFERENCES Tickets(TicketID)
);
GO

-- ----------------------------------------------------------------------------
-- Table: ActivityLogs
-- Description: Stores system activity logs for auditing
-- ----------------------------------------------------------------------------
CREATE TABLE ActivityLogs (
    LogID INT IDENTITY(1,1) PRIMARY KEY,
    ActionType NVARCHAR(50) NOT NULL,
    TableName NVARCHAR(50) NOT NULL,
    RecordID INT NULL,
    UserType NVARCHAR(20) NOT NULL, -- 'SystemAdmin', 'FirmAdmin', 'User'
    UserID INT NOT NULL,
    Description NVARCHAR(500) NOT NULL,
    OldValues NVARCHAR(MAX) NULL,
    NewValues NVARCHAR(MAX) NULL,
    IPAddress NVARCHAR(50) NULL,
    CreatedAt DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================================
-- SECTION 3: INDEXES FOR PERFORMANCE
-- ============================================================================

-- Trips indexes
CREATE INDEX IX_Trips_DepartureDate ON Trips(DepartureDate);
CREATE INDEX IX_Trips_DepartureCity ON Trips(DepartureCityID);
CREATE INDEX IX_Trips_ArrivalCity ON Trips(ArrivalCityID);
CREATE INDEX IX_Trips_Status ON Trips(Status);
CREATE INDEX IX_Trips_Search ON Trips(DepartureCityID, ArrivalCityID, DepartureDate, Status);

-- Tickets indexes
CREATE INDEX IX_Tickets_UserID ON Tickets(UserID);
CREATE INDEX IX_Tickets_TripID ON Tickets(TripID);
CREATE INDEX IX_Tickets_Status ON Tickets(Status);
CREATE INDEX IX_Tickets_PurchaseDate ON Tickets(PurchaseDate);

-- TicketSeats indexes
CREATE INDEX IX_TicketSeats_TripID ON TicketSeats(TripID);
CREATE INDEX IX_TicketSeats_SeatID ON TicketSeats(SeatID);

-- Users indexes
CREATE INDEX IX_Users_Email ON Users(Email);
CREATE INDEX IX_Users_IDNumber ON Users(IDNumber);

-- Payments indexes
CREATE INDEX IX_Payments_UserID ON Payments(UserID);
CREATE INDEX IX_Payments_CreatedAt ON Payments(CreatedAt);

GO

-- ============================================================================
-- SECTION 4: STORED PROCEDURES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Stored Procedure: sp_SearchTrips
-- Description: Searches for available trips based on criteria
-- This demonstrates EFFICIENT SQL querying as required by project guidelines
-- ----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE sp_SearchTrips
    @DepartureCityID INT,
    @ArrivalCityID INT,
    @DepartureDate DATE,
    @SortBy NVARCHAR(20) = 'DepartureTime', -- 'DepartureTime', 'Price', 'Duration'
    @SortOrder NVARCHAR(4) = 'ASC'
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Using specific SQL query instead of fetching all data and filtering in Python
    SELECT 
        t.TripID,
        t.TripCode,
        c.CompanyName,
        c.Rating AS CompanyRating,
        dep.CityName AS DepartureCity,
        arr.CityName AS ArrivalCity,
        t.DepartureDate,
        t.DepartureTime,
        t.ArrivalTime,
        t.DurationMinutes,
        t.Price,
        t.AvailableSeats,
        b.HasWifi,
        b.HasTV,
        b.HasRefreshments,
        b.HasPowerOutlet,
        b.HasEntertainment,
        t.Status
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
      AND c.IsActive = 1
    ORDER BY 
        CASE WHEN @SortBy = 'DepartureTime' AND @SortOrder = 'ASC' THEN t.DepartureTime END ASC,
        CASE WHEN @SortBy = 'DepartureTime' AND @SortOrder = 'DESC' THEN t.DepartureTime END DESC,
        CASE WHEN @SortBy = 'Price' AND @SortOrder = 'ASC' THEN t.Price END ASC,
        CASE WHEN @SortBy = 'Price' AND @SortOrder = 'DESC' THEN t.Price END DESC,
        CASE WHEN @SortBy = 'Duration' AND @SortOrder = 'ASC' THEN t.DurationMinutes END ASC,
        CASE WHEN @SortBy = 'Duration' AND @SortOrder = 'DESC' THEN t.DurationMinutes END DESC;
END
GO

-- ----------------------------------------------------------------------------
-- Stored Procedure: sp_GetTripSeatStatus
-- Description: Gets all seats and their availability for a specific trip
-- ----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE sp_GetTripSeatStatus
    @TripID INT
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        s.SeatID,
        s.SeatNumber,
        s.SeatRow,
        s.SeatColumn,
        CASE 
            WHEN ts.TicketSeatID IS NOT NULL THEN 'Occupied'
            ELSE 'Available'
        END AS SeatStatus,
        ts.PassengerName
    FROM Trips t
    INNER JOIN Buses b ON t.BusID = b.BusID
    INNER JOIN Seats s ON b.BusID = s.BusID
    LEFT JOIN TicketSeats ts ON s.SeatID = ts.SeatID 
        AND ts.TripID = @TripID
        AND EXISTS (SELECT 1 FROM Tickets tk WHERE tk.TicketID = ts.TicketID AND tk.Status IN ('Active', 'Completed'))
    WHERE t.TripID = @TripID
      AND s.IsActive = 1
    ORDER BY s.SeatRow, s.SeatColumn;
END
GO

-- ----------------------------------------------------------------------------
-- Stored Procedure: sp_PurchaseTicket (TRANSACTION EXAMPLE)
-- Description: Handles complete ticket purchase with seat reservation
-- This demonstrates transaction handling and multiple operations
-- ----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE sp_PurchaseTicket
    @UserID INT,
    @TripID INT,
    @SeatIDs NVARCHAR(MAX), -- Comma-separated seat IDs
    @CouponCode NVARCHAR(50) = NULL,
    @PassengerNames NVARCHAR(MAX), -- Comma-separated names matching seats
    @UseCredit BIT = 1,
    @TicketID INT OUTPUT,
    @Success BIT OUTPUT,
    @Message NVARCHAR(500) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    
    DECLARE @CouponID INT = NULL;
    DECLARE @DiscountRate DECIMAL(5,2) = 0;
    DECLARE @TripPrice DECIMAL(10,2);
    DECLARE @TotalSeats INT;
    DECLARE @TotalPrice DECIMAL(10,2);
    DECLARE @DiscountAmount DECIMAL(10,2) = 0;
    DECLARE @FinalPrice DECIMAL(10,2);
    DECLARE @UserCredit DECIMAL(10,2);
    DECLARE @TicketCode NVARCHAR(20);
    DECLARE @TripStatus NVARCHAR(20);
    DECLARE @AvailableSeats INT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- 1. Validate Trip exists and is active
        SELECT @TripPrice = Price, @TripStatus = Status, @AvailableSeats = AvailableSeats
        FROM Trips WHERE TripID = @TripID;
        
        IF @TripPrice IS NULL
        BEGIN
            SET @Success = 0;
            SET @Message = 'Trip not found.';
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        IF @TripStatus <> 'Active'
        BEGIN
            SET @Success = 0;
            SET @Message = 'Trip is not available for booking.';
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- 2. Count requested seats
        SELECT @TotalSeats = COUNT(value) 
        FROM STRING_SPLIT(@SeatIDs, ',');
        
        IF @TotalSeats > @AvailableSeats
        BEGIN
            SET @Success = 0;
            SET @Message = 'Not enough seats available.';
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        IF @TotalSeats > 5
        BEGIN
            SET @Success = 0;
            SET @Message = 'Maximum 5 seats per booking.';
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- 3. Check if seats are available (not already booked)
        IF EXISTS (
            SELECT 1 FROM TicketSeats ts
            INNER JOIN Tickets t ON ts.TicketID = t.TicketID
            WHERE ts.TripID = @TripID 
              AND ts.SeatID IN (SELECT CAST(value AS INT) FROM STRING_SPLIT(@SeatIDs, ','))
              AND t.Status IN ('Active', 'Completed')
        )
        BEGIN
            SET @Success = 0;
            SET @Message = 'One or more selected seats are already booked.';
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- 4. Validate coupon if provided
        IF @CouponCode IS NOT NULL AND @CouponCode <> ''
        BEGIN
            SELECT @CouponID = CouponID, @DiscountRate = DiscountRate
            FROM Coupons 
            WHERE CouponCode = @CouponCode 
              AND IsActive = 1 
              AND ExpiryDate >= CAST(GETDATE() AS DATE)
              AND TimesUsed < UsageLimit;
              
            IF @CouponID IS NULL
            BEGIN
                SET @Success = 0;
                SET @Message = 'Invalid or expired coupon code.';
                ROLLBACK TRANSACTION;
                RETURN;
            END
            
            -- Check if user already used this coupon
            IF EXISTS (SELECT 1 FROM UserCoupons WHERE UserID = @UserID AND CouponID = @CouponID AND IsUsed = 1)
            BEGIN
                SET @Success = 0;
                SET @Message = 'You have already used this coupon.';
                ROLLBACK TRANSACTION;
                RETURN;
            END
        END
        
        -- 5. Calculate prices
        SET @TotalPrice = @TripPrice * @TotalSeats;
        SET @DiscountAmount = @TotalPrice * (@DiscountRate / 100);
        SET @FinalPrice = @TotalPrice - @DiscountAmount;
        
        -- 6. Check user credit if using credit
        IF @UseCredit = 1
        BEGIN
            SELECT @UserCredit = CreditBalance FROM Users WHERE UserID = @UserID;
            
            IF @UserCredit < @FinalPrice
            BEGIN
                SET @Success = 0;
                SET @Message = 'Insufficient credit balance. Required: ' + CAST(@FinalPrice AS NVARCHAR) + ' TL, Available: ' + CAST(@UserCredit AS NVARCHAR) + ' TL';
                ROLLBACK TRANSACTION;
                RETURN;
            END
        END
        
        -- 7. Generate ticket code
        SET @TicketCode = 'TKT-' + CAST(YEAR(GETDATE()) AS NVARCHAR) + '-' + RIGHT('000000' + CAST(NEXT VALUE FOR TicketSequence AS NVARCHAR), 6);
        
        -- 8. Create ticket
        INSERT INTO Tickets (TicketCode, UserID, TripID, CouponID, TotalPrice, DiscountAmount, FinalPrice, Status)
        VALUES (@TicketCode, @UserID, @TripID, @CouponID, @TotalPrice, @DiscountAmount, @FinalPrice, 'Active');
        
        SET @TicketID = SCOPE_IDENTITY();
        
        -- 9. Create ticket seats
        DECLARE @SeatIDTable TABLE (SeatID INT, RowNum INT);
        INSERT INTO @SeatIDTable (SeatID, RowNum)
        SELECT CAST(value AS INT), ROW_NUMBER() OVER (ORDER BY (SELECT NULL))
        FROM STRING_SPLIT(@SeatIDs, ',');
        
        DECLARE @NameTable TABLE (PassengerName NVARCHAR(100), RowNum INT);
        INSERT INTO @NameTable (PassengerName, RowNum)
        SELECT value, ROW_NUMBER() OVER (ORDER BY (SELECT NULL))
        FROM STRING_SPLIT(@PassengerNames, ',');
        
        INSERT INTO TicketSeats (TicketID, SeatID, TripID, PassengerName)
        SELECT @TicketID, s.SeatID, @TripID, n.PassengerName
        FROM @SeatIDTable s
        INNER JOIN @NameTable n ON s.RowNum = n.RowNum;
        
        -- 10. Update trip available seats
        UPDATE Trips 
        SET AvailableSeats = AvailableSeats - @TotalSeats,
            UpdatedAt = GETDATE()
        WHERE TripID = @TripID;
        
        -- 11. Deduct user credit if using credit
        IF @UseCredit = 1
        BEGIN
            UPDATE Users 
            SET CreditBalance = CreditBalance - @FinalPrice,
                UpdatedAt = GETDATE()
            WHERE UserID = @UserID;
            
            -- Record payment
            INSERT INTO Payments (UserID, TicketID, Amount, PaymentType, PaymentMethod, Status)
            VALUES (@UserID, @TicketID, @FinalPrice, 'TicketPurchase', 'UserCredit', 'Completed');
        END
        
        -- 12. Update coupon usage if used
        IF @CouponID IS NOT NULL
        BEGIN
            UPDATE Coupons SET TimesUsed = TimesUsed + 1 WHERE CouponID = @CouponID;
            
            -- Mark user coupon as used or create new record
            IF EXISTS (SELECT 1 FROM UserCoupons WHERE UserID = @UserID AND CouponID = @CouponID)
            BEGIN
                UPDATE UserCoupons 
                SET IsUsed = 1, UsedAt = GETDATE() 
                WHERE UserID = @UserID AND CouponID = @CouponID;
            END
            ELSE
            BEGIN
                INSERT INTO UserCoupons (UserID, CouponID, IsUsed, UsedAt)
                VALUES (@UserID, @CouponID, 1, GETDATE());
            END
        END
        
        -- 13. Log activity
        INSERT INTO ActivityLogs (ActionType, TableName, RecordID, UserType, UserID, Description)
        VALUES ('INSERT', 'Tickets', @TicketID, 'User', @UserID, 
                'Purchased ticket ' + @TicketCode + ' for trip ' + CAST(@TripID AS NVARCHAR) + 
                ', ' + CAST(@TotalSeats AS NVARCHAR) + ' seats, Total: ' + CAST(@FinalPrice AS NVARCHAR) + ' TL');
        
        COMMIT TRANSACTION;
        
        SET @Success = 1;
        SET @Message = 'Ticket purchased successfully! Ticket Code: ' + @TicketCode;
        
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
            
        SET @Success = 0;
        SET @Message = 'Error: ' + ERROR_MESSAGE();
        SET @TicketID = NULL;
    END CATCH
END
GO

-- Create sequence for ticket codes
IF NOT EXISTS (SELECT * FROM sys.sequences WHERE name = 'TicketSequence')
BEGIN
    CREATE SEQUENCE TicketSequence
    START WITH 1
    INCREMENT BY 1;
END
GO

-- ----------------------------------------------------------------------------
-- Stored Procedure: sp_CancelTicket
-- Description: Cancels a ticket and processes refund
-- ----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE sp_CancelTicket
    @TicketID INT,
    @UserID INT,
    @Success BIT OUTPUT,
    @Message NVARCHAR(500) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    
    DECLARE @TicketStatus NVARCHAR(20);
    DECLARE @TripID INT;
    DECLARE @FinalPrice DECIMAL(10,2);
    DECLARE @TripDepartureDate DATE;
    DECLARE @TripDepartureTime TIME;
    DECLARE @SeatsCount INT;
    DECLARE @RefundAmount DECIMAL(10,2);
    DECLARE @HoursUntilDeparture INT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- 1. Get ticket details
        SELECT @TicketStatus = t.Status, @TripID = t.TripID, @FinalPrice = t.FinalPrice,
               @TripDepartureDate = tr.DepartureDate, @TripDepartureTime = tr.DepartureTime
        FROM Tickets t
        INNER JOIN Trips tr ON t.TripID = tr.TripID
        WHERE t.TicketID = @TicketID AND t.UserID = @UserID;
        
        IF @TicketStatus IS NULL
        BEGIN
            SET @Success = 0;
            SET @Message = 'Ticket not found or does not belong to this user.';
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        IF @TicketStatus <> 'Active'
        BEGIN
            SET @Success = 0;
            SET @Message = 'Only active tickets can be cancelled.';
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- 2. Calculate hours until departure
        SET @HoursUntilDeparture = DATEDIFF(HOUR, GETDATE(), 
            CAST(@TripDepartureDate AS DATETIME) + CAST(@TripDepartureTime AS DATETIME));
        
        -- 3. Calculate refund based on cancellation policy
        -- Full refund if more than 1 hour before departure
        IF @HoursUntilDeparture >= 1
        BEGIN
            SET @RefundAmount = @FinalPrice;
        END
        ELSE IF @HoursUntilDeparture >= 0
        BEGIN
            -- 50% refund if less than 1 hour but not departed yet
            SET @RefundAmount = @FinalPrice * 0.5;
        END
        ELSE
        BEGIN
            SET @Success = 0;
            SET @Message = 'Cannot cancel ticket after departure.';
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- 4. Count seats to release
        SELECT @SeatsCount = COUNT(*) FROM TicketSeats WHERE TicketID = @TicketID;
        
        -- 5. Update ticket status
        UPDATE Tickets 
        SET Status = 'Cancelled', 
            CancellationDate = GETDATE(),
            RefundAmount = @RefundAmount
        WHERE TicketID = @TicketID;
        
        -- 6. Update trip available seats
        UPDATE Trips 
        SET AvailableSeats = AvailableSeats + @SeatsCount,
            UpdatedAt = GETDATE()
        WHERE TripID = @TripID;
        
        -- 7. Refund to user credit
        UPDATE Users 
        SET CreditBalance = CreditBalance + @RefundAmount,
            UpdatedAt = GETDATE()
        WHERE UserID = @UserID;
        
        -- 8. Record refund payment
        INSERT INTO Payments (UserID, TicketID, Amount, PaymentType, PaymentMethod, Status)
        VALUES (@UserID, @TicketID, @RefundAmount, 'Refund', 'UserCredit', 'Completed');
        
        -- 9. Log activity
        INSERT INTO ActivityLogs (ActionType, TableName, RecordID, UserType, UserID, Description)
        VALUES ('UPDATE', 'Tickets', @TicketID, 'User', @UserID, 
                'Cancelled ticket, Refund: ' + CAST(@RefundAmount AS NVARCHAR) + ' TL');
        
        COMMIT TRANSACTION;
        
        SET @Success = 1;
        SET @Message = 'Ticket cancelled successfully. Refund of ' + CAST(@RefundAmount AS NVARCHAR) + ' TL credited to your account.';
        
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
            
        SET @Success = 0;
        SET @Message = 'Error: ' + ERROR_MESSAGE();
    END CATCH
END
GO

-- ----------------------------------------------------------------------------
-- Stored Procedure: sp_GetUserTickets
-- Description: Gets all tickets for a specific user with filters
-- ----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE sp_GetUserTickets
    @UserID INT,
    @StatusFilter NVARCHAR(20) = NULL -- NULL for all, or 'Active', 'Completed', 'Cancelled'
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        t.TicketID,
        t.TicketCode,
        c.CompanyName,
        dep.CityName AS DepartureCity,
        arr.CityName AS ArrivalCity,
        tr.DepartureDate,
        tr.DepartureTime,
        tr.ArrivalTime,
        tr.DurationMinutes,
        t.TotalPrice,
        t.DiscountAmount,
        t.FinalPrice,
        t.Status,
        t.PurchaseDate,
        t.CancellationDate,
        t.RefundAmount,
        STRING_AGG(CAST(s.SeatNumber AS NVARCHAR), ', ') AS SeatNumbers,
        COUNT(ts.TicketSeatID) AS SeatCount
    FROM Tickets t
    INNER JOIN Trips tr ON t.TripID = tr.TripID
    INNER JOIN Buses b ON tr.BusID = b.BusID
    INNER JOIN Companies c ON b.CompanyID = c.CompanyID
    INNER JOIN Cities dep ON tr.DepartureCityID = dep.CityID
    INNER JOIN Cities arr ON tr.ArrivalCityID = arr.CityID
    LEFT JOIN TicketSeats ts ON t.TicketID = ts.TicketID
    LEFT JOIN Seats s ON ts.SeatID = s.SeatID
    WHERE t.UserID = @UserID
      AND (@StatusFilter IS NULL OR t.Status = @StatusFilter)
    GROUP BY t.TicketID, t.TicketCode, c.CompanyName, dep.CityName, arr.CityName,
             tr.DepartureDate, tr.DepartureTime, tr.ArrivalTime, tr.DurationMinutes,
             t.TotalPrice, t.DiscountAmount, t.FinalPrice, t.Status, 
             t.PurchaseDate, t.CancellationDate, t.RefundAmount
    ORDER BY 
        CASE t.Status 
            WHEN 'Active' THEN 1 
            WHEN 'Completed' THEN 2 
            WHEN 'Cancelled' THEN 3 
        END,
        tr.DepartureDate DESC;
END
GO

-- ----------------------------------------------------------------------------
-- Stored Procedure: sp_AddUserCredit
-- Description: Adds credit to user account
-- ----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE sp_AddUserCredit
    @UserID INT,
    @Amount DECIMAL(10,2),
    @PaymentMethod NVARCHAR(20),
    @Success BIT OUTPUT,
    @Message NVARCHAR(500) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    IF @Amount <= 0 OR @Amount > 10000
    BEGIN
        SET @Success = 0;
        SET @Message = 'Invalid amount. Must be between 1 and 10000 TL.';
        RETURN;
    END
    
    IF @PaymentMethod NOT IN ('CreditCard', 'BankTransfer')
    BEGIN
        SET @Success = 0;
        SET @Message = 'Invalid payment method.';
        RETURN;
    END
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Update user credit
        UPDATE Users 
        SET CreditBalance = CreditBalance + @Amount,
            UpdatedAt = GETDATE()
        WHERE UserID = @UserID;
        
        -- Record payment
        INSERT INTO Payments (UserID, Amount, PaymentType, PaymentMethod, Status)
        VALUES (@UserID, @Amount, 'CreditTopUp', @PaymentMethod, 'Completed');
        
        -- Log activity
        INSERT INTO ActivityLogs (ActionType, TableName, RecordID, UserType, UserID, Description)
        VALUES ('UPDATE', 'Users', @UserID, 'User', @UserID, 
                'Added credit: ' + CAST(@Amount AS NVARCHAR) + ' TL via ' + @PaymentMethod);
        
        COMMIT TRANSACTION;
        
        SET @Success = 1;
        SET @Message = 'Credit of ' + CAST(@Amount AS NVARCHAR) + ' TL added successfully.';
        
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
            
        SET @Success = 0;
        SET @Message = 'Error: ' + ERROR_MESSAGE();
    END CATCH
END
GO

-- ----------------------------------------------------------------------------
-- Stored Procedure: sp_GetDashboardStats (For Admins)
-- Description: Gets dashboard statistics
-- ----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE sp_GetDashboardStats
    @CompanyID INT = NULL -- NULL for system-wide stats
AS
BEGIN
    SET NOCOUNT ON;
    
    -- General statistics
    SELECT
        (SELECT COUNT(*) FROM Companies WHERE IsActive = 1 AND (@CompanyID IS NULL OR CompanyID = @CompanyID)) AS TotalCompanies,
        (SELECT COUNT(*) FROM FirmAdmins WHERE IsActive = 1 AND (@CompanyID IS NULL OR CompanyID = @CompanyID)) AS TotalFirmAdmins,
        (SELECT COUNT(*) FROM Users WHERE IsActive = 1) AS TotalUsers,
        (SELECT COUNT(*) FROM Coupons WHERE IsActive = 1 AND ExpiryDate >= CAST(GETDATE() AS DATE)) AS ActiveCoupons,
        (SELECT COUNT(*) FROM Trips WHERE Status = 'Active' AND DepartureDate >= CAST(GETDATE() AS DATE) 
            AND (@CompanyID IS NULL OR BusID IN (SELECT BusID FROM Buses WHERE CompanyID = @CompanyID))) AS ActiveTrips,
        (SELECT COUNT(*) FROM Tickets WHERE Status = 'Active' 
            AND TripID IN (SELECT TripID FROM Trips WHERE DepartureDate >= CAST(GETDATE() AS DATE)
                AND (@CompanyID IS NULL OR BusID IN (SELECT BusID FROM Buses WHERE CompanyID = @CompanyID)))) AS UpcomingTickets,
        (SELECT ISNULL(SUM(FinalPrice), 0) FROM Tickets 
            WHERE Status IN ('Active', 'Completed') 
            AND MONTH(PurchaseDate) = MONTH(GETDATE()) 
            AND YEAR(PurchaseDate) = YEAR(GETDATE())
            AND (@CompanyID IS NULL OR TripID IN (SELECT TripID FROM Trips WHERE BusID IN (SELECT BusID FROM Buses WHERE CompanyID = @CompanyID)))) AS MonthlyRevenue;
END
GO

-- ----------------------------------------------------------------------------
-- Stored Procedure: sp_CreateTrip (For Firm Admins)
-- Description: Creates a new trip
-- ----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE sp_CreateTrip
    @BusID INT,
    @DepartureCityID INT,
    @ArrivalCityID INT,
    @DepartureDate DATE,
    @DepartureTime TIME,
    @ArrivalTime TIME,
    @DurationMinutes INT,
    @Price DECIMAL(10,2),
    @CreatedByFirmAdminID INT,
    @TripID INT OUTPUT,
    @Success BIT OUTPUT,
    @Message NVARCHAR(500) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @TotalSeats INT;
    DECLARE @TripCode NVARCHAR(20);
    DECLARE @CompanyID INT;
    
    BEGIN TRY
        -- Validate bus belongs to admin's company
        SELECT @CompanyID = b.CompanyID, @TotalSeats = b.TotalSeats
        FROM Buses b
        INNER JOIN FirmAdmins fa ON b.CompanyID = fa.CompanyID
        WHERE b.BusID = @BusID AND fa.FirmAdminID = @CreatedByFirmAdminID;
        
        IF @CompanyID IS NULL
        BEGIN
            SET @Success = 0;
            SET @Message = 'Bus not found or you do not have permission.';
            RETURN;
        END
        
        -- Check for conflicting trips
        IF EXISTS (
            SELECT 1 FROM Trips 
            WHERE BusID = @BusID 
              AND DepartureDate = @DepartureDate 
              AND Status = 'Active'
              AND (
                  (@DepartureTime BETWEEN DepartureTime AND ArrivalTime)
                  OR (@ArrivalTime BETWEEN DepartureTime AND ArrivalTime)
              )
        )
        BEGIN
            SET @Success = 0;
            SET @Message = 'Bus has a conflicting trip at this time.';
            RETURN;
        END
        
        -- Generate trip code
        SET @TripCode = 'TRP-' + CAST(YEAR(@DepartureDate) AS NVARCHAR) + '-' + RIGHT('000000' + CAST(NEXT VALUE FOR TripSequence AS NVARCHAR), 6);
        
        INSERT INTO Trips (TripCode, BusID, DepartureCityID, ArrivalCityID, DepartureDate, 
                          DepartureTime, ArrivalTime, DurationMinutes, Price, AvailableSeats, Status)
        VALUES (@TripCode, @BusID, @DepartureCityID, @ArrivalCityID, @DepartureDate,
                @DepartureTime, @ArrivalTime, @DurationMinutes, @Price, @TotalSeats, 'Active');
        
        SET @TripID = SCOPE_IDENTITY();
        
        -- Log activity
        INSERT INTO ActivityLogs (ActionType, TableName, RecordID, UserType, UserID, Description)
        VALUES ('INSERT', 'Trips', @TripID, 'FirmAdmin', @CreatedByFirmAdminID, 
                'Created trip ' + @TripCode);
        
        SET @Success = 1;
        SET @Message = 'Trip created successfully. Trip Code: ' + @TripCode;
        
    END TRY
    BEGIN CATCH
        SET @Success = 0;
        SET @Message = 'Error: ' + ERROR_MESSAGE();
        SET @TripID = NULL;
    END CATCH
END
GO

-- Create sequence for trip codes
IF NOT EXISTS (SELECT * FROM sys.sequences WHERE name = 'TripSequence')
BEGIN
    CREATE SEQUENCE TripSequence
    START WITH 1
    INCREMENT BY 1;
END
GO

-- ----------------------------------------------------------------------------
-- Stored Procedure: sp_ValidateCoupon
-- Description: Validates a coupon code for a user
-- ----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE sp_ValidateCoupon
    @CouponCode NVARCHAR(50),
    @UserID INT,
    @IsValid BIT OUTPUT,
    @DiscountRate DECIMAL(5,2) OUTPUT,
    @Message NVARCHAR(500) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @CouponID INT;
    DECLARE @UsageLimit INT;
    DECLARE @TimesUsed INT;
    DECLARE @ExpiryDate DATE;
    DECLARE @IsActive BIT;
    
    SELECT @CouponID = CouponID, @DiscountRate = DiscountRate, 
           @UsageLimit = UsageLimit, @TimesUsed = TimesUsed,
           @ExpiryDate = ExpiryDate, @IsActive = IsActive
    FROM Coupons WHERE CouponCode = @CouponCode;
    
    IF @CouponID IS NULL
    BEGIN
        SET @IsValid = 0;
        SET @DiscountRate = 0;
        SET @Message = 'Coupon code not found.';
        RETURN;
    END
    
    IF @IsActive = 0
    BEGIN
        SET @IsValid = 0;
        SET @DiscountRate = 0;
        SET @Message = 'Coupon is no longer active.';
        RETURN;
    END
    
    IF @ExpiryDate < CAST(GETDATE() AS DATE)
    BEGIN
        SET @IsValid = 0;
        SET @DiscountRate = 0;
        SET @Message = 'Coupon has expired.';
        RETURN;
    END
    
    IF @TimesUsed >= @UsageLimit
    BEGIN
        SET @IsValid = 0;
        SET @DiscountRate = 0;
        SET @Message = 'Coupon usage limit reached.';
        RETURN;
    END
    
    -- Check if user already used this coupon
    IF EXISTS (SELECT 1 FROM UserCoupons WHERE UserID = @UserID AND CouponID = @CouponID AND IsUsed = 1)
    BEGIN
        SET @IsValid = 0;
        SET @DiscountRate = 0;
        SET @Message = 'You have already used this coupon.';
        RETURN;
    END
    
    SET @IsValid = 1;
    SET @Message = 'Coupon is valid! ' + CAST(@DiscountRate AS NVARCHAR) + '% discount will be applied.';
END
GO

-- ============================================================================
-- SECTION 5: VIEWS FOR REPORTING
-- ============================================================================

-- View: Active Trips with Details
CREATE OR ALTER VIEW vw_ActiveTripsDetails AS
SELECT 
    t.TripID,
    t.TripCode,
    c.CompanyName,
    c.Rating AS CompanyRating,
    dep.CityName AS DepartureCity,
    arr.CityName AS ArrivalCity,
    t.DepartureDate,
    t.DepartureTime,
    t.ArrivalTime,
    t.DurationMinutes,
    t.Price,
    t.AvailableSeats,
    b.TotalSeats,
    b.TotalSeats - t.AvailableSeats AS BookedSeats,
    CAST((CAST(b.TotalSeats - t.AvailableSeats AS FLOAT) / b.TotalSeats) * 100 AS DECIMAL(5,2)) AS OccupancyRate,
    b.HasWifi,
    b.HasTV,
    b.HasRefreshments,
    b.HasPowerOutlet,
    t.Status
FROM Trips t
INNER JOIN Buses b ON t.BusID = b.BusID
INNER JOIN Companies c ON b.CompanyID = c.CompanyID
INNER JOIN Cities dep ON t.DepartureCityID = dep.CityID
INNER JOIN Cities arr ON t.ArrivalCityID = arr.CityID
WHERE t.Status = 'Active' AND t.DepartureDate >= CAST(GETDATE() AS DATE);
GO

-- View: Sales Report
CREATE OR ALTER VIEW vw_SalesReport AS
SELECT 
    c.CompanyID,
    c.CompanyName,
    YEAR(tk.PurchaseDate) AS Year,
    MONTH(tk.PurchaseDate) AS Month,
    COUNT(DISTINCT tk.TicketID) AS TotalTickets,
    SUM(ts.SeatCount) AS TotalSeats,
    SUM(tk.FinalPrice) AS TotalRevenue,
    SUM(tk.DiscountAmount) AS TotalDiscounts,
    AVG(tk.FinalPrice) AS AvgTicketPrice
FROM Tickets tk
INNER JOIN Trips t ON tk.TripID = t.TripID
INNER JOIN Buses b ON t.BusID = b.BusID
INNER JOIN Companies c ON b.CompanyID = c.CompanyID
INNER JOIN (
    SELECT TicketID, COUNT(*) AS SeatCount FROM TicketSeats GROUP BY TicketID
) ts ON tk.TicketID = ts.TicketID
WHERE tk.Status IN ('Active', 'Completed')
GROUP BY c.CompanyID, c.CompanyName, YEAR(tk.PurchaseDate), MONTH(tk.PurchaseDate);
GO

-- ============================================================================
-- SECTION 6: SAMPLE DATA INSERTION
-- ============================================================================

-- Insert Cities
INSERT INTO Cities (CityName) VALUES 
('Istanbul'), ('Ankara'), ('Izmir'), ('Antalya'), ('Bursa'),
('Adana'), ('Konya'), ('Gaziantep'), ('Mersin'), ('Kayseri'),
('Eskisehir'), ('Trabzon'), ('Samsun'), ('Denizli'), ('Mugla');
GO

-- Insert System Admin
INSERT INTO SystemAdmins (Username, Email, PasswordHash, FirstName, LastName)
VALUES ('admin', 'admin@buyticket.com', 'hashed_password_here', 'System', 'Admin');
GO

-- Insert Companies
INSERT INTO Companies (CompanyName, Phone, Email, Address, Rating, TotalRatings) VALUES
('Metro Turizm', '0850 222 33 44', 'info@metroturizm.com', 'Istanbul, Turkey', 4.8, 1520),
('Pamukkale Turizm', '0850 333 44 55', 'info@pamukkale.com', 'Denizli, Turkey', 4.5, 1280),
('Ali Osman Ulusoy', '0850 444 55 66', 'info@ulusoy.com', 'Trabzon, Turkey', 4.9, 980),
('Kamil Koc', '0850 555 66 77', 'info@kamilkoc.com', 'Ankara, Turkey', 4.6, 1150);
GO

-- Insert Firm Admins
INSERT INTO FirmAdmins (CompanyID, FirstName, LastName, Email, Phone, PasswordHash) VALUES
(1, 'Mehmet', 'Demir', 'mehmet.demir@metroturizm.com', '0532 111 22 33', 'hashed_password'),
(1, 'Ayse', 'Yilmaz', 'ayse.yilmaz@metroturizm.com', '0533 222 33 44', 'hashed_password'),
(2, 'Ali', 'Kaya', 'ali.kaya@pamukkale.com', '0534 333 44 55', 'hashed_password'),
(3, 'Fatma', 'Ozturk', 'fatma.ozturk@ulusoy.com', '0535 444 55 66', 'hashed_password'),
(4, 'Hasan', 'Celik', 'hasan.celik@kamilkoc.com', '0536 555 66 77', 'hashed_password');
GO

-- Insert Buses
INSERT INTO Buses (CompanyID, PlateNumber, TotalSeats, HasWifi, HasTV, HasRefreshments, HasPowerOutlet, HasEntertainment) VALUES
(1, '34 ABC 123', 40, 1, 1, 1, 1, 1),
(1, '34 DEF 456', 40, 1, 0, 1, 1, 0),
(2, '20 GHI 789', 40, 1, 1, 1, 0, 0),
(2, '20 JKL 012', 40, 1, 0, 1, 0, 0),
(3, '61 MNO 345', 40, 1, 1, 1, 1, 1),
(4, '06 PRS 678', 40, 1, 1, 1, 1, 0);
GO

-- Insert Seats for each bus (40 seats per bus: 10 rows x 4 seats)
DECLARE @BusID INT = 1;
WHILE @BusID <= 6
BEGIN
    DECLARE @SeatNum INT = 1;
    DECLARE @Row INT = 1;
    WHILE @Row <= 10
    BEGIN
        INSERT INTO Seats (BusID, SeatNumber, SeatRow, SeatColumn) VALUES
        (@BusID, @SeatNum, @Row, 'A'),
        (@BusID, @SeatNum + 1, @Row, 'B'),
        (@BusID, @SeatNum + 2, @Row, 'C'),
        (@BusID, @SeatNum + 3, @Row, 'D');
        SET @SeatNum = @SeatNum + 4;
        SET @Row = @Row + 1;
    END
    SET @BusID = @BusID + 1;
END
GO

-- Insert Sample Users
INSERT INTO Users (FirstName, LastName, Email, Phone, PasswordHash, IDNumber, CreditBalance, BirthDate) VALUES
('Ahmet', 'Yilmaz', 'ahmet.yilmaz@email.com', '0532 111 22 33', 'hashed_password', '12345678901', 1500.00, '1990-05-15'),
('Fatma', 'Demir', 'fatma.demir@email.com', '0533 222 33 44', 'hashed_password', '23456789012', 800.00, '1985-08-20'),
('Mehmet', 'Kaya', 'mehmet.kaya@email.com', '0534 333 44 55', 'hashed_password', '34567890123', 250.00, '1995-12-10'),
('Ayse', 'Ozturk', 'ayse.ozturk@email.com', '0535 444 55 66', 'hashed_password', '45678901234', 2000.00, '1988-03-25'),
('Ali', 'Celik', 'ali.celik@email.com', '0536 555 66 77', 'hashed_password', '56789012345', 500.00, '1992-07-30');
GO

-- Insert Coupons
INSERT INTO Coupons (CouponCode, DiscountRate, UsageLimit, ExpiryDate, Description, CreatedBy) VALUES
('DISCOUNT10', 10.00, 1000, '2025-12-31', '10% discount on all tickets', 1),
('DISCOUNT20', 20.00, 500, '2025-11-30', '20% discount - Limited time offer', 1),
('SUMMER25', 15.00, 2000, '2025-08-31', 'Summer special - 15% off', 1),
('WELCOME50', 50.00, 100, '2025-06-30', 'New user welcome bonus - 50% off first ticket', 1),
('BAYRAM25', 25.00, 500, '2025-04-15', 'Holiday special discount', 1);
GO

-- Assign some coupons to users
INSERT INTO UserCoupons (UserID, CouponID) VALUES
(1, 1), (1, 2),
(2, 1), (2, 3),
(3, 1),
(4, 1), (4, 2), (4, 3),
(5, 1);
GO

-- Insert Sample Trips (Future dates)
DECLARE @Today DATE = CAST(GETDATE() AS DATE);
INSERT INTO Trips (TripCode, BusID, DepartureCityID, ArrivalCityID, DepartureDate, DepartureTime, ArrivalTime, DurationMinutes, Price, AvailableSeats) VALUES
('TRP-2025-000001', 1, 1, 2, DATEADD(DAY, 1, @Today), '09:00', '14:30', 330, 350.00, 40),
('TRP-2025-000002', 1, 1, 2, DATEADD(DAY, 1, @Today), '13:30', '19:00', 330, 350.00, 40),
('TRP-2025-000003', 1, 1, 2, DATEADD(DAY, 1, @Today), '20:00', '01:30', 330, 320.00, 40),
('TRP-2025-000004', 2, 1, 2, DATEADD(DAY, 2, @Today), '10:00', '15:30', 330, 340.00, 40),
('TRP-2025-000005', 3, 1, 3, DATEADD(DAY, 1, @Today), '08:00', '16:00', 480, 420.00, 40),
('TRP-2025-000006', 3, 1, 3, DATEADD(DAY, 2, @Today), '14:00', '22:00', 480, 400.00, 40),
('TRP-2025-000007', 4, 2, 3, DATEADD(DAY, 1, @Today), '09:30', '17:30', 480, 380.00, 40),
('TRP-2025-000008', 5, 1, 4, DATEADD(DAY, 3, @Today), '22:00', '08:00', 600, 450.00, 40),
('TRP-2025-000009', 6, 2, 4, DATEADD(DAY, 2, @Today), '23:00', '07:30', 510, 380.00, 40),
('TRP-2025-000010', 6, 2, 1, DATEADD(DAY, 4, @Today), '08:00', '13:30', 330, 350.00, 40);
GO

-- Update sequence values
ALTER SEQUENCE TicketSequence RESTART WITH 1000;
ALTER SEQUENCE TripSequence RESTART WITH 11;
GO

PRINT 'Database created successfully with all tables, stored procedures, and sample data!';
GO

