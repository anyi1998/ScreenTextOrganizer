from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from app.services.scanner import scan_directory


def _make_test_images(directory: Path, count: int = 3) -> list[Path]:
    """Create small test images in the given directory."""
    paths = []
    for i in range(count):
        path = directory / f"test_{i}.png"
        img = Image.new("RGB", (100, 100), color=(i * 80, 50, 100))
        img.save(path)
        paths.append(path)
    return paths


def test_scan_inserts_images():
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_test_images(Path(tmpdir), 3)
        result = scan_directory(tmpdir, recursive=False)

    assert result["scanned"] == 3
    assert result["inserted"] == 3
    assert result["failed"] == 0
    assert result["errors"] == []


def test_scan_deduplicates():
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_test_images(Path(tmpdir), 2)
        scan_directory(tmpdir, recursive=False)
        result = scan_directory(tmpdir, recursive=False)

    assert result["inserted"] == 0
    assert result["updated"] == 2


def test_scan_nonexistent_directory_raises():
    import pytest

    with pytest.raises(ValueError, match="does not exist"):
        scan_directory("C:\\__nonexistent_dir_12345__", recursive=False)


def test_scan_records_errors():
    """If an image file is corrupted, scanner should record the error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bad = Path(tmpdir) / "bad.png"
        bad.write_bytes(b"not a real image")
        result = scan_directory(tmpdir, recursive=False)

    assert result["scanned"] == 1
    assert result["failed"] == 1
    assert len(result["errors"]) == 1
    assert "bad.png" in result["errors"][0]["file"]
