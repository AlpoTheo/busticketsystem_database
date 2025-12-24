-- Bus Ticket System Database
-- CENG 301 Database Systems Term Project
-- 
-- this script creates all the tables and stuff we need for the bus ticket system
-- run this on MSSQL Server

USE master;
GO

-- delete old db if it exists so we can start fresh
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


-- =====================
-- TABLES
-- =====================

-- cities table - pretty simple, just stores city names
CREATE TABLE Cities (
    CityID INT IDENTITY(1,1) PRIMARY KEY,
    CityName NVARCHAR(100) NOT NULL UNIQUE,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE()
);
GO

-- bus companies (like Metro, Pamukkale etc)
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

-- admins for each bus company
-- they can manage their own companys trips and buses
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
    CONSTRAINT FK_FirmAdmins_Companies FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID) ON DELETE CASCADE
);
GO

-- users table - for customers who buy tickets and also system admins
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    Phone NVARCHAR(20) NOT NULL,
    PasswordHash NVARCHAR(256) NOT NULL,
    IDNumber NVARCHAR(11) NOT NULL UNIQUE, -- TC kimlik no
    Role NVARCHAR(20) DEFAULT 'User' CHECK (Role IN ('User', 'SystemAdmin')),
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

-- buses - each company has multiple buses
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
    CONSTRAINT FK_Buses_Companies FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID) ON DELETE CASCADE
);
GO

-- seats in each bus
-- we need this to track which seats are taken for each trip
CREATE TABLE Seats (
    SeatID INT IDENTITY(1,1) PRIMARY KEY,
    BusID INT NOT NULL,
    SeatNumber INT NOT NULL CHECK (SeatNumber > 0),
    SeatRow INT NOT NULL,
    SeatColumn NVARCHAR(1) NOT NULL, -- A, B, C, D
    IsActive BIT DEFAULT 1,
    CONSTRAINT FK_Seats_Buses FOREIGN KEY (BusID) REFERENCES Buses(BusID) ON DELETE CASCADE,
    CONSTRAINT UQ_Seats_BusSeat UNIQUE (BusID, SeatNumber)
);
GO

-- trips table - this is where we store scheduled bus trips
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
    Status NVARCHAR(20) DEFAULT 'Active' CHECK (Status IN ('Active', 'Completed', 'Cancelled', 'Delayed')),
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME NULL,
    CONSTRAINT FK_Trips_Buses FOREIGN KEY (BusID) REFERENCES Buses(BusID),
    CONSTRAINT FK_Trips_DepartureCity FOREIGN KEY (DepartureCityID) REFERENCES Cities(CityID),
    CONSTRAINT FK_Trips_ArrivalCity FOREIGN KEY (ArrivalCityID) REFERENCES Cities(CityID),
    CONSTRAINT CK_Trips_DifferentCities CHECK (DepartureCityID <> ArrivalCityID) -- cant go from istanbul to istanbul lol
);
GO

-- discount coupons
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
    CreatedBy INT NULL
);
GO

-- which user has which coupon
-- we need this junction table to track usage
CREATE TABLE UserCoupons (
    UserCouponID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL,
    CouponID INT NOT NULL,
    IsUsed BIT DEFAULT 0,
    UsedAt DATETIME NULL,
    AssignedAt DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_UserCoupons_Users FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    CONSTRAINT FK_UserCoupons_Coupons FOREIGN KEY (CouponID) REFERENCES Coupons(CouponID) ON DELETE CASCADE,
    CONSTRAINT UQ_UserCoupons UNIQUE (UserID, CouponID)
);
GO

-- tickets - when user buys a ticket it goes here
CREATE TABLE Tickets (
    TicketID INT IDENTITY(1,1) PRIMARY KEY,
    TicketCode NVARCHAR(20) NOT NULL UNIQUE,
    UserID INT NOT NULL,
    TripID INT NOT NULL,
    CouponID INT NULL, -- can be null if no coupon used
    TotalPrice DECIMAL(10,2) NOT NULL,
    DiscountAmount DECIMAL(10,2) DEFAULT 0.00,
    FinalPrice DECIMAL(10,2) NOT NULL,
    Status NVARCHAR(20) DEFAULT 'Active' CHECK (Status IN ('Active', 'Completed', 'Cancelled', 'Refunded')),
    PurchaseDate DATETIME DEFAULT GETDATE(),
    CancellationDate DATETIME NULL,
    RefundAmount DECIMAL(10,2) NULL,
    CONSTRAINT FK_Tickets_Users FOREIGN KEY (UserID) REFERENCES Users(UserID),
    CONSTRAINT FK_Tickets_Trips FOREIGN KEY (TripID) REFERENCES Trips(TripID),
    CONSTRAINT FK_Tickets_Coupons FOREIGN KEY (CouponID) REFERENCES Coupons(CouponID)
);
GO

