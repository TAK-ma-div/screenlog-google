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
    SAVE_SCREENSHOTS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("screenlog.main")


def run_cycle() -> bool:
    """1サイクルを実行。成功時 True。例外は捕捉してログのみ。"""
    from capture import capture_screenshot, capture_error_hint
    from analyzer import analyze_screenshot
    from redaction import redact
    from sheets_store import append_row, build_record
    from gmail_notifier import send_notification

    try:
        image_bytes, saved_path = capture_screenshot()
    except Exception as e:  # noqa: BLE001
        log.error("キャプチャ失敗: %s", e)
        log.error("ヒント: %s", capture_error_hint())
        return False

    try:
        analysis = analyze_screenshot(image_bytes, interval_min=CAPTURE_INTERVAL_MINUTES)
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
    )

    try:
        append_row(record)
    except Exception as e:  # noqa: BLE001
        log.error("Sheets追記失敗: %s", e)
        return False

    # 確信度が低い場合は確認依頼を通知
    if record["confidence"] < CONFIDENCE_THRESHOLD:
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

    if args.once:
        ok = run_cycle()
        return 0 if ok else 1

    log.info("ループ開始（%d分間隔）。Ctrl+Cで停止。", CAPTURE_INTERVAL_MINUTES)
    try:
        while True:
            run_cycle()
            time.sleep(CAPTURE_INTERVAL_MINUTES * 60)
    except KeyboardInterrupt:
        log.info("停止しました")
        return 0


if __name__ == "__main__":
    sys.exit(main())
