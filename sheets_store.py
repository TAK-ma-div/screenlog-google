"""Google Sheets へのログ記録（notion_logger の置き換え）。"""
import json
import logging
from datetime import datetime

from config import SHEET_COLUMNS, SHEET_ID, SHEET_TAB
from google_auth import get_sheets_service

log = logging.getLogger("screenlog.sheets")


def build_record(
    timestamp: datetime,
    analysis: dict,
    screenshot_path: str | None = None,
    duration_min: int = 5,
    app_breakdown: dict | None = None,
) -> dict:
    """分析結果dict を Sheets 列スキーマに沿った record(dict) に整形する。"""
    vo = analysis.get("visual_observations") or {}
    return {
        "timestamp": timestamp.astimezone().isoformat(),
        "summary": str(analysis.get("summary", ""))[:2000],
        "category": str(analysis.get("category", "")),
        "confidence": int(analysis.get("confidence", 0) or 0),
        "duration_min": duration_min,
        "primary_screen": str(vo.get("primary_screen", "")),
        "visible_output": str(vo.get("visible_output", "")),
        "focus_risk": str(vo.get("focus_risk", "")),
        "non_productive_signal": str(vo.get("non_productive_signal", "")),
        "screenshot_path": screenshot_path or "",
        "app_breakdown": json.dumps(app_breakdown or {}, ensure_ascii=False),
    }


def _record_to_row(record: dict) -> list:
    return [record.get(col, "") for col in SHEET_COLUMNS]


def ensure_header() -> None:
    """先頭行にヘッダが無ければ書き込む。"""
    service = get_sheets_service()
    rng = f"{SHEET_TAB}!A1"
    resp = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range=f"{SHEET_TAB}!A1:A1")
        .execute()
    )
    if resp.get("values"):
        return  # 既にヘッダあり
    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=rng,
        valueInputOption="RAW",
        body={"values": [SHEET_COLUMNS]},
    ).execute()
    log.info("ヘッダ行を書き込みました")


def append_row(record: dict) -> None:
    """record を Sheets に1行追記する。"""
    service = get_sheets_service()
    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_TAB}!A1",
        valueInputOption="RAW",
        body={"values": [_record_to_row(record)]},
    ).execute()
    log.info("Sheetsに1行追記: %s", record.get("summary", "")[:40])
