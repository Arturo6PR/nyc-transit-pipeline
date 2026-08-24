from __future__ import annotations

import json
from pathlib import Path

import pytest

from transitpulse.cli import (
    EXIT_DUPLICATE,
    EXIT_OPERATIONAL_FAILURE,
    EXIT_SUCCESS,
    run,
)


def test_ingest_text_to_stdout(
    feed_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run(["ingest", str(feed_file), "--database", str(tmp_path / "data.duckdb")])

    captured = capsys.readouterr()
    assert code == EXIT_SUCCESS
    assert "Status: INGESTED" in captured.out
    assert captured.err == ""


def test_duplicate_has_distinct_exit_code(
    feed_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / "data.duckdb"
    assert run(["ingest", str(feed_file), "--database", str(database)]) == EXIT_SUCCESS
    capsys.readouterr()

    code = run(["ingest", str(feed_file), "--database", str(database), "--format", "json"])

    captured = capsys.readouterr()
    assert code == EXIT_DUPLICATE
    assert json.loads(captured.out)["status"] == "DUPLICATE"
    assert captured.err == ""


def test_output_file_keeps_stdout_empty(
    feed_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "reports with spaces" / "ingestion.json"

    code = run(
        [
            "ingest",
            str(feed_file),
            "--database",
            str(tmp_path / "data.duckdb"),
            "--format",
            "json",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert code == EXIT_SUCCESS
    assert captured.out == ""
    assert captured.err == ""
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "INGESTED"
    assert b"\r\n" not in output.read_bytes()


def test_missing_file_is_operational_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run(
        [
            "ingest",
            str(tmp_path / "missing.pb"),
            "--database",
            str(tmp_path / "data.duckdb"),
        ]
    )

    captured = capsys.readouterr()
    assert code == EXIT_OPERATIONAL_FAILURE
    assert captured.out == ""
    assert captured.err.startswith("transitpulse: error:")


def test_malformed_feed_is_operational_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    malformed = tmp_path / "malformed.pb"
    malformed.write_bytes(b"not-a-feed")

    code = run(["ingest", str(malformed), "--database", str(tmp_path / "data.duckdb")])

    captured = capsys.readouterr()
    assert code == EXIT_OPERATIONAL_FAILURE
    assert captured.out == ""
    assert "valid GTFS-Realtime" in captured.err


def test_summary_json_is_parseable(
    feed_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / "data.duckdb"
    assert run(["ingest", str(feed_file), "--database", str(database)]) == EXIT_SUCCESS
    capsys.readouterr()

    code = run(["summary", "--database", str(database), "--format", "json"])

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert code == EXIT_SUCCESS
    assert report["operation"] == "summary"
    assert report["counts"]["trip_stop_events"] == 3
    assert captured.err == ""


def test_first_ingestion_json_is_byte_identical_across_databases(
    feed_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    outputs: list[str] = []
    for name in ("one.duckdb", "two.duckdb"):
        code = run(
            [
                "ingest",
                str(feed_file),
                "--database",
                str(tmp_path / name),
                "--source",
                "mta-test",
                "--format",
                "json",
            ]
        )
        assert code == EXIT_SUCCESS
        outputs.append(capsys.readouterr().out)

    assert outputs[0].encode() == outputs[1].encode()


def test_invalid_format_is_cli_usage_failure(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run(["summary", "--format", "yaml"])

    assert exc_info.value.code == EXIT_OPERATIONAL_FAILURE
    assert capsys.readouterr().err.startswith("usage:")
