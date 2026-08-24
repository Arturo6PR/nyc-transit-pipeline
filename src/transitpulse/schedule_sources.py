"""Local GTFS Schedule directory and ZIP input adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from transitpulse.errors import InputLoadError

REQUIRED_SCHEDULE_FILES = ("routes.txt", "trips.txt", "stops.txt", "stop_times.txt")


@dataclass(frozen=True, slots=True)
class LoadedSchedule:
    files: dict[str, bytes]
    raw_payload: bytes
    input_format: str
    source_label: str


def _validated_label(value: str) -> str:
    if not value.strip():
        raise InputLoadError("source label must not be empty")
    return value


def _canonical_directory_payload(files: dict[str, bytes]) -> bytes:
    parts = [b"TRANSITPULSE-GTFS-DIRECTORY-V1\n"]
    for name in sorted(files):
        data = files[name]
        parts.extend((name.encode(), b"\n", str(len(data)).encode(), b"\n", data, b"\n"))
    return b"".join(parts)


def _load_directory(path: Path) -> tuple[dict[str, bytes], bytes]:
    files: dict[str, bytes] = {}
    for name in REQUIRED_SCHEDULE_FILES:
        file_path = path / name
        try:
            files[name] = file_path.read_bytes()
        except OSError as exc:
            raise InputLoadError(f"GTFS Schedule input is missing {name}: {path}") from exc
    return files, _canonical_directory_payload(files)


def _load_zip(path: Path) -> tuple[dict[str, bytes], bytes]:
    try:
        raw_payload = path.read_bytes()
        with ZipFile(path) as archive:
            by_basename: dict[str, str] = {}
            for member in archive.namelist():
                basename = PurePosixPath(member).name
                if basename in REQUIRED_SCHEDULE_FILES:
                    if basename in by_basename:
                        raise InputLoadError(f"GTFS Schedule ZIP contains duplicate {basename}")
                    by_basename[basename] = member
            missing = sorted(set(REQUIRED_SCHEDULE_FILES) - set(by_basename))
            if missing:
                raise InputLoadError(
                    "GTFS Schedule ZIP is missing required files: " + ", ".join(missing)
                )
            files = {name: archive.read(by_basename[name]) for name in REQUIRED_SCHEDULE_FILES}
    except BadZipFile as exc:
        raise InputLoadError(f"invalid GTFS Schedule ZIP: {path}") from exc
    except OSError as exc:
        raise InputLoadError(f"could not read GTFS Schedule input: {path}") from exc
    return files, raw_payload


def load_schedule(location: str, *, source_label: str | None = None) -> LoadedSchedule:
    path = Path(location).expanduser()
    if path.is_dir():
        files, raw_payload = _load_directory(path)
        input_format = "directory"
    elif path.suffix.lower() == ".zip":
        files, raw_payload = _load_zip(path)
        input_format = "zip"
    else:
        raise InputLoadError("GTFS Schedule input must be a directory or .zip file")

    label = source_label if source_label is not None else path.name
    return LoadedSchedule(
        files=files,
        raw_payload=raw_payload,
        input_format=input_format,
        source_label=_validated_label(label),
    )
