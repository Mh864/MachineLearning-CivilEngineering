# Datasets

This document describes datasets currently used in the project and datasets planned for future versions.

## 1) USGS daily gauge data (currently used)

### Source

- Provider: USGS NWIS Daily Values API
- Endpoint: `https://waterservices.usgs.gov/nwis/dv/`
- Parameters used:
  - `00060`: discharge (ft3/s)
  - `00065`: gage height/stage (ft), optional

### Site configuration

Sites are listed in `data_ingestion/sites.json`.
Current default example:

- `01646500` - Potomac River at Point of Rocks, MD

### Raw file location

- Directory: `data/raw/usgs/`
- Typical filenames:
  - `usgs_dv_daily_2018-01-01_2024-12-31.csv` (combined)
  - `usgs_dv_daily_01646500_2024-01-01_2024-01-10.csv` (per site, if `--per-site` is used)

### Raw schema

Raw output columns (normalized in ingestion):

- `site_id` (string): USGS site number
- `date` (string, `YYYY-MM-DD`)
- `discharge` (float): daily discharge, ft3/s
- `stage` (float, nullable): daily gage height, ft
- `source` (string): data source label (`USGS_NWIS_DV`)

## 2) Processed clean dataset (currently used)

### Location

- `data/processed/clean_data.csv`

### Produced by

- Script: `data_processing/clean_data.py`

### Processing summary

- Reads all CSVs in `data/raw/usgs/`.
- Validates required columns.
- Normalizes dtypes and dates.
- Drops duplicate `(site_id, date)` rows (keeps latest).
- Reindexes each site to a continuous daily date range from min to max date.
- Leaves missing values as `NaN` when a day exists in timeline but not in source records.

### Schema

- `site_id` (string)
- `date` (datetime/date)
- `discharge` (float, nullable)
- `stage` (float, nullable)
- `source` (string, nullable on inserted missing days)

## 3) Feature dataset (currently used)

### Location

- `data/processed/features.csv`

### Produced by

- Script: `modeling/features.py`

### Feature engineering logic

Per site, ordered by date:

- `discharge_lag1`, `discharge_lag2`, `discharge_lag3`
- `discharge_roll_mean_3`, `discharge_roll_mean_7`
- `discharge_diff_1`
- `month`
- `prcp_lag1`, `prcp_lag2`, `prcp_lag3`
- `prcp_roll_sum_3`, `prcp_roll_sum_7`
- `prcp_roll_mean_3`, `prcp_roll_mean_7`
- `heavy_rain_flag_1d`
- `tmax`, `tmin`, `tavg`, `temp_range`
- `awnd`, `snow`, `snow_depth`
- `prcp_x_discharge_lag1`
- `prcp_roll_sum_3_x_discharge_roll_mean_3`

Target is generated as:

- `threshold`: per-site discharge percentile (`--percentile`, default `0.9`)
- `discharge_next_day`: shifted discharge
- `target`: `1` if `discharge_next_day > threshold`, else `0`

Rows with `NaN` in required feature/target fields are dropped.

### Schema

- `site_id`
- `date`
- `discharge_lag1`
- `discharge_lag2`
- `discharge_lag3`
- `discharge_roll_mean_3`
- `discharge_roll_mean_7`
- `discharge_diff_1`
- `month`
- `prcp_lag1`
- `prcp_lag2`
- `prcp_lag3`
- `prcp_roll_sum_3`
- `prcp_roll_sum_7`
- `prcp_roll_mean_3`
- `prcp_roll_mean_7`
- `heavy_rain_flag_1d`
- `tmax`
- `tmin`
- `tavg`
- `temp_range`
- `awnd`
- `snow`
- `snow_depth`
- `prcp_x_discharge_lag1`
- `prcp_roll_sum_3_x_discharge_roll_mean_3`
- `threshold`
- `discharge_next_day`
- `target`

## 4) NOAA weather dataset (implemented)

### Status

- `data_ingestion/fetch_weather.py` is fully implemented using NOAA CDO API (`GHCND` daily summaries).
- It fetches `PRCP`, `TMAX`, `TMIN` per configured site and date range.
- It writes both:
  - one combined file for all sites
  - one per-location rainfall file (`rainfall_<LocationName>.csv`) used by `modeling/features.py`

