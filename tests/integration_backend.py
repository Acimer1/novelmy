"""在新目录运行真实 Flask 服务，仅替换外部书源；不启动桌面程序。"""
import importlib.util
import io
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path

TEXT = ('联调样章，验证文件与分卷内容。\r\n' * 18000).encode()
FAN = {'book_id': '10001', 'book_name': '番茄联调样书', 'author': '测试作者'}
CAT = {'id': '20001', 'title': '七猫联调样书', 'author': '测试作者'}


def content(fmt):
    if fmt == 'txt':
        return TEXT
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        archive.writestr('mimetype', 'application/epub+zip')
        archive.writestr('chapter.txt', TEXT)
    return out.getvalue()


def setup():
    project = Path(__file__).resolve().parents[1]
    base = project / '.integration'
    base.mkdir(exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='session-', dir=base))
    from unittest.mock import patch
    spec = importlib.util.spec_from_file_location('backend.server', project / 'backend' / 'server.py')
    s = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, {'NOVELMY_TEST_ROOT': str(root)}):
        spec.loader.exec_module(s)
    assert s.DB_PATH == root / 'app.db'
    jobs = []

    def desktop(action, payload=None):
        if action == 'search':
            return {'items': [FAN]}
        if action == 'book_detail':
            return FAN
        if action == 'create_download':
            fmt = payload['file_format']
            (s.DOWNLOAD_DIR / f'{FAN["book_name"]} - {FAN["author"]}.{fmt}').write_bytes(content(fmt))
            job = {'id': str(len(jobs)+1), 'book_id': FAN['book_id'], 'status': 'done'}
            jobs.append(job)
            return {**job, 'status': 'queued'}
        if action == 'list_jobs':
            return {'items': jobs}
        raise ValueError(action)

    s.invoke_tauri = desktop
    s.resolve_short_url = lambda url: {'url': url}
    s.get_cdp_ws_url = lambda: None
    s.check_exe = lambda: False
    s.qimao_api.search_books = lambda keyword: [CAT]
    s.qimao_api.fetch_book_info = lambda book_id: {'book': (
        {**CAT, 'id': '20002', 'title': '七猫第二册'} if str(book_id) == '20002' else CAT
    )}
    s.qimao_api.fetch_chapter_list = lambda book_id: [{'title': '联调样章'}]
    s.qimao_downloader.download_book = lambda info, chapters, fmt: content(fmt)
    s.init_db()
    with sqlite3.connect(s.DB_PATH) as db:
        db.execute('INSERT INTO card_keys(code,quota) VALUES (?,?)', ('LOCAL-TEST', 4))
        hashed, salt = s.hash_password('local-test-admin')
        db.execute('UPDATE users SET password_hash=?,salt=? WHERE username=?',(hashed,salt,'admin'))
    return s


if __name__ == '__main__':
    setup().app.run(host='127.0.0.1', port=5086, use_reloader=False)
