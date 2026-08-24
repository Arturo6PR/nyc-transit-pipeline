"""Local and HTTP GTFS-Realtime input adapters."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from transitpulse.errors import InputLoadError


@dataclass(frozen=True, slots=True)
class LoadedPayload:
    data: bytes
    source_label: str


def _validated_label(value: str) -> str:
    if not value.strip():
        raise InputLoadError("source label must not be empty")
    return value


def _is_url(value: str) -> bool:
    return urlsplit(value).scheme.lower() in {"http", "https"}


def _safe_url_label(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _decode_fixture(data: bytes, path: Path) -> bytes:
    try:
        return base64.b64decode(b"".join(data.split()), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InputLoadError(f"invalid base64 fixture: {path}") from exc


def load_payload(
    location: str, *, source_label: str | None = None, timeout: float = 20
) -> LoadedPayload:
    """Load raw protobuf bytes or a checked-in .pb64 fixture."""
    if timeout <= 0:
        raise InputLoadError("timeout must be greater than zero")

    if _is_url(location):
        request = Request(location, headers={"User-Agent": "TransitPulse/0.2"})
        try:
            with urlopen(request, timeout=timeout) as response:
                data = response.read()
        except HTTPError as exc:
            raise InputLoadError(f"HTTP {exc.code} while loading feed") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise InputLoadError(f"could not load feed URL: {exc}") from exc
        label = source_label if source_label is not None else _safe_url_label(location)
        return LoadedPayload(data=data, source_label=_validated_label(label))

    path = Path(location).expanduser()
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise InputLoadError(f"could not read feed file: {path}") from exc
    if path.suffix.lower() == ".pb64":
        data = _decode_fixture(data, path)
    label = source_label if source_label is not None else path.name
    return LoadedPayload(data=data, source_label=_validated_label(label))
