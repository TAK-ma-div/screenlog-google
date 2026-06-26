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

[Unreleased]: https://github.com/TAK-ma-div/screenlog-google
