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

PAGE = r"""<!doctype html>
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
 .chips{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}
 .chip{background:#2563eb22;border:1px solid #2563eb88;border-radius:999px;padding:2px 10px;display:inline-flex;align-items:center;gap:6px}
 .chip button{background:none;color:inherit;border:0;cursor:pointer;padding:0;font-size:1rem;line-height:1}
 .dirrow{padding:2px 4px} .dirrow a{text-decoration:none}
 #dir-list a:hover{text-decoration:underline}
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

<div class="step" id="s-settings">
  <span class="badge" id="b-settings">任意</span>
  <h2>5. カスタマイズ設定（任意）</h2>
  <p>自分の使い方に合わせて変更できます。空欄は既定値のままです。</p>

  <label>スクショ保存フォルダ（参照ボタンで選べます）</label>
  <div style="display:flex;gap:8px">
    <input id="set-dir" placeholder="screenshots" readonly style="background:#8881">
    <button type="button" class="sec" onclick="toggleBrowser()">参照…</button>
  </div>
  <div id="dir-browser" style="display:none;border:1px solid #8886;border-radius:8px;padding:10px;margin:6px 0">
    <div style="margin-bottom:6px"><b>現在地:</b> <span id="dir-current"></span></div>
    <div id="dir-shortcuts" style="margin-bottom:6px"></div>
    <div style="max-height:180px;overflow:auto;border:1px solid #8884;border-radius:6px;padding:4px">
      <div class="dirrow"><a href="#" onclick="browseUp();return false">⬆ 上のフォルダへ</a></div>
      <div id="dir-list"></div>
    </div>
    <button type="button" onclick="chooseDir()" style="margin-top:8px">このフォルダを保存先にする</button>
  </div>
  <label>ログファイル</label>
  <input id="set-log" placeholder="screenlog.log">

  <label>キャプチャ間隔（分）</label>
  <input id="set-interval" type="number" min="1" placeholder="5">
  <label>週次レポートの振り返り日数</label>
  <input id="set-weekly" type="number" min="1" placeholder="7">
  <label>スクショ保持日数（0で自動削除しない）</label>
  <input id="set-retention" type="number" min="0" placeholder="14">
  <label>確信度しきい値（これ未満で確認通知）</label>
  <input id="set-threshold" type="number" min="0" max="100" placeholder="70">

  <label><input type="checkbox" id="set-notify"> 低確信度のときメール通知する</label>

  <label><input type="checkbox" id="set-tracker"> アプリ使用時間を計測して分析精度を上げる
    <span style="opacity:.7;font-size:.85rem">（アクティブなアプリ名をGeminiに送信。<a href="#" onclick="alert('ウィンドウタイトル/アプリ名がGeminiに送信されます。詳細はPRIVACY.mdを参照。');return false">プライバシー</a>）</span></label>
  <label style="display:block">ウィンドウ計測の間隔（秒）</label>
  <input id="set-poll" type="number" min="1" placeholder="30">

  <label>カテゴリ分類（タグで追加・削除）</label>
  <div id="cat-chips" class="chips"></div>
  <div style="display:flex;gap:8px">
    <input id="cat-input" placeholder="カテゴリ名を入力して Enter">
    <button type="button" class="sec" onclick="addCat()">追加</button>
  </div>

  <label>記録する任意項目（チェックした列のみSheetsに記録）</label>
  <div id="set-columns"></div>

  <button onclick="saveSettings()">設定を保存</button>
  <div class="msg" id="m-settings"></div>
</div>

<div class="step" id="s-test">
  <span class="badge">任意</span>
  <h2>6. 動作確認とログ</h2>
  <p>設定が正しく動くか、ここから確認できます。</p>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <button type="button" class="sec" onclick="testSheet()">Sheets接続をテスト</button>
    <button type="button" class="sec" onclick="testEmail()">テストメール送信</button>
    <button type="button" onclick="runOnce()">1回だけ記録を実行</button>
  </div>
  <div class="msg" id="m-test"></div>
  <div style="display:flex;gap:8px;align-items:center;margin-top:12px">
    <b>アプリ別使用時間</b>
    <span id="bd-period" style="opacity:.7;font-size:.85rem"></span>
    <button type="button" class="sec" onclick="loadBreakdown()">読み込む</button>
  </div>
  <div id="bd-chart" style="margin-top:6px"></div>

  <div style="display:flex;gap:8px;align-items:center;margin-top:12px">
    <b>ログ</b>
    <button type="button" class="sec" onclick="loadLogs()">最新を読み込む</button>
  </div>
  <pre id="log-view" style="max-height:240px;overflow:auto;background:#8881;border:1px solid #8884;border-radius:6px;padding:8px;font-size:.8rem;white-space:pre-wrap"></pre>
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
async function loadSettings(){
  const s = await api('/api/settings');
  const v = s.values;
  $('set-dir').value = v.SCREENSHOT_DIR || '';
  $('set-log').value = v.LOG_FILE || '';
  $('set-interval').value = v.CAPTURE_INTERVAL_MINUTES || '';
  $('set-weekly').value = v.WEEKLY_REPORT_DAYS || '';
  $('set-retention').value = v.SCREENSHOT_RETENTION_DAYS || '';
  $('set-threshold').value = v.CONFIDENCE_THRESHOLD || '';
  $('set-notify').checked = String(v.NOTIFY_ENABLED).toLowerCase() === 'true';
  $('set-tracker').checked = String(v.ENABLE_WINDOW_TRACKER).toLowerCase() === 'true';
  $('set-poll').value = v.WINDOW_POLL_INTERVAL_SEC || '';
  catList = (v.CATEGORIES || '').split(',').map(x=>x.trim()).filter(Boolean);
  renderCats();
  const chosen = (v.RECORD_OPTIONAL_COLUMNS || '').split(',').map(x=>x.trim());
  $('set-columns').innerHTML = s.available_optional_columns.map(col =>
    '<label style="display:inline-block;margin-right:12px"><input type="checkbox" class="col" value="'
    + col + '"' + (chosen.includes(col) ? ' checked' : '') + '> ' + col + '</label>'
  ).join('');
}
async function saveSettings(){
  const cols = Array.from(document.querySelectorAll('#set-columns .col:checked')).map(c=>c.value).join(',');
  const body = {
    SCREENSHOT_DIR: $('set-dir').value,
    LOG_FILE: $('set-log').value,
    CAPTURE_INTERVAL_MINUTES: $('set-interval').value,
    WEEKLY_REPORT_DAYS: $('set-weekly').value,
    SCREENSHOT_RETENTION_DAYS: $('set-retention').value,
    CONFIDENCE_THRESHOLD: $('set-threshold').value,
    NOTIFY_ENABLED: $('set-notify').checked ? 'true' : 'false',
    ENABLE_WINDOW_TRACKER: $('set-tracker').checked ? 'true' : 'false',
    WINDOW_POLL_INTERVAL_SEC: $('set-poll').value,
    CATEGORIES: catList.join(','),
    RECORD_OPTIONAL_COLUMNS: cols
  };
  try{ await api('/api/save-settings', body);
    $('m-settings').textContent='設定を保存しました（次回起動から反映）。'; }
  catch(e){ $('m-settings').textContent='エラー: '+e.message; }
}

// --- カテゴリ タグUI ---
let catList = [];
function renderCats(){
  $('cat-chips').innerHTML = catList.map((c,i) =>
    '<span class="chip">'+escapeHtml(c)+'<button title="削除" onclick="removeCat('+i+')">×</button></span>'
  ).join('');
}
function addCat(){
  const v = $('cat-input').value.trim();
  if(v && !catList.includes(v)){ catList.push(v); renderCats(); }
  $('cat-input').value='';
}
function removeCat(i){ catList.splice(i,1); renderCats(); }
function escapeHtml(s){ return s.replace(/[&<>"']/g, m =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

// --- フォルダ参照UI ---
let browsePath='', browseParent=null;
function toggleBrowser(){
  const b=$('dir-browser');
  if(b.style.display==='none'){ b.style.display='block'; browseTo($('set-dir').value||''); }
  else { b.style.display='none'; }
}
async function browseTo(path){
  const data = await api('/api/browse?path='+encodeURIComponent(path||''));
  browsePath=data.path; browseParent=data.parent;
  $('dir-current').textContent=data.path;
  // data-path 属性＋イベント委譲で扱う（onclick文字列にパスを埋め込むと
  // Windowsのバックスラッシュや引用符で壊れるため）。属性値はHTMLエスケープ。
  $('dir-shortcuts').innerHTML = data.shortcuts.map(s =>
    '<button type="button" class="sec" style="margin:2px" data-path="'+escapeHtml(s.path)+'">'+escapeHtml(s.label)+'</button>'
  ).join('');
  $('dir-list').innerHTML = data.dirs.length
    ? data.dirs.map(d => '<div class="dirrow">📁 <a href="#" data-path="'+escapeHtml(d.path)+'">'+escapeHtml(d.name)+'</a></div>').join('')
    : '<div class="dirrow" style="opacity:.6">（サブフォルダなし）</div>';
}
function browseUp(){ if(browseParent) browseTo(browseParent); }
function chooseDir(){ $('set-dir').value=browsePath; $('dir-browser').style.display='none'; }

// --- 動作確認とログ ---
async function _runTest(path, label){
  $('m-test').textContent = label+'…';
  try{ const r = await api(path, {});
    $('m-test').textContent = (r.ok?'✅ ':'⚠️ ') + (r.message || (r.ok?'成功':'失敗'));
    loadLogs(); }
  catch(e){ $('m-test').textContent = '⚠️ エラー: '+e.message; }
}
function testSheet(){ _runTest('/api/test-sheet', 'Sheets接続を確認中'); }
function testEmail(){ _runTest('/api/test-email', 'テストメール送信中'); }
function runOnce(){ _runTest('/api/run-once', '1サイクル実行中'); }
async function loadLogs(){
  try{ const r = await api('/api/logs?lines=200');
    $('log-view').textContent = r.exists
      ? (r.lines.length ? r.lines.join('\n') : '（ログは空です）')
      : '（ログファイルはまだありません: '+r.path+'）';
    $('log-view').scrollTop = $('log-view').scrollHeight; }
  catch(e){ $('log-view').textContent = 'ログ取得エラー: '+e.message; }
}
function fmtMin(m){ return m>=60 ? (Math.floor(m/60)+'時間'+Math.round(m%60)+'分') : (Math.round(m*10)/10+'分'); }
async function loadBreakdown(){
  $('bd-chart').innerHTML = '読み込み中…';
  try{
    const r = await api('/api/app-breakdown');
    $('bd-period').textContent = '直近'+r.period_days+'日';
    if(!r.apps || !r.apps.length){
      $('bd-chart').innerHTML = r.tracker_enabled
        ? '<div style="opacity:.7">この期間に記録されたアプリ使用時間はまだありません。</div>'
        : '<div style="opacity:.7">ウィンドウ追跡（手順5）を有効にすると、ここにアプリ別の使用時間が表示されます。</div>';
      return;
    }
    const max = Math.max.apply(null, r.apps.map(a=>a.minutes)) || 1;
    $('bd-chart').innerHTML = r.apps.map(a => {
      const w = Math.max(2, Math.round(a.minutes/max*100));
      return '<div style="margin:4px 0">'
        + '<div style="display:flex;justify-content:space-between;font-size:.85rem">'
        + '<span>'+escapeHtml(a.name)+'</span><span style="opacity:.7">'+fmtMin(a.minutes)+'（'+a.percent+'%）</span></div>'
        + '<div style="background:#8883;border-radius:4px;height:14px"><div style="width:'+w+'%;height:100%;background:#2563eb;border-radius:4px"></div></div>'
        + '</div>';
    }).join('') + '<div style="opacity:.6;font-size:.8rem;margin-top:6px">合計 '+fmtMin(r.total_minutes)+'</div>';
  }catch(e){ $('bd-chart').innerHTML = '取得エラー: '+escapeHtml(e.message); }
}

document.getElementById('cat-input').addEventListener('keydown', e => {
  if(e.key==='Enter'){ e.preventDefault(); addCat(); }
});
// フォルダ参照: data-path を持つ要素のクリックで移動（イベント委譲）
$('dir-shortcuts').addEventListener('click', e => {
  const el = e.target.closest('[data-path]'); if(el){ browseTo(el.getAttribute('data-path')); }
});
$('dir-list').addEventListener('click', e => {
  const el = e.target.closest('[data-path]'); if(el){ e.preventDefault(); browseTo(el.getAttribute('data-path')); }
});
refresh();
loadSettings();
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
        elif self.path == "/api/settings":
            self._send_json(wizard.get_settings())
        elif self.path.startswith("/api/browse"):
            from urllib.parse import parse_qs, urlparse

            qs = parse_qs(urlparse(self.path).query)
            path = (qs.get("path") or [""])[0]
            self._send_json(wizard.list_dirs(path or None))
        elif self.path.startswith("/api/logs"):
            from urllib.parse import parse_qs, urlparse

            qs = parse_qs(urlparse(self.path).query)
            n = (qs.get("lines") or ["200"])[0]
            try:
                n = int(n)
            except ValueError:
                n = 200
            self._send_json(wizard.read_recent_logs(n))
        elif self.path.startswith("/api/app-breakdown"):
            self._send_json(wizard.get_app_breakdown())
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
            elif self.path == "/api/save-settings":
                self._send_json(wizard.save_settings(body))
            elif self.path == "/api/test-sheet":
                self._send_json(wizard.test_sheet())
            elif self.path == "/api/test-email":
                self._send_json(wizard.test_email())
            elif self.path == "/api/run-once":
                self._send_json(wizard.run_once())
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
