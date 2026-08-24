from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import duckdb

from transitpulse.pipeline import ingest_feed
from transitpulse.schedule_pipeline import ingest_schedule


def _dbt_build(
    database: Path, project: Path, output_root: Path
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["TRANSITPULSE_DATABASE"] = str(database)
    environment["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
    dbt_executable = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
    return subprocess.run(
        [
            str(dbt_executable),
            "build",
            "--project-dir",
            str(project),
            "--profiles-dir",
            str(project),
            "--target-path",
            str(output_root / "target"),
            "--log-path",
            str(output_root / "logs"),
            "--no-use-colors",
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
        timeout=60,
    )


def test_dbt_build_produces_tested_reliability_marts(
    feed_file: Path,
    schedule_dir: Path,
    tmp_path: Path,
) -> None:
    database = tmp_path / "analytics.duckdb"
    ingest_feed(str(feed_file), database=database, source_label="mta-sample")
    ingest_schedule(str(schedule_dir), database=database, source_label="mta-sample")
    project = Path(__file__).parents[1] / "analytics"
    result = _dbt_build(database, project, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    connection = duckdb.connect(str(database), read_only=True)
    try:
        fact_count = connection.execute(
            "SELECT COUNT(*) FROM analytics_marts.fct_stop_reliability"
        ).fetchone()
        quality = connection.execute(
            """
            SELECT event_count, schedule_matched_event_count, schedule_match_rate_pct
            FROM analytics_marts.feed_quality
            WHERE source = 'mta-sample'
            """
        ).fetchone()
        routes = connection.execute(
            """
            SELECT route_id, event_count, delayed_event_count
            FROM analytics_marts.route_reliability_hourly
            ORDER BY route_id
            """
        ).fetchall()
    finally:
        connection.close()

    assert fact_count == (3,)
    assert quality == (3, 3, 100.0)
    assert routes == [("A", 2, 1), ("B", 1, 0)]


def test_dbt_quality_gate_rejects_unmatched_realtime_events(
    feed_file: Path,
    schedule_dir: Path,
    tmp_path: Path,
) -> None:
    database = tmp_path / "unmatched.duckdb"
    ingest_feed(str(feed_file), database=database, source_label="realtime-only")
    ingest_schedule(str(schedule_dir), database=database, source_label="schedule-only")
    project = Path(__file__).parents[1] / "analytics"

    result = _dbt_build(database, project, tmp_path)

    assert result.returncode != 0
    assert "assert_schedule_match_rate" in result.stdout + result.stderr
