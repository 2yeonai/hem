#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RTS 복습 앱 로컬 서버 — 이 폴더(app/)를 서빙.

PC:  http://localhost:8901
폰:  같은 와이파이에 연결한 뒤, 실행할 때 화면에 뜨는 http://192.168.x.x:8901 주소로 접속.

실행: python3 server.py  (또는 RTS_앱_실행.bat 더블클릭)

※ 폰 접속을 위해 같은 와이파이 안의 기기에 열려 있다. 카페 등 공용 와이파이에서는
   같은 망의 다른 사람도 볼 수 있으니, 집·개인 와이파이에서만 쓰는 것을 권장한다.
   PC에서만 쓰고 싶으면 아래 BIND 값을 "127.0.0.1"로 바꾸면 된다.
"""
import os
import socket
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8901
BIND = "0.0.0.0"  # 폰에서도 접속 가능. PC 전용으로 잠그려면 "127.0.0.1"
HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        # 로컬 개인용 앱 — 캐시 최신화를 위해 매번 새로 받도록
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def lan_ip():
    """이 PC가 와이파이에서 쓰는 주소를 찾는다(폰에서 칠 주소)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # 실제로 데이터를 보내지는 않는다
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


def main():
    os.chdir(HERE)
    httpd = HTTPServer((BIND, PORT), Handler)
    ip = lan_ip()
    say = lambda t="": print(t, flush=True)
    say("=" * 52)
    say("RTS 앱 서버가 켜졌습니다.")
    say("")
    say(f"  이 컴퓨터에서 :  http://localhost:{PORT}")
    if ip:
        say(f"  폰에서       :  http://{ip}:{PORT}")
        say("")
        say("  * 폰이 이 컴퓨터와 같은 와이파이에 연결돼 있어야 합니다.")
        say("  * 폰 브라우저 주소창에 위 주소를 그대로 치세요.")
    else:
        say("  폰 주소를 찾지 못했습니다(와이파이 연결 확인).")
    say("")
    say("종료하려면 이 창을 닫거나 Ctrl+C 를 누르세요.")
    say("=" * 52)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
