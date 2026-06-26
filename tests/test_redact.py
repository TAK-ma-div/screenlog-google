"""機密領域のぼかし処理を検証する。"""
import io

from PIL import Image

from capture import redact_sensitive_regions
from dummy_capture import generate_dummy_screenshot


def _region_pixels(jpeg: bytes, box_pct):
    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    w, h = img.size
    x = int(box_pct["x_pct"] / 100 * w)
    y = int(box_pct["y_pct"] / 100 * h)
    rw = int(box_pct["w_pct"] / 100 * w)
    rh = int(box_pct["h_pct"] / 100 * h)
    return list(img.crop((x, y, x + rw, y + rh)).getdata())


def test_redact_changes_region():
    original = generate_dummy_screenshot()
    region = {"x_pct": 0, "y_pct": 10, "w_pct": 60, "h_pct": 10}

    redacted = redact_sensitive_regions(original, [region])

    before = _region_pixels(original, region)
    after = _region_pixels(redacted, region)
    assert before != after, "ぼかし対象領域のピクセルが変化していない"


def test_redact_empty_regions_is_noop_size():
    original = generate_dummy_screenshot()
    result = redact_sensitive_regions(original, [])
    # 空領域でも有効なJPEGが返る
    assert Image.open(io.BytesIO(result)).size == Image.open(io.BytesIO(original)).size
