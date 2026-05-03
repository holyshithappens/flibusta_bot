-- PaymentLog definition

CREATE TABLE PaymentLog (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT,
            amount INTEGER NOT NULL,
            currency TEXT NOT NULL,
            payment_method TEXT,
            payment_date TEXT NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'completed',
            telegram_payment_charge_id TEXT,
            data_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

CREATE INDEX idx_paymentlog_user_id ON PaymentLog(user_id);
CREATE INDEX idx_paymentlog_payment_date ON PaymentLog(payment_date);
CREATE INDEX idx_paymentlog_status ON PaymentLog(payment_status);

-- UserPayment definition OLD

--CREATE TABLE UserPayment (
--                    PaymentID VARCHAR(100) PRIMARY KEY,
--                    UserID INTEGER NOT NULL,
--                    UserName VARCHAR(100),
--                    Amount DECIMAL(15,2) NOT NULL,
--                    Currency VARCHAR(10) NOT NULL,
--                    PaymentMethod VARCHAR(50),
--                    PaymentDate DATETIME NOT NULL,
--                    PaymentStatus VARCHAR(20) NOT NULL,
--                    ProviderChargeID VARCHAR(100),
--                    TelegramPaymentChargeID VARCHAR(100),
--                    InvoicePayload TEXT,
--                    ProviderPaymentChargeID VARCHAR(100),
--                    OrderInfo TEXT,
--                    ShippingAddress TEXT,
--                    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
--                    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
--
--                    -- Для возможного возврата
--                    Refundable BOOLEAN DEFAULT TRUE,
--                    RefundedAmount DECIMAL(15,2) DEFAULT 0,
--                    RefundedAt DATETIME,
--                    RefundReason TEXT,
--                    RefundTransactionID VARCHAR(100),
--
--                    -- Дополнительная информация
--                    UserLanguage VARCHAR(10),
--                    UserTimezone VARCHAR(50),
--                    IPAddress VARCHAR(45),
--                    UserAgent TEXT
--                );
--
--CREATE INDEX IXUserPayments_UserID
--                ON UserPayment (UserID);