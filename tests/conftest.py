"""テスト用の環境設定。

config.py がインポートされる前にスタブ/ダミーを有効化する。
pytest は conftest.py を最初に読み込むため、ここで os.environ を設定すれば
各モジュールの import 時にこの値が使われる（load_dotenv は既存env を上書きしない）。
"""
import os
import sys
from pathlib import Path

# アプリのルートを import パスに追加
APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

os.environ.setdefault("GOOGLE_STUB", "true")
os.environ.setdefault("USE_DUMMY_CAPTURE", "true")
os.environ.setdefault("SAVE_SCREENSHOTS", "false")
os.environ.setdefault("SHEET_ID", "test-sheet-id")
os.environ.setdefault("AI_PROVIDER", "gemini")
