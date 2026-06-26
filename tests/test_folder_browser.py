"""wizard.list_dirs（フォルダ参照）を検証する。"""
import wizard


def test_lists_subdirs(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "file.txt").write_text("x", encoding="utf-8")

    result = wizard.list_dirs(str(tmp_path))

    names = [d["name"] for d in result["dirs"]]
    assert names == ["a", "b"]  # 隠しフォルダ/ファイルは除外・名前順
    assert result["path"] == str(tmp_path.resolve())
    assert result["parent"] == str(tmp_path.resolve().parent)


def test_each_dir_has_full_path(tmp_path):
    (tmp_path / "sub").mkdir()
    result = wizard.list_dirs(str(tmp_path))
    assert result["dirs"][0]["path"] == str((tmp_path / "sub").resolve())


def test_missing_path_falls_back_to_home(tmp_path):
    result = wizard.list_dirs(str(tmp_path / "does-not-exist"))
    from pathlib import Path

    assert result["path"] == str(Path.home().resolve())


def test_none_path_uses_home():
    result = wizard.list_dirs(None)
    from pathlib import Path

    assert result["path"] == str(Path.home().resolve())


def test_shortcuts_present():
    result = wizard.list_dirs(None)
    labels = [s["label"] for s in result["shortcuts"]]
    assert "ホーム" in labels
    # 各ショートカットは存在するパスのみ
    from pathlib import Path

    for s in result["shortcuts"]:
        assert Path(s["path"]).exists()
