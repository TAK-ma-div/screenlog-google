"""Gemini Vision API による画面内容の分析（Google専用版）。

AI_PROVIDER:
  - "gemini"      : Gemini API（APIキー課金）
  - "gemini_cli"  : gemini CLI 経由（OAuthログイン枠を使用）
window_data があればプロンプトに含め分析精度を上げる（MVPでは既定 None）。
"""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from config import AI_PROVIDER, CATEGORIES, GEMINI_API_KEY, GEMINI_MODEL

_BASE_PROMPT = """
あなたはPC画面の業務分析アシスタントです。
スクリーンショット{window_context}を見て、以下のJSONのみを返してください（前後の説明文は不要）。

{{
  "summary": "[プロジェクト名] 現在の業務内容の要約（日本語）。プロジェクト名は内容から推論し、不明なら省略可。",
  "category": "{categories} のいずれか1つ",
  "confidence": 確信度を表す0〜100の整数,
  "visual_observations": {{
    "primary_screen": "画面上で最も目立つ作業対象",
    "visible_output": "画面上に見える成果物。例: スライド、文書、コード、表、チャット回答、なし",
    "focus_risk": "集中を妨げている可能性のある状態。特になし も可",
    "non_productive_signal": "無駄・非生産の可能性。特になし も可"
  }},
  "sensitive_regions": [
    {{"x_pct": 左端X(0〜100), "y_pct": 上端Y(0〜100), "w_pct": 幅(0〜100), "h_pct": 高さ(0〜100)}}
  ]
}}

sensitive_regions: API キー / パスワード / トークン / 秘密鍵 / sk- / AIzaSy などの認証情報や
個人情報が表示されている行・領域をすべて列挙。座標は画像全体に対する割合（%）。
該当がなければ空リスト []。
重要: パスワード・個人情報・機密情報は summary 等に絶対に出力しないこと。
"""


def _build_prompt(window_data: dict | None, interval_min: int) -> str:
    # MVP: window_data は未使用（将来 window_tracker 連携で拡張）
    return _BASE_PROMPT.format(window_context="", categories="|".join(CATEGORIES))


def analyze_screenshot(
    image_bytes: bytes,
    window_data: dict | None = None,
    interval_min: int = 5,
) -> dict:
    """画像バイト列を Gemini に送り、構造化された分析結果を返す。"""
    prompt = _build_prompt(window_data, interval_min)
    if AI_PROVIDER in ("gemini_cli", "gemini-cli"):
        return _analyze_with_gemini_cli(image_bytes, prompt)
    return _analyze_with_gemini(image_bytes, prompt)


def generate_text(prompt: str) -> str:
    """Gemini にテキストプロンプトを送り、生成テキストを返す（週次レポート要約用）。"""
    if AI_PROVIDER in ("gemini_cli", "gemini-cli"):
        return _generate_text_with_gemini_cli(prompt)
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model=GEMINI_MODEL, contents=[prompt])
    return (response.text or "").strip()


def _generate_text_with_gemini_cli(prompt: str) -> str:
    timeout = int(os.getenv("GEMINI_CLI_TIMEOUT_SECONDS", "120"))
    tmpdir = Path(tempfile.mkdtemp(prefix="slg_txt_"))
    prompt_path = tmpdir / "instructions.txt"
    try:
        prompt_path.write_text(prompt, encoding="utf-8")
        ref = f"@{prompt_path} の指示に従って回答する"
        cmd = ["gemini", "--skip-trust", "--prompt", ref, "--output-format", "text"]
        result = subprocess.run(
            subprocess.list2cmdline(cmd) if os.name == "nt" else cmd,
            capture_output=True,
            shell=(os.name == "nt"),
            timeout=timeout,
            cwd=str(tmpdir),
        )
        return (result.stdout or b"").decode("utf-8", errors="replace").strip()
    finally:
        try:
            prompt_path.unlink(missing_ok=True)
            tmpdir.rmdir()
        except OSError:
            pass


def _parse_json(text: str) -> dict:
    """CLI/SDK 出力から JSON を頑健に取り出す。

    ```json ブロック → 最初の { から最後の } までの抽出、の順で試す。
    """
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        text = match.group(1)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _analyze_with_gemini(image_bytes: bytes, prompt: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt,
        ],
    )
    return _parse_json(response.text)


def _analyze_with_gemini_cli(image_bytes: bytes, prompt: str) -> dict:
    """gemini CLI 経由で解析（API キー課金を回避、OAuthログイン枠を使用）。"""
    timeout = int(os.getenv("GEMINI_CLI_TIMEOUT_SECONDS", "120"))
    tmpdir = Path(tempfile.mkdtemp(prefix="slg_cli_"))
    img_path = tmpdir / "screenshot.jpg"
    prompt_path = tmpdir / "instructions.txt"
    try:
        img_path.write_bytes(image_bytes)
        prompt_path.write_text(prompt, encoding="utf-8")
        ref = (
            f"@{img_path} 上のスクリーンショットを、次の指示に厳密に従って"
            f"分析してJSONのみ返す: @{prompt_path}"
        )
        cmd = ["gemini", "--skip-trust", "--prompt", ref, "--output-format", "text"]
        result = subprocess.run(
            subprocess.list2cmdline(cmd) if os.name == "nt" else cmd,
            capture_output=True,
            shell=(os.name == "nt"),
            timeout=timeout,
            cwd=str(tmpdir),
        )
        stdout = (result.stdout or b"").decode("utf-8", errors="replace")
        if result.returncode != 0 and not stdout.strip():
            stderr = (result.stderr or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"gemini CLI failed (rc={result.returncode}): {stderr[:300]}")
        return _parse_json(stdout)
    finally:
        try:
            img_path.unlink(missing_ok=True)
            prompt_path.unlink(missing_ok=True)
            tmpdir.rmdir()
        except OSError:
            pass
