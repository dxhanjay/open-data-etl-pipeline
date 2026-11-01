# Open-Data ETL Pipeline — Delhi Weather

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)
![Data Source](https://img.shields.io/badge/Data-Open--Meteo%20API-009688?style=flat)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen?style=flat)

A small data engineering project that extracts open weather data from a public API, cleans and validates it, loads it into a database, and analyses it with SQL — built step by step, with each stage kept separate and testable.

## Pipeline Architecture

```mermaid
flowchart LR
    A[Open-Meteo API<br/>Delhi hourly weather] -->|extract.py| B[(data/raw/<br/>JSON, untouched)]
    B -->|transform.py — Day 2| C[(data/processed/<br/>clean table)]
    C -->|load.py — Day 3| D[(SQLite database)]
    D -->|sql/ queries — Day 4| E[Analysis results]
```

**Design principle:** the raw layer is never edited. Every downstream stage can be rebuilt from `data/raw/` at any time.

## Data Source
- **Open-Meteo API** — https://open-meteo.com — free & open, no API key required
- **Location:** Delhi, India (28.6139, 77.2090) · Timezone: Asia/Kolkata
- **Fields:** `temperature_2m`, `relative_humidity_2m`, `precipitation`, `wind_speed_10m` (hourly, 7-day forecast = 168 records per extract)

## Quick Start

```bash
git clone https://github.com/dxhanjay/open-data-etl-pipeline.git
cd open-data-etl-pipeline
pip install -r requirements.txt         # pandas, needed for transform
./run_pipeline.sh                       # extract -> transform -> load, one command
```

Or step by step: `python extract.py` (stdlib only) → `python transform.py` → `python load.py`. The pipeline is safe to re-run end to end — verified from a fresh copy of this repo: one command rebuilt the raw file, the clean CSV, and the full 168-row database from nothing.

**Sample output — extract:**
```
Downloading: https://api.open-meteo.com/v1/forecast?latitude=28.6139&longitude=77.209&...
Saved raw file : data/raw/delhi_weather_raw_2026-10-31.json
Hourly records : 168
Fields         : time, temperature_2m, relative_humidity_2m, precipitation, wind_speed_10m
```

**Sample output — transform:**
```
Raw file      : delhi_weather_raw_2026-10-31.json
Rows in       : 168
Rows out      : 168
Duplicates    : 0 removed
Hourly gaps   : 0 filled
Dropped rows  : 0 (missing temperature)
Missing values: {'timestamp': 0, 'temperature_c': 0, 'humidity_pct': 0, 'precipitation_mm': 0, 'wind_speed_kmh': 0}
Range issues  : {'humidity_out_of_range': 0, 'negative_precipitation': 0, 'negative_wind_speed': 0, 'temperature_out_of_band': 0}
Clean CSV     : data/processed/delhi_weather_clean.csv (168 rows)
Quality checks: all value ranges OK.
```

**Cleaning rules (explicit, never silent):** readable column names with units; timestamps parsed and sorted; duplicate hours dropped; missing hours re-indexed onto a full hourly grid and counted; rows without a temperature dropped; value ranges validated every run (humidity 0–100 %, no negative precipitation/wind, temperature sanity band −10…55 °C) with a non-zero exit code if any violation is found.

**Sample output — load:**
```
Clean CSV rows : 168
Table before   : 0 rows
Table after    : 168 rows (+168 net new)
Coverage       : 2026-10-31 00:00:00  →  2026-11-06 23:00:00
Database       : data/delhi_weather.db
Load complete — safe to re-run, timestamps upsert by key.
```

**Load design:** schema in `sql/schema.sql` — one row per hour, `timestamp` as PRIMARY KEY, CHECK constraints mirroring the Day 2 quality rules, plus an index on the date for analysis queries. `load.py` upserts with `INSERT OR REPLACE` inside a single transaction, so re-running the pipeline updates existing hours and appends new ones without ever duplicating rows (verified: second run = +0 net new).

### v2 — PostgreSQL loader

The same pipeline can target PostgreSQL instead of SQLite — the stack most real data platforms use:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/weather"
python load_postgres.py
```

`load_postgres.py` reads the identical clean CSV and applies `sql/schema_postgres.sql` (real `TIMESTAMP`/`DOUBLE PRECISION` types, `TIMESTAMPTZ` load stamp), upserting with Postgres's native `INSERT ... ON CONFLICT (timestamp) DO UPDATE` — the same idempotency contract as the SQLite loader. Verified against PostgreSQL 16: first run loaded 168 rows, second run +0 net new, and aggregates match the SQLite database exactly (weekly average 22.39 °C; hottest hour Nov 5, 14:00 at 28.1 °C). Requires `psycopg[binary]` (in `requirements.txt`).

## Project Structure

```
open-data-etl-pipeline/
├── extract.py            # Day 1 — download raw data from the API
├── transform.py          # Day 2 — clean + data quality checks
├── load.py               # Day 3 — load clean CSV into SQLite (idempotent upsert)
├── load_postgres.py      # v2 — load clean CSV into PostgreSQL (ON CONFLICT upsert)
├── sql/
│   ├── schema.sql            # Day 3 — weather_hourly table + date index (SQLite)
│   ├── schema_postgres.sql   # v2 — same table, PostgreSQL dialect
│   └── analysis_queries.sql  # Day 4 — 10 analysis queries (all executed)
├── requirements.txt      # pandas (Day 2 onward)
├── run_pipeline.sh       # one-command end-to-end run
├── data/
│   ├── raw/              # raw API responses, untouched (git-ignored, regenerated by extract.py)
│   └── processed/        # cleaned CSV output (git-ignored, regenerated by transform.py)
├── README.md
├── LICENSE
└── .gitignore
```

## Build Roadmap

- [x] **Day 1 — Extract:** API → `data/raw/` as untouched JSON, with record count logged
- [x] **Day 2 — Transform:** parse JSON into a tidy table with pandas; duplicate/gap/missing-value handling; quality checks on timestamps and value ranges, reported every run
- [x] **Day 3 — Load:** SQLite schema (timestamp primary key, CHECK constraints, date index) + loader with `INSERT OR REPLACE` upserts — re-runs verified duplicate-free
- [x] **Day 4 — Analyse:** 10 SQL queries in `sql/analysis_queries.sql` — daily summaries, hottest/coldest hours, diurnal cycle, day-over-day change (LAG), 24 h rolling average, per-day RANK, comfort buckets — all executed against the loaded data, findings below
- [x] **Day 5 — Polish:** `run_pipeline.sh` one-command runner, findings write-up (below), fresh-copy reproducibility test passed, final documentation
- [x] **v2 — PostgreSQL target:** `load_postgres.py` + `sql/schema_postgres.sql` — native `ON CONFLICT` upserts, verified on PostgreSQL 16 (168 rows, re-run +0, aggregates match SQLite)

## Skills Demonstrated
*Listed only as the corresponding stage is completed.*

- **Day 1:** Python (REST APIs, JSON, file handling), ETL design, raw-layer data modelling
- **Day 2:** pandas (tidy tables, datetime handling, deduplication, reindexing), data cleaning, data quality checks
- **Day 3:** SQL DDL (tables, primary keys, CHECK constraints, indexes), SQLite, idempotent loads / upserts, transactional writes
- **Day 4:** SQL analysis — GROUP BY aggregation, date functions, window functions (LAG, rolling AVG, RANK), CTEs, CASE classification

## Findings — Delhi, Oct 31 – Nov 6, 2026 (forecast data, 168 hours)

From `sql/analysis_queries.sql`, run against the loaded database:

- **A stable, dry week:** daily averages stayed in a narrow 22.0–22.8 °C band, and the day-over-day change never exceeded 0.7 °C. Total precipitation was **0.0 mm — zero rainy hours** in the entire forecast week (Q5).
- **Hottest hour:** Nov 5 at 14:00, **28.1 °C**. The daily peak is remarkably consistent — 14:00 is the warmest hour of day on average (27.5 °C), with 13:00–15:00 close behind (Q2, Q4).
- **Coldest hours:** 17.3 °C, reached around 05:00–06:00 on Nov 3 and Nov 5 (Q3).
- **Biggest daily swing:** Nov 5 — 10.8 °C between its 05:00 low (17.3 °C) and 14:00 high (28.1 °C) (Q6).
- **How the week felt:** 42.9 % of hours were Pleasant (20–25 °C), 31.0 % Cool (<20 °C), and 26.2 % Warm (25 °C+) (Q10).

## Project Summary

A complete, reproducible ETL pipeline built in five stages, each independently testable: **extract** raw API data without touching it, **transform** it with pandas under explicit cleaning rules and data-quality checks, **load** it into SQLite with an idempotent upsert design, and **analyse** it with SQL including window functions. The design choices that matter in real data engineering are all here: a raw layer that is never edited, quality checks that fail loudly instead of silently, loads that can be re-run safely, and findings documented next to the code.

**Possible next steps:** add more cities as a dimension table, schedule daily runs (cron/Airflow), or read historical archive data instead of the forecast feed. (PostgreSQL support from the original list is done — see the v2 loader above.)

## Author
**Dhananjoy Mahato** — Final-year BTech CSE, GD Goenka University, Gurugram
LinkedIn: https://www.linkedin.com/in/dhananjoy-mahato-303462272 · GitHub: https://github.com/dxhanjay

## License
MIT — see [LICENSE](LICENSE).
