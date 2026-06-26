"""ローカルWebセットアップウィザード。

  python setup_web.py

ブラウザで http://localhost:8765 を開き、画面の案内に従って
  1) Geminiキー等を入力 → 保存
  2) credentials.json を配置（無ければ手順を表示）
  3) Google認証（OAuth）
  4) スプレッドシート自動作成
を順に行うと使い始められる。標準ライブラリのみで動作。
"""
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import wizard

PORT = int(os.getenv("SETUP_WEB_PORT", "8765"))

PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ScreenLog セットアップ</title>
<style>
 :root{color-scheme:light dark}
 body{font-family:system-ui,"Segoe UI",sans-serif;max-width:720px;margin:24px auto;padding:0 16px;line-height:1.6}
 h1{font-size:1.4rem} h2{font-size:1.05rem;margin:0 0 8px}
 .step{border:1px solid #8884;border-radius:10px;padding:16px;margin:14px 0}
 .badge{font-size:.8rem;padding:2px 8px;border-radius:999px;border:1px solid #8886;float:right}
 .ok{background:#1a7f3722;border-color:#1a7f37} .ng{background:#b9290022;border-color:#b92900}
 input{width:100%;padding:8px;margin:4px 0 10px;border:1px solid #8886;border-radius:6px;box-sizing:border-box}
 button{padding:9px 16px;border:0;border-radius:6px;background:#2563eb;color:#fff;cursor:pointer;font-size:.95rem}
 button.sec{background:#6b7280} button:disabled{opacity:.5;cursor:not-allowed}
 ol{padding-left:1.2em} li{margin:4px 0}
 .msg{margin-top:8px;font-size:.9rem;white-space:pre-wrap}
 a{color:#2563eb} code{background:#8882;padding:1px 5px;border-radius:4px}
 .done{font-size:1.05rem}
</style></head><body>
<h1>ScreenLog セットアップ</h1>
<p>画面の上から順に進めると使い始められます。</p>

<div class="step" id="s-config">
  <span class="badge" id="b-config">…</span>
  <h2>1. 基本情報を入力</h2>
  <label>Gemini API キー（<a href="https://aistudio.google.com/app/apikey" target="_blank">取得</a>）</label>
  <input id="gemini" type="password" placeholder="AIza...">
  <label>Gemini モデル（任意）</label>
  <input id="model" placeholder="gemini-2.5-flash">
  <label>通知メール宛先（任意・空なら自分宛）</label>
  <input id="gmail" placeholder="you@example.com">
  <button onclick="saveConfig()">保存</button>
  <div class="msg" id="m-config"></div>
</div>

<div class="step" id="s-cred">
  <span class="badge" id="b-cred">…</span>
  <h2>2. Google OAuth クライアント（credentials.json）</h2>
  <div id="cred-guide"></div>
  <button class="sec" onclick="recheck()">再チェック</button>
  <div class="msg" id="m-cred"></div>
</div>

<div class="step" id="s-auth">
  <span class="badge" id="b-auth">…</span>
  <h2>3. Google 認証</h2>
  <p>ブラウザが開くのでGoogleアカウントで許可してください。</p>
  <button onclick="auth()" id="btn-auth">Google認証する</button>
  <div class="msg" id="m-auth"></div>
</div>

<div class="step" id="s-sheet">
  <span class="badge" id="b-sheet">…</span>
  <h2>4. 記録用スプレッドシートを作成</h2>
  <button onclick="createSheet()" id="btn-sheet">作成する</button>
  <div class="msg" id="m-sheet"></div>
</div>

<div class="step" id="s-done" style="display:none">
  <h2>✅ 準備完了</h2>
  <p class="done">ターミナルで <code>python main.py --once</code> を実行すると記録が始まります。<br>
  週次レポートは <code>python weekly_report.py</code> です。</p>
</div>

<script>
const $ = id => document.getElementById(id);
function badge(id, ok){ const b=$(id); b.textContent= ok?'OK':'未完了'; b.className='badge '+(ok?'ok':'ng'); }
async function api(path, body){
  const r = await fetch(path, {method: body?'POST':'GET', headers:{'Content-Type':'application/json'},
    body: body?JSON.stringify(body):undefined});
  if(!r.ok){ throw new Error((await r.json()).error || r.statusText); }
  return r.json();
}
async function refresh(){
  const s = await api('/api/status');
  badge('b-config', s.has_gemini_key);
  badge('b-cred', s.has_credentials);
  badge('b-auth', s.has_token);
  badge('b-sheet', s.has_sheet);
  $('btn-auth').disabled = !s.has_credentials;
  $('btn-sheet').disabled = !s.has_token;
  // credentials ガイド
  if(s.has_credentials){
    $('cred-guide').innerHTML = '<p>credentials.json を検出しました（<code>'+s.credentials_path+'</code>）。</p>';
  } else {
    let html = '<p>未検出。以下の手順で作成し、<code>'+s.credentials_path+'</code> に保存してください。</p><ol>';
    s.guide.forEach(g => html += '<li>'+g+'</li>');
    $('cred-guide').innerHTML = html + '</ol>';
  }
  if(s.has_gemini_key && s.has_token && s.has_sheet){
    $('s-done').style.display='block';
    if(s.sheet_url) $('m-sheet').innerHTML = '作成済み: <a href="'+s.sheet_url+'" target="_blank">スプレッドシートを開く</a>';
  }
}
async function saveConfig(){
  try{
    await api('/api/save', {GEMINI_API_KEY:$('gemini').value, GEMINI_MODEL:$('model').value, GMAIL_TO:$('gmail').value});
    $('m-config').textContent='保存しました。'; refresh();
  }catch(e){ $('m-config').textContent='エラー: '+e.message; }
}
async function recheck(){ await refresh(); $('m-cred').textContent='再チェックしました。'; }
async function auth(){
  $('m-auth').textContent='認証中… ブラウザの許可画面を確認してください。';
  try{ await api('/api/auth', {}); $('m-auth').textContent='認証に成功しました。'; refresh(); }
  catch(e){ $('m-auth').textContent='エラー: '+e.message; }
}
async function createSheet(){
  $('m-sheet').textContent='作成中…';
  try{ const r=await api('/api/create-sheet', {});
    $('m-sheet').innerHTML='作成しました: <a href="'+r.sheet_url+'" target="_blank">開く</a>'; refresh(); }
  catch(e){ $('m-sheet').textContent='エラー: '+e.message; }
}
refresh();
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # ログを静かに
        pass

    def _send_json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            status = wizard.get_status()
            status["guide"] = wizard.CREDENTIALS_GUIDE
            self._send_json(status)
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            body = self._read_body()
            if self.path == "/api/save":
                self._send_json(wizard.save_config(body))
            elif self.path == "/api/auth":
                self._send_json(wizard.run_oauth())
            elif self.path == "/api/create-sheet":
                self._send_json(wizard.create_sheet())
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001 - エラーはJSONで返す
            self._send_json({"error": str(e)}, 500)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"セットアップ画面: {url}")
    print("ブラウザが自動で開きます。終了するには Ctrl+C。")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n終了しました")
        server.shutdown()


if __name__ == "__main__":
    main()
