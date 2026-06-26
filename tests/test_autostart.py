"""autostart のOS別生成・install/uninstall を検証する。"""
import autostart


def test_describe_windows(monkeypatch):
    monkeypatch.setattr(autostart.sys, "platform", "win32")
    d = autostart.describe()
    assert d["platform"] == "windows"
    assert str(d["target"]).endswith("screenlog.vbs")
    assert "main.py" in d["content"]


def test_describe_macos(monkeypatch):
    monkeypatch.setattr(autostart.sys, "platform", "darwin")
    d = autostart.describe()
    assert d["platform"] == "macos"
    assert str(d["target"]).endswith(".plist")
    assert "RunAtLoad" in d["content"]


def test_describe_linux(monkeypatch):
    monkeypatch.setattr(autostart.sys, "platform", "linux")
    d = autostart.describe()
    assert d["platform"] == "linux"
    assert str(d["target"]).endswith("screenlog.desktop")
    assert "[Desktop Entry]" in d["content"]


def test_install_and_uninstall(monkeypatch, tmp_path):
    target = tmp_path / "auto" / "screenlog.desktop"
    monkeypatch.setattr(
        autostart, "describe",
        lambda: {"platform": "linux", "target": target, "content": "X-content"},
    )

    written = autostart.install()
    assert written == target
    assert target.read_text(encoding="utf-8") == "X-content"
    assert autostart.status()["installed"] is True

    assert autostart.uninstall() is True
    assert not target.exists()
    assert autostart.uninstall() is False  # 既に無い