-- many to many between tickets and seats
-- one ticket can have multiple seats (family buying together etc)
CREATE TABLE TicketSeats (
    TicketSeatID INT IDENTITY(1,1) PRIMARY KEY,
    TicketID INT NOT NULL,
    SeatID INT NOT NULL,
    TripID INT NOT NULL,
    PassengerName NVARCHAR(100) NOT NULL,
    PassengerIDNumber NVARCHAR(11) NULL,
    CONSTRAINT FK_TicketSeats_Tickets FOREIGN KEY (TicketID) REFERENCES Tickets(TicketID) ON DELETE CASCADE,
    CONSTRAINT FK_TicketSeats_Seats FOREIGN KEY (SeatID) REFERENCES Seats(SeatID),
    CONSTRAINT FK_TicketSeats_Trips FOREIGN KEY (TripID) REFERENCES Trips(TripID),
    CONSTRAINT UQ_TicketSeats_TripSeat UNIQUE (TripID, SeatID) -- same seat cant be sold twice for same trip
);
GO

-- payment records
CREATE TABLE Payments (
    PaymentID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL,
    TicketID INT NULL,
    Amount DECIMAL(10,2) NOT NULL,
    PaymentType NVARCHAR(20) NOT NULL CHECK (PaymentType IN ('TicketPurchase', 'CreditTopUp', 'Refund')),
    PaymentMethod NVARCHAR(20) NOT NULL CHECK (PaymentMethod IN ('CreditCard', 'BankTransfer', 'UserCredit')),
    Status NVARCHAR(20) DEFAULT 'Completed' CHECK (Status IN ('Pending', 'Completed', 'Failed', 'Refunded')),
    TransactionReference NVARCHAR(100) NULL,
    CreatedAt DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Payments_Users FOREIGN KEY (UserID) REFERENCES Users(UserID),
    CONSTRAINT FK_Payments_Tickets FOREIGN KEY (TicketID) REFERENCES Tickets(TicketID)
);
GO

-- logs for admin to see what happened in the system
CREATE TABLE ActivityLogs (
    LogID INT IDENTITY(1,1) PRIMARY KEY,
    ActionType NVARCHAR(50) NOT NULL,
    TableName NVARCHAR(50) NOT NULL,
    RecordID INT NULL,
    UserType NVARCHAR(20) NOT NULL,
    UserID INT NOT NULL,
    Description NVARCHAR(500) NOT NULL,
    OldValues NVARCHAR(MAX) NULL,
    NewValues NVARCHAR(MAX) NULL,
    IPAddress NVARCHAR(50) NULL,
    CreatedAt DATETIME DEFAULT GETDATE()
);
GO


-- =====================
-- INDEXES
-- =====================
-- adding indexes on columns we search a lot

CREATE INDEX IX_Trips_DepartureDate ON Trips(DepartureDate);
CREATE INDEX IX_Trips_DepartureCity ON Trips(DepartureCityID);
CREATE INDEX IX_Trips_ArrivalCity ON Trips(ArrivalCityID);
CREATE INDEX IX_Trips_Status ON Trips(Status);
CREATE INDEX IX_Trips_Search ON Trips(DepartureCityID, ArrivalCityID, DepartureDate, Status);
CREATE INDEX IX_Tickets_UserID ON Tickets(UserID);
CREATE INDEX IX_Tickets_TripID ON Tickets(TripID);
CREATE INDEX IX_Tickets_Status ON Tickets(Status);
CREATE INDEX IX_Tickets_PurchaseDate ON Tickets(PurchaseDate);
CREATE INDEX IX_TicketSeats_TripID ON TicketSeats(TripID);
CREATE INDEX IX_TicketSeats_SeatID ON TicketSeats(SeatID);
CREATE INDEX IX_Users_Email ON Users(Email);
CREATE INDEX IX_Users_IDNumber ON Users(IDNumber);
CREATE INDEX IX_Payments_UserID ON Payments(UserID);
CREATE INDEX IX_Payments_CreatedAt ON Payments(CreatedAt);
GO


