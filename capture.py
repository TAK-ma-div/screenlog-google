"""スクリーンショット撮影モジュール。

実機では mss でデスクトップ全体をキャプチャ。
USE_DUMMY_CAPTURE=true（サンドボックス/CI）では合成画像を返す。
"""
import io
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

from config import SCREENSHOT_DIR, SAVE_SCREENSHOTS, USE_DUMMY_CAPTURE


def capture_error_hint() -> str:
    """キャプチャ失敗時に表示する、OS別の対処ヒントを返す。"""
    if sys.platform == "darwin":
        return (
            "macOSでは画面収録の許可が必要です。"
            "システム設定 → プライバシーとセキュリティ → 画面収録 で、"
            "実行中のターミナル（またはPython）にチェックを入れて再実行してください。"
            "（ヘッドレス環境では USE_DUMMY_CAPTURE=true を使用）"
        )
    if sys.platform.startswith("win"):
        return (
            "画面取得に失敗しました。サービス起動やリモート/別セッションでは"
            "撮れない場合があります。（ヘッドレス環境では USE_DUMMY_CAPTURE=true を使用）"
        )
    return (
        "この環境では画面を取得できません。"
        "ヘッドレス/コンテナでは USE_DUMMY_CAPTURE=true を使用してください。"
    )


def _encode_jpeg(img: Image.Image, max_width: int = 1920) -> bytes:
    if img.mode != "RGB":
        img = img.convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _grab_real() -> bytes:
    import mss  # ヘッドレス環境では import 時点で失敗しうるため遅延 import

    with mss.mss() as sct:
        monitor = sct.monitors[0]  # 全モニター結合した仮想スクリーン
        raw = sct.grab(monitor)
    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    return _encode_jpeg(img)


def capture_screenshot() -> tuple[bytes, str | None]:
    """デスクトップをキャプチャして (jpeg_bytes, saved_path|None) を返す。

    USE_DUMMY_CAPTURE=true の場合はダミー画像を生成する。
    SAVE_SCREENSHOTS=true の場合はローカルにも保存しパスを返す。
    """
    if USE_DUMMY_CAPTURE:
        from dummy_capture import generate_dummy_screenshot

        jpeg_bytes = generate_dummy_screenshot()
    else:
        jpeg_bytes = _grab_real()

    saved_path: str | None = None
    if SAVE_SCREENSHOTS:
        now = datetime.now()
        day_dir = Path(SCREENSHOT_DIR) / now.strftime("%Y%m%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        saved_path = str(day_dir / now.strftime("%H%M_%S.jpg"))
        with open(saved_path, "wb") as f:
            f.write(jpeg_bytes)

    return jpeg_bytes, saved_path


def redact_sensitive_regions(image_bytes: bytes, regions: list[dict]) -> bytes:
    """機密領域（%座標）をマスクした JPEG を返す。

    実体は redaction.mask_regions に委譲（既定は黒塗り＋余白）。
    各 region は {"x_pct","y_pct","w_pct","h_pct"}（画像サイズに対する%）。
    """
    from redaction import mask_regions

    return mask_regions(image_bytes, regions)
