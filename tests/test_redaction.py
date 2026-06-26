"""機密マスク（OCR/正規表現検出 + 黒塗り）を検証する。"""
import io

from PIL import Image

import redaction
from redaction import (
    boxes_to_regions,
    is_sensitive_text,
    mask_regions,
    ocr_sensitive_regions,
    redact,
    _pad_and_clamp,
)


def _white(w=200, h=100) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (255, 255, 255)).save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def _pixel(jpeg: bytes, x: int, y: int):
    return Image.open(io.BytesIO(jpeg)).convert("RGB").getpixel((x, y))


# --- 正規表現検出 ---
def test_is_sensitive_text_positive():
    assert is_sensitive_text("AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMY01")
    assert is_sensitive_text("sk-ant-abcdefghij1234567890")
    assert is_sensitive_text("password = hunter2")
    assert is_sensitive_text("API_KEY: abcdefABCDEF12345")
    assert is_sensitive_text("-----BEGIN RSA PRIVATE KEY-----")
    assert is_sensitive_text("AKIAIOSFODNN7EXAMPLE")


def test_is_sensitive_text_negative():
    assert not is_sensitive_text("def main():")
    assert not is_sensitive_text("これは普通の業務メモです")
    assert not is_sensitive_text("password")  # ラベル単体（値なし）は対象外
    assert not is_sensitive_text("")


# --- OCRボックス→領域変換 ---
def test_boxes_to_regions_filters_sensitive():
    items = [
        {"text": "AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMY01", "box": [[10, 10], [110, 10], [110, 30], [10, 30]]},
        {"text": "ただのラベル", "box": [[0, 0], [50, 0], [50, 20], [0, 20]]},
    ]
    regions = boxes_to_regions(items, img_w=200, img_h=100)
    assert len(regions) == 1
    r = regions[0]
    assert round(r["x_pct"]) == 5  # 10/200
    assert round(r["w_pct"]) == 50  # 100/200


def test_boxes_to_regions_empty_image():
    assert boxes_to_regions([{"text": "sk-xxxxxxxxxxxxxxxx", "box": [[0, 0]]}], 0, 0) == []


# --- 黒塗りマスク ---
def test_mask_fill_blackens_region():
    region = {"x_pct": 25, "y_pct": 25, "w_pct": 50, "h_pct": 50}
    out = mask_regions(_white(), [region], pad_pct=0, style="fill")
    assert _pixel(out, 100, 50) == (0, 0, 0)  # 中心は黒
    assert _pixel(out, 2, 2) == (255, 255, 255)  # 角は白のまま


def test_mask_padding_clamps_within_bounds():
    # 端の領域 + 余白でもはみ出さずクランプされる
    x1, y1, x2, y2 = _pad_and_clamp(
        {"x_pct": 95, "y_pct": 95, "w_pct": 10, "h_pct": 10}, 200, 100, pad_pct=5
    )
    assert x1 >= 0 and y1 >= 0
    assert x2 <= 200 and y2 <= 100


# --- OCR未導入時のフォールバック ---
def test_ocr_returns_empty_without_dependency():
    # rapidocr-onnxruntime 未導入の環境では [] を返す（例外を投げない）
    assert ocr_sensitive_regions(_white(), 200, 100) == []


# --- 統合（Gemini領域 + OCR領域） ---
def test_redact_unions_ai_and_ocr(monkeypatch):
    ai = [{"x_pct": 0, "y_pct": 0, "w_pct": 10, "h_pct": 10}]
    monkeypatch.setattr(
        redaction, "ocr_sensitive_regions",
        lambda b, w, h: [{"x_pct": 50, "y_pct": 50, "w_pct": 10, "h_pct": 10}],
    )
    out, count = redact(_white(), ai)
    assert count == 2
    assert out != _white()


def test_redact_no_regions_returns_original(monkeypatch):
    monkeypatch.setattr(redaction, "ocr_sensitive_regions", lambda b, w, h: [])
    original = _white()
    out, count = redact(original, [])
    assert count == 0
    assert out == original
