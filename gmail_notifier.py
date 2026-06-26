"""Gmail によるメール通知（discord_notifier の置き換え）。"""
import base64
import logging
from email.mime.text import MIMEText

from config import GMAIL_TO
from google_auth import get_gmail_service

log = logging.getLogger("screenlog.gmail")


def _build_raw(subject: str, body: str, to: str) -> dict:
    msg = MIMEText(body, _charset="utf-8")
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_notification(subject: str, body: str) -> None:
    """確認依頼などの通知メールを送る。宛先未設定なら自分宛("me")。

    失敗してもコアループを止めないよう、例外は握ってログのみ。
    """
    to = GMAIL_TO or "me@example.com"  # me@... はFromの自分宛として扱う
    try:
        service = get_gmail_service()
        message = _build_raw(subject, body, to)
        service.users().messages().send(userId="me", body=message).execute()
        log.info("Gmail通知を送信: %s", subject)
    except Exception as e:  # noqa: BLE001 - 通知失敗で本処理を止めない
        log.warning("Gmail通知に失敗（処理は継続）: %s", e)
