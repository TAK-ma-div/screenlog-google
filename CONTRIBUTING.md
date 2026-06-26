# コントリビューションガイド (CONTRIBUTING)

screenlog-google への貢献を歓迎します。

## 開発環境

```bash
# venv 作成（Windows は .venv\Scripts\python.exe）
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

サンドボックス（実画面・実Google認証なし）でテストできます:

```bash
USE_DUMMY_CAPTURE=true GOOGLE_STUB=true ./.venv/bin/python -m pytest -q
```

## 進め方

1. Issue で提案・バグを共有してから着手すると無駄が減ります。
2. ブランチを切って変更し、**テストを追加/更新**してください。
3. `pytest` がすべて通ることを確認してから Pull Request を作成してください。
4. PR テンプレートのチェック項目に従ってください。

## コーディング方針

- 既存のモジュール境界（`capture` / `analyzer` / `redaction` / `sheets_store` / `gmail_notifier` / `docs_writer` など）を尊重し、1ファイル1責務を保つ。
- 外部I/O（Gemini / Google API）に依存する処理は、スタブ（`stubs.py`）やモンキーパッチでテスト可能にする。
- 純粋ロジック（集計・正規表現・整形）は副作用と分離し、ユニットテストを書く。
- 秘密情報を**絶対にログ出力・コミットしない**。

## ライセンスと DCO

- 本プロジェクトは **Apache License 2.0** です。貢献は同ライセンスの下で提供されたものとみなされます。
- コミットには `Signed-off-by`（`git commit -s`）を付けて、[Developer Certificate of Origin](https://developercertificate.org/) に同意したことを示してください。

## 行動規範

敬意ある建設的なやり取りをお願いします。ハラスメント等は許容されません。
