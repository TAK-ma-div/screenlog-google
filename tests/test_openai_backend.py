"""OpenAI(GPT) バックエンドの選択・メッセージ組み立て・クライアント生成を検証する。"""
import base64

import pytest

import analyzer
import config


# --- 画像メッセージ組み立て（SDK不要・どこでも実行） ---
def test_build_messages_has_text_and_image():
    msgs = analyzer._build_openai_image_messages("PROMPT", b"\xff\xd8\xff jpeg bytes")
    assert msgs[0]["role"] == "user"
    parts = msgs[0]["content"]
    assert parts[0] == {"type": "text", "text": "PROMPT"}
    url = parts[1]["image_url"]["url"]
    assert url.startswith("data:image/jpeg;base64,")
    # base64 部分が元のバイト列に戻る
    decoded = base64.b64decode(url.split(",", 1)[1])
    assert decoded == b"\xff\xd8\xff jpeg bytes"


# --- APIキー未設定なら明確なエラー（SDK import 前に弾く） ---
def test_openai_requires_key(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        analyzer._make_openai_client()


# --- AI_PROVIDER=openai のとき OpenAI パスにルーティングされる ---
def test_analyze_routes_to_openai(monkeypatch):
    monkeypatch.setenv("GOOGLE_STUB", "false")  # スタブを切ってルーティングを通す
    monkeypatch.setattr(analyzer, "AI_PROVIDER", "openai")
    called = {}

    def fake(image_bytes, prompt):
        called["yes"] = (image_bytes, prompt)
        return {"summary": "x"}

    monkeypatch.setattr(analyzer, "_analyze_with_openai", fake)
    out = analyzer.analyze_screenshot(b"img", interval_min=5)
    assert out == {"summary": "x"}
    assert called["yes"][0] == b"img"


def test_generate_text_routes_to_openai(monkeypatch):
    monkeypatch.setenv("GOOGLE_STUB", "false")
    monkeypatch.setattr(analyzer, "AI_PROVIDER", "openai")
    monkeypatch.setattr(analyzer, "_generate_text_with_openai", lambda p: "TEXT:" + p)
    assert analyzer.generate_text("hello") == "TEXT:hello"


# --- クライアント生成（openai 導入時のみ。CIでは requirements-openai.txt で導入） ---
def test_make_openai_client_uses_key_and_base_url(monkeypatch):
    openai_mod = pytest.importorskip("openai")
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kw):
            captured.update(kw)

    monkeypatch.setattr(openai_mod, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(config, "OPENAI_BASE_URL", "https://example.test/v1")
    analyzer._make_openai_client()
    assert captured == {"api_key": "sk-test", "base_url": "https://example.test/v1"}


def test_make_openai_client_without_base_url(monkeypatch):
    openai_mod = pytest.importorskip("openai")
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kw):
            captured.update(kw)

    monkeypatch.setattr(openai_mod, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(config, "OPENAI_BASE_URL", "")
    analyzer._make_openai_client()
    assert captured == {"api_key": "sk-test"}