-- sequences for generating ticket and trip codes
CREATE SEQUENCE TicketSequence START WITH 1000 INCREMENT BY 1;
CREATE SEQUENCE TripSequence START WITH 100 INCREMENT BY 1;
GO


-- =====================
-- STORED PROCEDURES
-- =====================

-- search trips procedure
-- takes departure/arrival city and date, returns matching trips
CREATE OR ALTER PROCEDURE sp_SearchTrips
    @DepartureCityID INT,
    @ArrivalCityID INT,
    @DepartureDate DATE,
    @SortBy NVARCHAR(20) = 'DepartureTime',
    @SortOrder NVARCHAR(4) = 'ASC'
AS
BEGIN
    SET NOCOUNT ON;
    
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


-- get seat status for a specific trip
-- shows which seats are available and which are taken
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
    WHERE t.TripID = @TripID AND s.IsActive = 1
    ORDER BY s.SeatRow, s.SeatColumn;
END
GO


-- this is the main ticket purchase procedure
-- handles everything: validation, payment, seat assignment etc
-- uses transaction so if anything fails it rolls back
CREATE OR ALTER PROCEDURE sp_PurchaseTicket
    @UserID INT,
    @TripID INT,
    @SeatIDs NVARCHAR(MAX), -- comma separated seat ids
    @PassengerNames NVARCHAR(MAX), -- pipe separated names
    @CouponCode NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    
    -- declare all the variables we need
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
    DECLARE @TicketID INT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- first check if trip exists and is active
        SELECT @TripPrice = Price, @TripStatus = Status, @AvailableSeats = AvailableSeats
        FROM Trips WHERE TripID = @TripID;
        
        IF @TripPrice IS NULL
        BEGIN
            SELECT 0 AS Success, 'Trip not found.' AS Message, NULL AS TicketID;
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        IF @TripStatus <> 'Active'
        BEGIN
            SELECT 0 AS Success, 'Trip is not available.' AS Message, NULL AS TicketID;
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- count how many seats user wants
        SELECT @TotalSeats = COUNT(value) FROM STRING_SPLIT(@SeatIDs, ',');
        
        IF @TotalSeats > @AvailableSeats
        BEGIN
            SELECT 0 AS Success, 'Not enough seats available.' AS Message, NULL AS TicketID;
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- max 5 seats per booking
        IF @TotalSeats > 5
        BEGIN
            SELECT 0 AS Success, 'Maximum 5 seats per booking.' AS Message, NULL AS TicketID;
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- check if any of the seats are already booked
        IF EXISTS (
            SELECT 1 FROM TicketSeats ts
            INNER JOIN Tickets t ON ts.TicketID = t.TicketID
            WHERE ts.TripID = @TripID 
                AND ts.SeatID IN (SELECT CAST(value AS INT) FROM STRING_SPLIT(@SeatIDs, ','))
                AND t.Status IN ('Active', 'Completed')
        )
        BEGIN
            SELECT 0 AS Success, 'One or more seats are already booked.' AS Message, NULL AS TicketID;
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- validate coupon if provided
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
                SELECT 0 AS Success, 'Invalid or expired coupon.' AS Message, NULL AS TicketID;
                ROLLBACK TRANSACTION;
                RETURN;
            END
            
            -- check if user already used this coupon before
            IF EXISTS (SELECT 1 FROM UserCoupons WHERE UserID = @UserID AND CouponID = @CouponID AND IsUsed = 1)
            BEGIN
                SELECT 0 AS Success, 'Coupon already used.' AS Message, NULL AS TicketID;
                ROLLBACK TRANSACTION;
                RETURN;
            END
        END
        
        -- calculate the prices
        SET @TotalPrice = @TripPrice * @TotalSeats;
        SET @DiscountAmount = @TotalPrice * (@DiscountRate / 100);
        SET @FinalPrice = @TotalPrice - @DiscountAmount;
        
        -- check if user has enough credit
        SELECT @UserCredit = CreditBalance FROM Users WHERE UserID = @UserID;
        
        IF @UserCredit < @FinalPrice
        BEGIN
            SELECT 0 AS Success, 'Insufficient credit. Required: ' + CAST(@FinalPrice AS NVARCHAR) + ' TL' AS Message, NULL AS TicketID;
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- generate unique ticket code
        SET @TicketCode = 'TKT-' + CAST(YEAR(GETDATE()) AS NVARCHAR) + '-' + RIGHT('000000' + CAST(NEXT VALUE FOR TicketSequence AS NVARCHAR), 6);
        
        -- create the ticket record
        INSERT INTO Tickets (TicketCode, UserID, TripID, CouponID, TotalPrice, DiscountAmount, FinalPrice, Status)
        VALUES (@TicketCode, @UserID, @TripID, @CouponID, @TotalPrice, @DiscountAmount, @FinalPrice, 'Active');
        
        SET @TicketID = SCOPE_IDENTITY();
        
        -- now we need to assign seats to this ticket
        -- split the seat ids and passenger names into temp tables
        DECLARE @SeatIDTable TABLE (SeatID INT, RowNum INT);
        INSERT INTO @SeatIDTable (SeatID, RowNum)
        SELECT CAST(value AS INT), ROW_NUMBER() OVER (ORDER BY (SELECT NULL))
        FROM STRING_SPLIT(@SeatIDs, ',');
        
        DECLARE @NameTable TABLE (PassengerName NVARCHAR(100), RowNum INT);
        INSERT INTO @NameTable (PassengerName, RowNum)
        SELECT TRIM(value), ROW_NUMBER() OVER (ORDER BY (SELECT NULL))
        FROM STRING_SPLIT(@PassengerNames, '|');
        
        -- insert into ticketseats
        INSERT INTO TicketSeats (TicketID, SeatID, TripID, PassengerName)
        SELECT @TicketID, s.SeatID, @TripID, ISNULL(n.PassengerName, 'Passenger')
        FROM @SeatIDTable s
        LEFT JOIN @NameTable n ON s.RowNum = n.RowNum;
        
        -- update available seats count on the trip
        UPDATE Trips SET AvailableSeats = AvailableSeats - @TotalSeats, UpdatedAt = GETDATE()
        WHERE TripID = @TripID;
        
        -- deduct money from user
        UPDATE Users SET CreditBalance = CreditBalance - @FinalPrice, UpdatedAt = GETDATE()
        WHERE UserID = @UserID;
        
        -- record the payment
        INSERT INTO Payments (UserID, TicketID, Amount, PaymentType, PaymentMethod, Status)
        VALUES (@UserID, @TicketID, @FinalPrice, 'TicketPurchase', 'UserCredit', 'Completed');
        
        -- if coupon was used, mark it as used
        IF @CouponID IS NOT NULL
        BEGIN
            UPDATE Coupons SET TimesUsed = TimesUsed + 1 WHERE CouponID = @CouponID;
            
            IF EXISTS (SELECT 1 FROM UserCoupons WHERE UserID = @UserID AND CouponID = @CouponID)
                UPDATE UserCoupons SET IsUsed = 1, UsedAt = GETDATE() WHERE UserID = @UserID AND CouponID = @CouponID;
            ELSE
                INSERT INTO UserCoupons (UserID, CouponID, IsUsed, UsedAt) VALUES (@UserID, @CouponID, 1, GETDATE());
        END
        
        COMMIT TRANSACTION;
        SELECT 1 AS Success, 'Ticket purchased! Code: ' + @TicketCode AS Message, @TicketID AS TicketID;
        
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SELECT 0 AS Success, 'Error: ' + ERROR_MESSAGE() AS Message, NULL AS TicketID;
    END CATCH
