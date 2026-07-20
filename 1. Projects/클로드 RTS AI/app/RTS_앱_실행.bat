@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  RTS 복습·실기 연습 앱을 켭니다.
echo.
echo  [이 컴퓨터]  잠시 후 브라우저가 자동으로 열립니다.
echo               (주소창 오른쪽 설치 아이콘을 누르면 앱처럼 설치됩니다)
echo.
echo  [폰에서 보기] 아래 창에 뜨는 "폰에서: http://192.168.x.x:8901" 주소를
echo               폰 브라우저 주소창에 그대로 치세요.
echo               폰이 이 컴퓨터와 같은 와이파이여야 합니다.
echo.
echo  * 이 창을 닫으면 앱이 꺼집니다. 공부하는 동안은 켜두세요.
echo.
start http://localhost:8901
py server.py 2>nul || python server.py 2>nul || (echo. & echo [문제] 파이썬이 설치되어 있지 않습니다. "0. Docs\수동작업_가이드.md"의 1번을 따라 설치하세요. & pause)
