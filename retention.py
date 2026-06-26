"""古いスクリーンショットの自動削除。

capture.py は screenshots/YYYYMMDD/ 配下に保存する。
保持日数を過ぎた日付フォルダを丸ごと削除する。
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("screenlog.retention")


def cleanup_old_screenshots(
    base_dir, retention_days: int, now: datetime | None = None
) -> int:
    """保持日数を超えた YYYYMMDD フォルダを削除し、削除したフォルダ数を返す。

    retention_days <= 0 のときは無効（何もしない）。
    """
    if retention_days <= 0:
        return 0
    base = Path(base_dir)
    if not base.exists():
        return 0

    now = now or datetime.now()
    cutoff = (now - timedelta(days=retention_days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    removed = 0
    for child in base.iterdir():
        if not child.is_dir():
            continue
        try:
            day = datetime.strptime(child.name, "%Y%m%d")
        except ValueError:
            continue  # 想定外の名前はスキップ
        if day >= cutoff:
            continue
        try:
            for f in child.iterdir():
                if f.is_file():
                    f.unlink()
            child.rmdir()
            removed += 1
        except OSError as e:
            log.warning("古いスクショ削除に失敗 %s: %s", child, e)
    if removed:
        log.info("古いスクショフォルダを %d 件削除しました（保持%d日）", removed, retention_days)
    return removed
