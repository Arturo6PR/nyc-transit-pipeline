"""TransitPulse command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from transitpulse import __version__
from transitpulse.errors import TransitPulseError
from transitpulse.pipeline import ingest_feed, summarize
from transitpulse.render import render

EXIT_SUCCESS = 0
EXIT_OPERATIONAL_FAILURE = 2
EXIT_DUPLICATE = 10


def _output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="report format (default: text)",
    )
    parser.add_argument("--output", type=Path, help="write the report to this file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transitpulse",
        description="Replay GTFS-Realtime feeds into a local analytical store.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="ingest a .pb, .pb64, or HTTP(S) feed")
    ingest.add_argument("input", help="local feed path or HTTP(S) URL")
    ingest.add_argument(
        "--database",
        type=Path,
        default=Path("transitpulse.duckdb"),
        help="DuckDB path (default: transitpulse.duckdb)",
    )
    ingest.add_argument("--source", help="stable source label used for idempotency")
    ingest.add_argument("--timeout", type=float, default=20, help="URL timeout in seconds")
    _output_options(ingest)

    summary = commands.add_parser("summary", help="summarize the local analytical store")
    summary.add_argument(
        "--database",
        type=Path,
        default=Path("transitpulse.duckdb"),
        help="DuckDB path (default: transitpulse.duckdb)",
    )
    _output_options(summary)
    return parser


def _emit(content: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(content)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(content)


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "ingest":
            report = ingest_feed(
                args.input,
                database=args.database,
                source_label=args.source,
                timeout=args.timeout,
            )
            exit_code = EXIT_DUPLICATE if report["status"] == "DUPLICATE" else EXIT_SUCCESS
        else:
            report = summarize(args.database)
            exit_code = EXIT_SUCCESS
        _emit(render(report, args.output_format), args.output)
        return exit_code
    except (TransitPulseError, OSError, ValueError) as exc:
        print(f"transitpulse: error: {exc}", file=sys.stderr)
        return EXIT_OPERATIONAL_FAILURE


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
