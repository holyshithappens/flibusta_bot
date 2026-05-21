-- ============================================
-- Структурированное логирование (SQLite)
-- ============================================

CREATE TABLE IF NOT EXISTS StructuredLog (
    timestamp TEXT NOT NULL,                    -- ISO 8601: '2025-12-23 14:30:45.123'
    category TEXT NOT NULL,
    event_type TEXT NOT NULL,

    -- Пользователь (NULL для системных событий)
    user_id INTEGER,
    username TEXT,

    -- Контекст
    chat_type TEXT NOT NULL,
    chat_id INTEGER,

    -- Данные события (JSON, хранится как TEXT)
    data_json TEXT,

    -- Метрики
    duration_ms INTEGER,

    -- Ошибки
    error_message TEXT,
    error_type TEXT
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_structuredlog_timestamp ON StructuredLog(timestamp);
CREATE INDEX IF NOT EXISTS idx_structuredlog_category ON StructuredLog(category);
CREATE INDEX IF NOT EXISTS idx_structuredlog_event_type ON StructuredLog(event_type);
CREATE INDEX IF NOT EXISTS idx_structuredlog_user_id ON StructuredLog(user_id);
CREATE INDEX IF NOT EXISTS idx_structuredlog_category_timestamp ON StructuredLog(category, timestamp);
CREATE INDEX IF NOT EXISTS idx_structuredlog_event_type_timestamp ON StructuredLog(event_type, timestamp);