"""
v2 — LOAD step, PostgreSQL variant of the Open-Data ETL Pipeline.

Same contract as load.py (SQLite), different database: reads the cleaned
CSV written by transform.py (data/processed/delhi_weather_clean.csv),
applies sql/schema_postgres.sql, and upserts every row into PostgreSQL.

Idempotent by design: `timestamp` is the PRIMARY KEY and rows are written
with INSERT ... ON CONFLICT (timestamp) DO UPDATE, so re-running this
loader leaves exactly one row per hour — Postgres's native upsert, the
same idea as SQLite's INSERT OR REPLACE in load.py.

Connection comes from the DATABASE_URL environment variable, e.g.:
    export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/weather"
(defaults to that local value when the variable is not set).

Requires: pip install "psycopg[binary]"   (see requirements.txt)

Run:  python load_postgres.py   (after extract.py and transform.py)
"""

import csv
import os
import sys
from pathlib import Path

try:
    import psycopg
except ImportError:
    sys.exit('psycopg is not installed — run: pip install "psycopg[binary]"')

BASE = Path(__file__).parent
CSV_PATH = BASE / "data" / "processed" / "delhi_weather_clean.csv"
SCHEMA_PATH = BASE / "sql" / "schema_postgres.sql"
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/weather")

COLUMNS = ["timestamp", "temperature_c", "humidity_pct",
           "precipitation_mm", "wind_speed_kmh"]

UPSERT_SQL = f"""
INSERT INTO weather_hourly ({", ".join(COLUMNS)})
VALUES ({", ".join("%s" for _ in COLUMNS)})
ON CONFLICT (timestamp) DO UPDATE SET
    temperature_c    = EXCLUDED.temperature_c,
    humidity_pct     = EXCLUDED.humidity_pct,
    precipitation_mm = EXCLUDED.precipitation_mm,
    wind_speed_kmh   = EXCLUDED.wind_speed_kmh,
    loaded_at        = now()
"""


def read_clean_csv(path: Path) -> list[tuple]:
    """Read the clean CSV into row tuples, converting numbers to float."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} not found — run transform.py first.")
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(tuple(
                record["timestamp"] if col == "timestamp"
                else (float(record[col]) if record[col] != "" else None)
                for col in COLUMNS))
    return rows


def main() -> int:
    rows = read_clean_csv(CSV_PATH)
    if not rows:
        print("Clean CSV is empty — nothing to load.")
        return 1

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
            cur.execute("SELECT COUNT(*) FROM weather_hourly")
            before = cur.fetchone()[0]
            cur.executemany(UPSERT_SQL, rows)  # one transaction: all or none
            cur.execute(
                "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) "
                "FROM weather_hourly")
            after, first, last = cur.fetchone()
        conn.commit()

    print(f"Clean CSV rows : {len(rows)}")
    print(f"Table before   : {before} rows")
    print(f"Table after    : {after} rows "
          f"({after - before:+d} net new)")
    print(f"Coverage       : {first}  →  {last}")
    print("Database       : PostgreSQL (weather_hourly)")
    print("Load complete — safe to re-run, timestamps upsert by key.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
