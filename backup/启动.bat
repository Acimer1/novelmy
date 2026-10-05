@echo off
chcp 65001 >nul

cd /d "%~dp0"


echo.
echo  番茄小说下载器
echo  http://localhost:5000
echo.

python server.py

pause