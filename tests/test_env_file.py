"""env_file の読み書きを検証する。"""
from env_file import read_env, update_env


def test_update_preserves_other_lines(tmp_path):
    p = tmp_path / ".env"
    p.write_text(
        "# comment\nGEMINI_API_KEY=old\n\nSHEET_TAB=log\n", encoding="utf-8"
    )

    update_env(p, {"GEMINI_API_KEY": "new", "SHEET_ID": "abc123"})

    text = p.read_text(encoding="utf-8")
    assert "# comment" in text  # コメント保持
    assert "SHEET_TAB=log" in text  # 未指定キー保持
    env = read_env(p)
    assert env["GEMINI_API_KEY"] == "new"  # 既存キー更新
    assert env["SHEET_ID"] == "abc123"  # 新規キー追記


def test_read_env_missing_file(tmp_path):
    assert read_env(tmp_path / "nope.env") == {}


def test_update_creates_file(tmp_path):
    p = tmp_path / ".env"
    update_env(p, {"SHEET_ID": "x"})
    assert read_env(p) == {"SHEET_ID": "x"}


def test_read_env_ignores_comments_and_blanks(tmp_path):
    p = tmp_path / ".env"
    p.write_text("#c\n\nA=1\nB = 2\n", encoding="utf-8")
    env = read_env(p)
    assert env == {"A": "1", "B": "2"}
