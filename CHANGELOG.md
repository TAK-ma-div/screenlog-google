# Changelog

本プロジェクトの主な変更点を記録します。形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に準拠し、[Semantic Versioning](https://semver.org/lang/ja/) を用います。

## [Unreleased]

初回オープンソース公開に向けた整備。

### Added
- コアループ: 画面キャプチャ → Gemini分析 → Google Sheets記録 → Gmail通知
- 週次レポート生成（Google Docs 出力）
- ローカルWebセットアップウィザード（`setup_web.py`）
- 機密情報マスク（Gemini領域 + OCR/正規表現の2層検出、黒塗り＋余白）
- クロスプラットフォーム対応（Windows / macOS / Linux）
- サンドボックスモード（ダミー画像 + Googleスタブ）でのテスト
- オープンソース公開用ドキュメント一式（LICENSE/NOTICE/PRIVACY/SECURITY/CONTRIBUTING）
- GitHub Actions による CI（Win/Mac/Linux × pytest）
- 運用機能: ファイルログ＋ローテーション（`logging_setup.py`）、API再試行/指数バックオフ
  （`retry.py`）、古いスクショの自動削除（`retention.py`）
- ログイン時自動起動（`autostart.py`、Windows/macOS/Linux）
- システムトレイ常駐（`tray.py`、任意 `pystray`）
- `pyproject.toml` による pip インストールとコマンド（`screenlog` / `screenlog-setup` /
  `screenlog-report` / `screenlog-autostart`）
- ウィンドウ追跡（任意・既定オフ, `window_tracker.py`）: アクティブなアプリ名/ウィンドウ
  タイトルを実測し、アプリ別使用時間を Gemini に渡して分析精度を向上（`ENABLE_WINDOW_TRACKER`）
- セットアップ画面に「カスタマイズ設定（手順5）」と「動作確認とログ（手順6）」を追加:
  フォルダ参照UI・カテゴリのタグUI・記録列選択、Sheets/メール/単発実行のテストボタン、ログ閲覧
- アプリ別使用時間の横棒グラフ（手順6・依存ゼロのCSS描画、`WEEKLY_REPORT_DAYS` 期間で集計）
- `GOOGLE_STUB` 時は analyzer もスタブ応答を返し、実Geminiなしで単発実行を検証可能に
- Vertex AI バックエンド対応（`GEMINI_BACKEND=vertex`）: Google Cloud 上の Gemini を使い、
  送信データを学習に使わせないエンタープライズ利用が可能（ADC認証・要課金）

### Changed
- `LICENSE` の先頭空行を除去（正準 Apache-2.0 テキストにバイト一致）

### Fixed
- セットアップ画面の埋め込み JavaScript が非raw文字列により壊れ、ブラウザで SyntaxError と
  なりページ全体が動作しない不具合を修正（`PAGE` を raw 文字列化、フォルダ参照を
  `data-path`＋イベント委譲へ変更）。再発防止に埋め込みJSの構文テストを追加

[Unreleased]: https://github.com/TAK-ma-div/screenlog-google
