# screenlog-google

![CI](https://github.com/TAK-ma-div/screenlog-google/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)

**自分のPC画面を定期的にキャプチャし、Google Gemini で分析して、自分の Google アカウント（Sheets / Docs / Gmail）に記録する**オープンソースの作業ログツール。外部依存は Google サービスのみ。Windows / macOS / Linux 対応。

```
capture（実機:mss / サンドボックス:ダミー画像）
  → Gemini分析
  → 機密領域をマスク（黒塗り＋余白／保存画像のみ）
  → Google Sheets に1行追記
  → confidence < しきい値 で Gmail 通知
```

| 役割 | サービス |
|---|---|
| AI分析 | Gemini API（または gemini CLI） |
| ログ保存 | Google Sheets |
| レポート | Google Docs |
| 通知 | Gmail |

> ## ⚠️ 使う前に必ずお読みください
>
> - これは**画面を撮影して Google Gemini に送る**ツールです。データの流れと取り扱いは **[PRIVACY.md](PRIVACY.md)** を必ず確認してください。
> - **自分が所有・管理する端末でのみ使用してください。** 他者の監視目的での使用は法的問題（プライバシー権・労働法等）を生じ得ます。共用/業務端末では対象者・管理者の同意を得てください。
> - 機密情報マスクは **AI/OCRによるベストエフォート**であり、**取りこぼす可能性があります**。完全な秘匿は保証しません。
> - 本ソフトは無保証（AS IS）で提供されます（[LICENSE](LICENSE)）。

## 対応OS

**Windows / macOS / Linux** で同じコードが動きます。キャプチャは `mss`、それ以外（Gemini / Sheets / Gmail / Docs / セットアップ画面）は Google API と Python 標準ライブラリのみで、OS非依存です。

| 機能 | Windows | macOS | Linux | 備考 |
|---|:---:|:---:|:---:|---|
| 画面キャプチャ（`mss`） | ✅ | ✅ | ✅ | macOSは「画面収録」許可が必要（下記） |
| Gemini分析 / Sheets / Gmail / Docs | ✅ | ✅ | ✅ | Google API・OS非依存 |
| セットアップWebウィザード | ✅ | ✅ | ✅ | 標準ライブラリのみ |
| ダミー＋スタブ（ヘッドレス/CI） | ✅ | ✅ | ✅ | `USE_DUMMY_CAPTURE`＋`GOOGLE_STUB` |

### macOS で使うときの注意

- **画面収録の許可が必須**: 初回キャプチャ前に「システム設定 → プライバシーとセキュリティ → 画面収録」で、実行するアプリ（ターミナル / iTerm / Python など）にチェックを入れてください。**許可がないと画面が真っ黒・デスクトップのみになり中身が映りません。** 許可後はアプリの再起動が必要な場合があります。
- 失敗時はアプリが対処法を表示します（`capture.capture_error_hint()` がOS別に案内）。

### コマンドのOS差

venv の Python のパスがOSで異なります。本READMEのコマンド例は **Windows と macOS/Linux を併記**しています。

| | Windows (PowerShell) | macOS / Linux |
|---|---|---|
| venv作成 | `python -m venv .venv` | `python3 -m venv .venv` |
| Python実行 | `.\.venv\Scripts\python.exe` | `./.venv/bin/python` |

## かんたんセットアップ（推奨）

依存をインストールしたら、**ブラウザのセットアップ画面**で数項目入力するだけで使い始められます。

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup_web.py
```

```bash
# macOS / Linux
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python setup_web.py
```

ブラウザで `http://localhost:8765` が自動で開き、上から順に:

1. **基本情報を入力** — Gemini APIキー（[取得](https://aistudio.google.com/app/apikey)）、通知メール宛先（任意）→「保存」
2. **OAuthクライアント** — `credentials.json` が無ければ作成手順を画面に表示。配置後「再チェック」
3. **Google認証** — ボタンを押すとブラウザで許可 → `token.json` 生成
4. **スプレッドシート作成** — ボタン一発で記録用シートを自動作成

「✅ 準備完了」が出たら `python main.py --once` で記録開始。

> `credentials.json`（手順2）だけは Google Cloud Console での手動作成が必要です（OAuthの仕様上、自動化できません）。画面の番号付き手順に従ってください。
> `credentials.json` / `token.json` / `.env` は **gitignore** 済み。リポジトリにコミットしないこと。

## 手動セットアップ（上級者向け）

ウィザードを使わない場合:

```powershell
# Windows (PowerShell)
copy .env.example .env   # GEMINI_API_KEY などを編集
# credentials.json を配置後:
.\.venv\Scripts\python.exe setup_sheet.py   # 表示された SHEET_ID を .env に設定
```

```bash
# macOS / Linux
cp .env.example .env      # GEMINI_API_KEY などを編集
# credentials.json を配置後:
./.venv/bin/python setup_sheet.py   # 表示された SHEET_ID を .env に設定
```

| 変数 | 説明 | 取得先 |
|---|---|---|
| `GEMINI_API_KEY` | Gemini APIキー | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `SHEET_ID` | ログ保存先スプレッドシートID | `setup_sheet.py` 実行後に表示 |
| `GMAIL_TO` | 通知メール宛先（空なら自分宛） | 任意 |

OAuthスコープ: `spreadsheets` / `gmail.send` / `documents`。

## 実行

```powershell
# Windows (PowerShell)
.\.venv\Scripts\python.exe main.py --once   # 1サイクルだけ
.\.venv\Scripts\python.exe main.py          # CAPTURE_INTERVAL_MINUTES 間隔でループ
```

```bash
# macOS / Linux
./.venv/bin/python main.py --once   # 1サイクルだけ
./.venv/bin/python main.py          # CAPTURE_INTERVAL_MINUTES 間隔でループ
```

## サンドボックス / CI（実認証なし）

実画面・実Google認証なしで動作確認・テストできる:

```powershell
# Windows (PowerShell)
$env:USE_DUMMY_CAPTURE="true"; $env:GOOGLE_STUB="true"
.\.venv\Scripts\python.exe -m pytest -q
```

```bash
# macOS / Linux
USE_DUMMY_CAPTURE=true GOOGLE_STUB=true ./.venv/bin/python -m pytest -q
```

- `USE_DUMMY_CAPTURE=true` … 合成スクショ（`dummy_capture.py`）を使用
- `GOOGLE_STUB=true` … Google API を呼ばずスタブ動作（`stubs.py`）
- ヘッドレス環境（CI・Docker・SSH）では実画面を撮れないため、この2つを有効にして検証する。テストは全OSで同一。

## 機密情報マスク（精度強化）

保存するスクリーンショットからAPIキー・パスワード・トークン等を**2層**で検出し、**黒塗り＋余白**でマスクします（復元不可）。

1. **Gemini層** — 画面全体の見た目から機密領域を推論（座標は概略）
2. **OCR＋正規表現層** — 文字の**正確な位置**を取得し、`AIzaSy…` `sk-…` `password=…` `-----BEGIN…PRIVATE KEY` JWT 等を確実に検出

2層の領域を統合し、周囲に余白（既定1.5%）を足して取りこぼしを防ぎます。マスクは黒塗り（`MASK_STYLE=fill`、既定）かぼかし（`blur`）を選択可能。

### OCR層を有効にする（任意・精度大幅向上）

OCRはオプション依存です。**未導入でも Gemini＋正規表現＋黒塗りで動作**し、導入すると検出精度が大きく上がります。pipのみ・全OS対応・システムバイナリ不要です。

```powershell
# Windows
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
```
```bash
# macOS / Linux
./.venv/bin/python -m pip install -r requirements-ocr.txt
```

関連設定（`.env`）: `USE_OCR_REDACTION`（既定true） / `REDACTION_PAD_PCT`（余白%） / `MASK_STYLE`（fill|blur）。

> 画像は分析のため Gemini にのみ送信されます。Sheets/Gmail には画像を送りません。ローカル保存画像にはマスクが適用されます。

## 構成

| ファイル | 役割 |
|---|---|
| `config.py` | 環境変数設定 |
| `capture.py` | キャプチャ（mss） |
| `redaction.py` | 機密マスク（OCR＋正規表現検出・黒塗り） |
| `dummy_capture.py` | サンドボックス用合成画像 |
| `analyzer.py` | Gemini Vision 分析 |
| `google_auth.py` | OAuth・Sheets/Gmailクライアント生成 |
| `sheets_store.py` | Sheets 追記 |
| `gmail_notifier.py` | Gmail 通知 |
| `docs_writer.py` | Google Docs レポート作成 |
| `report_reader.py` | Sheets読込＋週次集計 |
| `weekly_report.py` | 週次レポート生成 |
| `main.py` | コアループ |
| `setup_sheet.py` | スプレッドシート初期作成 |
| `setup_web.py` | ローカルWebセットアップウィザード |
| `wizard.py` | セットアップロジック |
| `env_file.py` | `.env` 読み書き |
| `stubs.py` | スタブクライアント（dev/test用） |
| `tests/` | pytest |

## MVP外（フォローアップ候補）

- ~~週次レポート（Google Docs 出力）~~ → 実装済み（`weekly_report.py`）
- `window_tracker`（アプリ別の実測使用時間でAI分析の精度を上げる機能）
- プロジェクト学習・分類自動化・ダッシュボード

### `window_tracker` を入れる場合のOS依存に注意

現状のコアループは全OS共通コードですが、`window_tracker`（前面ウィンドウ名やアプリ別の使用時間を取得する機能）**だけはOSごとに実装が分かれます**。移植する場合は、OSを判定して実装を切り替える抽象化レイヤー（例: `WindowTracker` インターフェース＋OS別バックエンド）が必要です。

| OS | 取得方法（例） | 追加依存 |
|---|---|---|
| Windows | `pywin32`（GetForegroundWindow 等）＋ `psutil` | `pywin32`, `psutil` |
| macOS | Quartz / AppleScript（`pyobjc`）。アクセシビリティ許可が必要 | `pyobjc` |
| Linux | X11（`wmctrl`/`xdotool`）。Wayland は取得制限あり | 環境依存 |

このため `window_tracker` は「全OSで同じコード」では実現できず、OS別バックエンドの追加が前提になります。導入しない限り、本アプリは全OSで単一コードのまま動きます。

## コントリビューション

歓迎します。開発手順・方針は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。バグ・要望は Issue へ、セキュリティ問題は [SECURITY.md](SECURITY.md) の手順で非公開報告をお願いします。

## プライバシー

データの流れ・同意・マスクの限界については [PRIVACY.md](PRIVACY.md) を参照してください。

## ライセンス

[Apache License 2.0](LICENSE)。著作権表示は [NOTICE](NOTICE) を参照。
