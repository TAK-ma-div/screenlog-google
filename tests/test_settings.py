"""カスタマイズ設定（カテゴリ・列・通知・フォルダ・日数）を検証する。"""
import os

import pytest

import analyzer
import config
import wizard
from env_file import read_env

_KEYS = list(wizard.SETTINGS_DEFAULTS.keys())


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path, monkeypatch):
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


# --- wizard settings round-trip ---
def test_get_settings_returns_defaults():
    s = wizard.get_settings()
    assert s["values"]["CAPTURE_INTERVAL_MINUTES"] == "5"
    assert s["values"]["NOTIFY_ENABLED"] == "true"
    assert "primary_screen" in s["available_optional_columns"]
    assert "開発" in s["default_categories"]


def test_save_settings_writes_env():
    result = wizard.save_settings(
        {
            "SCREENSHOT_DIR": "myshots",
            "WEEKLY_REPORT_DAYS": "30",
            "CATEGORIES": "開発,営業,制作",
            "RECORD_OPTIONAL_COLUMNS": "primary_screen,screenshot_path",
            "NOTIFY_ENABLED": "false",
        }
    )
    assert "SCREENSHOT_DIR" in result["saved"]
    env = read_env(wizard.ENV_PATH)
    assert env["SCREENSHOT_DIR"] == "myshots"
    assert env["WEEKLY_REPORT_DAYS"] == "30"
    assert env["CATEGORIES"] == "開発,営業,制作"
    assert env["NOTIFY_ENABLED"] == "false"


def test_save_settings_ignores_unknown_keys():
    result = wizard.save_settings({"EVIL_KEY": "x", "SCREENSHOT_DIR": "ok"})
    assert result["saved"] == ["SCREENSHOT_DIR"]
    assert "EVIL_KEY" not in read_env(wizard.ENV_PATH)


def test_get_settings_reflects_saved():
    wizard.save_settings({"CONFIDENCE_THRESHOLD": "55"})
    assert wizard.get_settings()["values"]["CONFIDENCE_THRESHOLD"] == "55"


# --- config: 列選択 ---
def test_sheet_columns_core_present():
    for c in config.CORE_COLUMNS:
        assert c in config.SHEET_COLUMNS
    # 既定では任意列も全て含む
    assert "app_breakdown" in config.SHEET_COLUMNS


# --- analyzer: プロンプトにカテゴリが反映される ---
def test_prompt_includes_configured_categories():
    prompt = analyzer._build_prompt(None, 5)
    assert config.CATEGORIES[0] in prompt
    # パイプ区切りで列挙される
    assert "|".join(config.CATEGORIES) in prompt
