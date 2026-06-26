"""Google Sheets からログ行を読み込み、週次集計を行う。

集計ロジック（aggregate_rows）はネットワーク非依存の純関数として切り出し、
テストしやすくする。
"""
import logging
from datetime import datetime, timedelta

from config import SHEET_COLUMNS, SHEET_ID, SHEET_TAB
from google_auth import get_sheets_service

log = logging.getLogger("screenlog.report")


def read_rows() -> list[dict]:
    """Sheets 全行を読み、ヘッダを使って dict のリストに変換して返す。"""
    service = get_sheets_service()
    resp = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range=f"{SHEET_TAB}!A1:Z")
        .execute()
    )
    values = resp.get("values", [])
    if not values:
        return []

    # 1行目がヘッダ（SHEET_COLUMNS）かどうか判定。違えばSHEET_COLUMNSを使う。
    first = values[0]
    if first and first[0] == SHEET_COLUMNS[0]:
        header, data = first, values[1:]
    else:
        header, data = SHEET_COLUMNS, values

    rows: list[dict] = []
    for raw in data:
        row = {header[i]: (raw[i] if i < len(raw) else "") for i in range(len(header))}
        rows.append(row)
    return rows


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def aggregate_rows(rows: list[dict], now: datetime, days: int = 7) -> dict:
    """直近 days 日の行をカテゴリ別に集計する。

    Returns:
        {
          "period_days": int,
          "record_count": int,
          "total_minutes": int,
          "by_category": [ {"category","minutes","count","percent"}... ]  # 時間降順
          "recent_summaries": [str, ...]  # 直近の要約（最大20件）
        }
    """
    cutoff = now - timedelta(days=days)
    cat_minutes: dict[str, int] = {}
    cat_count: dict[str, int] = {}
    summaries: list[tuple[datetime, str]] = []
    total = 0
    count = 0

    for row in rows:
        dt = _parse_dt(row.get("timestamp", ""))
        if dt is None:
            continue
        # タイムゾーン有無を揃える（naive 比較）
        dt_naive = dt.replace(tzinfo=None)
        if dt_naive < cutoff.replace(tzinfo=None):
            continue
        try:
            minutes = int(float(row.get("duration_min", 0) or 0))
        except (ValueError, TypeError):
            minutes = 0
        category = (row.get("category") or "その他").strip() or "その他"
        cat_minutes[category] = cat_minutes.get(category, 0) + minutes
        cat_count[category] = cat_count.get(category, 0) + 1
        total += minutes
        count += 1
        summary = (row.get("summary") or "").strip()
        if summary:
            summaries.append((dt_naive, summary))

    by_category = [
        {
            "category": cat,
            "minutes": mins,
            "count": cat_count[cat],
            "percent": round(mins / total * 100, 1) if total else 0.0,
        }
        for cat, mins in sorted(cat_minutes.items(), key=lambda kv: kv[1], reverse=True)
    ]
    summaries.sort(key=lambda x: x[0], reverse=True)
    recent = [s for _, s in summaries[:20]]

    return {
        "period_days": days,
        "record_count": count,
        "total_minutes": total,
        "by_category": by_category,
        "recent_summaries": recent,
    }