END
GO


-- cancel ticket and give refund
CREATE OR ALTER PROCEDURE sp_CancelTicket
    @TicketID INT,
    @UserID INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    
    DECLARE @TicketStatus NVARCHAR(20);
    DECLARE @TripID INT;
    DECLARE @FinalPrice DECIMAL(10,2);
    DECLARE @SeatsCount INT;
    DECLARE @RefundAmount DECIMAL(10,2);
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- get ticket info
        SELECT @TicketStatus = t.Status, @TripID = t.TripID, @FinalPrice = t.FinalPrice
        FROM Tickets t WHERE t.TicketID = @TicketID AND t.UserID = @UserID;
        
        IF @TicketStatus IS NULL
        BEGIN
            SELECT 0 AS Success, 'Ticket not found.' AS Message;
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        IF @TicketStatus <> 'Active'
        BEGIN
            SELECT 0 AS Success, 'Only active tickets can be cancelled.' AS Message;
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        -- for now we give full refund (could add partial refund based on time later)
        SET @RefundAmount = @FinalPrice;
        SELECT @SeatsCount = COUNT(*) FROM TicketSeats WHERE TicketID = @TicketID;
        
        -- update ticket status
        UPDATE Tickets SET Status = 'Cancelled', CancellationDate = GETDATE(), RefundAmount = @RefundAmount
        WHERE TicketID = @TicketID;
        
        -- release the seats
        UPDATE Trips SET AvailableSeats = AvailableSeats + @SeatsCount, UpdatedAt = GETDATE()
        WHERE TripID = @TripID;
        
        -- give money back to user
        UPDATE Users SET CreditBalance = CreditBalance + @RefundAmount, UpdatedAt = GETDATE()
        WHERE UserID = @UserID;
        
        -- record the refund
        INSERT INTO Payments (UserID, TicketID, Amount, PaymentType, PaymentMethod, Status)
        VALUES (@UserID, @TicketID, @RefundAmount, 'Refund', 'UserCredit', 'Completed');
        
        COMMIT TRANSACTION;
        SELECT 1 AS Success, 'Ticket cancelled. Refund: ' + CAST(@RefundAmount AS NVARCHAR) + ' TL' AS Message;
        
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SELECT 0 AS Success, 'Error: ' + ERROR_MESSAGE() AS Message;
    END CATCH
