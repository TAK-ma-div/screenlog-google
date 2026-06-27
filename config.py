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

# Gemini バックエンド: "aistudio"（既定/APIキー）か "vertex"（Google Cloud/Vertex AI）
# vertex は送信データが学習に使われない（エンタープライズ保護）。認証は ADC
# （gcloud auth application-default login など）。詳細は README / PRIVACY.md。
GEMINI_BACKEND = os.getenv("GEMINI_BACKEND", "aistudio").strip().lower()
USE_VERTEX = GEMINI_BACKEND == "vertex"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global").strip()

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
# 保存したスクショを何日で自動削除するか（0以下で無効）
SCREENSHOT_RETENTION_DAYS = int(os.getenv("SCREENSHOT_RETENTION_DAYS", "14"))

# --- Window tracker (アプリ別の実測使用時間で分析精度を上げる。任意・既定オフ) ---
# 有効にするとアクティブウィンドウ名/アプリ名をGeminiに渡す（PRIVACY.md参照）
ENABLE_WINDOW_TRACKER = _flag("ENABLE_WINDOW_TRACKER", "false")
WINDOW_POLL_INTERVAL_SEC = int(os.getenv("WINDOW_POLL_INTERVAL_SEC", "30"))

# --- Logging ---
LOG_FILE = _resolve(os.getenv("LOG_FILE", "screenlog.log"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))  # 5MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))

# --- API retry (指数バックオフ) ---
API_RETRY_ATTEMPTS = int(os.getenv("API_RETRY_ATTEMPTS", "3"))
API_RETRY_BASE_DELAY = float(os.getenv("API_RETRY_BASE_DELAY", "1.0"))

# --- Filters / Notification ---
CONFIDENCE_THRESHOLD = int(os.getenv("CONFIDENCE_THRESHOLD", "70"))
# 低確信度の確認依頼メールを送るか
NOTIFY_ENABLED = _flag("NOTIFY_ENABLED", "true")


def _csv(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or default


# --- Categories (業務分類。自分の業務に合わせて変更可) ---
DEFAULT_CATEGORIES = [
    "開発", "設計・企画", "資料作成", "ドキュメント作成", "調査・リサーチ",
    "会議", "メール・チャット", "学習", "事務処理", "私用", "その他",
]
CATEGORIES = _csv("CATEGORIES", DEFAULT_CATEGORIES)

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

# Sheets の列（ヘッダ兼レコードの正本）。
# コア列は常に記録。任意列は RECORD_OPTIONAL_COLUMNS で取捨選択できる。
CORE_COLUMNS = ["timestamp", "summary", "category", "confidence", "duration_min"]
OPTIONAL_COLUMNS_ALL = [
    "primary_screen",
    "visible_output",
    "focus_risk",
    "non_productive_signal",
    "screenshot_path",
    "app_breakdown",
]
_selected_optional = _csv("RECORD_OPTIONAL_COLUMNS", OPTIONAL_COLUMNS_ALL)
# 不正な列名は除外し、全体の順序は OPTIONAL_COLUMNS_ALL に揃える
RECORD_OPTIONAL_COLUMNS = [c for c in OPTIONAL_COLUMNS_ALL if c in _selected_optional]
SHEET_COLUMNS = CORE_COLUMNS + RECORD_OPTIONAL_COLUMNS
