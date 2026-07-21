@echo off
chcp 65001 >nul
set "HYEMI_GOV_ROOT=%~dp0"
set "HYEMI_FACTORY_DATA_ROOT=%~dp0.runtime\factory-data"
set "HYEMI_FACTORY_BIND=0.0.0.0"
set "APP_DIR=%~dp0.runtime\jbjw-source\hyemi-ai-factory"
set "APP_PY=%~dp0.runtime\jbjw-venv\Scripts\python.exe"
if not exist "%APP_PY%" (
  echo 먼저 정부지원AI_설치.bat을 실행하세요.
  pause
  exit /b 1
)
pushd "%APP_DIR%"
"%APP_PY%" 08_factory_tools\app.py
popd
pause