END
GO


-- get all tickets for a user
-- can filter by status if needed
CREATE OR ALTER PROCEDURE sp_GetUserTickets
    @UserID INT,
    @StatusFilter NVARCHAR(20) = NULL
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
        t.FinalPrice AS PaidAmount,
        t.Status,
        t.PurchaseDate,
        STRING_AGG(CAST(s.SeatNumber AS NVARCHAR), ', ') AS SeatNumber,
        STRING_AGG(ts.PassengerName, ', ') AS PassengerName
    FROM Tickets t
    INNER JOIN Trips tr ON t.TripID = tr.TripID
    INNER JOIN Buses b ON tr.BusID = b.BusID
    INNER JOIN Companies c ON b.CompanyID = c.CompanyID
    INNER JOIN Cities dep ON tr.DepartureCityID = dep.CityID
    INNER JOIN Cities arr ON tr.ArrivalCityID = arr.CityID
    LEFT JOIN TicketSeats ts ON t.TicketID = ts.TicketID
    LEFT JOIN Seats s ON ts.SeatID = s.SeatID
    WHERE t.UserID = @UserID
        AND (@StatusFilter IS NULL OR @StatusFilter = '' OR t.Status = @StatusFilter)
    GROUP BY t.TicketID, t.TicketCode, c.CompanyName, dep.CityName, arr.CityName,
             tr.DepartureDate, tr.DepartureTime, tr.ArrivalTime, tr.DurationMinutes,
             t.FinalPrice, t.Status, t.PurchaseDate
    ORDER BY t.PurchaseDate DESC;
END
GO


-- add credit to user account (like topping up balance)
CREATE OR ALTER PROCEDURE sp_AddUserCredit
    @UserID INT,
    @Amount DECIMAL(10,2),
    @PaymentMethod NVARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    
    -- basic validation
    IF @Amount <= 0 OR @Amount > 10000
    BEGIN
        SELECT 0 AS Success, 'Invalid amount (1-10000 TL).' AS Message;
        RETURN;
    END
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        UPDATE Users SET CreditBalance = CreditBalance + @Amount, UpdatedAt = GETDATE()
        WHERE UserID = @UserID;
        
        INSERT INTO Payments (UserID, Amount, PaymentType, PaymentMethod, Status)
        VALUES (@UserID, @Amount, 'CreditTopUp', @PaymentMethod, 'Completed');
        
        COMMIT TRANSACTION;
        SELECT 1 AS Success, CAST(@Amount AS NVARCHAR) + ' TL added successfully.' AS Message;
        
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SELECT 0 AS Success, 'Error: ' + ERROR_MESSAGE() AS Message;
    END CATCH
END
GO


