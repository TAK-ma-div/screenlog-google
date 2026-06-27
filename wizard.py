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
    "ENABLE_WINDOW_TRACKER": "false",
    "WINDOW_POLL_INTERVAL_SEC": "30",
    "CATEGORIES": ",".join(DEFAULT_CATEGORIES),
    "RECORD_OPTIONAL_COLUMNS": ",".join(OPTIONAL_COLUMNS_ALL),
}


def _sheet_url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit" if sheet_id else ""


def get_status() -> dict:
    """各セットアップ項目の充足状況を返す（.envファイルを正本に判定）。"""
    env = read_env(ENV_PATH)
    gemini_key = env.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    openai_key = env.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    provider = (env.get("AI_PROVIDER") or os.getenv("AI_PROVIDER", "gemini")).strip() or "gemini"
    sheet_id = env.get("SHEET_ID", "")
    has_gemini_key = bool(gemini_key.strip())
    has_openai_key = bool(openai_key.strip())
    # 選択中プロバイダに必要な鍵が揃っているか（vertex/gemini_cli は鍵不要とみなす）
    if provider == "openai":
        has_ai_key = has_openai_key
    elif provider in ("gemini_cli", "gemini-cli"):
        has_ai_key = True
    else:
        has_ai_key = has_gemini_key
    return {
        "has_credentials": GOOGLE_CREDENTIALS_FILE.exists(),
        "has_token": GOOGLE_TOKEN_FILE.exists(),
        "ai_provider": provider,
        "has_gemini_key": has_gemini_key,
        "has_openai_key": has_openai_key,
        "has_ai_key": has_ai_key,
        "openai_model": env.get("OPENAI_MODEL", ""),
        "openai_base_url": env.get("OPENAI_BASE_URL", ""),
        "has_sheet": bool(sheet_id.strip()),
        "sheet_url": _sheet_url(sheet_id.strip()),
        "credentials_path": str(GOOGLE_CREDENTIALS_FILE),
    }


def save_config(values: dict) -> dict:
    """入力値（プロバイダ・各APIキー等）を .env に保存する。空値はスキップ。"""
    allowed = (
        "AI_PROVIDER", "GEMINI_API_KEY", "GEMINI_MODEL",
        "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "GMAIL_TO",
    )
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


def read_recent_logs(lines: int = 200) -> dict:
    """ログファイルの末尾を読み、行配列で返す（ログ閲覧UI用）。"""
    from config import LOG_FILE

    path = Path(LOG_FILE)
    if not path.exists():
        return {"path": str(path), "exists": False, "lines": []}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            tail = f.readlines()[-max(1, int(lines)):]
    except OSError as e:
        return {"path": str(path), "exists": True, "error": str(e), "lines": []}
    return {"path": str(path), "exists": True, "lines": [ln.rstrip("\n") for ln in tail]}


def get_app_breakdown() -> dict:
    """直近（WEEKLY_REPORT_DAYS日）のアプリ別使用時間を集計して返す（グラフUI用）。

    Sheets未設定・データ無し・読込失敗でも例外を投げず空の結果を返す。
    """
    from datetime import datetime

    from config import WEEKLY_REPORT_DAYS

    env = read_env(ENV_PATH)
    days = int(env.get("WEEKLY_REPORT_DAYS", WEEKLY_REPORT_DAYS) or WEEKLY_REPORT_DAYS)
    tracker_on = str(env.get("ENABLE_WINDOW_TRACKER", "")).lower() in {"1", "true", "yes", "on"}
    try:
        from report_reader import aggregate_app_breakdown, read_rows

        result = aggregate_app_breakdown(read_rows(), datetime.now(), days)
    except Exception as e:  # noqa: BLE001
        return {"period_days": days, "total_minutes": 0, "apps": [],
                "tracker_enabled": tracker_on, "error": str(e)}
    result["tracker_enabled"] = tracker_on
    return result


def test_sheet() -> dict:
    """Sheets 接続を検証（ヘッダ確認のみ。GOOGLE_STUB時はスタブで成功）。"""
    try:
        from sheets_store import ensure_header

        ensure_header()
        return {"ok": True, "message": "Sheetsへの接続に成功しました"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": f"Sheets接続に失敗: {e}"}


def test_email() -> dict:
    """通知メールの送信を検証（テストメールを1通送る）。"""
    try:
        from gmail_notifier import send_notification

        send_notification(
            subject="[ScreenLog] テスト通知",
            body="これは ScreenLog のテスト通知メールです。受信できていれば設定は正常です。",
        )
        return {"ok": True, "message": "テストメールを送信しました"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": f"メール送信に失敗: {e}"}


def run_once() -> dict:
    """1サイクルだけ実行して動作確認する（テスト実行ボタン用）。"""
    try:
        from main import run_cycle

        ok = run_cycle()
        return {
            "ok": bool(ok),
            "message": "1サイクル実行に成功しました" if ok else "実行に失敗しました（ログを確認）",
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": f"実行エラー: {e}"}


# credentials.json 作成の案内（setup_web から表示）
CREDENTIALS_GUIDE = [
    "Google Cloud Console (https://console.cloud.google.com/) でプロジェクトを作成/選択",
    "「APIとサービス」→「ライブラリ」で Google Sheets API / Google Docs API / Gmail API を有効化",
    "「OAuth同意画面」を構成（ユーザーの種類=外部、テストユーザーに自分のGmailを追加）",
    "「認証情報」→「認証情報を作成」→「OAuthクライアントID」→ アプリの種類「デスクトップアプリ」",
    "作成後にJSONをダウンロードし、credentials.json としてこのアプリのフォルダに保存",
    "下の「再チェック」を押す",
]
