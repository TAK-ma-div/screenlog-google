"""機密情報マスク。

2層で機密領域を検出し、黒塗り（または ぼかし）でマスクする:
  1. Gemini が返す sensitive_regions（画面全体の見た目から推論）
  2. OCR + 正規表現の決定的レイヤー（文字の正確な位置から確実に検出）

OCRレイヤーは任意依存 RapidOCR（rapidocr-onnxruntime, pipのみ・全OS対応）を使う。
未導入/失敗時は自動でスキップし、Gemini + 正規表現なしで動作する（degrade gracefully）。
"""
import io
import logging
import re

from PIL import Image, ImageDraw, ImageFilter

from config import MASK_STYLE, REDACTION_PAD_PCT, USE_OCR_REDACTION

log = logging.getLogger("screenlog.redaction")

# --- 機密と判断する正規表現（クレデンシャル系に絞り、過剰マスクを避ける） ---
SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),                 # Google APIキー
    re.compile(r"sk-(?:ant-)?[0-9A-Za-z\-_]{16,}"),          # OpenAI / Anthropic
    re.compile(r"AKIA[0-9A-Z]{12,}"),                        # AWS アクセスキー
    re.compile(r"gh[pousr]_[0-9A-Za-z]{20,}"),               # GitHub トークン
    re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}"),            # Slack トークン
    re.compile(r"eyJ[0-9A-Za-z\-_]{10,}\.[0-9A-Za-z\-_]{10,}\.[0-9A-Za-z\-_]{6,}"),  # JWT
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),       # 秘密鍵
    re.compile(r"secret_[0-9A-Za-z]{10,}"),                  # Notion 等
    # key/password/token/secret = 値（代入形）
    re.compile(
        r"(?i)\b(?:api[_-]?key|password|passwd|secret|token|access[_-]?token|"
        r"client[_-]?secret)\b\s*[:=]\s*\S+"
    ),
    re.compile(r"(?i)\bBearer\s+[0-9A-Za-z\-_\.=]{10,}"),    # Bearer トークン
]


def is_sensitive_text(text: str) -> bool:
    """文字列が機密パターンに一致するか。"""
    if not text:
        return False
    return any(p.search(text) for p in SECRET_PATTERNS)


def _bbox_from_points(points) -> tuple[float, float, float, float]:
    """4点ポリゴン [[x,y],...] から (minx, miny, maxx, maxy) を返す。"""
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def boxes_to_regions(ocr_items: list[dict], img_w: int, img_h: int) -> list[dict]:
    """OCR結果から機密テキストの領域だけを抽出し、%座標の region に変換する。

    ocr_items: [{"text": str, "box": [[x,y],[x,y],[x,y],[x,y]]}, ...]（boxはピクセル）
    返り値: [{"x_pct","y_pct","w_pct","h_pct"}, ...]
    """
    if img_w <= 0 or img_h <= 0:
        return []
    regions: list[dict] = []
    for item in ocr_items:
        text = item.get("text", "")
        if not is_sensitive_text(text):
            continue
        box = item.get("box") or []
        if len(box) < 2:
            continue
        minx, miny, maxx, maxy = _bbox_from_points(box)
        regions.append(
            {
                "x_pct": minx / img_w * 100,
                "y_pct": miny / img_h * 100,
                "w_pct": (maxx - minx) / img_w * 100,
                "h_pct": (maxy - miny) / img_h * 100,
            }
        )
    return regions


def ocr_sensitive_regions(image_bytes: bytes, img_w: int, img_h: int) -> list[dict]:
    """RapidOCRで文字を読み、機密パターンに一致した領域を%座標で返す。

    RapidOCR未導入/失敗時は [] を返す（degrade gracefully）。
    """
    if not USE_OCR_REDACTION:
        return []
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        log.info(
            "OCRマスクは無効（rapidocr-onnxruntime 未導入）。"
            "精度を上げるには requirements-ocr.txt を導入してください。"
        )
        return []
    try:
        import numpy as np

        engine = RapidOCR()
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        result, _ = engine(np.array(img))
        if not result:
            return []
        # RapidOCR 出力: [[box(4点), text, score], ...]
        ocr_items = [{"box": row[0], "text": row[1]} for row in result]
        return boxes_to_regions(ocr_items, img_w, img_h)
    except Exception as e:  # noqa: BLE001 - OCR失敗で本処理を止めない
        log.warning("OCRマスクに失敗（スキップ）: %s", e)
        return []


def _pad_and_clamp(region: dict, img_w: int, img_h: int, pad_pct: float):
    """region(%)を px の (x1,y1,x2,y2) に変換し、余白を足して画像内にクランプ。"""
    x = region.get("x_pct", 0) / 100 * img_w
    y = region.get("y_pct", 0) / 100 * img_h
    w = region.get("w_pct", 0) / 100 * img_w
    h = region.get("h_pct", 0) / 100 * img_h
    pad_x = pad_pct / 100 * img_w
    pad_y = pad_pct / 100 * img_h
    x1 = int(max(0, x - pad_x))
    y1 = int(max(0, y - pad_y))
    x2 = int(min(img_w, x + w + pad_x))
    y2 = int(min(img_h, y + h + pad_y))
    return x1, y1, x2, y2


def mask_regions(
    image_bytes: bytes,
    regions: list[dict],
    pad_pct: float | None = None,
    style: str | None = None,
) -> bytes:
    """領域(%)を黒塗り（fill）またはぼかし（blur）でマスクしたJPEGを返す。"""
    pad_pct = REDACTION_PAD_PCT if pad_pct is None else pad_pct
    style = MASK_STYLE if style is None else style

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)

    for region in regions:
        x1, y1, x2, y2 = _pad_and_clamp(region, w, h, pad_pct)
        if x2 <= x1 or y2 <= y1:
            continue
        if style == "blur":
            cropped = img.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(radius=24))
            img.paste(cropped, (x1, y1))
        else:  # fill（黒塗り・復元不可）
            draw.rectangle((x1, y1, x2, y2), fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def redact(image_bytes: bytes, ai_regions: list[dict] | None = None) -> tuple[bytes, int]:
    """Gemini領域 + OCR/正規表現領域 を統合してマスクする。

    Returns:
        (masked_jpeg_bytes, masked_region_count)
    """
    ai_regions = ai_regions or []
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    ocr_regions = ocr_sensitive_regions(image_bytes, w, h)
    all_regions = list(ai_regions) + ocr_regions
    if not all_regions:
        return image_bytes, 0
    return mask_regions(image_bytes, all_regions), len(all_regions)
