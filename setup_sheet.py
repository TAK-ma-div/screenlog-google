"""ログ保存用スプレッドシートを新規作成してヘッダを書き込む（初回のみ）。

  python setup_sheet.py

実行後、表示される SHEET_ID を .env の SHEET_ID に設定する。
GOOGLE_STUB=true ではスタブのため実シートは作られない（動作確認用）。
"""
import logging

from config import GOOGLE_STUB, SHEET_COLUMNS, SHEET_TAB
from google_auth import get_sheets_service

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("screenlog.setup")


def create_spreadsheet(title: str = "ScreenLog") -> str:
    """新規スプレッドシートを作成し、ヘッダ行を書き込んで spreadsheetId を返す。"""
    service = get_sheets_service()

    if GOOGLE_STUB:
        log.info("[STUB] スプレッドシート作成はスキップ（GOOGLE_STUB=true）")
        return "stub-sheet-id"

    spreadsheet = (
        service.spreadsheets()
        .create(
            body={
                "properties": {"title": title},
                "sheets": [{"properties": {"title": SHEET_TAB}}],
            },
            fields="spreadsheetId",
        )
        .execute()
    )
    sheet_id = spreadsheet["spreadsheetId"]

    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{SHEET_TAB}!A1",
        valueInputOption="RAW",
        body={"values": [SHEET_COLUMNS]},
    ).execute()

    return sheet_id


if __name__ == "__main__":
    sid = create_spreadsheet()
    print("\n=== スプレッドシートを作成しました ===")
    print(f"SHEET_ID={sid}")
    print("この値を .env の SHEET_ID に設定してください。")
    print(f"URL: https://docs.google.com/spreadsheets/d/{sid}/edit")
