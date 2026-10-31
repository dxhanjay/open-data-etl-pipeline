"""
Day 1 — EXTRACT step of the Open-Data ETL Pipeline.

Downloads hourly weather data for Delhi from the Open-Meteo API
(free, open data, no API key needed) and saves the RAW response
to data/raw/ completely untouched. No cleaning happens here —
cleaning/transform is Day 2's job, so the raw file always stays
as the single source of truth.

Run:  python extract.py
"""
import json
import urllib.request
from datetime import date
from pathlib import Path

# --- Config -------------------------------------------------------------
LATITUDE = 28.6139    # Delhi
LONGITUDE = 77.2090
HOURLY_FIELDS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    f"&hourly={HOURLY_FIELDS}&forecast_days=7&timezone=Asia%2FKolkata"
)
RAW_DIR = Path(__file__).parent / "data" / "raw"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading: {API_URL}")
    with urllib.request.urlopen(API_URL, timeout=30) as response:
        payload = response.read()

    data = json.loads(payload)
    hourly = data.get("hourly", {})
    n_records = len(hourly.get("time", []))

    out_file = RAW_DIR / f"delhi_weather_raw_{date.today().isoformat()}.json"
    out_file.write_bytes(payload)  # raw bytes, untouched

    print(f"Saved raw file : {out_file}")
    print(f"Hourly records : {n_records}")
    print(f"Fields         : {', '.join(hourly.keys())}")
    print("Extract complete. Next step (Day 2): transform.py — clean & validate.")


if __name__ == "__main__":
    main()
