"""在独立测试库中驱动 Chrome；浏览器配置和夹具均位于 .integration。"""
import os
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from werkzeug.serving import make_server
from .integration_backend import setup


class BrowserLive(unittest.TestCase):
    def test_online_ui(self):
        s = setup()
        driver = Path(__file__).with_name('live-flow.js')

        @s.app.get('/_acceptance/<role>')
        def acceptance(role):
            if role not in ('reader', 'admin'):
                return '', 404
            return ('<!doctype html><meta charset="utf-8"><body data-role="'+role+'">'
                    '<iframe style="width:100%;height:800px;border:0" src="/web_static/preview/index.html?mode=live"></iframe>'
                    '<script>'+driver.read_text(encoding='utf-8')+'</script>')

        http = make_server('127.0.0.1', 0, s.app, threaded=True)
        threading.Thread(target=http.serve_forever, daemon=True).start()
        try:
            for role, width in [('reader',390),('admin',1000)]:
                with self.subTest(role=role), tempfile.TemporaryDirectory(dir=s.DB_PATH.parent) as profile:
                    args = [os.environ['CHROME_BIN'], '--headless', '--disable-gpu', '--no-first-run',
                            '--disable-background-networking', '--disable-extensions', '--user-data-dir='+profile,
                            f'--window-size={width},900', '--virtual-time-budget=60000', '--dump-dom',
                            f'http://127.0.0.1:{http.server_port}/_acceptance/{role}']
                    proc=subprocess.run(args, capture_output=True, timeout=60)
                    dom=proc.stdout.decode('utf-8', errors='replace')
                    self.assertIn('data-result="passed"',dom.split('<iframe')[0],dom.split('<iframe')[0])
            with sqlite3.connect(s.DB_PATH) as db:
                self.assertEqual(db.execute("SELECT download_quota, is_disabled FROM users WHERE username='browser-reader'").fetchone(), (4, 0))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM downloads WHERE file_size>0").fetchone(), (3,))
        finally:
            http.shutdown();http.server_close()
