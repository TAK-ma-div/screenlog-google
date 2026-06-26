"""setup_web.PAGE に埋め込んだ JavaScript が壊れていないことを検証する。

過去、PAGE を非raw文字列にしていたため `\\'` や `\\n` が Python に消費され、
ブラウザに渡る JS が SyntaxError になりページ全体が動かない不具合があった。
その再発を防ぐ。
"""
import re
import shutil
import subprocess

import pytest

import setup_web


def _extract_script() -> str:
    m = re.search(r"<script>(.*?)</script>", setup_web.PAGE, re.S)
    assert m, "PAGE に <script> が見つからない"
    return m.group(1)


def test_page_is_raw_string_behavior():
    """raw文字列なら JS の `\\n` はバックスラッシュ+n のまま届く。

    非rawに戻すと実改行になり JS文字列リテラルが壊れるため、これを検出する。
    """
    script = _extract_script()
    assert r"join('\n')" in script, "join('\\n') が壊れている（PAGE が raw 文字列でない可能性）"


def test_no_broken_inline_onclick_with_path():
    """パスを onclick 文字列に直接埋め込む壊れやすいパターンを禁止。"""
    script = _extract_script()
    assert 'onclick="browseTo(' not in script, "壊れやすい inline onclick が復活している"
    assert 'data-path="' in script, "フォルダ参照は data-path + イベント委譲で実装すること"


def test_no_adjacent_empty_string_literals():
    """`''` の連続（mangledエスケープの痕跡）が無いこと。"""
    script = _extract_script()
    assert "browseTo(''" not in script


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不在のためスキップ")
def test_script_parses_with_node(tmp_path):
    """node があれば実際に構文解析して SyntaxError を検出する。"""
    js = tmp_path / "page.js"
    js.write_text(_extract_script(), encoding="utf-8")
    result = subprocess.run(
        ["node", "--check", str(js)], capture_output=True, text=True
    )
    assert result.returncode == 0, f"埋め込みJSが構文エラー:\n{result.stderr}"
