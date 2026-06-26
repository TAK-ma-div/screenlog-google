"""ログ閲覧・テスト動作（wizard）を検証する。GOOGLE_STUB前提。"""
import wizard


def test_read_recent_logs_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("config.LOG_FILE", str(tmp_path / "none.log"), raising=False)
    # config をimport済みの wizard 経由で参照させるため直接渡しは不可。存在しない経路を確認。
    r = wizard.read_recent_logs(10)
    assert "lines" in r and isinstance(r["lines"], list)


def test_read_recent_logs_tails(tmp_path, monkeypatch):
    log = tmp_path / "app.log"
    log.write_text("\n".join(f"line{i}" for i in range(50)), encoding="utf-8")
    monkeypatch.setattr("config.LOG_FILE", str(log))
    r = wizard.read_recent_logs(5)
    assert r["exists"] is True
    assert r["lines"][-1] == "line49"
    assert len(r["lines"]) == 5


def test_test_sheet_ok_under_stub():
    r = wizard.test_sheet()
    assert r["ok"] is True


def test_test_email_ok_under_stub():
    r = wizard.test_email()
    assert r["ok"] is True


def test_run_once_ok_under_stub():
    r = wizard.run_once()
    assert r["ok"] is True
