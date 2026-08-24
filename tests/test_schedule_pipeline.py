from __future__ import annotations

from pathlib import Path

from transitpulse.pipeline import summarize
from transitpulse.schedule_pipeline import ingest_schedule
from transitpulse.storage import TransitStore


def test_schedule_ingestion_is_idempotent(schedule_dir: Path, tmp_path: Path) -> None:
    database = tmp_path / "schedule.duckdb"

    first = ingest_schedule(str(schedule_dir), database=database, source_label="mta-sample")
    duplicate = ingest_schedule(str(schedule_dir), database=database, source_label="mta-sample")

    assert first["status"] == "IMPORTED"
    assert duplicate["status"] == "DUPLICATE"
    assert duplicate["schedule_id"] == first["schedule_id"]
    assert first["counts"] == {"routes": 2, "trips": 2, "stops": 4, "stop_times": 4}
    assert summarize(database)["counts"]["schedule_imports"] == 1  # type: ignore[index]


def test_directory_and_zip_have_the_same_semantic_identity(
    schedule_dir: Path, schedule_zip: Path, tmp_path: Path
) -> None:
    directory = ingest_schedule(
        str(schedule_dir), database=tmp_path / "one.duckdb", source_label="mta-sample"
    )
    archive = ingest_schedule(
        str(schedule_zip), database=tmp_path / "two.duckdb", source_label="mta-sample"
    )

    assert directory["schedule_id"] == archive["schedule_id"]
    assert directory["content_sha256"] == archive["content_sha256"]
    assert directory["input_format"] == "directory"
    assert archive["input_format"] == "zip"


def test_new_schedule_becomes_active_for_source(schedule_dir: Path, tmp_path: Path) -> None:
    database = tmp_path / "versions.duckdb"
    original = ingest_schedule(str(schedule_dir), database=database, source_label="mta-sample")
    routes = schedule_dir / "routes.txt"
    routes.write_text(
        routes.read_text(encoding="utf-8").replace("8 Avenue Express", "8 Avenue Updated"),
        encoding="utf-8",
        newline="\n",
    )

    updated = ingest_schedule(str(schedule_dir), database=database, source_label="mta-sample")

    assert updated["schedule_id"] != original["schedule_id"]
    with TransitStore(database) as store:
        row = store.connection.execute(
            "SELECT active_schedule_id FROM schedule_sources WHERE source = 'mta-sample'"
        ).fetchone()
    assert row == (updated["schedule_id"],)
    assert summarize(database)["counts"]["schedule_imports"] == 2  # type: ignore[index]
