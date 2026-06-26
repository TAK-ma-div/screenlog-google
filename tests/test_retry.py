"""retry_call（指数バックオフ再試行）を検証する。"""
import pytest

from retry import retry_call


def test_succeeds_first_try():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        return "ok"

    assert retry_call(fn, sleep=lambda s: None) == "ok"
    assert calls["n"] == 1


def test_succeeds_after_failures():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    result = retry_call(fn, attempts=3, base_delay=0, sleep=lambda s: None)
    assert result == "ok"
    assert calls["n"] == 3


def test_raises_after_exhausting():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise RuntimeError("always")

    with pytest.raises(RuntimeError, match="always"):
        retry_call(fn, attempts=3, base_delay=0, sleep=lambda s: None)
    assert calls["n"] == 3


def test_only_retries_listed_exceptions():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise KeyError("not retried")

    with pytest.raises(KeyError):
        retry_call(fn, attempts=3, base_delay=0, exceptions=(ValueError,), sleep=lambda s: None)
    assert calls["n"] == 1  # KeyError は対象外なので即時送出


def test_records_sleep_delays():
    delays = []

    def fn():
        raise ValueError("x")

    with pytest.raises(ValueError):
        retry_call(fn, attempts=3, base_delay=1, sleep=delays.append)
    # 2回待機（1回目失敗後、2回目失敗後）。指数的に増える
    assert len(delays) == 2
    assert delays[1] > delays[0]
