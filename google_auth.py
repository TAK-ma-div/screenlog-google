"""Google OAuth（個人アカウント）認証と Sheets/Gmail クライアント生成。

初回実行で credentials.json を使ったブラウザOAuthを行い token.json を生成（gitignore）。
GOOGLE_STUB=true のときはネットワークを使わずスタブクライアントを返す。
"""
from config import (
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_SCOPES,
    GOOGLE_STUB,
    GOOGLE_TOKEN_FILE,
)

_cached_creds = None


def _load_credentials():
    """token.json をロード/更新。なければOAuthフローを起動。"""
    global _cached_creds
    if _cached_creds is not None:
        return _cached_creds

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if GOOGLE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), GOOGLE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not GOOGLE_CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"OAuthクライアント設定が見つかりません: {GOOGLE_CREDENTIALS_FILE}\n"
                    "Google Cloud ConsoleでデスクトップアプリのOAuthクライアントを作成し、"
                    "credentials.json をこのフォルダに配置してください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GOOGLE_CREDENTIALS_FILE), GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        GOOGLE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    _cached_creds = creds
    return creds


def ensure_credentials():
    """OAuth認証を確立（token.json生成/更新）。STUB時は何もしない。

    セットアップウィザードから「Google認証」ボタンで呼ばれる。
    """
    if GOOGLE_STUB:
        return None
    return _load_credentials()


def get_sheets_service():
    """Sheets API サービスを返す。STUB時は StubSheets。"""
    if GOOGLE_STUB:
        from stubs import StubSheetsService

        return StubSheetsService()
    from googleapiclient.discovery import build

    return build("sheets", "v4", credentials=_load_credentials(), cache_discovery=False)


def get_gmail_service():
    """Gmail API サービスを返す。STUB時は StubGmail。"""
    if GOOGLE_STUB:
        from stubs import StubGmailService

        return StubGmailService()
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=_load_credentials(), cache_discovery=False)


def get_docs_service():
    """Docs API サービスを返す。STUB時は StubDocs。"""
    if GOOGLE_STUB:
        from stubs import StubDocsService

        return StubDocsService()
    from googleapiclient.discovery import build

    return build("docs", "v1", credentials=_load_credentials(), cache_discovery=False)
