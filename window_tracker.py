"""アクティブウィンドウ/アプリ名を一定間隔でサンプリングし、
分析サイクル中のアプリ別使用時間（実測）を集計する。

クロスプラットフォーム対応（依存ライブラリ追加なし）:
  - Windows: ctypes (user32 / psapi)
  - macOS:   osascript (AppleScript)
  - Linux:   xdotool（任意。無ければスキップ）

プライバシー: 有効化時のみ動作し、ウィンドウタイトル/アプリ名を
analyzer 経由で Gemini に渡す。既定オフ。PRIVACY.md 参照。
"""
from __future__ import annotations

import platform
import subprocess
import threading
import time
from collections import defaultdict

_SYSTEM = platform.system()  # "Windows" / "Darwin" / "Linux"


# --- OS別: 前面ウィンドウの (app_name, window_title) を取得 ---
def _active_window_windows() -> tuple[str, str] | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi

    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value or ""

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    app = ""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if handle:
        try:
            name_buf = ctypes.create_unicode_buffer(260)
            if psapi.GetModuleBaseNameW(handle, None, name_buf, 260):
                app = name_buf.value or ""
        finally:
            kernel32.CloseHandle(handle)
    app = app[:-4] if app.lower().endswith(".exe") else app
    return (app, title)


_MAC_SCRIPT = (
    'tell application "System Events" to set p to name of first process '
    "whose frontmost is true\n"
    'return p'
)


def _active_window_macos() -> tuple[str, str] | None:
    try:
        out = subprocess.run(
            ["osascript", "-e", _MAC_SCRIPT],
            capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    app = (out.stdout or "").strip()
    if not app:
        return None
    return (app, "")


def _active_window_linux() -> tuple[str, str] | None:
    try:
        title = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    name = (title.stdout or "").strip()
    if not name:
        return None
    # xdotool は WM_CLASS をアプリ名の代替に使う
    app = ""
    try:
        cls = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowclassname"],
            capture_output=True, text=True, timeout=3,
        )
        app = (cls.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        app = ""
    return (app or name, name)


def _get_active_window() -> tuple[str, str] | None:
    try:
        if _SYSTEM == "Windows":
            return _active_window_windows()
        if _SYSTEM == "Darwin":
            return _active_window_macos()
        if _SYSTEM == "Linux":
            return _active_window_linux()
    except Exception:
        return None
    return None


def available() -> bool:
    """この環境でウィンドウ取得が機能するか（1回サンプリングして判定）。"""
    return _get_active_window() is not None


class WindowTracker:
    """バックグラウンドスレッドでアクティブアプリを定期サンプリングし、
    アプリ別の累積秒数を集計する。スレッドセーフ。

    使い方:
        t = WindowTracker(poll_interval=30); t.start()
        ... 分析サイクル ...
        breakdown = t.snapshot_and_reset()  # {app: minutes} を返しカウンタをリセット
        t.stop()
    """

    def __init__(self, poll_interval: float = 30.0):
        self.poll_interval = max(1.0, float(poll_interval))
        self._counts: dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            win = _get_active_window()
            if win:
                app = (win[0] or "unknown").strip() or "unknown"
                with self._lock:
                    self._counts[app] += self.poll_interval
            self._stop.wait(self.poll_interval)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="window-tracker", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def snapshot_and_reset(self) -> dict[str, float]:
        """アプリ別の使用「分」を多い順に返し、内部カウンタをリセットする。"""
        with self._lock:
            counts = dict(self._counts)
            self._counts.clear()
        minutes = {
            app: round(sec / 60.0, 1)
            for app, sec in sorted(counts.items(), key=lambda kv: -kv[1])
        }
        return minutes


def format_breakdown(minutes: dict[str, float], top: int = 8) -> str:
    """{app: minutes} を Gemini プロンプト用の1行サマリへ整形する。"""
    if not minutes:
        return ""
    items = list(minutes.items())[:top]
    return ", ".join(f"{app}: {m}分" for app, m in items if m > 0)
