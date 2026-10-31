-- Open-Data ETL Pipeline — Analysis Queries (Day 4)
-- Run against data/delhi_weather.db (table: weather_hourly).
-- Every query below was executed against the loaded Delhi data;
-- headline findings are summarised in the README.
--
-- Skills covered: GROUP BY aggregation, date functions, ORDER BY/LIMIT,
-- window functions (LAG, rolling AVG, RANK), CASE bucketing.

-- ---------------------------------------------------------------
-- Q1. Daily summary — one row per day
-- ---------------------------------------------------------------
SELECT
    date(timestamp)              AS day,
    COUNT(*)                     AS hours,
    ROUND(AVG(temperature_c), 1) AS avg_temp_c,
    ROUND(MIN(temperature_c), 1) AS min_temp_c,
    ROUND(MAX(temperature_c), 1) AS max_temp_c,
    ROUND(AVG(humidity_pct), 0)  AS avg_humidity_pct,
    ROUND(SUM(precipitation_mm), 1) AS total_precip_mm,
    ROUND(MAX(wind_speed_kmh), 1)   AS max_wind_kmh
FROM weather_hourly
GROUP BY date(timestamp)
ORDER BY day;

-- ---------------------------------------------------------------
-- Q2. The five hottest hours of the week
-- ---------------------------------------------------------------
SELECT timestamp, temperature_c, humidity_pct
FROM weather_hourly
ORDER BY temperature_c DESC
LIMIT 5;

-- ---------------------------------------------------------------
-- Q3. The five coldest hours of the week
-- ---------------------------------------------------------------
SELECT timestamp, temperature_c, humidity_pct
FROM weather_hourly
ORDER BY temperature_c ASC
LIMIT 5;

-- ---------------------------------------------------------------
-- Q4. Diurnal cycle — average temperature by hour of day
--     (Which hours are typically hottest / coolest?)
-- ---------------------------------------------------------------
SELECT
    strftime('%H', timestamp)    AS hour_of_day,
    ROUND(AVG(temperature_c), 1) AS avg_temp_c
FROM weather_hourly
GROUP BY hour_of_day
ORDER BY avg_temp_c DESC;

-- ---------------------------------------------------------------
-- Q5. Rain check — rainy hours and total rainfall
--     (precipitation > 0 counts as a rainy hour)
-- ---------------------------------------------------------------
SELECT
    COUNT(*) FILTER (WHERE precipitation_mm > 0) AS rainy_hours,
    ROUND(SUM(precipitation_mm), 1)              AS total_precip_mm,
    ROUND(MAX(precipitation_mm), 1)              AS wettest_hour_mm
FROM weather_hourly;

-- ---------------------------------------------------------------
-- Q6. Biggest temperature swing — which day varied the most?
-- ---------------------------------------------------------------
SELECT
    date(timestamp) AS day,
    ROUND(MAX(temperature_c) - MIN(temperature_c), 1) AS swing_c,
    ROUND(MIN(temperature_c), 1) AS min_temp_c,
    ROUND(MAX(temperature_c), 1) AS max_temp_c
FROM weather_hourly
GROUP BY day
ORDER BY swing_c DESC;

-- ---------------------------------------------------------------
-- Q7. Day-over-day change in average temperature (window: LAG)
-- ---------------------------------------------------------------
WITH daily AS (
    SELECT date(timestamp) AS day,
           ROUND(AVG(temperature_c), 1) AS avg_temp_c
    FROM weather_hourly
    GROUP BY day
)
SELECT
    day,
    avg_temp_c,
    ROUND(avg_temp_c - LAG(avg_temp_c) OVER (ORDER BY day), 1)
        AS change_vs_yesterday_c
FROM daily
ORDER BY day;

-- ---------------------------------------------------------------
-- Q8. 24-hour rolling average temperature (window: frame AVG)
--     Smooths the hourly noise into a trend line.
-- ---------------------------------------------------------------
SELECT
    timestamp,
    temperature_c,
    ROUND(AVG(temperature_c) OVER (
        ORDER BY timestamp
        ROWS BETWEEN 23 PRECEDING AND CURRENT ROW), 1) AS rolling_24h_avg_c
FROM weather_hourly
ORDER BY timestamp;

-- ---------------------------------------------------------------
-- Q9. Rank each day's hours by temperature (window: RANK)
--     Shows the top-3 hottest hours within every single day.
-- ---------------------------------------------------------------
SELECT day, timestamp, temperature_c, rnk
FROM (
    SELECT
        date(timestamp) AS day,
        timestamp,
        temperature_c,
        RANK() OVER (PARTITION BY date(timestamp)
                     ORDER BY temperature_c DESC) AS rnk
    FROM weather_hourly
)
WHERE rnk <= 3
ORDER BY day, rnk;

-- ---------------------------------------------------------------
-- Q10. Comfort buckets — how the week's hours split by feel
--      (CASE-based classification)
-- ---------------------------------------------------------------
SELECT
    CASE
        WHEN temperature_c < 20 THEN 'Cool (<20°C)'
        WHEN temperature_c < 25 THEN 'Pleasant (20–25°C)'
        ELSE 'Warm (25°C+)'
    END AS comfort_bucket,
    COUNT(*) AS hours,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM weather_hourly), 1)
        AS pct_of_week
FROM weather_hourly
GROUP BY comfort_bucket
ORDER BY hours DESC;
