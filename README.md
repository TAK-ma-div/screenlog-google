# screenlog-google

![CI](https://github.com/TAK-ma-div/screenlog-google/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
[![Code of Conduct](https://img.shields.io/badge/code%20of%20conduct-v2.1-ff69b4)](CODE_OF_CONDUCT.md)

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
5. **カスタマイズ設定（任意）** — 保存フォルダ（参照ボタンで選択）、間隔・保持日数、カテゴリ（タグUI）、記録する列、ウィンドウ追跡などを画面から変更
6. **動作確認とログ** — 「Sheets接続テスト」「テストメール送信」「1回だけ記録を実行」ボタンで疎通確認し、最新ログを画面で閲覧

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

## Vertex AI（エンタープライズ／データを学習に使わせない）

既定の **AI Studio（APIキー）** は無料枠がありますが、**無料枠では送信内容がモデル改善に使われ得ます**。画面に機密が映る用途や組織利用では、**Vertex AI** バックエンドを使うと送信データが学習に使われず、リージョン等を統制できます（**Google Cloud の課金が必要**）。

`.env` で切り替えます（`GEMINI_API_KEY` は不要）:

```bash
GEMINI_BACKEND=vertex
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global        # 例: global / us-central1 / asia-northeast1
```

認証は **アプリケーションデフォルト認証情報(ADC)** を使います。事前に一度だけ:

```bash
gcloud auth application-default login
# 対象プロジェクトで Vertex AI API を有効化しておく
gcloud services enable aiplatform.googleapis.com --project your-gcp-project-id
```

> どちらのバックエンドでも `gemini-2.5-flash` 等の `GEMINI_MODEL` がそのまま使えます。
> Sheets / Docs / Gmail 側の OAuth（`credentials.json`）は Vertex 利用時も同じく必要です。

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

## 常駐・自動起動・運用

### pip でインストール（コマンド化）

```bash
pip install .            # この後 screenlog 等のコマンドが使える
screenlog                # コアループ（= main.py）
screenlog-setup          # セットアップ画面（= setup_web.py）
screenlog-report         # 週次レポート（= weekly_report.py）
screenlog-autostart      # 自動起動の設定（= autostart.py）
```

### システムトレイ常駐（任意）

トレイアイコンから「一時停止／再開／今すぐ実行／終了」を操作できます。任意依存 `pystray` が必要です。

```bash
pip install -r requirements-tray.txt
python tray.py
```

### ログイン時に自動起動

OSに応じた自動起動を登録/解除できます（Windows=スタートアップ、macOS=launchd、Linux=XDG autostart）。

```bash
python autostart.py print       # 書き込む内容/場所を確認（変更しない）
python autostart.py install     # 自動起動を登録
python autostart.py status      # 状態確認
python autostart.py uninstall   # 解除
```

### ログ・データ保持・再試行

- **ログ**: コンソールに加え `screenlog.log` に出力（サイズ上限でローテーション）。`LOG_FILE` / `LOG_MAX_BYTES` / `LOG_BACKUP_COUNT` / `LOG_LEVEL` で調整。
- **古いスクショの自動削除**: ループ実行中、`SCREENSHOT_RETENTION_DAYS`（既定14日）を過ぎた `screenshots/YYYYMMDD/` を自動削除。
- **API再試行**: Gemini / Sheets 呼び出しは一時的失敗時に指数バックオフで再試行（`API_RETRY_ATTEMPTS` / `API_RETRY_BASE_DELAY`）。

### カスタマイズ設定（セットアップ画面の手順5）

保存フォルダ・キャプチャ間隔・保持日数・確信度しきい値・通知ON/OFF・**カテゴリ分類（タグUIで追加削除）**・**Sheetsに記録する任意列**を画面から変更でき、すべて `.env` に保存されます。フォルダは「参照…」ボタンのフォルダブラウザで選択できます。

### ウィンドウ追跡で分析精度を上げる（任意・既定オフ）

有効にすると、一定間隔で**アクティブなアプリ名・ウィンドウタイトル**をサンプリングし、その区間のアプリ別使用時間（実測）を Gemini に文脈として渡します。これにより「どのアプリに何分使ったか」が分析へ反映され、要約・カテゴリの精度が上がります。アプリ別内訳は Sheets の任意列 `app_breakdown` にも記録できます。

- 設定画面の「アプリ使用時間を計測して分析精度を上げる」をオン、または `.env` で `ENABLE_WINDOW_TRACKER=true`（間隔は `WINDOW_POLL_INTERVAL_SEC`、既定30秒）。
- 取得はローカルOSのみ（Windows=ctypes / macOS=osascript / Linux=`xdotool` が必要）。Linux で `xdotool` が無い環境では自動でスキップします。
- **ウィンドウタイトルにはファイル名・URL・メール件名などが含まれ、Gemini に送信されます。** 既定オフ。詳細は [PRIVACY.md](PRIVACY.md)。

### 動作確認とログ閲覧（セットアップ画面の手順6）

セットアップ画面から「Sheets接続テスト」「テストメール送信」「1回だけ記録を実行」で疎通を確認でき、`screenlog.log` の最新行を画面上で閲覧できます。

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
| `window_tracker.py` | アクティブアプリ計測（任意・分析精度向上） |
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
| `tray.py` | システムトレイ常駐（任意） |
| `autostart.py` | ログイン時自動起動（OS別） |
| `logging_setup.py` | ログ設定（ローテーション） |
| `retry.py` | API再試行（指数バックオフ） |
| `retention.py` | 古いスクショの自動削除 |
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

歓迎します。開発手順・方針は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。バグ・要望は Issue へ、セキュリティ問題は [SECURITY.md](SECURITY.md) の手順で非公開報告をお願いします。参加にあたっては [行動規範（CODE_OF_CONDUCT.md）](CODE_OF_CONDUCT.md) を守ってください。コミットは `git commit -s`（DCO サインオフ）でお願いします。

## プライバシー

データの流れ・同意・マスクの限界については [PRIVACY.md](PRIVACY.md) を参照してください。

## ライセンス

[Apache License 2.0](LICENSE)。著作権表示は [NOTICE](NOTICE) を参照。
