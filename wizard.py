"""セットアップウィザードのロジック（HTTP非依存・テスト容易）。

setup_web.py（ローカルWeb画面）から呼ばれる。
GOOGLE_STUB=true のときは実際のGoogleアクセスをせずスタブで完結する。
"""
import os
from pathlib import Path

from config import (
    BASE_DIR,
    DEFAULT_CATEGORIES,
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_TOKEN_FILE,
    OPTIONAL_COLUMNS_ALL,
    SHEET_TAB,
)
from env_file import read_env, update_env

ENV_PATH = BASE_DIR / ".env"


def folder_shortcuts() -> list[dict]:
    """フォルダ選択の起点となる定番ディレクトリ。存在するものだけ返す。"""
    home = Path.home()
    candidates = [
        ("ホーム", home),
        ("デスクトップ", home / "Desktop"),
        ("書類", home / "Documents"),
        ("アプリ既定", BASE_DIR),
    ]
    return [{"label": label, "path": str(p)} for label, p in candidates if p.exists()]


def list_dirs(path: str | None = None) -> dict:
    """指定フォルダ直下のサブフォルダを列挙する（フォルダ選択UI用）。

    存在しない/権限が無い場合はホームにフォールバック。隠しフォルダは除外。
    Returns: {"path","parent","dirs":[{name,path}],"shortcuts":[...]}
    """
    base = Path(path).expanduser() if path else Path.home()
    if not base.exists() or not base.is_dir():
        base = Path.home()
    try:
        base = base.resolve()
    except OSError:
        base = Path.home()

    dirs: list[dict] = []
    try:
        for child in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            if child.is_dir() and not child.name.startswith("."):
                dirs.append({"name": child.name, "path": str(child)})
    except (OSError, PermissionError):
        dirs = []

    parent = str(base.parent) if base.parent != base else None
    return {
        "path": str(base),
        "parent": parent,
        "dirs": dirs,
        "shortcuts": folder_shortcuts(),
    }

# Web設定ページで編集できる項目と既定値（すべて .env に保存）
SETTINGS_DEFAULTS: dict[str, str] = {
    "SCREENSHOT_DIR": "screenshots",
    "LOG_FILE": "screenlog.log",
    "CAPTURE_INTERVAL_MINUTES": "5",
    "WEEKLY_REPORT_DAYS": "7",
    "SCREENSHOT_RETENTION_DAYS": "14",
    "CONFIDENCE_THRESHOLD": "70",
    "NOTIFY_ENABLED": "true",
    "CATEGORIES": ",".join(DEFAULT_CATEGORIES),
    "RECORD_OPTIONAL_COLUMNS": ",".join(OPTIONAL_COLUMNS_ALL),
}


def _sheet_url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit" if sheet_id else ""


def get_status() -> dict:
    """各セットアップ項目の充足状況を返す（.envファイルを正本に判定）。"""
    env = read_env(ENV_PATH)
    gemini_key = env.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    sheet_id = env.get("SHEET_ID", "")
    return {
        "has_credentials": GOOGLE_CREDENTIALS_FILE.exists(),
        "has_token": GOOGLE_TOKEN_FILE.exists(),
        "has_gemini_key": bool(gemini_key.strip()),
        "has_sheet": bool(sheet_id.strip()),
        "sheet_url": _sheet_url(sheet_id.strip()),
        "credentials_path": str(GOOGLE_CREDENTIALS_FILE),
    }


def save_config(values: dict) -> dict:
    """入力値（Geminiキー等）を .env に保存する。空値はスキップ。"""
    allowed = ("GEMINI_API_KEY", "GEMINI_MODEL", "GMAIL_TO")
    to_write = {
        k: str(values[k]).strip()
        for k in allowed
        if values.get(k) is not None and str(values[k]).strip() != ""
    }
    if to_write:
        update_env(ENV_PATH, to_write)
        # 同プロセスでも反映されるよう os.environ も更新
        os.environ.update(to_write)
    return {"saved": list(to_write.keys())}


def get_settings() -> dict:
    """カスタマイズ可能な設定の現在値を返す（.env優先・無ければ既定値）。"""
    env = read_env(ENV_PATH)
    values = {key: env.get(key, default) for key, default in SETTINGS_DEFAULTS.items()}
    return {
        "values": values,
        "available_optional_columns": list(OPTIONAL_COLUMNS_ALL),
        "default_categories": list(DEFAULT_CATEGORIES),
    }


def save_settings(values: dict) -> dict:
    """設定値（フォルダ・日数・カテゴリ・列・通知）を .env に保存する。

    SETTINGS_DEFAULTS のキーのみ許可。値が None のキーはスキップ（空文字は許可＝
    例: CATEGORIES を空にしたい等は呼び出し側で制御）。
    """
    to_write: dict[str, str] = {}
    for key in SETTINGS_DEFAULTS:
        if key in values and values[key] is not None:
            to_write[key] = str(values[key]).strip()
    if to_write:
        update_env(ENV_PATH, to_write)
        os.environ.update(to_write)
    return {"saved": list(to_write.keys())}


def run_oauth() -> dict:
    """Google OAuth を実行し token.json を生成する。"""
    from google_auth import ensure_credentials

    ensure_credentials()
    return {"has_token": GOOGLE_TOKEN_FILE.exists() or os.getenv("GOOGLE_STUB", "").lower()
            in {"1", "true", "yes", "on"}}


def create_sheet(title: str = "ScreenLog") -> dict:
    """ログ用スプレッドシートを作成し SHEET_ID を .env に保存、URLを返す。"""
    from setup_sheet import create_spreadsheet

    sheet_id = create_spreadsheet(title)
    update_env(ENV_PATH, {"SHEET_ID": sheet_id, "SHEET_TAB": SHEET_TAB})
    os.environ["SHEET_ID"] = sheet_id
    return {"sheet_id": sheet_id, "sheet_url": _sheet_url(sheet_id)}


# credentials.json 作成の案内（setup_web から表示）
CREDENTIALS_GUIDE = [
    "Google Cloud Console (https://console.cloud.google.com/) でプロジェクトを作成/選択",
    "「APIとサービス」→「ライブラリ」で Google Sheets API / Google Docs API / Gmail API を有効化",
    "「OAuth同意画面」を構成（ユーザーの種類=外部、テストユーザーに自分のGmailを追加）",
    "「認証情報」→「認証情報を作成」→「OAuthクライアントID」→ アプリの種類「デスクトップアプリ」",
    "作成後にJSONをダウンロードし、credentials.json としてこのアプリのフォルダに保存",
    "下の「再チェック」を押す",
]
