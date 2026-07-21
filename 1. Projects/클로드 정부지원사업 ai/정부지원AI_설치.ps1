$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeRoot = Join-Path $projectRoot ".runtime"
$sourceRoot = Join-Path $runtimeRoot "jbjw-source"
$venvRoot = Join-Path $runtimeRoot "jbjw-venv"
$repoUrl = "https://github.com/2yeonai/jbjw.git"

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null

if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot ".git"))) {
    git clone $repoUrl $sourceRoot
} else {
    Write-Host "공개 앱 코드가 이미 있습니다. 덮어쓰지 않습니다: $sourceRoot"
}

if (-not (Test-Path -LiteralPath (Join-Path $venvRoot "Scripts\python.exe"))) {
    python -m venv $venvRoot
}

& (Join-Path $venvRoot "Scripts\python.exe") -m pip install PyYAML "python-pptx>=1.0"

$dataRoot = Join-Path $runtimeRoot "factory-data"
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null

Write-Host "설치 완료. 이제 정부지원AI_실행.bat을 더블클릭하세요."
