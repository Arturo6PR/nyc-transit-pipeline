# TransitPulse

[![CI](https://github.com/Arturo6PR/nyc-transit-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Arturo6PR/nyc-transit-pipeline/actions/workflows/ci.yml)

TransitPulse is a local-first data pipeline for replaying GTFS-Realtime transit feeds into an
embedded analytical store. It turns opaque protobuf messages into deterministic trip-stop and
service-alert records, prevents duplicate ingestion, and produces machine-readable operational
reports.

The project answers a practical data-platform question:

> Can a recorded or live transit feed be ingested repeatedly, audited, and summarized without
> creating inconsistent downstream data?

## Phase 1 capabilities

- Reads raw GTFS-Realtime protobuf files, checked-in `.pb64` fixtures, or HTTP(S) feed URLs.
- Normalizes trip updates and service alerts behind a parser boundary.
- Stores raw payloads and normalized records atomically in DuckDB.
- Uses content-derived ingestion and event identifiers instead of random IDs.
- Treats replaying the same source and payload as an explicit, non-mutating duplicate.
- Produces deterministic text or report-schema `1.0` JSON.
- Summarizes event counts, alerts, average route delay, and events delayed at least five minutes.
- Runs entirely offline with the included realistic fixture.

## Pipeline

```text
GTFS-Realtime .pb / .pb64 / URL
                 |
                 v
        input adapter + checksum
                 |
                 v
         protobuf normalization
                 |
                 v
        deterministic identities
                 |
                 v
       atomic, idempotent DuckDB write
                 |
                 +----------> raw payload archive
                 |
                 +----------> trip-stop events
                 |
                 +----------> service alerts
                 |
                 v
       text / versioned JSON report
```

The boundaries are intentionally explicit:

```text
sources -> parser -> domain models -> pipeline -> storage -> renderer / CLI
```

Input code does not write to the database, parsing code does not fetch from the network, and the
CLI does not contain transformation rules.

## Quick start

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

Replay the included feed and inspect the local store:

```powershell
transitpulse ingest examples/mta_sample.pb64 --database demo.duckdb
transitpulse summary --database demo.duckdb
```

Request structured output:

```powershell
transitpulse ingest examples/mta_sample.pb64 --database demo.duckdb --format json
transitpulse summary --database demo.duckdb --format json --output reports/summary.json
```

The second replay is detected without adding rows:

```text
TransitPulse ingestion
Status: DUPLICATE
...
```

## Live feeds

An HTTP(S) URL can be supplied explicitly:

```powershell
transitpulse ingest "https://example.net/vehicle-feed.pb" `
  --source mta-ace `
  --database transitpulse.duckdb
```

`--source` is recommended for live feeds because it provides a stable identity when URL query
parameters change. TransitPulse does not run a background scheduler in Phase 1; an operator or
external scheduler invokes each ingestion.

## CLI contract

```text
transitpulse ingest INPUT [--database PATH] [--source LABEL]
                          [--timeout SECONDS] [--format text|json] [--output PATH]

transitpulse summary [--database PATH] [--format text|json] [--output PATH]
```

Reports go to stdout by default. With `--output`, stdout remains empty and the report is written
using UTF-8 and platform-independent `LF` line endings. Expected operational errors go to stderr.

| Exit code | Meaning |
|---:|---|
| `0` | Feed ingested or summary generated |
| `2` | Invalid input, malformed feed, storage failure, or CLI usage error |
| `10` | The same source and payload were already ingested; no rows changed |

## Determinism and idempotency

The payload SHA-256 and source label generate the ingestion ID. Normalized event identifiers are
derived from the ingestion and stable GTFS fields. Replaying identical bytes from the same source
therefore reaches the same identity and returns `DUPLICATE`.

JSON uses sorted keys and stable record ordering. Reports exclude wall-clock ingestion time, local
absolute paths, random UUIDs, and database-generated sequence values. The same feed and source
produce byte-identical first-ingestion JSON even when stored in different databases.

## Analytical model

DuckDB contains four Phase 1 tables:

| Table | Purpose |
|---|---|
| `ingestion_runs` | One auditable record per unique source/payload pair |
| `raw_payloads` | Original protobuf bytes for replay and debugging |
| `trip_stop_events` | Normalized arrival and departure predictions/delays |
| `alerts` | Normalized service alerts and affected routes |

The database schema version is `1`. The external JSON report schema is independently versioned as
`1.0` and documented in [`docs/report-schema-v1.json`](docs/report-schema-v1.json).

## Development

```powershell
ruff check .
ruff format --check .
pytest
```

Tests generate protobuf feeds in memory and cover parsing, translation fallback, ordering,
malformed input, local and base64 sources, URL behavior without network access, storage
transactions, idempotency, analytical summaries, deterministic JSON, output files,
stdout/stderr separation, paths containing spaces, and exit codes.

## Current scope

TransitPulse Phase 1 is a deterministic ingestion and local analytics foundation. It does **not**
currently claim:

- a continuously running production ingestion service;
- Kafka or another streaming broker;
- dbt transformations or an orchestration platform;
- a REST API, dashboard, prediction model, or anomaly detector;
- Docker, Kubernetes, Terraform, AWS, or another cloud deployment;
- live-service reliability guarantees for any external transit provider.

Those are future phases only after the replayable data contract is stable.

## License

[MIT](LICENSE)
