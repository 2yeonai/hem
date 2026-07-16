#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RTS 복습 앱 로컬 서버 — 이 폴더(app/)를 http://localhost:8901 로 서빙.
PWA 설치(서비스워커 등록)는 file:// 에서는 동작하지 않아 localhost로 띄운다.
실행: python3 server.py  (또는 RTS_앱_실행.bat 더블클릭)
"""
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8901
HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        # 로컬 개인용 앱 — 캐시 최신화를 위해 매번 새로 받도록
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main():
    os.chdir(HERE)
    httpd = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"RTS 앱 서버 시작: http://localhost:{PORT}")
    print("종료하려면 이 창을 닫거나 Ctrl+C 를 누르세요.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
