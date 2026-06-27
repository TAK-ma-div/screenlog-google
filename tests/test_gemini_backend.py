"""Gemini バックエンド選択（AI Studio / Vertex AI）を検証する。"""
import pytest

import analyzer
import config


def test_vertex_requires_project(monkeypatch):
    """vertex 指定でプロジェクト未設定なら明確なエラー（genai import 前に弾く）。"""
    monkeypatch.setattr(config, "USE_VERTEX", True)
    monkeypatch.setattr(config, "GOOGLE_CLOUD_PROJECT", "")
    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT"):
        analyzer._make_client()


def test_aistudio_uses_api_key(monkeypatch):
    genai = pytest.importorskip("google.genai")
    captured = {}

    class FakeClient:
        def __init__(self, **kw):
            captured.update(kw)

    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setattr(config, "USE_VERTEX", False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    analyzer._make_client()
    assert captured == {"api_key": "test-key"}


def test_vertex_uses_project_and_location(monkeypatch):
    genai = pytest.importorskip("google.genai")
    captured = {}

    class FakeClient:
        def __init__(self, **kw):
            captured.update(kw)

    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setattr(config, "USE_VERTEX", True)
    monkeypatch.setattr(config, "GOOGLE_CLOUD_PROJECT", "my-proj")
    monkeypatch.setattr(config, "GOOGLE_CLOUD_LOCATION", "us-central1")
    analyzer._make_client()
    assert captured == {"vertexai": True, "project": "my-proj", "location": "us-central1"}


def test_backend_defaults_to_aistudio():
    # 既定では Vertex を使わない（後方互換）
    assert config.GEMINI_BACKEND == "aistudio"
    assert config.USE_VERTEX is False
