$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot

Write-Host "==> KIS 단타봇 설치를 시작합니다 ($ProjectRoot)"

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "Python이 설치되어 있지 않습니다. https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치한 뒤(설치 시 'Add python.exe to PATH' 체크) 다시 실행하세요." -ForegroundColor Red
    exit 1
}
$pythonExe = $pythonCmd.Source

Write-Host "==> 가상환경 생성 (.venv)"
& $pythonExe -m venv "$ProjectRoot\.venv"

$venvPython = "$ProjectRoot\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "가상환경 생성에 실패했습니다." -ForegroundColor Red
    exit 1
}

Write-Host "==> 의존성 설치"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r "$ProjectRoot\requirements.txt"

$envFile = "$ProjectRoot\.env"
if (-not (Test-Path $envFile)) {
    Copy-Item "$ProjectRoot\.env.example" $envFile
    Write-Host "==> .env 파일을 새로 만들었습니다. 실행 전에 반드시 앱키/시크릿/계좌번호를 채워넣으세요: $envFile" -ForegroundColor Yellow
} else {
    Write-Host "==> 기존 .env 파일이 있어 그대로 두었습니다."
}

Write-Host "==> 바탕화면 바로가기 생성"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "KIS 단타봇.lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $ProjectRoot "scripts\windows\run.bat"
$shortcut.WorkingDirectory = $ProjectRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,43"
$shortcut.Description = "KIS 국내 주식 단타 자동매매 봇 실행"
$shortcut.Save()

Write-Host ""
Write-Host "==> 설치 완료!" -ForegroundColor Green
Write-Host "1. $envFile 파일을 메모장으로 열어 KIS_APP_KEY / KIS_APP_SECRET / KIS_ACCOUNT_NO / WATCHLIST 등을 채워넣으세요."
Write-Host "2. 처음에는 IS_VIRTUAL=true(모의투자), DRY_RUN=true 상태로 충분히 검증하세요."
Write-Host "3. 바탕화면의 'KIS 단타봇' 아이콘을 더블클릭하면 실행됩니다 (콘솔 창이 열리고 로그가 표시됩니다)."
Write-Host "4. 끄려면 콘솔 창에서 Ctrl+C 를 누르세요."
