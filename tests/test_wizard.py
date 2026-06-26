"""ウィザードのロジックをスタブモードで検証する。"""
import os

import pytest

import wizard
from env_file import read_env, update_env

_KEYS = ("GEMINI_API_KEY", "GEMINI_MODEL", "GMAIL_TO", "SHEET_ID", "SHEET_TAB")


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path, monkeypatch):
    """各テストで .env をtmpに、os.environの該当キーを退避/復元する。"""
    monkeypatch.setattr(wizard, "ENV_PATH", tmp_path / ".env")
    saved = {k: os.environ.get(k) for k in _KEYS}
    for k in _KEYS:
        os.environ.pop(k, None)
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_save_config_writes_and_skips_empty():
    result = wizard.save_config({"GEMINI_API_KEY": "key123", "GMAIL_TO": "", "GEMINI_MODEL": "m"})
    assert set(result["saved"]) == {"GEMINI_API_KEY", "GEMINI_MODEL"}  # 空のGMAIL_TOは除外
    env = read_env(wizard.ENV_PATH)
    assert env["GEMINI_API_KEY"] == "key123"
    assert "GMAIL_TO" not in env


def test_create_sheet_stub_writes_sheet_id():
    result = wizard.create_sheet("ScreenLog")
    assert result["sheet_id"] == "stub-sheet-id"
    assert "stub-sheet-id" in result["sheet_url"]
    assert read_env(wizard.ENV_PATH)["SHEET_ID"] == "stub-sheet-id"


def test_get_status_reflects_env():
    update_env(wizard.ENV_PATH, {"GEMINI_API_KEY": "k", "SHEET_ID": "sid"})
    status = wizard.get_status()
    assert status["has_gemini_key"] is True
    assert status["has_sheet"] is True
    assert "sid" in status["sheet_url"]


def test_get_status_empty_env():
    status = wizard.get_status()
    assert status["has_gemini_key"] is False
    assert status["has_sheet"] is False
    assert status["sheet_url"] == ""


def test_run_oauth_stub_ok():
    # GOOGLE_STUB=true（conftest）なので実認証せず完了する
    result = wizard.run_oauth()
    assert "has_token" in result