### Source

- Provider: NOAA NCEI Climate Data Online (CDO)
- Endpoint: `https://www.ncei.noaa.gov/cdo-web/api/v2/data`
- Dataset ID: `GHCND`
- Data types fetched: `PRCP`, `TMAX`, `TMIN` (with optional `AWND`, `SNOW`, `SNWD` when available)
- Units: metric
- Authentication: required CDO token (`--token` or `NOAA_CDO_TOKEN` env var)

### Raw locations and filenames

- Directory: `data/raw/noaa/`
- Combined output:
  - `noaa_daily_<start>_<end>.csv`
- Per-location outputs (used by feature pipeline):
  - `rainfall_Potomac_DC.csv`
  - `rainfall_Neuse_NC.csv`
  - `rainfall_Allegheny_PA.csv`
  - `rainfall_RedRiver_ND.csv`
  - `rainfall_CherryCreek_CO.csv`
  - `rainfall_Trinity_TX.csv`
  - `rainfall_Colorado_AZ.csv`
  - `rainfall_Sacramento_CA.csv`
  - `rainfall_ClarkFork_MT.csv`
  - `rainfall_Willamette_OR.csv`

### Combined NOAA schema (`noaa_daily_<start>_<end>.csv`)

- `site_id`
- `date`
- `precip_mm`
- `tmin_c`
- `tmax_c`
- `source`

### Per-location rainfall schema (`rainfall_<LocationName>.csv`)

- `STATION`
- `NAME`
- `DATE`
- `PRCP`
- `TMAX`
- `TMIN`

Notes:

- `PRCP` is precipitation in millimeters.
- Missing `PRCP` values are filled with `0.0`.
- These per-location files are what `modeling/features.py` reads via `load_noaa_precip()`.

### Site-to-location mapping used by features

`modeling/features.py` maps USGS sites to expected NOAA rainfall filenames:

- `01646500 -> Potomac_DC`
- `02087500 -> Neuse_NC`
- `03015500 -> Allegheny_PA`
- `05054000 -> RedRiver_ND`
- `06710247 -> CherryCreek_CO`
- `08066500 -> Trinity_TX`
- `09380000 -> Colorado_AZ`
- `11447650 -> Sacramento_CA`
- `12301933 -> ClarkFork_MT`
- `14211720 -> Willamette_OR`

### How to run NOAA ingestion

Example (PowerShell):

```bash
$env:NOAA_CDO_TOKEN="your_token_here"
python -m data_ingestion.fetch_weather --sites-config data_ingestion/sites.json --start-date 2015-01-01 --end-date 2023-12-31 --out-dir data/raw/noaa
```

or pass token directly:

```bash
python -m data_ingestion.fetch_weather --sites-config data_ingestion/sites.json --start-date 2015-01-01 --end-date 2023-12-31 --out-dir data/raw/noaa --token your_token_here
```

Note: NOAA CDO rejects date spans >= 1 year in one request; the script automatically paginates by sub-year windows and merges results.

### Station mapping behavior

- The script includes default `site_id -> NOAA station_id` mappings.
- You can override per site in `data_ingestion/sites.json` by adding `noaa_station_id`.
- If a site has no station mapping, it is skipped with a warning (pipeline continues).

## 5) Datasets to consider next

For improved flood-risk modeling, these are good candidates:

- **Meteorological forcing**: precipitation totals/intensity, temperature, snowmelt indicators.
- **Hydrologic context**: upstream gauges, reservoir release data, soil moisture proxies.
- **Static basin features**: watershed area, slope, land cover, imperviousness.
- **Event labels**: externally validated flood event records for robust supervision.

## Data quality notes

- USGS daily series may have missing days or missing parameters.
- Stage (`00065`) can be unavailable for some sites/time ranges.
- Current baseline supports missingness in early stages, but modeling rows are dropped when engineered features or target cannot be computed.
- Use one combined raw file per time range or be careful with overlap to avoid accidental duplicate windows (the cleaner deduplicates by `site_id + date`).

## Reproducibility notes

- Ingestion date ranges are passed via CLI (`--start-date`, `--end-date`).
- Sites are controlled through `data_ingestion/sites.json`.
- Model target prevalence changes with percentile threshold (`--percentile`), so keep it fixed when comparing experiments.
