"""セットアップウィザードのロジック（HTTP非依存・テスト容易）。

setup_web.py（ローカルWeb画面）から呼ばれる。
GOOGLE_STUB=true のときは実際のGoogleアクセスをせずスタブで完結する。
"""
import os

from config import (
    BASE_DIR,
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_TOKEN_FILE,
    SHEET_TAB,
)
from env_file import read_env, update_env

ENV_PATH = BASE_DIR / ".env"


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
