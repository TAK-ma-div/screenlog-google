"""ScreenLog (Google版) メイン。

コアループ:
  capture → Gemini分析 → 機密ぼかし(保存画像) → Sheets追記 → (任意)Gmail通知

実行モード:
  python main.py --once   : 1サイクルだけ実行
  python main.py          : CAPTURE_INTERVAL_MINUTES 間隔でループ
"""
import argparse
import logging
import sys
import time
from datetime import datetime

from config import (
    CAPTURE_INTERVAL_MINUTES,
    CONFIDENCE_THRESHOLD,
    ENABLE_WINDOW_TRACKER,
    NOTIFY_ENABLED,
    SAVE_SCREENSHOTS,
    SCREENSHOT_DIR,
    SCREENSHOT_RETENTION_DAYS,
    WINDOW_POLL_INTERVAL_SEC,
)
from logging_setup import setup_logging

setup_logging()
log = logging.getLogger("screenlog.main")


def run_cycle(tracker=None) -> bool:
    """1サイクルを実行。成功時 True。例外は捕捉してログのみ。

    tracker: WindowTracker（任意）。あれば実測アプリ使用時間を分析へ渡す。
    """
    from capture import capture_screenshot, capture_error_hint
    from analyzer import analyze_screenshot
    from redaction import redact
    from retry import retry_call
    from sheets_store import append_row, build_record
    from gmail_notifier import send_notification

    try:
        image_bytes, saved_path = capture_screenshot()
    except Exception as e:  # noqa: BLE001
        log.error("キャプチャ失敗: %s", e)
        log.error("ヒント: %s", capture_error_hint())
        return False

    window_data = None
    if tracker is not None:
        breakdown = tracker.snapshot_and_reset()
        if breakdown:
            window_data = {"app_breakdown": breakdown}

    try:
        analysis = retry_call(
            lambda: analyze_screenshot(
                image_bytes,
                window_data=window_data,
                interval_min=CAPTURE_INTERVAL_MINUTES,
            ),
            label="gemini",
        )
    except Exception as e:  # noqa: BLE001
        log.error("Gemini分析失敗: %s", e)
        return False

    # 機密領域をマスク（Gemini領域 + OCR/正規表現領域を統合し黒塗り）して保存画像を上書き
    if saved_path and SAVE_SCREENSHOTS:
        try:
            ai_regions = analysis.get("sensitive_regions") or []
            masked, count = redact(image_bytes, ai_regions)
            if count:
                with open(saved_path, "wb") as f:
                    f.write(masked)
                log.info("機密領域 %d 箇所をマスクしました", count)
        except Exception as e:  # noqa: BLE001
            log.warning("マスク処理に失敗: %s", e)

    record = build_record(
        timestamp=datetime.now(),
        analysis=analysis,
        screenshot_path=saved_path,
        duration_min=CAPTURE_INTERVAL_MINUTES,
        app_breakdown=(window_data or {}).get("app_breakdown"),
    )

    try:
        retry_call(lambda: append_row(record), label="sheets")
    except Exception as e:  # noqa: BLE001
        log.error("Sheets追記失敗: %s", e)
        return False

    # 確信度が低い場合は確認依頼を通知（NOTIFY_ENABLED で無効化可）
    if NOTIFY_ENABLED and record["confidence"] < CONFIDENCE_THRESHOLD:
        send_notification(
            subject=f"[ScreenLog] 要確認: {record['category']} ({record['confidence']})",
            body=(
                f"確信度が低い記録です。内容を確認してください。\n\n"
                f"時刻: {record['timestamp']}\n"
                f"要約: {record['summary']}\n"
                f"カテゴリ: {record['category']}\n"
                f"確信度: {record['confidence']}\n"
            ),
        )

    log.info("サイクル完了: %s", record["summary"][:50])
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="ScreenLog (Google版)")
    parser.add_argument("--once", action="store_true", help="1サイクルだけ実行")
    args = parser.parse_args()

    tracker = _start_tracker()

    if args.once:
        ok = run_cycle(tracker=tracker)
        if tracker:
            tracker.stop()
        return 0 if ok else 1

    from retention import cleanup_old_screenshots

    log.info("ループ開始（%d分間隔）。Ctrl+Cで停止。", CAPTURE_INTERVAL_MINUTES)
    try:
        while True:
            run_cycle(tracker=tracker)
            try:
                cleanup_old_screenshots(SCREENSHOT_DIR, SCREENSHOT_RETENTION_DAYS)
            except Exception as e:  # noqa: BLE001
                log.warning("古いスクショ削除でエラー: %s", e)
            time.sleep(CAPTURE_INTERVAL_MINUTES * 60)
    except KeyboardInterrupt:
        log.info("停止しました")
        return 0
    finally:
        if tracker:
            tracker.stop()


def _start_tracker():
    """ENABLE_WINDOW_TRACKER が真かつ環境対応なら WindowTracker を起動して返す。"""
    if not ENABLE_WINDOW_TRACKER:
        return None
    from window_tracker import WindowTracker, available

    if not available():
        log.warning("ウィンドウ追跡はこの環境で利用できません（無効化して継続）")
        return None
    tracker = WindowTracker(poll_interval=WINDOW_POLL_INTERVAL_SEC)
    tracker.start()
    log.info("ウィンドウ追跡を有効化（%d秒間隔）", WINDOW_POLL_INTERVAL_SEC)
    return tracker


if __name__ == "__main__":
    sys.exit(main())
