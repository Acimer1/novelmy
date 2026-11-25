@echo off
rem ============================================================
rem  小说下载器 - 每日数据库备份邮件推送
rem  由 Windows 任务计划程序每天 08:00 自动调用
rem  日志: backup_db.log
rem ============================================================
setlocal
cd /d "%~dp0..\.." || exit /b 1
set "PYTHON=python"
if exist "C:\Users\Administrator\Python312\python.exe" set "PYTHON=C:\Users\Administrator\Python312\python.exe"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
"%PYTHON%" "%~dp0backup_db.py" %*
exit /b %errorlevel%
