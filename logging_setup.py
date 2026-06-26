"""ロギング設定（コンソール + ファイルローテーション）。

main / weekly_report の起動時に setup_logging() を1回呼ぶ。
ファイルログは RotatingFileHandler でサイズ上限を超えると自動ローテーションする。
"""
import logging
from logging.handlers import RotatingFileHandler

from config import LOG_BACKUP_COUNT, LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES

_FMT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_configured = False


def setup_logging() -> None:
    """ルートロガーにコンソール+ローテーションファイルのハンドラを設定する（冪等）。"""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    formatter = logging.Formatter(_FMT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            str(LOG_FILE),
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as e:  # ファイルに書けない環境（読み取り専用等）でも継続
        root.warning("ファイルログを開けませんでした（コンソールのみ継続）: %s", e)

    _configured = True
