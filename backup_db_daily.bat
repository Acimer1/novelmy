@echo off
rem ============================================================
rem  小说下载器 - 每日数据库备份邮件推送
rem  由 Windows 任务计划程序每天 08:00 自动调用
rem  日志: backup_db.log
rem ============================================================
cd /d "C:\Users\Administrator\Desktop\novelmy_full_backup"
"C:\Users\Administrator\Python312\python.exe" backup_db.py
