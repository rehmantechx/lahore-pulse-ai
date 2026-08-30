# Lahore Pulse AI — Phase 0.5 Data Source Research & Feasibility Assessment

**Date**: 2026-08-14  
**Status**: Research Complete  
**Author**: Architecture Research (AI-assisted)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Research Methodology](#2-research-methodology)
3. [Primary Data Source: Open-Meteo](#3-primary-data-source-open-meteo)
4. [Secondary Data Source: OpenAQ](#4-secondary-data-source-openaq)
5. [Tertiary Data Source: AQICN / WAQI](#5-tertiary-data-source-aqicn--waqi)
6. [Supplementary Sources Evaluated](#6-supplementary-sources-evaluated)
7. [Prediction Target Determination](#7-prediction-target-determination)
8. [Historical Data Feasibility Assessment](#8-historical-data-feasibility-assessment)
9. [Temporal Alignment Design](#9-temporal-alignment-design)
10. [Spatial Architecture Design](#10-spatial-architecture-design)
11. [Data Quality Contracts](#11-data-quality-contracts)
12. [Provenance Requirements](#12-provenance-requirements)
13. [Licensing Documentation](#13-licensing-documentation)
14. [Source Reliability Ranking](#14-source-reliability-ranking)
15. [Future Ingestion Architecture](#15-future-ingestion-architecture)
16. [Provider Abstraction Design](#16-provider-abstraction-design)
17. [Risk Register](#17-risk-register)
18. [Recommendations](#18-recommendations)

---

## 1. Executive Summary

### Key Findings

**Lahore's air quality crisis is well-documented and data-rich.** The city regularly ranks among the world's most polluted, with PM2.5 concentrations frequently exceeding WHO guidelines by 5–40×. Winter smog seasons (October–February) produce AQI readings above 1000, causing school closures and health emergencies.

**Three free, open data sources provide sufficient coverage for a viable prediction model:**

| Source | What It Provides | Lahore Coverage | Cost |
|--------|-----------------|-----------------|------|
| **Open-Meteo** | Historical weather (1940+) + AQ forecasts (5-day) | Global, hourly, 9km resolution | Free (non-commercial) |
| **OpenAQ** | Ground-truth PM2.5/PM10/NO₂/SO₂/O₃/CO measurements | 60+ stations in Lahore via IQAir contributors | Free (API key required) |
| **AQICN/WAQI** | Real-time AQI + daily forecasts | Lahore station (US Embassy + citizen sensors) | Free (API token) |

**Primary Prediction Target: 24-hour ahead PM2.5 concentration forecasting for Lahore city center.**

This is feasible because:
- Open-Meteo provides 8+ years of hourly weather reanalysis data (2017–present) at 9km resolution for Lahore coordinates
- OpenAQ/IQAir network provides 60+ ground-truth PM2.5 monitoring stations across Lahore
- The causal relationship between meteorology and air quality is well-established in literature
- Lahore's pollution patterns are strongly seasonal, making them predictable with weather features

---

## 2. Research Methodology

Research was conducted through:
1. **API documentation review** — Official docs for Open-Meteo, OpenAQ v3, AQICN
2. **Terms of service analysis** — Licensing, rate limits, commercial use restrictions
3. **Data availability verification** — Checking Lahore-specific station coverage
4. **Feasibility assessment** — Can we build a training dataset with sufficient history and quality?
5. **Architecture design** — How should the ingestion pipeline be structured?

---

## 3. Primary Data Source: Open-Meteo

### 3.1 Overview

Open-Meteo is a free, open-source weather API operated by OpenMeteo GmbH (Switzerland). It aggregates data from multiple national weather services and reanalysis datasets.

**URL**: https://open-meteo.com  
**Source code**: https://github.com/open-meteo/open-meteo (AGPLv3)  
**Data licence**: CC-BY 4.0

### 3.2 APIs Relevant to Lahore Pulse AI

#### 3.2.1 Historical Weather API

| Property | Value |
|----------|-------|
| **Endpoint** | `https://archive-api.open-meteo.com/v1/archive` |
| **Coverage** | Global |
| **Models** | ECMWF IFS (9km, 2017+), ERA5 (0.25°, 1940+), ERA5-Land (0.1°, 1950+) |
| **Temporal resolution** | Hourly |
| **Lahore recommendation** | ECMWF IFS for 2017–present (highest resolution); ERA5 for longer history |

**Key hourly variables available:**

| Variable | Description | Unit |
|----------|-------------|------|
| `temperature_2m` | Air temperature at 2m | °C |
| `relative_humidity_2m` | Relative humidity at 2m | % |
| `dew_point_2m` | Dew point temperature at 2m | °C |
| `apparent_temperature` | Feels-like temperature | °C |
| `precipitation` | Total precipitation (preceding hour) | mm |
| `rain` | Liquid precipitation only | mm |
| `snowfall` | Snowfall amount | cm |
| `cloud_cover` | Total cloud cover | % |
| `cloud_cover_low/mid/high` | Cloud layers | % |
| `pressure_msl` | Sea-level pressure | hPa |
| `surface_pressure` | Surface pressure | hPa |
| `wind_speed_10m` | Wind speed at 10m | km/h |
| `wind_direction_10m` | Wind direction at 10m | ° |
| `wind_gusts_10m` | Wind gusts at 10m | km/h |
| `shortwave_radiation` | Solar radiation | W/m² |
| `et0_fao_evapotranspiration` | Reference evapotranspiration | mm |
| `vapour_pressure_deficit` | VPD | kPa |
| `weather_code` | WMO weather code | — |
| `soil_temperature_0_to_7cm` | Soil temperature | °C |
| `soil_moisture_0_to_7cm` | Soil moisture | m³/m³ |

**Daily aggregations available:**

| Variable | Description | Unit |
|----------|-------------|------|
| `temperature_2m_max/min` | Max/min daily temperature | °C |
| `apparent_temperature_max/min` | Max/min feels-like | °C |
| `precipitation_sum` | Daily precipitation total | mm |
| `rain_sum` | Daily rain total | mm |
| `wind_speed_10m_max` | Max daily wind speed | km/h |
| `wind_gusts_10m_max` | Max daily wind gusts | km/h |
| `wind_direction_10m_dominant` | Dominant wind direction | ° |
| `shortwave_radiation_sum` | Daily solar radiation sum | MJ/m² |
| `sunshine_duration` | Daily sunshine duration | seconds |
| `daylight_duration` | Daylight duration | seconds |
| `weather_code` | Most severe weather condition | WMO code |

**JSON response structure:**

```json
{
    "latitude": 31.52,
    "longitude": 74.36,
    "elevation": 217.0,
    "generationtime_ms": 2.2,
    "utc_offset_seconds": 0,
    "timezone": "Asia/Karachi",
    "timezone_abbreviation": "PKT",
    "hourly": {
        "time": ["2024-01-01T00:00", "2024-01-01T01:00", ...],
        "temperature_2m": [12.5, 12.3, ...],
        "relative_humidity_2m": [65, 67, ...],
        "pm2_5": [89.2, 85.1, ...]
    },
    "hourly_units": {
        "temperature_2m": "°C",
        "relative_humidity_2m": "%"
    }
}
```

#### 3.2.2 Air Quality API

| Property | Value |
|----------|-------|
| **Endpoint** | `https://air-quality-api.open-meteo.com/v1/air-quality` |
| **Coverage** | Global (CAMS) + Europe (CAMS European) |
| **Models** | CAMS European (11km, 2013+), CAMS Global (45km, 2022+) |
| **Temporal resolution** | Hourly |
| **Forecast horizon** | 5 days (up to 7) |
| **Lahore recommendation** | CAMS Global domain |

**Key AQ variables:**

| Variable | Description | Unit |
|----------|-------------|------|
| `pm10` | Particulate matter ≤10μm | μg/m³ |
| `pm2_5` | Particulate matter ≤2.5μm | μg/m³ |
| `carbon_monoxide` | CO concentration | μg/m³ |
| `nitrogen_dioxide` | NO₂ concentration | μg/m³ |
| `sulphur_dioxide` | SO₂ concentration | μg/m³ |
| `ozone` | O₃ concentration | μg/m³ |
| `aerosol_optical_depth` | AOD at 550nm | — |
| `dust` | Saharan dust particles | μg/m³ |
| `european_aqi` | European AQI | Index |
| `us_aqi` | US AQI | Index |

#### 3.2.3 Weather Forecast API

| Property | Value |
|----------|-------|
| **Endpoint** | `https://api.open-meteo.com/v1/forecast` |
| **Coverage** | Global |
| **Forecast horizon** | Up to 16 days |
| **Temporal resolution** | Hourly |

This will serve as the **inference-time weather input** for the ML model.

### 3.3 Rate Limits & Terms

| Constraint | Value |
|------------|-------|
| **Daily limit** | 10,000 API calls |
| **Hourly limit** | 5,000 API calls |
| **Minute limit** | 600 API calls |
| **Commercial use** | Not permitted on free tier |
| **Attribution required** | Yes — link to open-meteo.com |
| **Licence** | CC-BY 4.0 |

**Feasibility for training data collection**: A single API call with date range parameters can retrieve up to several years of hourly data. For ECMWF IFS (2017–2026), that's ~78,000 hourly observations per variable in ONE call. This is well within rate limits.

### 3.4 Lahore-Specific Considerations

- Lahore coordinates: `31.5204, 74.3587`
- Timezone: `Asia/Karachi` (UTC+5)
- Elevation: ~217m above sea level
- ECMWF IFS grid cell nearest to Lahore center will be within a few km
- ERA5 resolution (25km) is coarse but provides data back to 1940
- For training, ECMWF IFS (2017+) is preferred for highest accuracy

---

## 4. Secondary Data Source: OpenAQ

### 4.1 Overview

OpenAQ is a nonprofit platform aggregating ground-level ambient air quality data from government agencies and citizen science networks worldwide.

**URL**: https://openaq.org  
**API docs**: https://docs.openaq.org  
**API version**: v3 (v1/v2 retired January 2025)  
**S3 archive**: `s3://openaq-data-archive/` (no auth required)

### 4.2 API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.openaq.org/v3` |
| **Authentication** | API key via `X-API-Key` header |
| **Free tier rate limit** | 60 requests/minute, 2,000/hour |
| **Key registration** | https://explore.openaq.org/register |

### 4.3 Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /v3/locations?coordinates=31.5204,74.3587&radius=25000` | Find Lahore stations |
| `GET /v3/locations/{id}` | Station details (sensors, instruments, coordinates) |
| `GET /v3/sensors/{id}/measurements` | Raw measurement values |
| `GET /v3/sensors/{id}/hours` | Hourly averages |
| `GET /v3/sensors/{id}/days` | Daily averages |
| `GET /v3/sensors/{id}/months` | Monthly averages |
| `GET /v3/parameters` | List of measured parameters |

### 4.4 Measured Parameters

| Parameter | ID | Units | Description |
|-----------|-----|-------|-------------|
| PM2.5 | 2 | μg/m³ | Fine particulate matter |
| PM10 | 1 | μg/m³ | Coarse particulate matter |
| NO₂ | 7 | ppb or μg/m³ | Nitrogen dioxide |
| SO₂ | 9 | ppb or μg/m³ | Sulphur dioxide |
| CO | 8 | ppm | Carbon monoxide |
| O₃ | 10 | ppb or μg/m³ | Ozone |
| BC | — | μg/m³ | Black carbon |
| Temperature | — | °C | Temperature |
| Relative Humidity | — | % | Relative humidity |

### 4.5 Geospatial Queries

Two methods available (mutually exclusive):

1. **Bounding box**: `?bbox=minLon,minLat,maxLon,maxLat`
2. **Point + radius**: `?coordinates=lat,lon&radius=M` (max 25,000m)

For Lahore: `?coordinates=31.5204,74.3587&radius=25000` covers the entire metro area.

### 4.6 Measurement Response Structure

```json
{
    "meta": { "name": "openaq-api", "page": 1, "limit": 100, "found": 42 },
    "results": [
        {
            "value": 89.2,
            "parameter": { "id": 2, "name": "pm25", "units": "μg/m3", "displayName": "PM2.5" },
            "period": {
                "label": "raw",
                "interval": "01:00:00",
                "datetimeFrom": { "utc": "2024-01-01T00:00:00Z", "local": "2024-01-01T05:00:00+05:00" },
                "datetimeTo": { "utc": "2024-01-01T01:00:00Z", "local": "2024-01-01T06:00:00+05:00" }
            },
            "coordinates": null,
            "coverage": {
                "expectedCount": 1,
                "observedCount": 1,
                "percentComplete": 100.0
            }
        }
    ]
}
```

### 4.7 AWS S3 Bulk Data

The full OpenAQ archive is available on S3 without authentication:

```
s3://openaq-data-archive/records/csv.gz/locationid={id}/year={year}/month={month}/
```

**File naming**: `location-{id}-{YYYYMMDD}.csv.gz`  
**Update frequency**: 72 hours after end of day  
**CSV columns**: `location_id, sensor_id, location, datetime, lat, lon, parameter, units, value`

This is the **preferred method for bulk historical data download** — no rate limits, no API calls needed.

### 4.8 Terms of Use

| Rule | Detail |
|------|--------|
| **API key required** | Yes, for API access |
| **Attribution** | Must attribute both OpenAQ AND original data sources |
| **Cannot sell data** | Prohibited |
| **Cannot cache/redistribute** | Prohibited for bulk redistribution |
| **Cannot compete** | Cannot build a competing service using their hosted API |
| **S3 archive** | Public domain, no auth needed, standard AWS Open Data terms |
| **Self-hosting** | Permitted under open-source licence |

### 4.9 Lahore Station Coverage Assessment

Based on IQAir data (which feeds into OpenAQ), Lahore has **60+ monitoring stations** from **32 contributors**, including:

- Pakistan Air Quality Initiative
- The Urban Unit (government)
- Punjab Environmental Protection Agency
- U.S. Embassy/Consulate Lahore
- Lahore American School
- Various citizen science contributors

**Station coverage is excellent for Lahore.** Ground-truth PM2.5 data is available at hourly resolution from multiple locations across the city.

---

## 5. Tertiary Data Source: AQICN / WAQI

### 5.1 Overview

The World Air Quality Index (WAQI) Project operates aqicn.org, providing real-time AQI data aggregated from government monitoring stations worldwide.

**URL**: https://aqicn.org  
**API docs**: https://aqicn.org/json-api/doc

### 5.2 API Details

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.waqi.info` |
| **Authentication** | Token required (free registration at aqicn.org/data-platform/token) |
| **Rate limit** | 1,000 requests/second |
| **Format** | JSON |

### 5.3 Lahore Data Available

- **Station**: "Lahore" (US Embassy station + others)
- **Current AQI**: Variable (e.g., PM2.5 AQI: 128 on research date)
- **Pollutants**: PM2.5, PM10, NO₂, SO₂, O₃, CO
- **Forecast**: Daily AQI forecast (PM2.5 avg/max/min for ~3 days)
- **Historical**: Limited — primarily current + recent past

### 5.4 Limitations

| Limitation | Impact |
|------------|--------|
| **No historical data API** | Cannot use for training dataset |
| **Real-time only** | Good for live predictions, not model training |
| **Unvalidated data** | Data may be amended without notice |
| **Attribution mandatory** | Must credit WAQI Project |
| **Cannot sell data** | Prohibited |
| **Cannot use in paid apps** | Prohibited |

### 5.5 Role in Architecture

AQICN/WAQI will serve as:
- **Real-time input** for live prediction serving
- **Cross-validation source** for model predictions
- **NOT a training data source** (insufficient historical depth)

---

## 6. Supplementary Sources Evaluated

### 6.1 IQAir / AirVisual

| Property | Assessment |
|----------|-----------|
| **Coverage** | 60+ stations in Lahore |
| **Data type** | Real-time PM2.5, PM10, O₃, NO₂, SO₂, CO |
| **API** | Commercial API (AirVisual); limited free tier |
| **Historical** | Available via paid plans |
| **Verdict** | ⚠️ Good data but API restrictions make it unsuitable as primary source. Data flows into OpenAQ. |

### 6.2 Pakistan EPA / Punjab Environmental Protection Agency

| Property | Assessment |
|----------|-----------|
| **Coverage** | Government monitoring stations |
| **Data type** | PM2.5, PM10 |
| **Public access** | ❌ Government does NOT publish real-time data publicly |
| **Historical** | Not publicly available |
| **Verdict** | ❌ Cannot be used — data not publicly accessible |

### 6.3 U.S. Embassy/Consulate Air Monitoring

| Property | Assessment |
|----------|-----------|
| **Coverage** | Lahore, Islamabad, Karachi, Peshawar |
| **Data type** | Real-time PM2.5 |
| **Public access** | Via AQICN and OpenAQ |
| **Historical** | Available via OpenAQ |
| **Verdict** | ✅ Already captured through OpenAQ |

### 6.4 Copernicus Atmosphere Monitoring Service (CAMS)

| Property | Assessment |
|----------|-----------|
| **Coverage** | Global |
| **Data type** | Aerosol, pollutant forecasts and reanalysis |
| **Resolution** | 11km (European), 45km (Global) |
| **Access** | Available through Open-Meteo (free) or Copernicus ADS (registration) |
| **Historical** | European reanalysis from 2013; Global from 2022 |
| **Verdict** | ✅ Already captured through Open-Meteo Air Quality API |

### 6.5 ERA5 Reanalysis (ECMWF)

| Property | Assessment |
|----------|-----------|
| **Coverage** | Global, hourly, 0.25° (~25km) |
| **Historical** | 1940–present |
| **Variables** | Full atmospheric reanalysis |
| **Access** | Via Open-Meteo (free) or Copernicus CDS (registration) |
| **Verdict** | ✅ Available through Open-Meteo Historical Weather API |

### 6.6 OpenStreetMap (OSM)

| Property | Assessment |
|----------|-----------|
| **Data type** | Road networks, land use, POIs |
| **Relevance** | Traffic patterns, industrial zones, green spaces |
| **Access** | Free, open licence |
| **Verdict** | ⚠️ Useful as supplementary features (distance to major roads, industrial areas) but not for Phase 1. Could enhance model with spatial context. |

### 6.7 WorldPop / Population Density

| Property | Assessment |
|----------|-----------|
| **Data type** | Gridded population estimates |
| **Resolution** | 100m |
| **Relevance** | Population exposure mapping |
| **Access** | Free, open licence |
| **Verdict** | ⚠️ Useful for risk assessment layer (Phase 2+) but not for PM2.5 prediction model |

### 6.8 MODIS / VIIRS Satellite AOD

| Property | Assessment |
|----------|-----------|
| **Data type** | Aerosol Optical Depth from satellites |
| **Resolution** | 1km (MODIS), 750m (VIIRS) |
| **Temporal** | Daily |
| **Access** | NASA Earthdata (free, registration required) |
| **Verdict** | ⚠️ Could enhance PM2.5 prediction but introduces complexity (cloud masking, retrieval errors). CAMS AOD via Open-Meteo is a simpler alternative for Phase 1. |

---

## 7. Prediction Target Determination

### 7.1 Candidate Targets

| Target | Description | Data Availability | Scientific Basis | Recommendation |
|--------|-------------|-------------------|-----------------|----------------|
| **PM2.5 (24h ahead)** | Forecast fine particulate matter concentration | ✅ OpenAQ historical + Open-Meteo forecast | ✅ Strong meteorological drivers | **✅ PRIMARY TARGET** |
| **PM2.5 (72h ahead)** | Extended forecast | ✅ Same sources | ✅ But accuracy degrades | ⚠️ Secondary target |
| **AQI (US standard)** | Derived from PM2.5 + other pollutants | ✅ Derived from PM2.5 | ✅ Direct health relevance | ✅ Output format |
| **Heat risk index** | Temperature-based risk | ✅ Open-Meteo weather | ⚠️ Less novel, simpler | ❌ Not primary |
| **Flood risk** | Precipitation-based | ✅ Open-Meteo flood API | ⚠️ Different timescale | ❌ Phase 2 |

### 7.2 Primary Target: PM2.5 24-Hour Forecast

**Why PM2.5?**

1. **Most dangerous pollutant**: PM2.5 causes the most health damage in Lahore (cardiovascular, respiratory, neurological)
2. **Strongest seasonal signal**: Winter smog (Oct–Feb) produces PM2.5 10–40× WHO guidelines
3. **Meteorological drivers**: Temperature inversions, low wind, humidity, and precipitation strongly control PM2.5 levels
4. **Data abundance**: 60+ ground stations provide hourly PM2.5 readings; 8+ years of weather reanalysis available
5. **Policy relevance**: Directly informs school closure decisions, health advisories, and emission control policies
6. **Hackathon impact**: Most visible and understandable metric for judges

**Why 24-hour ahead?**

1. **Actionable**: 24h gives enough lead time for health advisories and policy responses
2. **Accurate**: Sufficient meteorological signal at this horizon
3. **Aligned with forecast data**: Open-Meteo weather forecast provides 5-day hourly data
4. **Matches existing systems**: AQICN provides daily AQI forecasts

### 7.3 Model Inputs (Features)

Based on meteorological literature and data availability:

| Feature Category | Variables | Source |
|-----------------|-----------|--------|
| **Temperature** | `temperature_2m`, `apparent_temperature`, `dew_point_2m` | Open-Meteo Historical/Forecast |
| **Humidity** | `relative_humidity_2m`, `vapour_pressure_deficit` | Open-Meteo Historical/Forecast |
| **Wind** | `wind_speed_10m`, `wind_direction_10m`, `wind_gusts_10m` | Open-Meteo Historical/Forecast |
| **Pressure** | `pressure_msl`, `surface_pressure` | Open-Meteo Historical/Forecast |
| **Precipitation** | `precipitation`, `rain`, `rain_sum` | Open-Meteo Historical/Forecast |
| **Radiation** | `shortwave_radiation`, `sunshine_duration` | Open-Meteo Historical/Forecast |
| **Cloud cover** | `cloud_cover`, `cloud_cover_low/mid/high` | Open-Meteo Historical/Forecast |
| **Soil** | `soil_temperature_0_to_7cm`, `soil_moisture_0_to_7cm` | Open-Meteo Historical |
| **Seasonal** | Hour-of-day, day-of-year, month | Derived |
| **Lagged PM2.5** | Previous 24–72h PM2.5 values | OpenAQ (ground truth) |
| **CAMS AQ** | `pm2_5`, `pm10`, `aerosol_optical_depth` | Open-Meteo Air Quality API |

---

## 8. Historical Data Feasibility Assessment

### 8.1 Training Dataset Requirements

| Requirement | Minimum | Ideal | Available |
|-------------|---------|-------|-----------|
| **History depth** | 2 years | 5+ years | 8 years (2017–2026) ECMWF IFS |
| **Temporal resolution** | Daily | Hourly | ✅ Hourly |
| **Target variable** | PM2.5 daily mean | PM2.5 hourly | ✅ Available from OpenAQ |
| **Weather features** | 5 core variables | 15+ variables | ✅ 20+ available |
| **Spatial coverage** | 1 station | 10+ stations | ✅ 60+ in Lahore |
| **Completeness** | 80% | 95%+ | ⚠️ Need to verify per station |

### 8.2 Data Collection Strategy

**Step 1: Ground-truth PM2.5 from OpenAQ S3 archive**
- Download hourly PM2.5 data for all Lahore stations
- Period: 2017–present (when OpenAQ coverage for Pakistan begins)
- Source: `s3://openaq-data-archive/records/csv.gz/locationid={id}/year={year}/month={month}/`
- No API key needed, no rate limits

**Step 2: Weather features from Open-Meteo Historical API**
- Single API call per year with all variables
- Coordinates: `31.5204, 74.3587` (Lahore center)
- Model: ECMWF IFS (9km, 2017–present)
- Timezone: `Asia/Karachi`
- ~78,888 hourly observations per variable per year (8,760 hours × 9 years)

**Step 3: CAMS AQ forecasts from Open-Meteo Air Quality API**
- Historical CAMS reanalysis (European: 2013+, Global: 2022+)
- PM2.5, PM10, AOD from CAMS model

### 8.3 Estimated Data Volume

| Data Type | Records | Size Estimate |
|-----------|---------|---------------|
| PM2.5 ground truth (60 stations × 9 years × 8,760 hours) | ~4.7M rows | ~200MB CSV |
| Weather features (9 years × 8,760 hours × 20 variables) | ~1.6M rows | ~150MB JSON |
| **Total training dataset** | **~6.3M rows** | **~350MB** |

This is **very manageable** — no large dataset download needed, and can be built incrementally.

### 8.4 Data Quality Concerns

| Concern | Mitigation |
|---------|------------|
| **Station gaps** | Use multiple stations; interpolate or use nearest-neighbor |
| **Sensor drift** | Cross-validate between nearby stations |
| **Temporal gaps** | Use Open-Meteo weather reanalysis as continuous backup |
| **Unit conversion** | OpenAQ provides units per measurement; normalize to μg/m³ |
| **CAMS model updates** | Pin to specific model version during training |

---

## 9. Temporal Alignment Design

### 9.1 Timezone Handling

| Source | Timezone | Resolution |
|--------|----------|------------|
| Open-Meteo | UTC (default) or local via `timezone` param | Hourly, ISO 8601 |
| OpenAQ | UTC + local (both provided) | Hourly |
| AQICN | Local | Hourly |

**Design Decision**: All internal storage in **UTC**. Conversion to local time (Asia/Karachi, UTC+5) only for display.

### 9.2 Temporal Resolution

| Source | Native Resolution | Alignment |
|--------|-------------------|-----------|
| Open-Meteo | Hourly (ISO 8601: `2024-01-01T00:00`) | UTC or local |
| OpenAQ | Hourly (ISO 8601 with tz offset: `2024-01-01T05:00:00+05:00`) | Local + UTC |
| AQICN | Hourly | Local |

**Design Decision**: Align all data to **UTC hourly bins**. For training, aggregate ground-truth PM2.5 to hourly means within each UTC bin.

### 9.3 Data Leakage Prevention

| Risk | Mitigation |
|------|------------|
| **Future data in training** | Strict temporal train/test split; never use data from prediction time |
| **CAMS forecast vs reanalysis** | Use reanalysis (historical) for training, forecast (real-time) for inference |
| **Ground-truth lag** | OpenAQ data available ~72h after observation; design pipeline accordingly |
| **Look-ahead bias** | Features must use only data available at prediction time |

### 9.4 Recommended Time Bins

```
Training features:  t-72h to t-1h weather variables
Training target:    t+1h to t+24h PM2.5 average
Inference features: current weather forecast (t+0 to t+24h)
Inference target:   next 24h PM2.5 forecast
```

---

## 10. Spatial Architecture Design

### 10.1 Lahore Geographic Boundaries

| Property | Value |
|----------|-------|
| **Center** | 31.5204°N, 74.3587°E |
| **Approximate bounds** | 31.44°N–31.60°N, 74.28°E–74.44°E |
| **Area** | ~1,172 km² (metro area) |
| **Elevation** | 200–220m above sea level |
| **Timezone** | Asia/Karachi (UTC+5) |

### 10.2 Spatial Aggregation Strategy

**For the ML model**: Single point prediction at Lahore center coordinates.

**Rationale**: 
- Open-Meteo grid cell (~9km) covers most of Lahore
- Most ground stations are within 15km of center
- A single city-wide prediction is the most useful for public health advisories
- Future versions can add sub-city spatial resolution

### 10.3 Station Selection for Ground Truth

| Criterion | Approach |
|-----------|----------|
| **Minimum stations** | 3 active stations with >90% completeness |
| **Preferred stations** | Government/institutional (higher quality) |
| **Aggregation** | Mean PM2.5 across selected stations |
| **Fallback** | Nearest-station if primary stations fail |

### 10.4 Spatial Features (Future)

For Phase 2+ enhancements:
- Distance to major roads (OSM)
- Industrial zone proximity
- Green space coverage
- Population density (WorldPop)
- Crop burning hotspots (VIIRS fire data)

---

## 11. Data Quality Contracts

### 11.1 Per-Observation Quality Requirements

```python
class DataQualityContract:
    """Quality requirements for a single observation."""
    
    # Value bounds
    PM25_MIN_UG_M3: float = 0.0          # Physical minimum
    PM25_MAX_UG_M3: float = 1000.0       # Extreme but possible (Lahore hit 1900 AQI)
    
    # Temporal requirements
    MAX_GAP_HOURS: int = 6               # Alert if gap > 6 hours
    MIN_COMPLETENESS: float = 0.90       # 90% completeness per day
    
    # Spatial requirements
    MAX_STATION_DISTANCE_KM: float = 25.0  # Maximum distance from Lahore center
    
    # Freshness
    MAX_STALENESS_HOURS: int = 24         # Data older than 24h triggers warning
```

### 11.2 Per-Dataset Quality Requirements

| Metric | Threshold | Action on Failure |
|--------|-----------|-------------------|
| **Station count** | ≥3 active stations | Degraded mode (use fewer) |
| **Daily completeness** | ≥90% of hours | Skip incomplete days |
| **Value range** | 0–1000 μg/m³ | Flag outliers |
| **Temporal consistency** | No gaps >6h | Interpolate short gaps |
| **Cross-station correlation** | r > 0.8 | Flag divergent stations |

### 11.3 Provenance Tracking

Every observation must carry:

```python
class Provenance:
    source_id: str           # "openaq_v3", "openmeteo_archive", etc.
    source_identifier: str   # Original ID from source
    retrieved_at: datetime   # When we fetched it
    quality_flag: str        # "verified", "estimated", "interpolated"
    license: str             # "CC-BY-4.0", "OpenAQ-ToU", etc.
```

---

## 12. Provenance Requirements

### 12.1 Data Lineage Chain

```
OpenAQ S3 archive → Ingestion pipeline → Training dataset → Model → Predictions
       ↓                    ↓                  ↓              ↓          ↓
   Raw CSV.gz          Validated &        Feature store    Trained   Served via
                       normalized         (Parquet)        weights    API
```

### 12.2 Attribution Chain

For every data product, we must attribute:

1. **Original data provider** (e.g., "Data from Pakistan Air Quality Initiative via OpenAQ")
2. **Aggregation platform** (e.g., "Air quality data provided by OpenAQ")
3. **Weather data** (e.g., "Weather data by Open-Meteo.com")
4. **Reanalysis source** (e.g., "ERA5 data from ECMWF")

---

## 13. Licensing Documentation

### 13.1 Source Licence Summary

| Source | Licence | Commercial Use | Attribution Required |
|--------|---------|---------------|---------------------|
| **Open-Meteo** | CC-BY 4.0 | ❌ (free tier) | ✅ Link to open-meteo.com |
| **OpenAQ (API)** | OpenAQ ToU | ✅ (with restrictions) | ✅ OpenAQ + original sources |
| **OpenAQ (S3)** | AWS Open Data | ✅ | ✅ OpenAQ + original sources |
| **AQICN/WAQI** | WAQI ToU | ❌ (free tier) | ✅ WAQI Project |
| **CAMS (via Open-Meteo)** | CC-BY 4.0 | Via Open-Meteo terms | ✅ CAMS + Open-Meteo |
| **ERA5 (via Open-Meteo)** | CC-BY 4.0 | Via Open-Meteo terms | ✅ ECMWF + Open-Meteo |

### 13.2 Hackathon Compliance

For the Smart City Hackathon Lahore (non-commercial educational use):
- ✅ All free-tier restrictions satisfied
- ✅ Attribution will be included in all outputs
- ✅ No data will be resold or redistributed as cached data
- ✅ Open-Meteo link required on any UI displaying weather data

### 13.3 Attribution Templates

```python
ATTRIBUTION = {
    "open_meteo": 'Weather data by <a href="https://open-meteo.com/">Open-Meteo.com</a>',
    "open_aq": 'Air quality data provided by <a href="https://openaq.org/">OpenAQ</a> '
               'under the <a href="https://creativecommons.org/licenses/by/4.0/">CC-BY 4.0</a> licence. '
               'Original data: {source_name}',
    "cams": 'CAMS data by Copernicus Atmosphere Monitoring Service (CAMS), '
            'European Centre for Medium-Range Weather Forecasts.',
    "era5": 'ERA5 data from ECMWF. Hersbach et al. (2023). '
            'ERA5 hourly data on single levels from 1940 to present.',
}
```

---

## 14. Source Reliability Ranking

### 14.1 Reliability Matrix

| Rank | Source | Reliability | Rationale |
|------|--------|------------|-----------|
| **1** | Open-Meteo (ECMWF IFS) | ⭐⭐⭐⭐⭐ | Professional meteorological reanalysis; 9km resolution; global validation |
| **2** | Open-Meteo (ERA5) | ⭐⭐⭐⭐⭐ | Gold-standard climate reanalysis; 80+ year history; peer-reviewed |
| **3** | OpenAQ (government stations) | ⭐⭐⭐⭐ | Government instruments; calibration standards; but varies by provider |
| **4** | Open-Meteo (CAMS) | ⭐⭐⭐⭐ | Atmospheric composition model; validated against ground stations |
| **5** | OpenAQ (citizen stations) | ⭐⭐⭐ | Variable quality; some uncalibrated sensors; but large network |
| **6** | AQICN/WAQI | ⭐⭐⭐ | Aggregator; data unvalidated at publication; depends on source |
| **7** | IQAir (community) | ⭐⭐ | Mix of professional and consumer-grade sensors |

### 14.2 Data Fusion Strategy

For training data quality:
1. **Primary ground truth**: OpenAQ government/institutional stations
2. **Secondary ground truth**: OpenAQ citizen stations (with quality flags)
3. **Weather features**: Open-Meteo ECMWF IFS (highest resolution available)
4. **AQ model features**: CAMS via Open-Meteo Air Quality API
5. **Cross-validation**: Compare OpenAQ vs AQICN readings for same time periods

---

## 15. Future Ingestion Architecture

### 15.1 Architecture Overview (Phase 1 Design)

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │ Open-Meteo│  │ OpenAQ   │  │ AQICN/   │  │ Future  ││
│  │ Archive  │  │ S3/AWS   │  │ WAQI API │  │ Sources ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘│
│       │              │              │              │      │
└───────┼──────────────┼──────────────┼──────────────┼──────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                 INGESTION LAYER                          │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Provider Abstraction Layer              │   │
│  │  (implements DataProvider ABC)                    │   │
│  └──────────┬──────────┬──────────┬─────────────────┘   │
│             │          │          │                       │
│  ┌──────────▼──┐ ┌─────▼────┐ ┌──▼──────────┐          │
│  │OpenMeteo   │ │OpenAQ    │ │AQICN       │          │
│  │Provider    │ │Provider  │ │Provider    │          │
│  └──────┬─────┘ └────┬─────┘ └─────┬──────┘          │
│         │             │             │                    │
│         ▼             ▼             ▼                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Validation & Normalization Layer          │   │
│  │  - Unit conversion (→ μg/m³, °C, hPa)           │   │
│  │  - Quality flagging                               │   │
│  │  - Deduplication                                   │   │
│  │  - UTC normalization                               │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
└─────────────────────────┼────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  STORAGE LAYER                           │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            Raw Data Lake (S3/local)               │   │
│  │  source={source}/date={YYYY-MM-DD}/               │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────▼───────────────────────────┐   │
│  │          Feature Store (Parquet)                   │   │
│  │  hourly_features_{date}.parquet                   │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────▼───────────────────────────┐   │
│  │          Training Dataset                          │   │
│  │  training_{year}.parquet                          │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 15.2 Ingestion Modes

| Mode | Trigger | Data Window | Purpose |
|------|---------|-------------|---------|
| **Historical backfill** | Manual | 2017–present | Build training dataset |
| **Daily refresh** | Cron (02:00 UTC) | Past 72h | Update ground truth, correct gaps |
| **Real-time** | On-demand | Current hour | Live prediction serving |

### 15.3 Error Handling Strategy

| Error Type | Response |
|------------|----------|
| **Source unavailable** | Retry with exponential backoff (3 attempts) |
| **Partial data** | Accept with quality flag; log gap |
| **Rate limit** | Queue and throttle; respect limits |
| **Schema change** | Alert; fallback to previous schema version |
| **Duplicate data** | Deduplicate by source_id + timestamp |

---

## 16. Provider Abstraction Design

### 16.1 Interface Definition

```python
from abc import ABC, abstractmethod
from datetime import datetime

class WeatherDataProvider(ABC):
    """Interface for weather data providers."""
    
    @abstractmethod
    async def get_historical_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
        variables: list[str],
    ) -> WeatherData:
        """Retrieve historical weather data."""
        ...
    
    @abstractmethod
    async def get_weather_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 5,
        variables: list[str] | None = None,
    ) -> WeatherForecast:
        """Retrieve weather forecast."""
        ...
    
    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check provider availability."""
        ...


class AirQualityDataProvider(ABC):
    """Interface for air quality data providers."""
    
    @abstractmethod
    async def get_measurements(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        parameter: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[AirQualityMeasurement]:
        """Retrieve air quality measurements."""
        ...
    
    @abstractmethod
    async def get_locations(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> list[AirQualityStation]:
        """Discover monitoring stations."""
        ...
    
    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check provider availability."""
        ...
```

### 16.2 Provider Implementations (Phase 1)

| Provider | Class | Data Type | Source |
|----------|-------|-----------|--------|
| `OpenMeteoWeatherProvider` | WeatherDataProvider | Historical + forecast weather | Open-Meteo API |
| `OpenMeteoAirQualityProvider` | AirQualityDataProvider | CAMS AQ forecasts | Open-Meteo Air Quality API |
| `OpenAQProvider` | AirQualityDataProvider | Ground-truth measurements | OpenAQ v3 API + S3 |
| `AQICNProvider` | AirQualityDataProvider | Real-time AQI | AQICN/WAQI API |

### 16.3 Provider Selection Strategy

```python
# Priority order for each data type
WEATHER_PRIORITY = ["openmeteo"]  # Single source for weather
AQ_GROUND_TRUTH_PRIORITY = ["openaq", "aqicn"]  # OpenAQ primary
AQ_FORECAST_PRIORITY = ["openmeteo_airquality"]  # CAMS model
```

---

## 17. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| OpenAQ S3 archive missing Lahore data for some years | Medium | High | Cross-reference with AQICN; interpolate gaps |
| Open-Meteo rate limit hit during bulk download | Low | Medium | Chunk requests by year; respect rate limits |
| Ground-truth PM2.5 sensor quality varies | High | Medium | Weight government stations higher; cross-validate |
| CAMS model resolution too coarse for Lahore (45km) | Low | Low | 9km ECMWF IFS weather data compensates |
| API terms change or service degrades | Low | Medium | Archive data locally; implement circuit breakers |
| Lahore station network sparse before 2017 | Medium | Medium | Use ERA5 weather reanalysis for longer history |
| Data leakage in training pipeline | Medium | Critical | Strict temporal splits; automated leakage detection tests |

---

## 18. Recommendations

### 18.1 Immediate Actions (Phase 0.5 → Phase 1)

1. **Register for OpenAQ API key** at explore.openaq.org
2. **Register for AQICN API token** at aqicn.org/data-platform/token
3. **Design and implement provider abstraction layer** (Section 16)
4. **Implement Open-Meteo historical weather ingestion** (highest priority — most data)
5. **Implement OpenAQ S3 bulk download** for ground-truth PM2.5
6. **Build training dataset schema** with provenance tracking

### 18.2 Model Architecture Direction

For PM2.5 24h forecasting, recommended approaches:
1. **Baseline**: XGBoost/LightGBM with engineered weather features
2. **Advanced**: Temporal fusion transformer (TFT) for multi-horizon forecasting
3. **Ensemble**: Combine meteorological model with statistical baseline

### 18.3 Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| **MAE (PM2.5)** | < 15 μg/m³ | Better than persistence baseline |
| **R² score** | > 0.7 | Strong predictive power |
| **Smog event detection** | > 90% recall | Must catch extreme pollution events |
| **Data completeness** | > 95% | Minimal gaps in predictions |
| **Inference latency** | < 500ms | Real-time API serving |

---

*This document serves as the foundation for Phase 1 implementation. All architectural decisions made here should be codified as ADRs and implemented through the provider abstraction layer defined in Section 16.*
