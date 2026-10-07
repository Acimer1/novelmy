#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库每日备份 - SMTP 邮件推送
把 app.db 以附件形式发送到指定邮箱，防止数据丢失。

配置：读取同目录 config_backup.json（首次运行自动生成模板，请填入真实 SMTP 配置）
用法：python backup_db.py
      python backup_db.py --test   # 测试发送（不写定时逻辑）
"""

import os
import json
import ssl
import smtplib
import logging
import argparse
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from email.utils import formataddr

BASE = Path(__file__).parent
DB_FILE = BASE / 'app.db'
CONFIG_FILE = BASE / 'config_backup.json'
LOG_FILE = BASE / 'backup_db.log'

# 日志
logging.basicConfig(
    filename=str(LOG_FILE), level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8',
)

# 默认配置模板（首次运行会生成 config_backup.json 让用户填写）
# 注意：真实邮箱/授权码请填到 config_backup.json，不要写进源码！
DEFAULT_CONFIG = {
    "smtp_host": "smtp.qq.com",       # 发件邮箱 SMTP 服务器
    "smtp_port": 465,                  # 465=SSL / 587=STARTTLS
    "smtp_ssl": True,                  # True 用 SSL，False 用 STARTTLS
    "sender": "你的QQ邮箱@qq.com",     # 发件邮箱
    "auth_code": "你的SMTP授权码",     # SMTP 授权码（不是登录密码）
    "receiver": "接收邮箱@qq.com",     # 收件邮箱（可填自己）
    "subject_prefix": "[小说下载器] 数据库备份"
}


def load_config():
    """读取配置；不存在则从模板生成并提示"""
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'[首次运行] 已生成配置文件: {CONFIG_FILE}')
        print('请编辑该文件，填入 SMTP 邮箱和授权码后重新运行！')
        return None
    cfg = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    # 校验是否还是模板占位值（sender/receiver/auth_code 三处都要查）
    placeholder_marks = ('你的', '接收邮箱')
    for key in ('sender', 'receiver', 'auth_code'):
        if any(mark in str(cfg.get(key, '')) for mark in placeholder_marks):
            print(f'[警告] {CONFIG_FILE} 还是模板占位值，请先填写真实邮箱/授权码！')
            return None
    return cfg


def send_backup(cfg, db_bytes: bytes, extra_note: str = ''):
    """把数据库字节作为附件发送邮件"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    subject = f"{cfg.get('subject_prefix', '数据库备份')} {now}"
    sender = cfg['sender']
    receiver = cfg['receiver']

    msg = MIMEMultipart()
    msg['From'] = formataddr((str(Header('小说下载器备份', 'utf-8')), sender))
    msg['To'] = receiver
    msg['Subject'] = Header(subject, 'utf-8')

    body = (f"数据库自动备份\n"
            f"时间: {now}\n"
            f"数据库大小: {len(db_bytes)} 字节\n"
            f"{extra_note}\n")
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    attach = MIMEApplication(db_bytes, _subtype='octet-stream')
    attach.add_header('Content-Disposition', 'attachment',
                      filename=('utf-8', '', 'app.db'))
    msg.attach(attach)

    server = None
    try:
        if cfg.get('smtp_ssl', True):
            server = smtplib.SMTP_SSL(cfg['smtp_host'], int(cfg['smtp_port']), timeout=30)
        else:
            server = smtplib.SMTP(cfg['smtp_host'], int(cfg['smtp_port']), timeout=30)
            server.starttls(context=ssl.create_default_context())
        server.login(sender, cfg['auth_code'])
        server.sendmail(sender, [receiver], msg.as_string())
    finally:
        if server is not None:
            server.quit()
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='测试发送一封，验证配置')
    args = parser.parse_args()

    cfg = load_config()
    if cfg is None:
        return

    if not DB_FILE.exists():
        logging.error('数据库文件不存在: %s', DB_FILE)
        print('[失败] 数据库文件不存在！')
        return

    db_bytes = DB_FILE.read_bytes()
    note = '这是测试邮件，验证备份配置是否可用。' if args.test else '每日自动备份。'
    try:
        send_backup(cfg, db_bytes, note)
        logging.info('备份邮件发送成功, %d 字节', len(db_bytes))
        print(f'[成功] 备份邮件已发送: {len(db_bytes)} 字节 → {cfg["receiver"]}')
    except Exception as e:
        logging.error('备份邮件发送失败: %s', e)
        print(f'[失败] 邮件发送失败: {e}')


if __name__ == '__main__':
    main()
