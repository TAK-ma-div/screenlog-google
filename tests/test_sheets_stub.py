"""sheets_store.append_row がスタブSheetsへ正しく行を送るか検証する。"""
from datetime import datetime

import sheets_store
from sheets_store import append_row, build_record
from stubs import StubSheetsService


def test_append_row_writes_to_stub(monkeypatch):
    stub = StubSheetsService()
    monkeypatch.setattr(sheets_store, "get_sheets_service", lambda: stub)

    rec = build_record(
        datetime(2026, 6, 26, 13, 0),
        {"summary": "テスト", "category": "開発", "confidence": 90},
    )
    append_row(rec)

    assert len(stub.appended_rows) == 1
    row = stub.appended_rows[0]
    # timestamp が先頭、summary が2列目
    assert row[1] == "テスト"
    assert row[2] == "開発"
    assert row[3] == 90
