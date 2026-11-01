-- EarthMind D1 Database Schema
-- Environmental monitoring platform

-- Environmental sensor readings from multiple sources
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,           -- e.g. 'sensor-42', 'satellite-eo1', 'station-abc'
    source_type TEXT NOT NULL,      -- 'iot_sensor', 'satellite', 'weather_station', 'community'
    location TEXT,                  -- Human-readable location name
    latitude REAL,
    longitude REAL,
    parameter TEXT NOT NULL,        -- e.g. 'pm2_5', 'co2', 'temperature', 'ph', 'noise_db'
    value REAL NOT NULL,
    unit TEXT,                      -- e.g. 'µg/m³', 'ppm', '°C', 'dB'
    timestamp TEXT NOT NULL,        -- ISO 8601 datetime
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_readings_parameter ON readings(parameter);
CREATE INDEX IF NOT EXISTS idx_readings_source ON readings(source);
CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_readings_location ON readings(latitude, longitude);

-- Active and historical alerts
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,             -- 'threshold', 'anomaly', 'trend', 'ecological_risk'
    severity TEXT NOT NULL,         -- 'low', 'medium', 'high', 'critical'
    message TEXT NOT NULL,
    location TEXT,
    latitude REAL,
    longitude REAL,
    parameter TEXT,
    threshold_value REAL,
    actual_value REAL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    resolved_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);

-- Detected anomalies
CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_id INTEGER REFERENCES readings(id),
    parameter TEXT NOT NULL,
    location TEXT,
    latitude REAL,
    longitude REAL,
    expected_value REAL,
    actual_value REAL,
    deviation REAL,                 -- Z-score or IQR-based deviation
    method TEXT NOT NULL,           -- 'zscore', 'iqr', 'rolling_avg'
    severity TEXT NOT NULL,         -- 'low', 'medium', 'high'
    detected_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_anomalies_parameter ON anomalies(parameter);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected ON anomalies(detected_at);

-- AI-generated analysis reports
CREATE TABLE IF NOT EXISTS analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT NOT NULL,      -- 'trend', 'risk', 'ecological_impact', 'summary'
    parameter TEXT,
    location TEXT,
    time_range_start TEXT,
    time_range_end TEXT,
    content TEXT NOT NULL,          -- AI-generated report text
    model_used TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_type ON analysis_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_created ON analysis_reports(created_at);

-- Seed data for demonstration
INSERT OR IGNORE INTO readings (source, source_type, location, latitude, longitude, parameter, value, unit, timestamp)
VALUES
    ('sensor-001', 'iot_sensor', 'Downtown Station', 40.7128, -74.0060, 'pm2_5', 12.4, 'µg/m³', datetime('now', '-1 hour')),
    ('sensor-001', 'iot_sensor', 'Downtown Station', 40.7128, -74.0060, 'pm2_5', 14.1, 'µg/m³', datetime('now', '-2 hours')),
    ('sensor-001', 'iot_sensor', 'Downtown Station', 40.7128, -74.0060, 'co2', 412.3, 'ppm', datetime('now', '-1 hour')),
    ('sensor-002', 'iot_sensor', 'Riverside Park', 40.7282, -73.9942, 'temperature', 22.5, '°C', datetime('now', '-1 hour')),
    ('sensor-002', 'iot_sensor', 'Riverside Park', 40.7282, -73.9942, 'ph', 7.2, 'pH', datetime('now', '-1 hour')),
    ('station-nyc1', 'weather_station', 'NYC Central', 40.7831, -73.9712, 'temperature', 21.8, '°C', datetime('now', '-30 minutes')),
    ('station-nyc1', 'weather_station', 'NYC Central', 40.7831, -73.9712, 'humidity', 65.0, '%', datetime('now', '-30 minutes')),
    ('sensor-003', 'iot_sensor', 'Industrial Zone', 40.6892, -74.0445, 'no2', 48.7, 'µg/m³', datetime('now', '-45 minutes')),
    ('sensor-003', 'iot_sensor', 'Industrial Zone', 40.6892, -74.0445, 'pm2_5', 28.9, 'µg/m³', datetime('now', '-45 minutes'));
