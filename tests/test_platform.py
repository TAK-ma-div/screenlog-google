"""OS別キャプチャヒントを検証する。"""
import capture


def test_hint_macos(monkeypatch):
    monkeypatch.setattr(capture.sys, "platform", "darwin")
    hint = capture.capture_error_hint()
    assert "画面収録" in hint


def test_hint_windows(monkeypatch):
    monkeypatch.setattr(capture.sys, "platform", "win32")
    hint = capture.capture_error_hint()
    assert "USE_DUMMY_CAPTURE" in hint


def test_hint_linux(monkeypatch):
    monkeypatch.setattr(capture.sys, "platform", "linux")
    hint = capture.capture_error_hint()
    assert "USE_DUMMY_CAPTURE" in hint
    assert hint  # 非空
