"""window_tracker の集計ロジックとプロンプト連携を検証する（OS非依存）。"""
import analyzer
import window_tracker
from window_tracker import WindowTracker, format_breakdown


def test_snapshot_aggregates_and_resets():
    t = WindowTracker(poll_interval=10)
    # OS依存のサンプリングを使わず、内部カウンタを直接操作して集計を検証
    t._counts["Code"] = 120.0  # 2分
    t._counts["Chrome"] = 30.0  # 0.5分
    snap = t.snapshot_and_reset()
    assert snap == {"Code": 2.0, "Chrome": 0.5}
    # 多い順
    assert list(snap.keys())[0] == "Code"
    # リセットされている
    assert t.snapshot_and_reset() == {}


def test_format_breakdown_human_readable():
    s = format_breakdown({"Code": 12.0, "Slack": 3.0})
    assert "Code: 12.0分" in s
    assert "Slack: 3.0分" in s


def test_format_breakdown_empty():
    assert format_breakdown({}) == ""
    assert format_breakdown(None or {}) == ""


def test_available_returns_bool():
    # 環境により True/False どちらもありうる。例外を投げず bool を返すこと。
    assert isinstance(window_tracker.available(), bool)


def test_prompt_includes_window_data():
    prompt = analyzer._build_prompt({"app_breakdown": {"Code": 15.0}}, 5)
    assert "Code: 15.0分" in prompt
    assert "実測アプリ使用時間" in prompt


def test_prompt_without_window_data_unchanged():
    prompt = analyzer._build_prompt(None, 5)
    assert "実測アプリ使用時間" not in prompt
    # window_section プレースホルダが消費されている（波括弧が残らない）
    assert "{window_section}" not in prompt
