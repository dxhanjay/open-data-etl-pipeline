#!/usr/bin/env bash
# Run the full ETL pipeline end to end: extract -> transform -> load.
# Safe to re-run any time: extract overwrites today's raw file,
# transform rebuilds the clean CSV, and load upserts by timestamp,
# so the database never gains duplicate hours.
set -euo pipefail
cd "$(dirname "$0")"

echo "== Step 1/3: Extract =="
python3 extract.py
echo
echo "== Step 2/3: Transform =="
python3 transform.py
echo
echo "== Step 3/3: Load =="
python3 load.py
echo
echo "Pipeline complete. Analysis: sql/analysis_queries.sql against data/delhi_weather.db"
