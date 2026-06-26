"""Gemini出力からのJSON抽出 _parse_json を検証する。"""
import pytest

from analyzer import _parse_json


def test_plain_json():
    assert _parse_json('{"a": 1}') == {"a": 1}


def test_fenced_json():
    text = "```json\n{\"summary\": \"x\", \"confidence\": 80}\n```"
    assert _parse_json(text) == {"summary": "x", "confidence": 80}


def test_prefixed_json():
    text = '✦ 以下が結果です:\n{"category": "開発"}\n以上です。'
    assert _parse_json(text) == {"category": "開発"}


def test_invalid_raises():
    with pytest.raises(Exception):
        _parse_json("これはJSONではありません")
