@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 러너 웹앱을 시작합니다. 잠시 후 브라우저에서 http://localhost:8765 를 여세요.
start http://localhost:8765
py "ai공장짓기\runner\webapp.py" 2>nul || python "ai공장짓기\runner\webapp.py" 2>nul || (echo. & echo [문제] 파이썬이 설치되어 있지 않습니다. "0. Docs\수동작업_가이드.md"의 1번을 따라 설치하세요. & pause)
