#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 공장 허브 로컬 서버 — 볼트 루트(hem/) 전체를 서빙한다.

왜 볼트 루트를 서빙하나: 방역/꽃집/정부지원 3개 공장의 승인화면 목업이
각자 자기 프로젝트 폴더(`1. Projects/클로드 방역 ai/ui/` 등)에 원본 그대로
있고, "같은 사실은 한 곳에만 적고 나머지는 링크한다" 원칙에 따라 이 허브
폴더로 복사하지 않는다. 대신 이 서버가 볼트 루트를 서빙 루트로 잡아서
상대경로(`/1. Projects/.../승인화면_프로토타입_v1.html`)로 원본 파일을
그대로 이어준다. RTS 앱(`1. Projects/클로드 RTS AI/app/server.py`)의
패턴을 그대로 재사용했다.

PWA 설치(서비스워커 등록)는 file:// 에서는 동작하지 않아 localhost/LAN IP로
띄운다. 실행: python3 server.py (또는 AI공장허브_실행.bat 더블클릭)
"""
import os
import socket
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote

PORT = 8899
# 이 파일 위치: 1. Projects/ai공장짓기/AI공장_모바일허브/server.py
# 볼트 루트는 여기서 3단계 위(hem/).
HERE = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
HUB_REL_PATH = "1. Projects/ai공장짓기/AI공장_모바일허브/index.html"
HUB_URL_PATH = quote(HUB_REL_PATH)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        # 로컬 개인용 앱 — 캐시 최신화를 위해 매번 새로 받도록
        self.send_header("Cache-Control", "no-cache")
        # sw.js는 허브 폴더 안에 있지만 scope를 볼트 루트("/")로 등록해야
        # 다른 공장 폴더(ui/)의 파일도 같은 서비스워커가 캐시할 수 있다.
        # 기본은 sw.js가 위치한 폴더까지만 scope가 허용되므로, 이 헤더로
        # 브라우저에 "/" scope 등록을 명시적으로 허용해준다.
        if self.path.endswith("sw.js"):
            self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()


def get_local_ip():
    """같은 wifi에서 폰이 접속할 PC의 LAN IP를 알아낸다."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 실제로 연결하지 않고 라우팅 테이블만 이용해 로컬 IP를 얻는 트릭
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    os.chdir(VAULT_ROOT)
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)
    local_ip = get_local_ip()
    hub_url_pc = f"http://localhost:{PORT}/{HUB_URL_PATH}"
    hub_url_phone = f"http://{local_ip}:{PORT}/{HUB_URL_PATH}"
    print("=" * 60)
    print("AI 공장 허브 서버 시작")
    print(f"서빙 루트: {VAULT_ROOT}")
    print(f"PC에서 접속: {hub_url_pc}")
    print(f"폰에서 접속(같은 wifi 필요): {hub_url_phone}")
    print("종료하려면 이 창을 닫거나 Ctrl+C 를 누르세요.")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
