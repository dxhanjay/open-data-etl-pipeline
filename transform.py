"""
Day 2 — TRANSFORM step of the Open-Data ETL Pipeline.

Reads the latest raw Open-Meteo JSON from data/raw/ (written by
extract.py), flattens the hourly arrays into a tidy table with pandas,
cleans it, runs data-quality checks, and writes the result to
data/processed/delhi_weather_clean.csv — ready for Day 3's load step
into SQLite.

Cleaning rules (kept explicit on purpose — silent fixes hide bugs):
  1. Rename API fields to readable names with units.
  2. Parse timestamps properly (not strings) and sort by time.
  3. Drop exact duplicate timestamps, keeping the first.
  4. Fill missing hourly timestamps (reindex to a full hourly grid);
     rows created this way are COUNTED in the quality report.
  5. Drop rows where temperature is missing (a weather row without a
     temperature is not usable); other gaps are left as NaN and flagged
     in the report instead of being invented.

Quality checks reported every run:
  rows in / rows out, missing values per column, duplicate timestamps
  removed, gaps filled, and value-range violations
  (humidity must be 0-100 %, precipitation and wind speed cannot be
  negative, Delhi temperature sanity band -10..55 C).

Run:  python transform.py
Needs: pandas  (pip install pandas)
"""

import json
import sys
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).parent / "data" / "raw"
OUT_PATH = Path(__file__).parent / "data" / "processed" / "delhi_weather_clean.csv"

RENAME = {
    "time": "timestamp",
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
}


def latest_raw_file() -> Path:
    """Return the most recently modified raw JSON, fail loudly if none."""
    files = sorted(RAW_DIR.glob("delhi_weather_raw_*.json"),
                   key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(
            f"No raw files in {RAW_DIR} — run extract.py first.")
    return files[-1]


def load_raw(path: Path) -> pd.DataFrame:
    """Flatten the Open-Meteo hourly arrays into a DataFrame."""
    with path.open(encoding="utf-8") as f:
        hourly = json.load(f)["hourly"]
    df = pd.DataFrame(hourly).rename(columns=RENAME)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply the cleaning rules and return (clean_df, stats)."""
    stats = {"rows_in": len(df)}

    stats["missing_per_column"] = {
        col: int(df[col].isna().sum()) for col in df.columns}

    df = df.sort_values("timestamp")
    dupes = int(df.duplicated(subset="timestamp").sum())
    df = df.drop_duplicates(subset="timestamp", keep="first")
    stats["duplicates_removed"] = dupes

    # Reindex onto a complete hourly grid so gaps become visible rows.
    full_range = pd.date_range(df["timestamp"].min(),
                               df["timestamp"].max(), freq="h")
    stats["gaps_filled"] = int(len(full_range) - len(df))
    df = df.set_index("timestamp").reindex(full_range)
    df.index.name = "timestamp"
    df = df.reset_index().rename(columns={"index": "timestamp"})

    before = len(df)
    df = df.dropna(subset=["temperature_c"])
    stats["rows_dropped_no_temperature"] = int(before - len(df))

    stats["rows_out"] = len(df)
    return df, stats


def quality_checks(df: pd.DataFrame) -> dict:
    """Count value-range violations in the cleaned data."""
    return {
        "humidity_out_of_range":
            int(((df["humidity_pct"] < 0) | (df["humidity_pct"] > 100)).sum()),
        "negative_precipitation":
            int((df["precipitation_mm"] < 0).sum()),
        "negative_wind_speed":
            int((df["wind_speed_kmh"] < 0).sum()),
        "temperature_out_of_band":
            int(((df["temperature_c"] < -10) | (df["temperature_c"] > 55)).sum()),
    }


def main() -> int:
    raw_path = latest_raw_file()
    print(f"Raw file      : {raw_path.name}")

    raw = load_raw(raw_path)
    clean_df, stats = clean(raw)
    violations = quality_checks(clean_df)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(OUT_PATH, index=False)

    print(f"Rows in       : {stats['rows_in']}")
    print(f"Rows out      : {stats['rows_out']}")
    print(f"Duplicates    : {stats['duplicates_removed']} removed")
    print(f"Hourly gaps   : {stats['gaps_filled']} filled")
    print(f"Dropped rows  : {stats['rows_dropped_no_temperature']} "
          "(missing temperature)")
    print(f"Missing values: {stats['missing_per_column']}")
    print(f"Range issues  : {violations}")
    print(f"Clean CSV     : {OUT_PATH.relative_to(Path.cwd()) if OUT_PATH.is_relative_to(Path.cwd()) else OUT_PATH} "
          f"({len(clean_df)} rows)")

    total_violations = sum(violations.values())
    if total_violations:
        print(f"WARNING: {total_violations} range violation(s) found — "
              "see 'Range issues' above.")
        return 1
    print("Quality checks: all value ranges OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
