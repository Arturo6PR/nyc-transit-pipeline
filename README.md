# TransitPulse

[![CI](https://github.com/Arturo6PR/nyc-transit-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Arturo6PR/nyc-transit-pipeline/actions/workflows/ci.yml)

TransitPulse is a local-first transit data platform for replaying GTFS-Realtime feeds, loading the
matching static GTFS Schedule, and building tested reliability marts in DuckDB. It turns opaque
protobuf messages and schedule CSV files into auditable, idempotent data products without requiring
a database server, transit credentials, or cloud resources.

The project answers a practical data-platform question:

> Can scheduled and real-time transit data be replayed, joined, tested, and analyzed repeatedly
> without creating inconsistent downstream data?

## Current capabilities — v0.2.0

- Reads GTFS-Realtime protobuf files, portable `.pb64` fixtures, or explicit HTTP(S) URLs.
- Strictly validates the analytical subset of GTFS Schedule from a directory or ZIP.
- Normalizes trip updates, service alerts, routes, trips, stops, and stop times.
- Stores original inputs and normalized records atomically in DuckDB.
- Uses canonical content-derived identifiers instead of random IDs.
- Detects repeated real-time feeds and semantically identical schedules without adding rows.
- Tracks one active schedule per source while retaining previous schedule imports for audit.
- Builds an incremental stop-reliability fact and route, station, and feed-quality marts with dbt.
- Tests uniqueness, completeness, schedule-match coverage, and aggregate consistency.
- Produces deterministic text or report-schema `1.1` JSON with stable exit codes.
- Runs end to end offline with realistic synthetic NYC subway fixtures.

## Pipeline

```text
GTFS-Realtime .pb / .pb64 / URL       GTFS Schedule directory / ZIP
                  |                                  |
                  v                                  v
          validated adapters                 strict CSV parser
                  |                                  |
                  +---------------+------------------+
                                  |
                                  v
                    deterministic identities
                                  |
                                  v
                    atomic, idempotent DuckDB
                         |                 |
                         v                 v
                  raw audit layer    normalized source tables
                                           |
                                           v
                                    dbt staging models
                                           |
                                           v
                              incremental reliability fact
                                           |
                    +----------------------+--------------------+
                    v                      v                    v
             route reliability     station reliability     feed quality
```

Application boundaries remain explicit:

```text
input adapters -> parsers -> domain models -> pipelines -> storage -> renderer / CLI
                                                        |
                                                        v
                                               dbt transformations/tests
```

Input adapters do not write to the database, parsing code does not fetch from the network, dbt
does not own ingestion, and the CLI does not contain transformation SQL.

## Five-minute offline demonstration

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,analytics]"
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

Load matching real-time and schedule fixtures under one stable source label:

```powershell
transitpulse ingest examples/mta_sample.pb64 `
  --database demo.duckdb `
  --source mta-sample

transitpulse schedule ingest examples/gtfs_schedule `
  --database demo.duckdb `
  --source mta-sample
```

Build and test the analytical models:

```powershell
$env:TRANSITPULSE_DATABASE = (Resolve-Path demo.duckdb).Path
dbt build --project-dir analytics --profiles-dir analytics
```

On macOS or Linux:

```bash
export TRANSITPULSE_DATABASE="$(pwd)/demo.duckdb"
dbt build --project-dir analytics --profiles-dir analytics
```

Inspect the operational summary:

```powershell
transitpulse summary --database demo.duckdb --format json
```

The demonstration is offline. The checked-in schedule and real-time records are synthetic,
deterministic, and shaped like NYC subway data; they are not presented as a live MTA recording.

## Idempotent replay

Replaying the same source and real-time payload returns `DUPLICATE`. A schedule is identified from
its normalized semantic content, so repackaging identical files into a different ZIP also reaches
the same identity.

```text
TransitPulse schedule ingestion
Status: DUPLICATE
...
```

When a genuinely changed schedule is imported under the same source label, TransitPulse retains
both imports and atomically points that source at the new active schedule.

## CLI contract

```text
transitpulse ingest INPUT [--database PATH] [--source LABEL]
                          [--timeout SECONDS] [--format text|json] [--output PATH]

transitpulse schedule ingest INPUT [--database PATH] [--source LABEL]
                                    [--format text|json] [--output PATH]

transitpulse summary [--database PATH] [--format text|json] [--output PATH]
```

Reports go to stdout by default. With `--output`, stdout remains empty and the report is written
using UTF-8 and platform-independent `LF` line endings. Expected operational errors go to stderr.

| Exit code | Meaning |
|---:|---|
| `0` | Feed or schedule ingested, or summary generated |
| `2` | Invalid input, malformed feed, storage failure, or CLI usage error |
| `10` | The same source and semantic input was already stored; no rows changed |

## Determinism and data contracts

The real-time payload SHA-256 and source label generate the ingestion ID. Schedule IDs use a
canonical representation of parsed GTFS records, not ZIP metadata or file order. Normalized event
identifiers are derived from stable GTFS fields.

JSON uses sorted keys and stable record ordering. Reports exclude wall-clock ingestion time, local
absolute paths, random UUIDs, and database-generated sequence values. First-ingestion reports from
identical inputs are byte-identical across databases and operating systems.

The database schema version is `2`. The external JSON report schema is independently versioned as
`1.1` and documented in [`docs/report-schema-v1.1.json`](docs/report-schema-v1.1.json).

## Source and analytical models

The source layer includes:

| Table | Purpose |
|---|---|
| `ingestion_runs` | One record per unique real-time source/payload pair |
| `raw_payloads` | Original protobuf bytes for replay and debugging |
| `trip_stop_events` | Normalized arrival and departure predictions/delays |
| `alerts` | Normalized service alerts and affected routes |
| `schedule_imports` | Auditable static-schedule versions and record counts |
| `schedule_sources` | Active schedule pointer for each stable source label |
| `schedule_raw_archives` | Original ZIP or deterministic directory archive |
| `schedule_routes`, `schedule_trips` | Static route and trip entities |
| `schedule_stops`, `schedule_stop_times` | Static stop entities and scheduled times |

dbt produces:

| Model | Grain and purpose |
|---|---|
| `fct_stop_reliability` | One real-time stop event enriched with its schedule match |
| `route_reliability_hourly` | Hourly route delay distribution and delayed-event rate |
| `station_reliability` | Stop-level event counts and delay distribution |
| `feed_quality` | Schedule-match coverage and missing-delay indicators by source |
| `dim_routes`, `dim_stops` | Active schedule dimensions |

The fact model is incremental and keyed by deterministic `event_id`; repeated builds do not create
duplicate facts.

## Data-quality gates

`dbt build` fails when:

- fact identifiers are duplicated or required keys are null;
- route or stop dimension keys repeat within a source;
- aggregate counts or rates are internally inconsistent; or
- fewer than 95% of real-time events match the active static schedule.

The Python loader fails earlier for missing files/columns, duplicate identifiers, broken
route/trip/stop references, invalid coordinates, invalid direction IDs, duplicate stop sequences,
and malformed GTFS times—including while supporting service times after midnight such as
`25:05:00`.

## Development

```powershell
ruff check .
ruff format --check .
pytest
```

Tests generate protobuf feeds in memory and exercise directory and ZIP schedules, malformed input,
cross-file relationships, after-midnight time parsing, schema migration, atomic persistence,
active-schedule replacement, idempotency, dbt builds and tests, deterministic JSON, output files,
paths containing spaces, stdout/stderr separation, and process exit codes.

## Current scope

TransitPulse v0.2.0 is a deterministic ingestion, transformation, and local analytics platform. It
does **not** currently claim:

- a continuously running production ingestion service;
- Kafka or another streaming broker;
- Dagster, Prefect, or another production orchestrator;
- a REST API, dashboard, prediction model, or anomaly detector;
- Docker, Kubernetes, Terraform, AWS, or another cloud deployment;
- live-service reliability guarantees for any external transit provider.

Those remain possible later phases. The current portfolio demonstration requires no cloud account,
credentials, external AI service, or paid resource.

## License

[MIT](LICENSE)
