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

from config import AI_PROVIDER, CATEGORIES, GEMINI_MODEL

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
{window_section}"""


def _build_prompt(window_data: dict | None, interval_min: int) -> str:
    """プロンプトを生成。window_data（アプリ別実測使用時間）があれば文脈として付与。

    window_data 形式: {"app_breakdown": {app: 分, ...}} または {app: 分, ...}
    """
    window_context = ""
    window_section = ""
    breakdown = None
    if window_data:
        breakdown = window_data.get("app_breakdown", window_data)
    if breakdown:
        from window_tracker import format_breakdown

        summary = format_breakdown(breakdown)
        if summary:
            window_context = "と、直近の実測アプリ使用時間"
            window_section = (
                f"\n参考: この区間（約{interval_min}分）の実測アプリ使用時間 → {summary}\n"
                "この実測値を踏まえ、最も時間を割いた作業を summary と category に反映してください。"
            )
    return _BASE_PROMPT.format(
        window_context=window_context,
        categories="|".join(CATEGORIES),
        window_section=window_section,
    )


def _stub_enabled() -> bool:
    return os.getenv("GOOGLE_STUB", "").lower() in {"1", "true", "yes", "on"}


def _make_client():
    """設定に応じて Gemini クライアントを生成する。

    - Vertex AI モード（GEMINI_BACKEND=vertex）: Google Cloud 上の Gemini を使用。
      送信データはモデル学習に使われない（エンタープライズ保護）。認証はアプリ
      ケーションデフォルト認証情報(ADC)＝`gcloud auth application-default login`
      かサービスアカウント。GOOGLE_CLOUD_PROJECT 必須。
    - AI Studio モード（既定）: GEMINI_API_KEY を使用。
    """
    import config  # テストでの monkeypatch を効かせるため属性参照で読む

    if config.USE_VERTEX and not config.GOOGLE_CLOUD_PROJECT:
        raise RuntimeError(
            "GEMINI_BACKEND=vertex には GOOGLE_CLOUD_PROJECT が必要です。"
            ".env に Google Cloud のプロジェクトIDを設定してください。"
        )
    from google import genai

    if config.USE_VERTEX:
        return genai.Client(
            vertexai=True,
            project=config.GOOGLE_CLOUD_PROJECT,
            location=config.GOOGLE_CLOUD_LOCATION,
        )
    return genai.Client(api_key=config.GEMINI_API_KEY)


def analyze_screenshot(
    image_bytes: bytes,
    window_data: dict | None = None,
    interval_min: int = 5,
) -> dict:
    """画像バイト列を Gemini に送り、構造化された分析結果を返す。"""
    prompt = _build_prompt(window_data, interval_min)
    if _stub_enabled():
        # サンドボックス/ドライラン: 実際のGeminiを呼ばずダミー分析を返す
        return {
            "summary": "[サンドボックス] スタブ分析結果（実Geminiは未使用）",
            "category": CATEGORIES[0] if CATEGORIES else "その他",
            "confidence": 90,
            "visual_observations": {
                "primary_screen": "stub", "visible_output": "stub",
                "focus_risk": "特になし", "non_productive_signal": "特になし",
            },
            "sensitive_regions": [],
        }
    if AI_PROVIDER in ("gemini_cli", "gemini-cli"):
        return _analyze_with_gemini_cli(image_bytes, prompt)
    return _analyze_with_gemini(image_bytes, prompt)


def generate_text(prompt: str) -> str:
    """Gemini にテキストプロンプトを送り、生成テキストを返す（週次レポート要約用）。"""
    if _stub_enabled():
        return "[サンドボックス] スタブ要約（実Geminiは未使用）"
    if AI_PROVIDER in ("gemini_cli", "gemini-cli"):
        return _generate_text_with_gemini_cli(prompt)

    client = _make_client()
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
    from google.genai import types

    client = _make_client()
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
