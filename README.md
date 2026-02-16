# NYC Transit Delay Prediction Project

## Overview
This project builds a data pipeline around MTA GTFS-Realtime feeds.
Week 1–2 focuses on setup, API access, and database connectivity.

## What exists so far
- Config loader (`config.py`)
- MTA GTFS-RT fetch client (`mta_client.py`)
- Database connectivity helpers (`db.py`)
- API + DB test scripts

## What will be added next
- GTFS-Realtime protobuf parsing
- Database insertion logic
- End-to-end ingestion pipeline

## Setup
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
