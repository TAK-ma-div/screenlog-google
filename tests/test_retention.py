"""retention.cleanup_old_screenshots を検証する。"""
from datetime import datetime, timedelta

from retention import cleanup_old_screenshots

NOW = datetime(2026, 6, 26, 12, 0)


def _make_day(base, name: str):
    d = base / name
    d.mkdir(parents=True)
    (d / "0900_00.jpg").write_bytes(b"x")
    return d


def test_removes_old_keeps_recent(tmp_path):
    old = _make_day(tmp_path, (NOW - timedelta(days=20)).strftime("%Y%m%d"))
    recent = _make_day(tmp_path, (NOW - timedelta(days=2)).strftime("%Y%m%d"))

    removed = cleanup_old_screenshots(tmp_path, retention_days=14, now=NOW)

    assert removed == 1
    assert not old.exists()
    assert recent.exists()


def test_disabled_when_zero(tmp_path):
    _make_day(tmp_path, (NOW - timedelta(days=100)).strftime("%Y%m%d"))
    assert cleanup_old_screenshots(tmp_path, retention_days=0, now=NOW) == 0


def test_ignores_non_date_dirs(tmp_path):
    other = tmp_path / "notadate"
    other.mkdir()
    (other / "f.txt").write_bytes(b"x")
    removed = cleanup_old_screenshots(tmp_path, retention_days=1, now=NOW)
    assert removed == 0
    assert other.exists()


def test_missing_base_returns_zero(tmp_path):
    assert cleanup_old_screenshots(tmp_path / "nope", retention_days=14, now=NOW) == 0
