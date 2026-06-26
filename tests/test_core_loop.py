"""コアループ run_cycle の配線を検証する（ダミー画像 + スタブ + Geminiモック）。"""
import analyzer
import main
import sheets_store
from stubs import StubSheetsService


def _fake_analysis(*args, **kwargs):
    return {
        "summary": "[テスト] ダミー画面を分析",
        "category": "開発",
        "confidence": 90,
        "visual_observations": {
            "primary_screen": "コードエディタ",
            "visible_output": "コード",
            "focus_risk": "特になし",
            "non_productive_signal": "特になし",
        },
        "sensitive_regions": [],
    }


def test_run_cycle_appends_one_row(monkeypatch):
    stub = StubSheetsService()
    monkeypatch.setattr(analyzer, "analyze_screenshot", _fake_analysis)
    monkeypatch.setattr(sheets_store, "get_sheets_service", lambda: stub)

    ok = main.run_cycle()

    assert ok is True
    assert len(stub.appended_rows) == 1
    assert stub.appended_rows[0][2] == "開発"


def test_run_cycle_low_confidence_sends_gmail(monkeypatch):
    stub_sheets = StubSheetsService()
    sent = []

    def low_conf(*a, **k):
        d = _fake_analysis()
        d["confidence"] = 10
        return d

    monkeypatch.setattr(analyzer, "analyze_screenshot", low_conf)
    monkeypatch.setattr(sheets_store, "get_sheets_service", lambda: stub_sheets)

    import gmail_notifier

    monkeypatch.setattr(
        gmail_notifier, "send_notification", lambda subject, body: sent.append(subject)
    )

    ok = main.run_cycle()

    assert ok is True
    assert len(sent) == 1, "低確信度で通知が送られていない"
