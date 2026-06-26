"""build_record が分析dictを列スキーマ通りに整形するか検証する。"""
from datetime import datetime

from config import SHEET_COLUMNS
from sheets_store import build_record


def _analysis():
    return {
        "summary": "[テスト] コードを書いている",
        "category": "開発",
        "confidence": 85,
        "visual_observations": {
            "primary_screen": "コードエディタ",
            "visible_output": "コード",
            "focus_risk": "特になし",
            "non_productive_signal": "特になし",
        },
        "sensitive_regions": [],
    }


def test_record_has_all_columns():
    rec = build_record(datetime(2026, 6, 26, 13, 0), _analysis(), screenshot_path="s.jpg")
    for col in SHEET_COLUMNS:
        assert col in rec


def test_record_values_mapped():
    rec = build_record(datetime(2026, 6, 26, 13, 0), _analysis(), screenshot_path="s.jpg")
    assert rec["category"] == "開発"
    assert rec["confidence"] == 85
    assert rec["primary_screen"] == "コードエディタ"
    assert rec["screenshot_path"] == "s.jpg"
    assert rec["app_breakdown"] == "{}"


def test_missing_fields_default_safely():
    rec = build_record(datetime(2026, 6, 26, 13, 0), {})
    assert rec["confidence"] == 0
    assert rec["summary"] == ""
    assert rec["screenshot_path"] == ""
