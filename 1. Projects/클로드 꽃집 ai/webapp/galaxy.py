"""Installed Chrome share target. Shared bodies are intercepted locally by SW only."""
from flask import jsonify, send_from_directory, g, abort
from pathlib import Path

ROOT=Path(__file__).parent/'static'/'galaxy'


def register(app,web):
    @app.get('/galaxy.webmanifest')
    def galaxy_manifest():
        return jsonify(id='/galaxy',name='온천꽃 주문 전달',short_name='꽃집 전달',start_url='/galaxy',scope='/',
                       display='standalone',background_color='#f7f5ef',theme_color='#1f5c3a',
                       icons=[{'src':'/static/galaxy/icon.svg','sizes':'any','type':'image/svg+xml','purpose':'any'}],
                       share_target={'action':'/galaxy-share','method':'POST','enctype':'multipart/form-data',
                                     'params':{'title':'title','text':'text','files':[{'name':'files','accept':['audio/*','text/plain','.m4a','.wav','.mp3','.txt']}]}})

    @app.get('/galaxy-sw.js')
    def galaxy_worker():
        response=send_from_directory(ROOT,'sw.js',mimetype='application/javascript')
        response.headers['Service-Worker-Allowed']='/'
        return response

    @app.post('/galaxy-share')
    def galaxy_share_fallback():
        # No CSRF exemption and no blind upload. Working SW must intercept before network.
        return '공유 수신 준비가 안 됐습니다. 앱에서 로그인 후 공유 준비를 하고 다시 공유해주세요.',409

    @app.get('/galaxy')
    def galaxy_page():
        if g.user['role'] not in {'admin','staff'}: abort(403)
        return web.render_page(web.BASE_STYLE+'''
<link rel="manifest" href="/galaxy.webmanifest"><meta name="theme-color" content="#1f5c3a">
<h1>통화 주문 전달</h1><p>처음 한 번 Chrome 메뉴에서 앱 설치를 선택하세요. 공유 준비 후 삼성 전화/음성녹음의 공유에서 꽃집 전달을 선택하세요.</p>
<p>기존 전화번호로 통화하고, 종료 후 녹음 또는 전사문을 공유합니다. 이 앱은 전화를 감지하거나 녹음을 자동으로 가져오지 않습니다.</p>
<p id="status" role="status">공유 준비 중…</p>
<form id="transfer" method="post" action="/intakes" enctype="multipart/form-data">
<label>전사문<textarea name="raw_text" id="transcript" rows="8"></textarea></label>
<p id="file-name"></p><label><input type="checkbox" id="use-text">전사문만 보내기(별도 음성인식 생략)</label>
<button id="send" type="submit" disabled>내용 확인 후 AI 접수</button><button type="button" id="discard">기기 임시 자료 지우기</button></form>
<script src="/static/galaxy/store.js"></script><script src="/static/galaxy/share.js" defer></script>''')
