# NYC Transit Delay Prediction Project

## Overview
This project builds an end-to-end data pipeline around MTA GTFS-Realtime feeds,
ingesting real-time subway data into a PostgreSQL database for delay prediction
and anomaly detection.

## Project Structure
```
nyc-transit-pipeline/
├── sql/
│   └── 01_create_tables.sql   # DB schema
├── src/
│   ├── config.py              # Environment + settings loader
│   ├── db.py                  # SQLAlchemy engine + health check
│   ├── mta_client.py          # MTA GTFS-RT fetch client
│   ├── gtfs_parser.py         # Protobuf parser (trip updates + alerts)
│   ├── db_writer.py           # DB insertion logic
│   └── ingest.py              # End-to-end pipeline + hourly scheduler
├── test_parser.py             # Unit tests for parser
├── .env.example               # Environment variable template
└── requirements.txt
```

## What's Been Built
- Config loader (`config.py`)
- MTA GTFS-RT fetch client (`mta_client.py`)
- Database connectivity helpers (`db.py`)
- API + DB test scripts
- GTFS-Realtime protobuf parsing for trip updates and alerts (`gtfs_parser.py`)
- Raw payload storage, trip update and alert DB writers (`db_writer.py`)
- End-to-end ingestion pipeline with error handling and logging (`ingest.py`)
- Hourly scheduler with configurable interval (`ingest.py`)
- Unit tests for parser logic (`test_parser.py`)

## Enhancements Added
- Departure time and departure delay captured alongside arrival data
- Alert text filtered for English with graceful fallback to first available translation
- Scheduler interval configurable via `INGEST_INTERVAL_SECONDS` in `.env`
- Duplicate row prevention via `ON CONFLICT DO NOTHING` on all DB inserts

## What's Yet To Be Done
- Feature engineering from ingested transit data
- ML models: delay prediction, station clustering, anomaly detection
- REST API serving predictions and anomaly alerts
- Live web dashboard

## Setup

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Windows
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## Configuration
Edit `.env` with your values:

| Variable | Description | Default |
|---|---|---|
| `MTA_API_KEY` | MTA API key from api.mta.info | required |
| `MTA_FEEDS` | Comma-separated feed paths | `nyct/gtfs-ace` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `nyc_transit` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `postgres` |
| `INGEST_INTERVAL_SECONDS` | Scheduler interval in seconds | `3600` |

## Running the Pipeline
```bash
# Run once manually
python3 -m src.ingest

# Run on hourly schedule
python3.11 -m src.ingest
```

## Running Tests
```bash
python3.11 -m pytest test_parser.py -v
```

## Database Setup
Run the SQL schema before first use:
```bash
psql -U postgres -d nyc_transit -f sql/01_create_tables.sql
```