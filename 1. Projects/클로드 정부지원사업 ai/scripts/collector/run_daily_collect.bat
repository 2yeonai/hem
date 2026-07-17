@echo off
setlocal
set BIZINFO_API_KEY=X9HC6x
cd /d "C:\Users\82106\Desktop\hem\1. Projects\클로드 정부지원사업 ai"
python scripts\collector\collect_bizinfo.py >> scripts\collector\run_log.txt 2>&1
echo. >> scripts\collector\run_log.txt
echo EXIT_CODE: %ERRORLEVEL% >> scripts\collector\run_log.txt
echo -------- %DATE% %TIME% -------- >> scripts\collector\run_log.txt

if %ERRORLEVEL% EQU 0 (
    python scripts\collector\promote_candidates.py >> scripts\collector\run_log.txt 2>&1
)
