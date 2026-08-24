from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from transitpulse.pipeline import ingest_feed, summarize


def test_emitted_reports_match_versioned_json_schema(feed_file: Path, tmp_path: Path) -> None:
    schema_path = Path(__file__).parents[1] / "docs" / "report-schema-v1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    database = tmp_path / "reports.duckdb"

    ingestion = ingest_feed(str(feed_file), database=database, source_label="mta-test")
    summary = summarize(database)

    validator.validate(ingestion)
    validator.validate(summary)
