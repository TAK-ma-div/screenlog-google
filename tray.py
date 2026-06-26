"""システムトレイ常駐（任意）。

  python tray.py

トレイアイコンから 一時停止/再開/今すぐ実行/終了 を操作できる。
任意依存 pystray（+Pillow）が必要。未導入時は案内して終了する。
バックグラウンドスレッドでコアループを回し、UIスレッドでアイコンを表示する。
"""
import logging
import threading
import time

from config import CAPTURE_INTERVAL_MINUTES
from logging_setup import setup_logging

log = logging.getLogger("screenlog.tray")


class LoopController:
    """コアループの実行・一時停止・停止を制御する。"""

    def __init__(self, interval_min: int = CAPTURE_INTERVAL_MINUTES):
        self.interval_sec = interval_min * 60
        self._paused = threading.Event()
        self._stop = threading.Event()
        self._wake = threading.Event()

    def run(self) -> None:
        from main import run_cycle
        from retention import cleanup_old_screenshots
        from config import SCREENSHOT_DIR, SCREENSHOT_RETENTION_DAYS

        while not self._stop.is_set():
            if not self._paused.is_set():
                try:
                    run_cycle()
                    cleanup_old_screenshots(SCREENSHOT_DIR, SCREENSHOT_RETENTION_DAYS)
                except Exception as e:  # noqa: BLE001
                    log.warning("サイクルでエラー: %s", e)
            # 次サイクルまで待機（途中で wake されたら即起床）
            self._wake.wait(timeout=self.interval_sec)
            self._wake.clear()

    def toggle_pause(self) -> None:
        if self._paused.is_set():
            self._paused.clear()
            log.info("再開しました")
        else:
            self._paused.set()
            log.info("一時停止しました")

    def is_paused(self) -> bool:
        return self._paused.is_set()

    def run_now(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()


def _make_icon_image():
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (64, 64), (37, 99, 235))
    d = ImageDraw.Draw(img)
    d.rectangle((16, 16, 48, 48), outline=(255, 255, 255), width=4)
    return img


def main() -> int:
    setup_logging()
    try:
        import pystray
    except Exception:
        print(
            "トレイ常駐には pystray が必要です。\n"
            "  pip install -r requirements-tray.txt\n"
            "（未導入のままなら python main.py で通常実行できます）"
        )
        return 1

    controller = LoopController()
    worker = threading.Thread(target=controller.run, daemon=True)
    worker.start()

    def on_toggle(icon, item):
        controller.toggle_pause()

    def on_run_now(icon, item):
        controller.run_now()

    def on_quit(icon, item):
        controller.stop()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: "再開" if controller.is_paused() else "一時停止", on_toggle
        ),
        pystray.MenuItem("今すぐ実行", on_run_now),
        pystray.MenuItem("終了", on_quit),
    )
    icon = pystray.Icon("screenlog", _make_icon_image(), "ScreenLog", menu)
    log.info("トレイ常駐を開始しました")
    icon.run()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
