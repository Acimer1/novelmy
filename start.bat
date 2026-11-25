@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0" || exit /b 1
where npm.cmd >nul 2>&1 || goto nonpm
if exist ".venv\Scripts\python.exe" goto deps
set "PYTHON=C:\Users\Administrator\Python312\python.exe"
if exist "%PYTHON%" goto venv
set "PYTHON=python"
python --version >nul 2>&1 || goto missing
:venv
"%PYTHON%" -m venv .venv || goto failed
:deps
set "PYTHON=.venv\Scripts\python.exe"
if /i "%~1"=="--build" goto frontend
"%PYTHON%" -c "import flask, flask_cors, requests, websocket, Crypto, psutil" >nul 2>&1 && goto frontend
call :installpython || goto failed
:frontend
if not exist "frontend\node_modules\.bin\vite.cmd" goto installnode
if not exist "frontend\node_modules\.package-lock.json" goto installnode
if not exist "frontend\node_modules\.start-lock" goto installnode
fc /b "frontend\package-lock.json" "frontend\node_modules\.start-lock" >nul && goto build
:installnode
call npm.cmd --prefix frontend ci --include=dev || goto failed
copy /y "frontend\package-lock.json" "frontend\node_modules\.start-lock" >nul || goto failed
:build
call npm.cmd --prefix frontend run build || goto failed
"%PYTHON%" script\check_frontend.py || goto failed
if /i "%~1"=="--build" exit /b 0
"%PYTHON%" server.py %*
if errorlevel 1 goto failed
exit /b 0
:installpython
"%PYTHON%" -m pip install -r requirements.txt
exit /b %errorlevel%
:missing
echo 未找到 Python。请先安装 Python 并加入 PATH，再双击 start.bat。
goto failed
:nonpm
echo 未找到 npm。请先安装 Node.js 22.12 或更高的 22.x 版本，并将 npm 加入 PATH。
:failed
echo 启动未完成，请查看上方错误。
pause
exit /b 1
