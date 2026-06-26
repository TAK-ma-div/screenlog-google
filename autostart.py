"""ログイン時の自動起動を設定する（OS別）。

  python autostart.py status      # 現在の状態を表示
  python autostart.py print       # 書き込む内容/パスを表示（書き込まない）
  python autostart.py install     # 自動起動を登録
  python autostart.py uninstall   # 自動起動を解除

OS別:
  Windows : スタートアップフォルダに .vbs（コンソール無しで起動）
  macOS   : ~/Library/LaunchAgents/<label>.plist（launchd）
  Linux   : ~/.config/autostart/<name>.desktop（XDG autostart）
"""
import argparse
import sys
from pathlib import Path

APP_LABEL = "com.screenlog.agent"
APP_NAME = "screenlog"
BASE_DIR = Path(__file__).resolve().parent
MAIN_SCRIPT = BASE_DIR / "main.py"


def run_command() -> list[str]:
    """ループ起動コマンド（python main.py）。"""
    return [sys.executable, str(MAIN_SCRIPT)]


def _windows_target() -> Path:
    startup = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
    return startup / f"{APP_NAME}.vbs"


def _windows_content() -> str:
    exe, script = run_command()
    # pythonw 相当でコンソールを出さずに起動
    pyw = exe.replace("python.exe", "pythonw.exe")
    return (
        'Set s = CreateObject("Wscript.Shell")\n'
        f's.CurrentDirectory = "{BASE_DIR}"\n'
        f's.Run """{pyw}"" ""{script}""", 0, False\n'
    )


def _macos_target() -> Path:
    return Path.home() / "Library/LaunchAgents" / f"{APP_LABEL}.plist"


def _macos_content() -> str:
    exe, script = run_command()
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f"  <key>Label</key><string>{APP_LABEL}</string>\n"
        "  <key>ProgramArguments</key>\n"
        f"  <array><string>{exe}</string><string>{script}</string></array>\n"
        f"  <key>WorkingDirectory</key><string>{BASE_DIR}</string>\n"
        "  <key>RunAtLoad</key><true/>\n"
        "</dict></plist>\n"
    )


def _linux_target() -> Path:
    return Path.home() / ".config/autostart" / f"{APP_NAME}.desktop"


def _linux_content() -> str:
    exe, script = run_command()
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=ScreenLog\n"
        f"Exec={exe} {script}\n"
        f"Path={BASE_DIR}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Terminal=false\n"
    )


def describe() -> dict:
    """書き込み先パスと内容を返す（書き込みはしない）。テスト・確認用。"""
    if sys.platform.startswith("win"):
        platform, target, content = "windows", _windows_target(), _windows_content()
    elif sys.platform == "darwin":
        platform, target, content = "macos", _macos_target(), _macos_content()
    else:
        platform, target, content = "linux", _linux_target(), _linux_content()
    return {"platform": platform, "target": target, "content": content}


def status() -> dict:
    info = describe()
    info["installed"] = info["target"].exists()
    return info


def install() -> Path:
    info = describe()
    target: Path = info["target"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(info["content"], encoding="utf-8")
    return target


def uninstall() -> bool:
    target: Path = describe()["target"]
    if target.exists():
        target.unlink()
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="ScreenLog 自動起動の設定")
    parser.add_argument(
        "action", choices=["status", "print", "install", "uninstall"], default="status",
        nargs="?",
    )
    args = parser.parse_args()

    if args.action == "status":
        s = status()
        print(f"OS: {s['platform']}")
        print(f"対象: {s['target']}")
        print(f"登録済み: {'はい' if s['installed'] else 'いいえ'}")
    elif args.action == "print":
        d = describe()
        print(f"# OS: {d['platform']}")
        print(f"# 書き込み先: {d['target']}")
        print(d["content"])
    elif args.action == "install":
        path = install()
        print(f"自動起動を登録しました: {path}")
    elif args.action == "uninstall":
        ok = uninstall()
        print("自動起動を解除しました" if ok else "登録は見つかりませんでした")
    return 0


if __name__ == "__main__":
    sys.exit(main())
