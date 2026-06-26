"""サンドボックス/CI 用の合成スクリーンショット生成。

実画面が撮れない環境で、コアループとぼかし処理を検証するためのダミー画像。
わざと "API_KEY=..." のような機密っぽい行を含め、redact のテストにも使える。
"""
import io

from PIL import Image, ImageDraw

WIDTH = 1280
HEIGHT = 720


def generate_dummy_screenshot() -> bytes:
    """エディタ風の合成画像を JPEG バイト列で返す。"""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)

    # 疑似タイトルバー
    draw.rectangle([0, 0, WIDTH, 36], fill=(50, 50, 64))
    draw.text((12, 10), "main.py - screenlog-google - Editor", fill=(220, 220, 230))

    # 疑似コード行
    lines = [
        "def main():",
        "    config = load_config()",
        "    # TODO: refactor capture loop",
        "    API_KEY=AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMYDUMMY",  # 機密っぽい行（ダミー）
        "    client = build_client(API_KEY)",
        "    for frame in capture():",
        "        analyze(frame)",
    ]
    y = 60
    for ln in lines:
        draw.text((24, y), ln, fill=(200, 210, 220))
        y += 28

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
