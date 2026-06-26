"""アプリ別使用時間の集計（report_reader）とwizard連携を検証する。"""
import json
from datetime import datetime, timedelta

from report_reader import aggregate_app_breakdown

NOW = datetime(2026, 6, 27, 12, 0, 0)


def _row(dt, breakdown):
    return {"timestamp": dt.isoformat(), "app_breakdown": json.dumps(breakdown, ensure_ascii=False)}


def test_sums_across_rows_and_sorts():
    rows = [
        _row(NOW - timedelta(hours=1), {"Code": 10, "Chrome": 5}),
        _row(NOW - timedelta(hours=2), {"Code": 6, "Slack": 4}),
    ]
    r = aggregate_app_breakdown(rows, NOW, days=7)
    names = [a["name"] for a in r["apps"]]
    assert names[0] == "Code"  # 16分で最多
    by = {a["name"]: a["minutes"] for a in r["apps"]}
    assert by["Code"] == 16.0
    assert by["Chrome"] == 5.0
    assert r["total_minutes"] == 25.0


def test_percent_computed():
    rows = [_row(NOW, {"A": 75, "B": 25})]
    r = aggregate_app_breakdown(rows, NOW, days=7)
    by = {a["name"]: a["percent"] for a in r["apps"]}
    assert by["A"] == 75.0 and by["B"] == 25.0


def test_excludes_old_rows():
    rows = [
        _row(NOW - timedelta(days=10), {"Old": 100}),
        _row(NOW - timedelta(days=1), {"New": 5}),
    ]
    r = aggregate_app_breakdown(rows, NOW, days=7)
    names = [a["name"] for a in r["apps"]]
    assert names == ["New"]


def test_handles_empty_and_bad_json():
    rows = [
        _row(NOW, {}),
        {"timestamp": NOW.isoformat(), "app_breakdown": "not json"},
        {"timestamp": NOW.isoformat(), "app_breakdown": ""},
        {"timestamp": NOW.isoformat()},  # 列なし
    ]
    r = aggregate_app_breakdown(rows, NOW, days=7)
    assert r["apps"] == []
    assert r["total_minutes"] == 0


def test_no_rows():
    r = aggregate_app_breakdown([], NOW, days=7)
    assert r == {"period_days": 7, "total_minutes": 0, "apps": []}


def test_wizard_get_app_breakdown_shape():
    import wizard

    r = wizard.get_app_breakdown()
    assert "apps" in r and "period_days" in r and "tracker_enabled" in r
    assert isinstance(r["apps"], list)
