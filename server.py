#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说下载器 - Web版（多用户版）
通过CDP调用exe的Tauri命令实现下载，支持账号登录与用户隔离
"""

import os
import json
import time
import shutil
import subprocess
import sqlite3
import hashlib
import secrets
import re
import requests
import websocket
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify, send_file, session, g
from flask_cors import CORS
from qimao_api import QimaoApiClient
from qimao_downloader import QimaoBookDownloader

app = Flask(__name__, static_folder='web_static')
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

# 配置
DOWNLOAD_DIR = Path('C:/Users/acimer/Downloads/FanqieNovels')
WEB_DIR = Path(__file__).parent / 'web_downloads'
CONFIG_FILE = Path(os.environ.get('APPDATA', '')) / 'com.pofl.fanqienoveldownloader' / 'rust_state.json'
EXE_PATH = Path(__file__).parent / 'fanqie-desktop.exe'
DB_PATH = Path(__file__).parent / 'app.db'
CDP_PORT = 9222

WEB_DIR.mkdir(exist_ok=True)

# Qimao (灵猫/七猫) 配置
qimao_api = QimaoApiClient()
qimao_downloader = QimaoBookDownloader(qimao_api)


# ==================== 数据库 ====================

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库，建表并创建admin账号"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_disabled INTEGER DEFAULT 0,
            download_quota INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_name TEXT NOT NULL,
            author TEXT DEFAULT '',
            book_id TEXT,
            file_name TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            download_time TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # 创建admin账号（如不存在）
    cur = conn.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    if not cur.fetchone():
        salt = secrets.token_hex(16)
        pw_hash = hashlib.sha256((salt + 'rem123456').encode()).hexdigest()
        conn.execute(
            'INSERT INTO users (username, password_hash, salt, is_admin, download_quota) VALUES (?, ?, ?, 1, 999999)',
            ('admin', pw_hash, salt)
        )
        print('已创建管理员账号: admin / rem123456')

    # 迁移：添加 source 字段（区分番茄/灵猫下载）
    try:
        conn.execute('ALTER TABLE downloads ADD COLUMN source TEXT DEFAULT "fanqie"')
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# ==================== 密码与认证 ====================

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return pw_hash, salt


def verify_password(password, pw_hash, salt):
    return hashlib.sha256((salt + password).encode()).hexdigest() == pw_hash


def current_user():
    """从session获取当前用户，返回dict或None"""
    sid = session.get('sid')
    if not sid:
        return None
    db = get_db()
    row = db.execute(
        '''SELECT u.* FROM users u JOIN sessions s ON u.id = s.user_id
           WHERE s.session_id = ?''', (sid,)
    ).fetchone()
    if not row:
        session.pop('sid', None)
        return None
    return dict(row)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({'error': '请先登录'}), 401
        if user['is_disabled']:
            return jsonify({'error': '账号已被禁用'}), 403
        g.user = user
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({'error': '请先登录'}), 401
        if not user['is_admin']:
            return jsonify({'error': '无权限'}), 403
        g.user = user
        return f(*args, **kwargs)
    return wrapper


# ==================== exe与CDP（原有逻辑，不改动） ====================

def get_book_id(url):
    """从URL提取book_id"""
    import re
    m = re.search(r'book_id=(\d+)', url)
    if m: return m.group(1)
    m = re.search(r'/page/(\d+)', url)
    return m.group(1) if m else None


def resolve_short_url(url):
    """短链接跟随302拿到长链接，再提取book_id"""
    try:
        r = requests.head(url, allow_redirects=True, timeout=8,
                          headers={'User-Agent': 'Mozilla/5.0'})
        final = r.url
        bid = get_book_id(final)
        return {'url': final, 'book_id': bid}
    except Exception as e:
        return {'url': url, 'book_id': None, 'error': str(e)}


def check_exe():
    """检查exe是否运行"""
    try:
        import psutil
        for p in psutil.process_iter(['name']):
            if 'fanqie-desktop.exe' in p.info.get('name', ''):
                return True
    except:
        pass
    return False


def start_exe():
    """启动exe（带DevTools），如果已有进程但CDP不通则先杀掉重启"""
    # 检查CDP是否已经可用
    try:
        r = requests.get(f'http://127.0.0.1:{CDP_PORT}/json/list', timeout=2)
        if r.status_code == 200 and r.json():
            return True
    except:
        pass

    # CDP不可用，杀掉旧进程
    if check_exe():
        try:
            import psutil
            for p in psutil.process_iter(['name']):
                if 'fanqie-desktop.exe' in p.info.get('name', ''):
                    p.kill()
        except:
            pass
        time.sleep(2)

    # 带CDP参数启动
    if EXE_PATH.exists():
        env = os.environ.copy()
        env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = f'--remote-debugging-port={CDP_PORT} --remote-allow-origins=*'
        subprocess.Popen(str(EXE_PATH), env=env)
        time.sleep(5)
        try:
            r = requests.get(f'http://127.0.0.1:{CDP_PORT}/json/list', timeout=3)
            return r.status_code == 200 and bool(r.json())
        except:
            pass
    return False


def get_cdp_ws_url():
    """获取CDP WebSocket URL"""
    try:
        r = requests.get(f'http://127.0.0.1:{CDP_PORT}/json/list', timeout=3)
        targets = r.json()
        if targets:
            return targets[0]['webSocketDebuggerUrl']
    except:
        pass
    return None


def invoke_tauri(action, payload=None):
    """调用Tauri命令"""
    ws_url = get_cdp_ws_url()
    if not ws_url:
        return {'error': '无法连接到exe'}
    try:
        ws = websocket.create_connection(ws_url, timeout=30)
        cmd = {
            'id': 1,
            'method': 'Runtime.evaluate',
            'params': {
                'expression': f'''
                (async () => {{
                    try {{
                        const result = await window.__TAURI__.core.invoke('dispatch', {{
                            action: '{action}',
                            payload: {json.dumps(payload or {}, ensure_ascii=False)}
                        }});
                        return JSON.stringify(result);
                    }} catch(e) {{
                        return JSON.stringify({{error: e.toString()}});
                    }}
                }})()
                ''',
                'awaitPromise': True,
                'returnByValue': True
            }
        }
        ws.send(json.dumps(cmd))
        result = json.loads(ws.recv())
        ws.close()
        value = result.get('result', {}).get('result', {}).get('value', '{}')
        if isinstance(value, str):
            return json.loads(value)
        return value
    except Exception as e:
        return {'error': str(e)}


# ==================== 文件同步与用户隔离 ====================

def sync_files_to_web():
    """把exe下载的文件同步到web目录（物理层，不分用户）"""
    count = 0
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text('utf-8'))
            for item in data.get('history', []):
                if item.get('file_exists'):
                    src = Path(item['save_path'])
                    if src.exists():
                        dst = WEB_DIR / src.name
                        if not dst.exists():
                            shutil.copy2(src, dst)
                            count += 1
        except:
            pass
    if DOWNLOAD_DIR.exists():
        for f in DOWNLOAD_DIR.glob('*.txt'):
            if f.stat().st_size > 1000:
                dst = WEB_DIR / f.name
                if not dst.exists():
                    shutil.copy2(f, dst)
                    count += 1
    return count


def record_download_for_user(user_id, book_name, author, book_id, file_name, file_size, source='fanqie'):
    """为用户记录一次下载（去重：同一用户同一本书只记一次）"""
    db = get_db()
    existing = db.execute(
        'SELECT id FROM downloads WHERE user_id=? AND file_name=?',
        (user_id, file_name)
    ).fetchone()
    if existing:
        # 已有记录，更新信息
        db.execute(
            'UPDATE downloads SET book_name=?, author=?, book_id=?, file_size=?, source=?, download_time=CURRENT_TIMESTAMP WHERE id=?',
            (book_name, author, book_id, file_size, source, existing['id'])
        )
    else:
        db.execute(
            'INSERT INTO downloads (user_id, book_name, author, book_id, file_name, file_size, source) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, book_name, author, book_id, file_name, file_size, source)
        )
    db.commit()


def get_file_list_for_user(user_id):
    """获取指定用户的文件列表"""
    db = get_db()
    rows = db.execute(
        'SELECT book_name, author, file_name, file_size, source, download_time FROM downloads WHERE user_id=? ORDER BY download_time DESC',
        (user_id,)
    ).fetchall()
    files = []
    for r in rows:
        files.append({
            'book_name': r['book_name'],
            'author': r['author'],
            'file_name': r['file_name'],
            'size': r['file_size'],
            'source': r['source'] or 'fanqie',
            'mtime': r['download_time']
        })
    return files


def find_physical_file(file_name):
    """在web目录查找物理文件（容忍异体字差异）"""
    # 1. 精确匹配
    p = WEB_DIR / file_name
    if p.exists():
        return p
    # 2. 用书名部分模糊匹配（文件名格式：书名 - 作者.txt）
    # 提取书名（去掉后缀和作者）
    stem = file_name.rsplit('.txt', 1)[0]
    book_part = stem.rsplit(' - ', 1)[0] if ' - ' in stem else stem
    # 取书名前几个字作为匹配关键词（异体字常出现在生僻字上）
    key = book_part[:4] if len(book_part) >= 4 else book_part
    for f in WEB_DIR.glob('*.txt'):
        if key and key in f.name:
            return f
    # 3. 退一步：用整个文件名做子串匹配
    for f in WEB_DIR.glob('*.txt'):
        if file_name in f.name or f.stem == stem:
            return f
    return None


# ==================== 认证 API ====================

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    if len(username) < 2 or len(username) > 20:
        return jsonify({'error': '用户名长度2-20字符'}), 400
    if len(password) < 6:
        return jsonify({'error': '密码至少6位'}), 400
    if username == 'admin':
        return jsonify({'error': '该用户名已存在'}), 400

    db = get_db()
    if db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
        return jsonify({'error': '用户名已存在'}), 400

    pw_hash, salt = hash_password(password)
    db.execute(
        'INSERT INTO users (username, password_hash, salt, download_quota) VALUES (?, ?, ?, 0)',
        (username, pw_hash, salt)
    )
    db.commit()
    return jsonify({'success': True, 'message': '注册成功，请登录'})


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    db = get_db()
    row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    if not row or not verify_password(password, row['password_hash'], row['salt']):
        return jsonify({'error': '用户名或密码错误'}), 401
    if row['is_disabled']:
        return jsonify({'error': '账号已被禁用，请联系管理员'}), 403

    sid = secrets.token_hex(32)
    db.execute('INSERT INTO sessions (session_id, user_id) VALUES (?, ?)', (sid, row['id']))
    # 清理该用户旧session（只保留最新）
    db.execute('DELETE FROM sessions WHERE user_id=? AND session_id!=?', (row['id'], sid))
    db.commit()

    session['sid'] = sid
    return jsonify({
        'success': True,
        'user': {
            'id': row['id'],
            'username': row['username'],
            'is_admin': bool(row['is_admin']),
            'download_quota': row['download_quota']
        }
    })


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    sid = session.get('sid')
    if sid:
        db = get_db()
        db.execute('DELETE FROM sessions WHERE session_id=?', (sid,))
        db.commit()
    session.pop('sid', None)
    return jsonify({'success': True})


@app.route('/api/auth/me')
def auth_me():
    user = current_user()
    if not user:
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'is_admin': bool(user['is_admin']),
            'is_disabled': bool(user['is_disabled']),
            'download_quota': user['download_quota']
        }
    })


# ==================== 管理员 API ====================

@app.route('/api/admin/users')
@admin_required
def admin_list_users():
    db = get_db()
    rows = db.execute(
        '''SELECT u.id, u.username, u.is_admin, u.is_disabled, u.download_quota, u.created_at,
           (SELECT COUNT(*) FROM downloads d WHERE d.user_id = u.id) as download_count
           FROM users u ORDER BY u.is_admin DESC, u.id ASC'''
    ).fetchall()
    users = [dict(r) for r in rows]
    return jsonify({'users': users})


@app.route('/api/admin/users', methods=['POST'])
@admin_required
def admin_create_user():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    quota = data.get('quota', 0)

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    if len(password) < 6:
        return jsonify({'error': '密码至少6位'}), 400

    db = get_db()
    if db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
        return jsonify({'error': '用户名已存在'}), 400

    pw_hash, salt = hash_password(password)
    db.execute(
        'INSERT INTO users (username, password_hash, salt, download_quota) VALUES (?, ?, ?, ?)',
        (username, pw_hash, salt, int(quota))
    )
    db.commit()
    return jsonify({'success': True})


@app.route('/api/admin/users/<int:uid>', methods=['DELETE'])
@admin_required
def admin_delete_user(uid):
    if uid == g.user['id']:
        return jsonify({'error': '不能删除自己'}), 400
    db = get_db()
    row = db.execute('SELECT is_admin FROM users WHERE id=?', (uid,)).fetchone()
    if not row:
        return jsonify({'error': '用户不存在'}), 404
    if row['is_admin']:
        return jsonify({'error': '不能删除管理员'}), 400
    db.execute('DELETE FROM downloads WHERE user_id=?', (uid,))
    db.execute('DELETE FROM sessions WHERE user_id=?', (uid,))
    db.execute('DELETE FROM users WHERE id=?', (uid,))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/admin/users/<int:uid>/disable', methods=['POST'])
@admin_required
def admin_disable_user(uid):
    if uid == g.user['id']:
        return jsonify({'error': '不能禁用自己'}), 400
    db = get_db()
    row = db.execute('SELECT is_admin FROM users WHERE id=?', (uid,)).fetchone()
    if not row:
        return jsonify({'error': '用户不存在'}), 404
    if row['is_admin']:
        return jsonify({'error': '不能禁用管理员'}), 400
    db.execute('UPDATE users SET is_disabled=1 WHERE id=?', (uid,))
    db.execute('DELETE FROM sessions WHERE user_id=?', (uid,))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/admin/users/<int:uid>/enable', methods=['POST'])
@admin_required
def admin_enable_user(uid):
    db = get_db()
    if not db.execute('SELECT id FROM users WHERE id=?', (uid,)).fetchone():
        return jsonify({'error': '用户不存在'}), 404
    db.execute('UPDATE users SET is_disabled=0 WHERE id=?', (uid,))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/admin/users/<int:uid>/quota', methods=['POST'])
@admin_required
def admin_add_quota(uid):
    data = request.get_json() or {}
    delta = int(data.get('delta', 0))
    if delta == 0:
        return jsonify({'error': '次数不能为0'}), 400
    db = get_db()
    row = db.execute('SELECT download_quota FROM users WHERE id=?', (uid,)).fetchone()
    if not row:
        return jsonify({'error': '用户不存在'}), 404
    new_quota = max(0, row['download_quota'] + delta)
    db.execute('UPDATE users SET download_quota=? WHERE id=?', (new_quota, uid))
    db.commit()
    return jsonify({'success': True, 'quota': new_quota})


# ==================== 业务 API（需登录） ====================

@app.route('/')
def index():
    return send_file('web_static/index.html')


@app.route('/api/info')
@login_required
def api_info():
    ws_url = get_cdp_ws_url()
    return jsonify({
        'exe_running': check_exe(),
        'cdp_connected': ws_url is not None,
        'files': len(get_file_list_for_user(g.user['id'])),
        'download_dir': str(WEB_DIR),
        'quota': g.user['download_quota']
    })


@app.route('/api/search')
@login_required
def api_search():
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify({'error': '请输入关键词'}), 400
    result = invoke_tauri('search', {'query': keyword})
    return jsonify(result)


@app.route('/api/book_detail')
@login_required
def api_book_detail():
    """获取番茄书籍详情（通过CDP）"""
    book_id = request.args.get('book_id', '')
    if not book_id:
        return jsonify({'error': '缺少book_id'}), 400
    detail = invoke_tauri('book_detail', {'book_id': book_id})
    if 'error' in detail:
        return jsonify({'error': detail['error']}), 500
    return jsonify(detail)


@app.route('/api/download', methods=['POST'])
@login_required
def api_download():
    """下载小说"""
    # 管理员也可以下载（不扣减配额）
    is_admin = g.user['is_admin']

    # 检查次数
    if g.user['download_quota'] <= 0:
        return jsonify({'error': '下载次数不足，请联系管理员'}), 403

    data = request.get_json() or {}
    url = data.get('url', '')
    book_id = data.get('book_id', '')
    fmt = data.get('format', 'txt')
    if fmt not in ('txt', 'epub'):
        fmt = 'txt'

    # 从输入中提取纯URL
    if url and not book_id:
        m = re.search(r'(https?://[^\s\u4e00-\u9fff]+)', url)
        if m:
            url = m.group(1).rstrip('/')

    if url and not book_id:
        book_id = get_book_id(url)

    if not book_id and url:
        resolved = resolve_short_url(url)
        if resolved.get('book_id'):
            book_id = resolved['book_id']

    if not book_id:
        return jsonify({'error': '无法识别书籍ID，可能是短链接解析失败'}), 400

    # 获取书籍信息
    detail = invoke_tauri('book_detail', {'book_id': book_id})
    if 'error' in detail:
        return jsonify({'error': '获取书籍信息失败'}), 500

    book_name = detail.get('book_name', '')
    author = detail.get('author', '')

    # 创建下载任务
    save_dir = str(DOWNLOAD_DIR).replace('\\', '/')
    result = invoke_tauri('create_download', {
        'book_id': book_id,
        'book_name': book_name,
        'author': author,
        'book_input': book_id,
        'save_dir': save_dir,
        'file_format': fmt,
        'overwrite_existing': True,
        'chapter_start': None,
        'chapter_end': None
    })

    if 'error' in result:
        return jsonify({'error': result['error']}), 500

    # 下载任务创建成功，扣减次数（管理员不扣减）
    if not is_admin:
        db = get_db()
        new_quota = g.user['download_quota'] - 1
        db.execute('UPDATE users SET download_quota=? WHERE id=?', (new_quota, g.user['id']))
        db.commit()
    else:
        new_quota = g.user['download_quota']

    return jsonify({
        'success': True,
        'job_id': result.get('id', ''),
        'book_name': book_name,
        'author': author,
        'book_id': book_id,
        'status': result.get('status', 'queued'),
        'quota': new_quota
    })


@app.route('/api/jobs')
@login_required
def api_jobs():
    result = invoke_tauri('list_jobs', {})
    return jsonify(result)


@app.route('/api/files')
@login_required
def api_files():
    """获取当前用户的文件列表"""
    sync_files_to_web()
    return jsonify({'files': get_file_list_for_user(g.user['id'])})


@app.route('/api/sync', methods=['POST'])
@login_required
def api_sync():
    """同步文件并记录到当前用户"""
    sync_files_to_web()
    return jsonify({
        'success': True,
        'files': get_file_list_for_user(g.user['id'])
    })


@app.route('/api/finish_download', methods=['POST'])
@login_required
def api_finish_download():
    """下载完成后，把文件记录到当前用户名下"""
    data = request.get_json() or {}
    book_name = data.get('book_name', '')
    author = data.get('author', '')
    book_id = data.get('book_id', '')
    file_name = data.get('file_name', '')

    if not file_name and book_name:
        file_name = f"{book_name} - {author}.txt" if author else f"{book_name}.txt"

    if not file_name:
        return jsonify({'error': '缺少文件名'}), 400

    # 同步物理文件
    sync_files_to_web()

    # 查找物理文件，用物理文件的真实名存库（避免异体字导致不匹配）
    physical = find_physical_file(file_name)
    if physical:
        actual_name = physical.name
        file_size = physical.stat().st_size
    else:
        actual_name = file_name
        file_size = 0

    record_download_for_user(g.user['id'], book_name, author, book_id, actual_name, file_size)
    return jsonify({'success': True, 'files': get_file_list_for_user(g.user['id'])})


@app.route('/api/file/<book_name>')
@login_required
def api_file(book_name):
    """下载文件（校验属于当前用户）"""
    from urllib.parse import unquote
    book_name = unquote(book_name)

    db = get_db()
    # 查当前用户名下是否有这本书
    rows = db.execute(
        'SELECT file_name, book_name FROM downloads WHERE user_id=?',
        (g.user['id'],)
    ).fetchall()

    matched_file = None
    for r in rows:
        fn = r['file_name']
        bn = r['book_name']
        # 多种匹配方式：file_name包含、book_name包含、去空格匹配
        if (book_name in fn or book_name in bn or
            book_name in fn.replace(' - ', ' ') or
            bn in book_name):
            matched_file = fn
            break

    if not matched_file:
        return jsonify({'error': '无权下载此文件或文件不存在'}), 403

    physical = find_physical_file(matched_file)
    if not physical:
        # 兜底：用book_name直接在目录里找
        physical = find_physical_file(book_name + '.txt')
    if not physical:
        return jsonify({'error': '物理文件不存在'}), 404

    return send_file(physical, as_attachment=True, download_name=physical.name)


# ==================== 灵猫/七猫 API ====================

@app.route('/api/qimao/search')
@login_required
def qimao_search():
    """搜索七猫小说"""
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify({'error': '请输入关键词'}), 400
    try:
        results = qimao_api.search_books(keyword)
        return jsonify({'items': results})
    except Exception as e:
        return jsonify({'error': f'搜索失败: {str(e)}'}), 500


@app.route('/api/qimao/book_detail')
@login_required
def qimao_book_detail():
    """获取七猫书籍详情"""
    book_id = request.args.get('book_id', '')
    if not book_id:
        return jsonify({'error': '缺少book_id'}), 400
    try:
        info = qimao_api.fetch_book_info(book_id)
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': f'获取详情失败: {str(e)}'}), 500


@app.route('/api/qimao/chapters')
@login_required
def qimao_chapters():
    """获取七猫章节目录"""
    book_id = request.args.get('book_id', '')
    if not book_id:
        return jsonify({'error': '缺少book_id'}), 400
    try:
        chapters = qimao_api.fetch_chapter_list(book_id)
        return jsonify({'chapters': chapters})
    except Exception as e:
        return jsonify({'error': f'获取章节失败: {str(e)}'}), 500


@app.route('/api/qimao/download', methods=['POST'])
@login_required
def qimao_download_start():
    """下载七猫小说"""
    is_admin = g.user['is_admin']
    if not is_admin and g.user['download_quota'] <= 0:
        return jsonify({'error': '下载次数不足，请联系管理员'}), 403

    data = request.get_json() or {}
    book_id = str(data.get('book_id', '')).strip()
    fmt = data.get('format', 'txt')
    if fmt not in ('txt', 'epub'):
        fmt = 'txt'

    if not book_id:
        return jsonify({'error': '缺少book_id'}), 400

    try:
        # 获取书籍信息和章节
        info = qimao_api.fetch_book_info(book_id)
        b = info.get('book', info)
        book_name = data.get('book_name') or b.get('title', '未知书名')
        author = data.get('author') or b.get('author', '未知作者')
        # 清理搜索高亮HTML标签
        book_name = re.sub(r'<[^>]*>', '', book_name)
        author = re.sub(r'<[^>]*>', '', author)
        chapters = qimao_api.fetch_chapter_list(book_id)

        if not chapters:
            return jsonify({'error': '未获取到章节列表'}), 500

        # 执行下载（阻塞，大书可能耗时较长）
        file_data = qimao_downloader.download_book(info, chapters, fmt=fmt)

        # 保存到 web_downloads
        safe_name = qimao_downloader.sanitize_filename(f'{book_name} - {author}.{fmt}')
        file_path = WEB_DIR / safe_name
        file_path.write_bytes(file_data)

        # 扣减次数（管理员不扣减）
        if not is_admin:
            db = get_db()
            new_quota = g.user['download_quota'] - 1
            db.execute('UPDATE users SET download_quota=? WHERE id=?', (new_quota, g.user['id']))
            db.commit()
        else:
            new_quota = g.user['download_quota']

        # 记录下载
        record_download_for_user(
            g.user['id'], book_name, author, book_id,
            safe_name, len(file_data), source='qimao'
        )

        return jsonify({
            'success': True,
            'book_name': book_name,
            'author': author,
            'book_id': book_id,
            'file_name': safe_name,
            'file_size': len(file_data),
            'format': fmt,
            'quota': new_quota
        })
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500


@app.route('/api/qimao/file/<book_name>')
@login_required
def qimao_get_file(book_name):
    """下载七猫小说文件（校验属于当前用户）"""
    from urllib.parse import unquote
    book_name = unquote(book_name)

    db = get_db()
    rows = db.execute(
        'SELECT file_name, book_name FROM downloads WHERE user_id=? AND source=?',
        (g.user['id'], 'qimao')
    ).fetchall()

    matched_file = None
    for r in rows:
        fn = r['file_name']
        bn = r['book_name']
        if (book_name in fn or book_name in bn or
            book_name in fn.replace(' - ', ' ') or
            bn in book_name):
            matched_file = fn
            break

    if not matched_file:
        return jsonify({'error': '无权下载此文件或文件不存在'}), 403

    physical = WEB_DIR / matched_file
    if not physical.exists():
        return jsonify({'error': '物理文件不存在'}), 404

    return send_file(physical, as_attachment=True, download_name=physical.name)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    print("初始化数据库...")
    init_db()

    print("同步已下载文件...")
    sync_files_to_web()

    print("启动exe...")
    start_exe()

    print("=" * 50)
    print(f"  番茄小说下载器（多用户版） http://localhost:{args.port}")
    print("=" * 50)

    app.run(host='0.0.0.0', port=args.port, threaded=True)
