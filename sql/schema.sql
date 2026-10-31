-- Open-Data ETL Pipeline — SQLite schema (Day 3)
--
-- One row per hour of Delhi weather. `timestamp` is the natural key:
-- the same hour can only appear once, which is what makes load.py
-- idempotent (re-running it replaces rows instead of duplicating them).
--
-- Types follow SQLite conventions: timestamps are stored as ISO-8601
-- TEXT ('YYYY-MM-DD HH:MM:SS'), measurements as REAL.

CREATE TABLE IF NOT EXISTS weather_hourly (
    timestamp        TEXT PRIMARY KEY,          -- local time, Asia/Kolkata
    temperature_c    REAL NOT NULL,             -- air temperature, °C
    humidity_pct     REAL CHECK (humidity_pct BETWEEN 0 AND 100),
    precipitation_mm REAL CHECK (precipitation_mm >= 0),
    wind_speed_kmh   REAL CHECK (wind_speed_kmh >= 0),
    loaded_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Day 4 analysis queries filter and group by day a lot; index the date.
CREATE INDEX IF NOT EXISTS idx_weather_date
    ON weather_hourly (date(timestamp));
