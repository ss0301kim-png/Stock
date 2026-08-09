@echo off
setlocal
cd /d "%~dp0..\.."

if not exist ".venv\Scripts\python.exe" (
    echo 가상환경이 없습니다. scripts\windows\install.ps1 을 먼저 실행하세요.
    pause
    exit /b 1
)

if not exist ".env" (
    echo .env 파일이 없습니다. .env.example을 복사해 .env로 만들고 값을 채워넣으세요.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py

echo.
echo 프로그램이 종료되었습니다.
pause
