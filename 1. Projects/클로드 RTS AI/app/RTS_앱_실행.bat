@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo RTS 복습·실기 연습 앱을 시작합니다. 잠시 후 브라우저에서 http://localhost:8901 을 여세요.
echo (처음 켜면 브라우저 주소창 오른쪽에 설치 아이콘이 뜹니다 - 눌러서 앱으로 설치하세요.)
start http://localhost:8901
py server.py 2>nul || python server.py 2>nul || (echo. & echo [문제] 파이썬이 설치되어 있지 않습니다. "0. Docs\수동작업_가이드.md"의 1번을 따라 설치하세요. & pause)
