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