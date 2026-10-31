"""
Day 3 — LOAD step of the Open-Data ETL Pipeline.

Reads the cleaned CSV written by transform.py
(data/processed/delhi_weather_clean.csv), applies sql/schema.sql to a
SQLite database (data/delhi_weather.db), and upserts every row.

Idempotent by design: `timestamp` is the table's PRIMARY KEY and rows
are written with INSERT OR REPLACE, so running load.py any number of
times leaves the table with exactly one row per hour — new extracts
update existing hours and append new ones, never duplicates.

Standard library only (sqlite3 + csv) — no extra installs.

Run:  python load.py        (after extract.py and transform.py)
"""

import csv
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent
CSV_PATH = BASE / "data" / "processed" / "delhi_weather_clean.csv"
SCHEMA_PATH = BASE / "sql" / "schema.sql"
DB_PATH = BASE / "data" / "delhi_weather.db"

COLUMNS = ["timestamp", "temperature_c", "humidity_pct",
           "precipitation_mm", "wind_speed_kmh"]

UPSERT_SQL = f"""
INSERT OR REPLACE INTO weather_hourly ({", ".join(COLUMNS)})
VALUES ({", ".join("?" for _ in COLUMNS)})
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

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        before = conn.execute(
            "SELECT COUNT(*) FROM weather_hourly").fetchone()[0]
        with conn:  # one transaction: all rows or none
            conn.executemany(UPSERT_SQL, rows)
        after, first, last = conn.execute(
            "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) "
            "FROM weather_hourly").fetchone()
    finally:
        conn.close()

    print(f"Clean CSV rows : {len(rows)}")
    print(f"Table before   : {before} rows")
    print(f"Table after    : {after} rows "
          f"({after - before:+d} net new)")
    print(f"Coverage       : {first}  →  {last}")
    print(f"Database       : data/{DB_PATH.name}")
    print("Load complete — safe to re-run, timestamps upsert by key.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
