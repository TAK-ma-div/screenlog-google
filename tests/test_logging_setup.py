"""logging_setup の冪等性を検証する。"""
import logging

import logging_setup


def test_setup_is_idempotent():
    logging_setup.setup_logging()
    root = logging.getLogger()
    count = len(root.handlers)

    logging_setup.setup_logging()  # 2回目は何も追加しない
    assert len(root.handlers) == count
    assert count >= 1  # 少なくともコンソールハンドラがある
