@echo off
chcp 65001 >nul

cd /d "%~dp0"


echo.
echo  番茄 + 灵猫 小说下载器
echo  http://localhost:5000
echo.

pip install -r requirements.txt >nul 2>&1
python server.py

pause