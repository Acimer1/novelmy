#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说下载器 - Web版
通过CDP调用exe的Tauri命令实现下载
"""

import os
import json
import time
import shutil
import subprocess
import requests
import websocket
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder='web_static')
CORS(app)

# 配置
DOWNLOAD_DIR = Path('C:/Users/acimer/Downloads/FanqieNovels')
WEB_DIR = Path(__file__).parent / 'web_downloads'
CONFIG_FILE = Path(os.environ.get('APPDATA', '')) / 'com.pofl.fanqienoveldownloader' / 'rust_state.json'
EXE_PATH = Path(__file__).parent / 'fanqie-desktop.exe'
CDP_PORT = 9222

WEB_DIR.mkdir(exist_ok=True)


def get_book_id(url):
    """从URL提取book_id"""
    import re
    m = re.search(r'book_id=(\d+)', url)
    if m: return m.group(1)
    m = re.search(r'/page/(\d+)', url)
    return m.group(1) if m else None


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
    """启动exe（带DevTools）"""
    if check_exe():
        return True

    if EXE_PATH.exists():
        env = os.environ.copy()
        env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = f'--remote-debugging-port={CDP_PORT} --remote-allow-origins=*'
        subprocess.Popen(str(EXE_PATH), env=env)
        time.sleep(5)
        return check_exe()
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


def sync_files():
    """同步文件到web目录"""
    count = 0
    if not CONFIG_FILE.exists():
        return 0
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


def get_file_list():
    """获取文件列表"""
    files = []
    for f in WEB_DIR.glob('*.txt'):
        name = f.stem
        parts = name.rsplit(' - ', 1)
        book_name = parts[0] if parts else name
        author = parts[1] if len(parts) > 1 else ''
        files.append({
            'book_name': book_name,
            'author': author,
            'size': f.stat().st_size,
            'mtime': time.strftime('%Y-%m-%d %H:%M', time.localtime(f.stat().st_mtime))
        })
    return sorted(files, key=lambda x: x['mtime'], reverse=True)


# ==================== API ====================

@app.route('/')
def index():
    return send_file('web_static/index.html')


@app.route('/api/info')
def api_info():
    ws_url = get_cdp_ws_url()
    return jsonify({
        'exe_running': check_exe(),
        'cdp_connected': ws_url is not None,
        'files': len(get_file_list()),
        'download_dir': str(WEB_DIR)
    })


@app.route('/api/search')
def api_search():
    """搜索小说"""
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify({'error': '请输入关键词'}), 400

    result = invoke_tauri('search', {'query': keyword})
    return jsonify(result)


@app.route('/api/download', methods=['POST'])
def api_download():
    """下载小说"""
    data = request.get_json() or {}
    url = data.get('url', '')
    book_id = data.get('book_id', '')

    # 从URL提取book_id
    if url and not book_id:
        book_id = get_book_id(url)

    if not book_id:
        return jsonify({'error': '无法识别书籍ID'}), 400

    # 先获取书籍信息
    detail = invoke_tauri('book_detail', {'book_id': book_id})
    if 'error' in detail:
        return jsonify({'error': '获取书籍信息失败'}), 500

    # 创建下载任务
    save_dir = str(DOWNLOAD_DIR).replace('\\', '/')
    result = invoke_tauri('create_download', {
        'book_id': book_id,
        'book_name': detail.get('book_name', ''),
        'author': detail.get('author', ''),
        'book_input': book_id,
        'save_dir': save_dir,
        'file_format': 'txt',
        'overwrite_existing': True,
        'chapter_start': None,
        'chapter_end': None
    })

    if 'error' in result:
        return jsonify({'error': result['error']}), 500

    return jsonify({
        'success': True,
        'job_id': result.get('id', ''),
        'book_name': detail.get('book_name', ''),
        'author': detail.get('author', ''),
        'status': result.get('status', 'queued')
    })


@app.route('/api/jobs')
def api_jobs():
    """查询下载任务状态"""
    result = invoke_tauri('list_jobs', {})
    return jsonify(result)


@app.route('/api/files')
def api_files():
    """获取文件列表"""
    sync_files()
    return jsonify({'files': get_file_list()})


@app.route('/api/sync', methods=['POST'])
def api_sync():
    """手动同步"""
    count = sync_files()
    return jsonify({
        'success': True,
        'new_files': count,
        'files': get_file_list()
    })


@app.route('/api/file/<book_name>')
def api_file(book_name):
    """下载文件"""
    from urllib.parse import unquote
    book_name = unquote(book_name)
    for f in WEB_DIR.glob('*.txt'):
        if book_name in f.stem:
            return send_file(f, as_attachment=True, download_name=f.name)
    return jsonify({'error': '文件不存在'}), 404


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    print("同步已下载文件...")
    n = sync_files()
    print(f"同步了 {n} 个文件")

    print("启动exe...")
    start_exe()

    print("=" * 50)
    print(f"  番茄小说下载器 http://localhost:{args.port}")
    print("=" * 50)

    app.run(host='0.0.0.0', port=args.port, threaded=True)