-- check if coupon is valid
CREATE OR ALTER PROCEDURE sp_ValidateCoupon
    @CouponCode NVARCHAR(50),
    @UserID INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @CouponID INT;
    DECLARE @DiscountRate DECIMAL(5,2);
    DECLARE @UsageLimit INT;
    DECLARE @TimesUsed INT;
    DECLARE @ExpiryDate DATE;
    DECLARE @IsActive BIT;
    
    SELECT @CouponID = CouponID, @DiscountRate = DiscountRate, 
           @UsageLimit = UsageLimit, @TimesUsed = TimesUsed,
           @ExpiryDate = ExpiryDate, @IsActive = IsActive
    FROM Coupons WHERE CouponCode = @CouponCode;
    
    -- check all the conditions
    IF @CouponID IS NULL
    BEGIN
        SELECT 0 AS IsValid, 0 AS DiscountRate, 'Coupon not found.' AS Message;
        RETURN;
    END
    
    IF @IsActive = 0
    BEGIN
        SELECT 0 AS IsValid, 0 AS DiscountRate, 'Coupon is inactive.' AS Message;
        RETURN;
    END
    
    IF @ExpiryDate < CAST(GETDATE() AS DATE)
    BEGIN
        SELECT 0 AS IsValid, 0 AS DiscountRate, 'Coupon expired.' AS Message;
        RETURN;
    END
    
    IF @TimesUsed >= @UsageLimit
    BEGIN
        SELECT 0 AS IsValid, 0 AS DiscountRate, 'Usage limit reached.' AS Message;
        RETURN;
    END
    
    IF EXISTS (SELECT 1 FROM UserCoupons WHERE UserID = @UserID AND CouponID = @CouponID AND IsUsed = 1)
    BEGIN
        SELECT 0 AS IsValid, 0 AS DiscountRate, 'Already used this coupon.' AS Message;
        RETURN;
    END
    
    -- coupon is valid
    SELECT 1 AS IsValid, @DiscountRate AS DiscountRate, CAST(@DiscountRate AS NVARCHAR) + '% discount!' AS Message;
END
GO


-- dashboard stats for admin panel
CREATE OR ALTER PROCEDURE sp_GetDashboardStats
    @CompanyID INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT
        (SELECT COUNT(*) FROM Users WHERE IsActive = 1 AND Role = 'User') AS TotalUsers,
        (SELECT COUNT(*) FROM Trips WHERE Status = 'Active' AND DepartureDate >= CAST(GETDATE() AS DATE)) AS TotalTrips,
        (SELECT COUNT(*) FROM Tickets WHERE Status = 'Active') AS TotalTickets,
        (SELECT ISNULL(SUM(FinalPrice), 0) FROM Tickets WHERE Status IN ('Active', 'Completed')) AS TotalRevenue,
        (SELECT COUNT(*) FROM Trips WHERE Status = 'Active' AND DepartureDate = CAST(GETDATE() AS DATE)) AS ActiveTrips;
END
GO


-- =====================
-- INSERT SAMPLE DATA
-- =====================

-- add some cities
INSERT INTO Cities (CityName) VALUES 
('Istanbul'), ('Ankara'), ('Izmir'), ('Antalya'), ('Bursa'),
('Adana'), ('Konya'), ('Gaziantep'), ('Mersin'), ('Kayseri'),
('Eskisehir'), ('Trabzon'), ('Samsun'), ('Denizli'), ('Mugla');
GO

-- add some bus companies
INSERT INTO Companies (CompanyName, Phone, Email, Address, Rating, TotalRatings) VALUES
('Metro Turizm', '0850 222 33 44', 'info@metroturizm.com', 'Istanbul, Turkey', 4.8, 1520),
('Pamukkale Turizm', '0850 333 44 55', 'info@pamukkale.com', 'Denizli, Turkey', 4.5, 1280),
('Kamil Koc', '0850 555 66 77', 'info@kamilkoc.com', 'Ankara, Turkey', 4.6, 1150);
GO

