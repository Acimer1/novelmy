import io
import sqlite3
import time
import unittest
import zipfile
from pathlib import Path
from urllib.parse import quote

from .integration_backend import FAN, CAT, TEXT, setup


class LiveFlows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = setup()

    def test_account_download_files_and_admin(self):
        c = self.s.app.test_client()
        admin = self.s.app.test_client()
        account = dict(username='reader-test', password='local-reader-test')

        def post(path, data, client=c, status=200):
            r = client.post('/api/'+path, json=data)
            self.assertEqual(r.status_code, status, r.get_json()); return r.get_json()

        def get(path):
            r = c.get('/api/'+path); self.assertEqual(r.status_code,200); return r.get_json()

        def file(path):
            with c.get('/api/'+path) as r:
                self.assertEqual(r.status_code,200); return r.get_data()

        self.assertEqual(c.get('/api/files').status_code,401)
        post('auth/register',account); post('auth/login',account)
        self.assertEqual(c.get('/api/admin/users').status_code,403)
        post('download',{'book_id':FAN['book_id']},status=403)
        self.assertEqual(post('card/redeem',{'code':'LOCAL-TEST'})['quota'],4)
        self.assertEqual(c.post('/api/card/redeem',json={'code':'LOCAL-TEST'}).status_code,400)
        self.assertEqual(get('search?q=test')['items'][0]['book_id'],FAN['book_id'])
        self.assertEqual(get('book_detail?book_id=10001')['book_name'],FAN['book_name'])
        fq=post('download',{'url':'10001','format':'txt'})
        self.assertEqual(fq['quota'],3); self.assertEqual(get('jobs')['items'][0]['status'],'done')
        self.assertTrue(post('finish_download',fq)['file_found'])
        post('download',{'book_id':'10001'},status=409)
        self.assertEqual(get('qimao/search?q=test')['items'][0]['id'],CAT['id'])
        self.assertTrue(get('qimao/chapters?book_id=20001')['chapters'])
        self.assertEqual(get('qimao/book_detail?book_id=20001')['book']['title'],CAT['title'])
        cat=post('qimao/download',{'book_id':CAT['id'],'format':'epub'}); self.assertEqual(cat['quota'],2)
        post('qimao/download',{'book_id':CAT['id']},status=409)
        files=get('files')['files']; self.assertEqual(len(files),2)
        self.assertEqual({f['source'] for f in files},{'fanqie','qimao'})
        self.assertTrue(all(f['size']>0 for f in files)); self.assertEqual(get('files?per_page=1&page=2')['page'],2)
        self.assertEqual(file('file/'+quote(FAN['book_name'])),TEXT)
        with zipfile.ZipFile(io.BytesIO(file('qimao/file/'+quote(CAT['title'])))) as archive:
            self.assertEqual(archive.read('chapter.txt'),TEXT)
        fname=next(f['file_name'] for f in files if f['source']=='fanqie')
        tid=post('novels/split',{'filename':fname,'chunkSizeMB':0.5})['taskId']
        for _ in range(100):
            d=get('novels/split/'+tid)
            if d['status']!='running': break
            time.sleep(0.05)
        self.assertEqual(d['status'],'done'); self.assertGreater(len(d['outputFiles']),1)
        self.assertEqual(b''.join(file('novels/download/'+quote(Path(fname).stem)+'/'+quote(f['name'])) for f in d['outputFiles']),TEXT)
        self.assertEqual(get('auth/me')['user']['download_quota'],2)
        a=post('auth/login',{'username':'admin','password':'local-test-admin'},admin)['user']
        self.assertEqual(post('qimao/download',{'book_id':CAT['id'],'format':'txt'},admin)['quota'],a['download_quota'])
        post('admin/users',dict(username='manage-test',password='local-manage-test',quota=2),admin)
        uid=admin.get('/api/admin/users?q=manage-test').json['users'][0]['id']; path=f'admin/users/{uid}/'
        post(path+'quota',{'delta':3},admin); post(path+'disable',{},admin)
        post('auth/login',dict(username='manage-test',password='local-manage-test'),status=403)
        post(path+'enable',{},admin)
        self.assertEqual(admin.delete('/api/'+path.rstrip('/')).status_code,200)
        with sqlite3.connect(self.s.DB_PATH) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM downloads WHERE user_id=?',(get('auth/me')['user']['id'],)).fetchone()[0],2)
        post('auth/logout',{}); self.assertFalse(get('auth/me')['logged_in'])

if __name__ == '__main__':
    unittest.main()
