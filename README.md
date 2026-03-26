# Freight Quote Engine

FastAPI backend for Rope Camp freight quoting.

## Features

- Reads customer-managed Google Sheet tabs:
  - `SKU_XREF`
  - `RC_MASTER`
  - `INPUTS`
- Translates brand SKU to RC Product Number
- Supports multi-piece kits
- Calls TMS for base rate
- Applies uplift / minimum pricing logic
- Optionally emails quote recipients listed in `INPUTS`

## Required Google Sheet structure

### `SKU_XREF`
Headers:

- `RC Product Number`
- `GameTime`
- `Park and Play Structures`
- `Superior Recreational Products`
- `Playcraft`
- `MSRP`
- `Active`

### `RC_MASTER`
Headers:

- `RC Product Number`
- `Component`
- `Pieces`
- `Length`
- `Width`
- `Height`
- `Weight`
- `Density`
- `Freight Class`
- `Overlength Tier`
- `Active`

### `INPUTS`
Headers:

- `Setting`
- `Value`

Required settings:

- `Uplift Percentage`
- `Flat Min. y/n`
- `Flat Min Value`
- `Min % MSRP`

Optional:
- `Quote Email Recipients`

## Environment variables

### Google
- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_SERVICE_ACCOUNT_FILE`

### Catalog refresh
- `CATALOG_REFRESH_TTL_SECONDS` default `3600`

### TMS
- `TMS_USE_MOCK` default `true`
- `TMS_BASE_URL`
- `TMS_USERNAME`
- `TMS_API_KEY`
- `TMS_TIMEOUT_SECONDS`

### Email
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `EMAIL_FROM`

## Local run

```bash
uvicorn app.main:app --reload