-- firm admins (all passwords are password123)
INSERT INTO FirmAdmins (CompanyID, FirstName, LastName, Email, Phone, PasswordHash) VALUES
(1, 'Mehmet', 'Demir', 'mehmet@metroturizm.com', '0532 111 22 33', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
(2, 'Ali', 'Kaya', 'ali@pamukkale.com', '0534 333 44 55', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
(3, 'Hasan', 'Celik', 'hasan@kamilkoc.com', '0536 555 66 77', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f');
GO

-- buses
INSERT INTO Buses (CompanyID, PlateNumber, TotalSeats, HasWifi, HasTV, HasRefreshments, HasPowerOutlet, HasEntertainment) VALUES
(1, '34 ABC 123', 40, 1, 1, 1, 1, 1),
(1, '34 DEF 456', 40, 1, 0, 1, 1, 0),
(2, '20 GHI 789', 40, 1, 1, 1, 0, 0),
(2, '20 JKL 012', 40, 1, 0, 1, 0, 0),
(3, '06 MNO 345', 40, 1, 1, 1, 1, 1),
(3, '06 PRS 678', 40, 1, 1, 1, 1, 0);
GO

-- generate seats for all buses (40 seats each, 4 columns A-B-C-D)
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

-- some test users
-- password hash is sha256 of "password123"
INSERT INTO Users (FirstName, LastName, Email, Phone, PasswordHash, IDNumber, Role, CreditBalance, BirthDate) VALUES
('Ahmet', 'Yilmaz', 'ahmet.yilmaz@email.com', '0532 111 22 33', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', '12345678901', 'User', 1500.00, '1990-05-15'),
('Fatma', 'Demir', 'fatma.demir@email.com', '0533 222 33 44', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', '23456789012', 'User', 800.00, '1985-08-20'),
('Mehmet', 'Kaya', 'mehmet.kaya@email.com', '0534 333 44 55', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', '34567890123', 'User', 250.00, '1995-12-10'),
('Admin', 'System', 'admin@busticket.com', '0500 000 00 00', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', '99999999999', 'SystemAdmin', 0.00, '1980-01-01');
GO

-- discount coupons
INSERT INTO Coupons (CouponCode, DiscountRate, UsageLimit, ExpiryDate, Description) VALUES
('DISCOUNT10', 10.00, 1000, '2025-12-31', '10% discount'),
('DISCOUNT20', 20.00, 500, '2025-12-31', '20% discount'),
('SUMMER25', 15.00, 2000, '2025-08-31', 'Summer special 15% off'),
('WELCOME50', 50.00, 100, '2025-12-31', 'Welcome bonus 50% off');
GO

-- give some coupons to users
INSERT INTO UserCoupons (UserID, CouponID) VALUES (1, 1), (1, 2), (2, 1), (2, 3), (3, 1);
GO

-- add some trips for testing
DECLARE @Today DATE = CAST(GETDATE() AS DATE);

INSERT INTO Trips (TripCode, BusID, DepartureCityID, ArrivalCityID, DepartureDate, DepartureTime, ArrivalTime, DurationMinutes, Price, AvailableSeats, Status) VALUES
('TRP-2025-000001', 1, 1, 2, DATEADD(DAY, 1, @Today), '09:00', '14:30', 330, 350.00, 40, 'Active'),
('TRP-2025-000002', 1, 1, 2, DATEADD(DAY, 1, @Today), '13:30', '19:00', 330, 350.00, 40, 'Active'),
('TRP-2025-000003', 1, 1, 2, DATEADD(DAY, 1, @Today), '20:00', '01:30', 330, 320.00, 40, 'Active'),
('TRP-2025-000004', 2, 1, 2, DATEADD(DAY, 2, @Today), '10:00', '15:30', 330, 340.00, 40, 'Active'),
('TRP-2025-000005', 3, 1, 3, DATEADD(DAY, 1, @Today), '08:00', '16:00', 480, 420.00, 40, 'Active'),
('TRP-2025-000006', 3, 1, 3, DATEADD(DAY, 2, @Today), '14:00', '22:00', 480, 400.00, 40, 'Active'),
('TRP-2025-000007', 4, 2, 3, DATEADD(DAY, 1, @Today), '09:30', '17:30', 480, 380.00, 40, 'Active'),
('TRP-2025-000008', 5, 1, 4, DATEADD(DAY, 3, @Today), '22:00', '08:00', 600, 450.00, 40, 'Active'),
('TRP-2025-000009', 6, 2, 4, DATEADD(DAY, 2, @Today), '23:00', '07:30', 510, 380.00, 40, 'Active'),
('TRP-2025-000010', 6, 2, 1, DATEADD(DAY, 4, @Today), '08:00', '13:30', 330, 350.00, 40, 'Active');
GO


-- done!
PRINT '========================================';
PRINT 'Database created successfully!';
PRINT '========================================';
PRINT 'Test logins:';
PRINT '  User: ahmet.yilmaz@email.com / password123';
PRINT '  Admin: admin@busticket.com / password123';
PRINT '========================================';
GO
