"""指数バックオフによるAPI再試行ヘルパー。

一時的な失敗（レート制限・ネットワーク断）に備え、関数呼び出しをリトライする。
テスト容易性のため sleep を差し替え可能にしている。
"""
import logging
import random
import time
from typing import Callable, TypeVar

from config import API_RETRY_ATTEMPTS, API_RETRY_BASE_DELAY

log = logging.getLogger("screenlog.retry")

T = TypeVar("T")


def retry_call(
    func: Callable[[], T],
    *,
    attempts: int | None = None,
    base_delay: float | None = None,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
    label: str = "",
) -> T:
    """func() を最大 attempts 回試す。失敗ごとに base_delay*2^(n-1) + ジッタ秒待つ。

    最終試行も失敗したら最後の例外を再送出する。
    """
    attempts = API_RETRY_ATTEMPTS if attempts is None else attempts
    base_delay = API_RETRY_BASE_DELAY if base_delay is None else base_delay
    attempts = max(1, attempts)

    last_exc: BaseException | None = None
    for i in range(1, attempts + 1):
        try:
            return func()
        except exceptions as e:
            last_exc = e
            if i >= attempts:
                break
            delay = base_delay * (2 ** (i - 1)) + random.uniform(0, base_delay * 0.1)
            log.warning(
                "再試行 %d/%d%s: %s（%.1f秒待機）",
                i,
                attempts,
                f" [{label}]" if label else "",
                e,
                delay,
            )
            sleep(delay)
    assert last_exc is not None
    raise last_exc
