"""週次レポートのテキスト組立とDocs書き出し（スタブ）を検証する。"""
from datetime import datetime

import docs_writer
import report_reader
import weekly_report
from stubs import StubDocsService, StubSheetsService

NOW = datetime(2026, 6, 26, 12, 0)


def _agg():
    return {
        "period_days": 7,
        "record_count": 3,
        "total_minutes": 150,
        "by_category": [
            {"category": "開発", "minutes": 90, "count": 2, "percent": 60.0},
            {"category": "会議", "minutes": 60, "count": 1, "percent": 40.0},
        ],
        "recent_summaries": ["[A] コード", "[B] 設計"],
    }


def test_build_report_text_contains_sections():
    text = weekly_report.build_report_text(_agg(), "・傾向\n・改善案", NOW)
    assert "カテゴリ別内訳" in text
    assert "開発" in text and "60.0%" in text
    assert "AIによる要約・気づき" in text
    assert "改善案" in text


def test_build_insights_prompt_lists_categories():
    prompt = weekly_report.build_insights_prompt(_agg())
    assert "開発" in prompt and "会議" in prompt
    assert "改善提案" in prompt


def test_create_report_doc_writes_to_stub(monkeypatch):
    stub = StubDocsService()
    monkeypatch.setattr(docs_writer, "get_docs_service", lambda: stub)

    doc_id, url = docs_writer.create_report_doc("タイトル", "本文テキスト")

    assert doc_id == "stub-doc-id"
    assert "stub-doc-id" in url
    assert stub.inserted_text == ["本文テキスト"]
    assert stub.created[0]["title"] == "タイトル"


def test_generate_weekly_report_end_to_end(monkeypatch):
    # Sheets: ヘッダ + 1データ行 を返すスタブ
    sheets = StubSheetsService()
    from config import SHEET_COLUMNS

    header = SHEET_COLUMNS
    data = {
        "timestamp": NOW.isoformat(),
        "summary": "[X] 開発作業",
        "category": "開発",
        "confidence": "90",
        "duration_min": "30",
    }
    sheets.appended_rows.append(header)
    sheets.appended_rows.append([data.get(c, "") for c in SHEET_COLUMNS])

    docs = StubDocsService()
    sent = []

    monkeypatch.setattr(report_reader, "get_sheets_service", lambda: sheets)
    monkeypatch.setattr(docs_writer, "get_docs_service", lambda: docs)
    import analyzer

    monkeypatch.setattr(analyzer, "generate_text", lambda prompt: "・要約\n・改善案")
    import gmail_notifier

    monkeypatch.setattr(
        gmail_notifier, "send_notification", lambda subject, body: sent.append(subject)
    )

    url, text = weekly_report.generate_weekly_report(days=7, notify=True)

    assert "stub-doc-id" in url
    assert "開発" in text
    assert len(docs.inserted_text) == 1
    assert len(sent) == 1
