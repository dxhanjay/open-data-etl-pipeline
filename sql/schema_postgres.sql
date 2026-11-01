-- Open-Data ETL Pipeline — PostgreSQL schema (v2 loader)
--
-- Same table as the SQLite version, in Postgres dialect. One row per
-- hour of Delhi weather; `timestamp` is the natural key (PRIMARY KEY),
-- which is what makes load_postgres.py idempotent: re-runs upsert on
-- conflict instead of duplicating rows.
--
-- Differences from SQLite worth knowing:
--   * Real column types (TIMESTAMP, DOUBLE PRECISION) instead of TEXT/REAL
--   * loaded_at is a true TIMESTAMPTZ defaulting to now()
--   * CHECK constraints work the same way and are enforced on every write

CREATE TABLE IF NOT EXISTS weather_hourly (
    timestamp        TIMESTAMP PRIMARY KEY,        -- local time, Asia/Kolkata
    temperature_c    DOUBLE PRECISION NOT NULL,    -- air temperature, °C
    humidity_pct     DOUBLE PRECISION CHECK (humidity_pct BETWEEN 0 AND 100),
    precipitation_mm DOUBLE PRECISION CHECK (precipitation_mm >= 0),
    wind_speed_kmh   DOUBLE PRECISION CHECK (wind_speed_kmh >= 0),
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Analysis queries filter and group by day a lot; index the date part.
CREATE INDEX IF NOT EXISTS idx_weather_date
    ON weather_hourly (CAST(timestamp AS DATE));
