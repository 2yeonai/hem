#!/usr/bin/env python3
# 범용 러너 웹 화면 — 브라우저에서 버튼으로 공장 검증/실행
# 실행: python3 ai공장짓기/runner/webapp.py  → 브라우저에서 http://localhost:8765
import os, sys, json, subprocess, html
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.abspath(os.path.join(HERE, "..", ".."))
RUNNER = os.path.join(HERE, "runner.py")
SKIP = {'.obsidian', '.git', '__pycache__', 'node_modules'}

def find_manifests():
    out = []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith('.')]
        for f in files:
            if f == "manifest.yaml":
                out.append(os.path.relpath(os.path.join(root, f), VAULT))
    return sorted(out)

PAGE = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>범용 러너</title>
<style>body{font-family:sans-serif;max-width:860px;margin:24px auto;padding:0 16px;background:#0f1220;color:#e8ecff}
h1{color:#7fd4ff}.card{background:#1a1f35;border-radius:12px;padding:14px 18px;margin:10px 0}
button{background:#2f6fed;color:#fff;border:0;border-radius:8px;padding:8px 14px;margin-right:8px;cursor:pointer;font-size:14px}
button.v{background:#3a9d5f}pre{background:#05070f;padding:12px;border-radius:8px;white-space:pre-wrap;font-size:12px;max-height:420px;overflow:auto}
small{opacity:.65}</style></head><body>
<h1>🏭 범용 러너</h1><p>공장 설계도(manifest.yaml)를 골라 <b>검증</b>(설계도가 올바른가) 또는 <b>모의실행</b>(끝까지 돌아가는가)을 누르세요.<br><small>실제 AI 호출은 아직 목업 — 구조 확인용. 결과는 아래에 그대로 표시됩니다(증거 기반).</small></p>
__CARDS__
<div class="card"><b>결과</b><pre id="out">아직 실행한 것 없음</pre></div>
<script>
async function go(p, mode){
  const out=document.getElementById('out');out.textContent='실행 중... ('+p+')';
  const r=await fetch('/run?path='+encodeURIComponent(p)+'&mode='+mode);
  out.textContent=await r.text();window.scrollTo(0,document.body.scrollHeight);}
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, body, ctype="text/html"):
        b = body.encode('utf-8')
        self.send_response(200); self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            cards = ""
            for m in find_manifests():
                e = html.escape(m)
                cards += f'<div class="card"><b>{e}</b><br><br><button class="v" onclick="go(\'{e}\',\'validate\')">검증</button><button onclick="go(\'{e}\',\'run\')">모의실행</button></div>'
            self._send(PAGE.replace("__CARDS__", cards or "<div class='card'>manifest.yaml 없음</div>"))
        elif u.path == "/run":
            q = parse_qs(u.query); rel = q.get("path", [""])[0]; mode = q.get("mode", ["validate"])[0]
            tgt = os.path.abspath(os.path.join(VAULT, rel))
            if not tgt.startswith(VAULT) or not os.path.isfile(tgt):
                self._send("잘못된 경로", "text/plain"); return
            cmd = [sys.executable, RUNNER, tgt] + (["--validate-only"] if mode == "validate" else [])
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=VAULT)
                out = f"$ {' '.join(os.path.basename(c) for c in cmd)}\n종료코드: {r.returncode}\n\n{r.stdout}\n{r.stderr}"
            except Exception as ex:
                out = f"실행 오류: {ex}"
            self._send(out, "text/plain")
        else:
            self.send_response(404); self.end_headers()

if __name__ == "__main__":
    port = 8765
    print(f"러너 웹앱 시작 — 브라우저에서 http://localhost:{port} 를 여세요 (끄기: 이 창 닫기)")
    HTTPServer(("127.0.0.1", port), H).serve_forever()
