"""`.env` ファイルの読み書きユーティリティ。

既存のキー/コメント/空行を保持したまま、指定キーだけを更新する。
"""
from pathlib import Path


def read_env(path: Path) -> dict[str, str]:
    """`.env` を読み、KEY=VALUE の dict を返す。無ければ空dict。"""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        result[key.strip()] = value.strip()
    return result


def update_env(path: Path, values: dict[str, str]) -> None:
    """`.env` の指定キーを更新（既存行は値だけ差し替え、無いキーは末尾に追記）。

    他の行（コメント・空行・未指定キー）はそのまま保持する。
    """
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    remaining = dict(values)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}")
                continue
        out.append(line)

    # 未反映（既存に無かった）キーを追記
    for key, value in remaining.items():
        out.append(f"{key}={value}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
