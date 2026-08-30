"""Verify weather API variable availability for Lahore."""

import httpx

vars_list = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature",
    "precipitation", "rain", "cloud_cover", "pressure_msl", "surface_pressure",
    "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "shortwave_radiation",
    "vapour_pressure_deficit", "soil_temperature_0_to_7cm", "soil_moisture_0_to_7cm",
]

params = {
    "latitude": 31.5204,
    "longitude": 74.3587,
    "hourly": ",".join(vars_list),
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "timezone": "UTC",
}

# Test ECMWF IFS
resp = httpx.get(
    "https://archive-api.open-meteo.com/v1/archive",
    params={**params, "models": "ecmwf_ifs"},
    timeout=30.0,
)
print(f"ECMWF IFS Jan 2024 - Status: {resp.status_code}")
data = resp.json()
hourly = data.get("hourly", {})
times = hourly.get("time", [])
print(f"Total hours: {len(times)}")
for var in vars_list:
    vals = hourly.get(var, [])
    non_null = len([v for v in vals if v is not None])
    print(f"  {var}: {non_null}/{len(times)} ({non_null * 100 // len(times)}%)")

# Test ERA5
resp2 = httpx.get(
    "https://archive-api.open-meteo.com/v1/archive",
    params={**params, "models": "era5"},
    timeout=30.0,
)
print(f"\nERA5 Jan 2024 - Status: {resp2.status_code}")
data2 = resp2.json()
hourly2 = data2.get("hourly", {})
for var in vars_list:
    vals = hourly2.get(var, [])
    non_null = len([v for v in vals if v is not None])
    print(f"  {var}: {non_null}/{len(times)} ({non_null * 100 // len(times)}%)")

# Test: earliest ECMWF IFS data available for Lahore
print("\n--- Testing ECMWF IFS earliest available ---")
for year in [2017, 2018, 2019, 2020, 2021, 2022]:
    resp3 = httpx.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": 31.5204,
            "longitude": 74.3587,
            "hourly": "temperature_2m",
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-01-07",
            "timezone": "UTC",
            "models": "ecmwf_ifs",
        },
        timeout=30.0,
    )
    if resp3.status_code == 200:
        d = resp3.json()
        t = d.get("hourly", {}).get("time", [])
        temp = d.get("hourly", {}).get("temperature_2m", [])
        nn = len([v for v in temp if v is not None])
        print(f"  {year}: {nn}/{len(t)} temp values")
    else:
        print(f"  {year}: HTTP {resp3.status_code}")

# Test: ERA5 from 2015-2016
print("\n--- Testing ERA5 earliest for Lahore ---")
for year in [2015, 2016, 2017]:
    resp4 = httpx.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": 31.5204,
            "longitude": 74.3587,
            "hourly": "temperature_2m",
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-01-07",
            "timezone": "UTC",
            "models": "era5",
        },
        timeout=30.0,
    )
    if resp4.status_code == 200:
        d = resp4.json()
        t = d.get("hourly", {}).get("time", [])
        temp = d.get("hourly", {}).get("temperature_2m", [])
        nn = len([v for v in temp if v is not None])
        print(f"  {year}: {nn}/{len(t)} temp values")
    else:
        print(f"  {year}: HTTP {resp4.status_code}")
