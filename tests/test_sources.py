from __future__ import annotations

from pathlib import Path

import pytest

from transitpulse.errors import InputLoadError
from transitpulse.sources import load_payload


def test_loads_raw_and_base64_files(
    feed_file: Path, base64_feed_file: Path, feed_bytes: bytes
) -> None:
    raw = load_payload(str(feed_file))
    encoded = load_payload(str(base64_feed_file))

    assert raw.data == encoded.data == feed_bytes
    assert raw.source_label == "feed sample.pb"
    assert encoded.source_label == "feed sample.pb64"


def test_explicit_source_label_wins(feed_file: Path) -> None:
    assert load_payload(str(feed_file), source_label="mta-ace").source_label == "mta-ace"


def test_empty_source_label_is_rejected(feed_file: Path) -> None:
    with pytest.raises(InputLoadError, match="must not be empty"):
        load_payload(str(feed_file), source_label="  ")


def test_missing_file_is_an_input_error(tmp_path: Path) -> None:
    with pytest.raises(InputLoadError, match="could not read feed file"):
        load_payload(str(tmp_path / "missing.pb"))


def test_invalid_base64_is_an_input_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.pb64"
    path.write_text("***", encoding="utf-8")

    with pytest.raises(InputLoadError, match="invalid base64 fixture"):
        load_payload(str(path))


def test_url_loading_removes_query_from_default_label(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"feed"

    def fake_urlopen(request: object, timeout: float) -> Response:
        assert timeout == 5
        assert request.full_url.endswith("?token=secret")  # type: ignore[attr-defined]
        return Response()

    monkeypatch.setattr("transitpulse.sources.urlopen", fake_urlopen)
    loaded = load_payload("https://feeds.example.test/a.pb?token=secret", timeout=5)

    assert loaded.data == b"feed"
    assert loaded.source_label == "https://feeds.example.test/a.pb"


def test_nonpositive_timeout_is_rejected(feed_file: Path) -> None:
    with pytest.raises(InputLoadError, match="greater than zero"):
        load_payload(str(feed_file), timeout=0)
