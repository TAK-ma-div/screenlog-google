"""report_reader.aggregate_rows のカテゴリ集計を検証する。"""
from datetime import datetime, timedelta

from report_reader import aggregate_rows

NOW = datetime(2026, 6, 26, 12, 0)


def _row(ts: datetime, category: str, minutes: int, summary: str = "作業"):
    return {
        "timestamp": ts.isoformat(),
        "category": category,
        "duration_min": str(minutes),
        "summary": summary,
    }


def test_aggregate_by_category_sorted():
    rows = [
        _row(NOW - timedelta(days=1), "開発", 30),
        _row(NOW - timedelta(days=2), "開発", 30),
        _row(NOW - timedelta(days=1), "会議", 60),
    ]
    agg = aggregate_rows(rows, now=NOW, days=7)

    assert agg["record_count"] == 3
    assert agg["total_minutes"] == 120
    # 時間降順: 会議(60) → 開発(60)... 同点なので両方60。先頭は60分のいずれか
    cats = {c["category"]: c for c in agg["by_category"]}
    assert cats["開発"]["minutes"] == 60
    assert cats["開発"]["count"] == 2
    assert cats["会議"]["minutes"] == 60
    assert cats["会議"]["percent"] == 50.0


def test_aggregate_excludes_old_rows():
    rows = [
        _row(NOW - timedelta(days=1), "開発", 30),
        _row(NOW - timedelta(days=10), "開発", 999),  # 期間外
    ]
    agg = aggregate_rows(rows, now=NOW, days=7)
    assert agg["record_count"] == 1
    assert agg["total_minutes"] == 30


def test_aggregate_handles_bad_rows():
    rows = [
        {"timestamp": "", "category": "開発", "duration_min": "5"},  # 日時不正→除外
        {"timestamp": NOW.isoformat(), "category": "", "duration_min": "x"},  # 数値不正→0分
    ]
    agg = aggregate_rows(rows, now=NOW, days=7)
    assert agg["record_count"] == 1
    assert agg["by_category"][0]["category"] == "その他"
    assert agg["total_minutes"] == 0


def test_aggregate_empty():
    agg = aggregate_rows([], now=NOW, days=7)
    assert agg["record_count"] == 0
    assert agg["by_category"] == []
