@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo AI 공장 허브 서버를 시작합니다.
echo 잠시 후 이 창에 폰에서 접속할 주소가 표시됩니다.
echo.
start "" "http://localhost:8899/1. Projects/ai공장짓기/AI공장_모바일허브/index.html"
py server.py 2>nul || python server.py 2>nul || (echo. & echo [문제] 파이썬이 설치되어 있지 않습니다. "0. Docs\수동작업_가이드.md"의 1번을 따라 설치하세요. & pause)
