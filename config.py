"""環境変数ベースの設定。MVP（Gemini / Sheets / Gmail）に必要な項目のみ。"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# このファイルのあるディレクトリを基準にする（相対パスの認証ファイル解決用）
BASE_DIR = Path(__file__).resolve().parent


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _resolve(path_str: str) -> Path:
    """相対パスは BASE_DIR 基準で解決する。"""
    p = Path(path_str)
    return p if p.is_absolute() else BASE_DIR / p


# --- AI (Gemini) ---
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- Google (Sheets / Gmail) ---
GOOGLE_CREDENTIALS_FILE = _resolve(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))
GOOGLE_TOKEN_FILE = _resolve(os.getenv("GOOGLE_TOKEN_FILE", "token.json"))
SHEET_ID = os.getenv("SHEET_ID", "")
SHEET_TAB = os.getenv("SHEET_TAB", "log")
GMAIL_TO = os.getenv("GMAIL_TO", "")  # 空なら自分宛("me")

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/documents",
]

# --- Capture ---
CAPTURE_INTERVAL_MINUTES = int(os.getenv("CAPTURE_INTERVAL_MINUTES", "5"))
SCREENSHOT_DIR = _resolve(os.getenv("SCREENSHOT_DIR", "screenshots"))
SAVE_SCREENSHOTS = _flag("SAVE_SCREENSHOTS", "true")
USE_DUMMY_CAPTURE = _flag("USE_DUMMY_CAPTURE", "false")

# --- Filters ---
CONFIDENCE_THRESHOLD = int(os.getenv("CONFIDENCE_THRESHOLD", "70"))

# --- Redaction (機密マスク) ---
# OCR+正規表現の決定的レイヤーを使うか（RapidOCR未導入なら自動でスキップ）
USE_OCR_REDACTION = _flag("USE_OCR_REDACTION", "true")
# マスク領域に足す余白（画像幅/高さに対する%）。取りこぼし防止。
REDACTION_PAD_PCT = float(os.getenv("REDACTION_PAD_PCT", "1.5"))
# マスク方式: "fill"=黒塗り（復元不可・推奨） / "blur"=ぼかし
MASK_STYLE = os.getenv("MASK_STYLE", "fill")

# --- Weekly report ---
WEEKLY_REPORT_DAYS = int(os.getenv("WEEKLY_REPORT_DAYS", "7"))
REPORT_TITLE_PREFIX = os.getenv("REPORT_TITLE_PREFIX", "ScreenLog週次レポート")

# --- Dev/sandbox ---
GOOGLE_STUB = _flag("GOOGLE_STUB", "false")

# Sheets の列順（ヘッダ兼レコードの正本）
SHEET_COLUMNS = [
    "timestamp",
    "summary",
    "category",
    "confidence",
    "duration_min",
    "primary_screen",
    "visible_output",
    "focus_risk",
    "non_productive_signal",
    "screenshot_path",
    "app_breakdown",
]
