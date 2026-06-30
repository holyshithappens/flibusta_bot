-- BotFeatureFlags definition
-- Global feature toggles for bot functionality, controlled by admin at runtime

CREATE TABLE IF NOT EXISTS BotFeatureFlags (
    feature_name TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT 1
);

-- Insert default values (all features enabled, maintenance off)
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('search', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('genre_filter', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('popular', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('genres_cmd', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('lang_search', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('max_books', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('book_format', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('search_type', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('size_limit', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('rating_filter', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('search_area', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('locale', 1);
INSERT OR IGNORE INTO BotFeatureFlags (feature_name, enabled) VALUES ('maintenance', 0);