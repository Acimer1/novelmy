"""
七猫(灵猫)小说 API 客户端
从 Flutter lib/core/api_client.dart 移植
"""

import hashlib
import base64
import re
import random
from urllib.parse import urlencode

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def _strip_html_tags(text: str) -> str:
    """去除HTML标签，如搜索高亮的 <font color='#ff4242'>xxx</font>"""
    if not text:
        return text
    return re.sub(r'<[^>]*>', '', text)


class QimaoApiClient:
    """七猫小说 API 客户端，处理签名、请求头伪装、AES解密"""

    # 签名密钥
    SIGN_KEY = 'd3dGiJc651gSQ8w1'
    # AES-128 密钥 hex → "242ccb8230d709e1"
    AES_KEY_HEX = '32343263636238323330643730396531'
    AES_KEY = bytes.fromhex(AES_KEY_HEX)  # 16 bytes

    # API 节点
    BASE_URL_BC = 'https://api-bc.wtzw.com'
    BASE_URL_KS = 'https://api-ks.wtzw.com'

    # 伪装 app 版本号池
    VERSION_LIST = [
        '73720', '73700', '73680', '73660', '73640',
        '73620', '73600', '73580', '73560', '73540',
        '73520', '73500', '73480', '73460', '73440',
        '73420', '73400', '73380', '73360', '73340',
        '62112',
    ]

    def __init__(self):
        self.session = requests.Session()

    # ── 签名算法 ──────────────────────────────────────

    def _generate_signature(self, params: dict, key: str) -> str:
        """参数按 key 排序拼接 k=v + 密钥，整体 MD5"""
        sorted_keys = sorted(params.keys())
        sign_str = ''.join(f'{k}={params[k]}' for k in sorted_keys) + key
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    # ── 请求头伪装 ──────────────────────────────────────

    def _get_headers(self, book_id: str = '0') -> dict:
        """生成带签名的请求头，用 book_id 做种子随机选版本号"""
        rng = random.Random()
        rng.seed(hash(book_id))
        version = rng.choice(self.VERSION_LIST)

        headers = {
            'AUTHORIZATION': '',
            'app-version': version,
            'application-id': 'com.****.reader',
            'channel': 'unknown',
            'net-env': '1',
            'platform': 'android',
            'qm-params': '',
            'reg': '0',
        }
        headers['sign'] = self._generate_signature(headers, self.SIGN_KEY)
        return headers

    # ── API 端点 ──────────────────────────────────────

    def search_books(self, keyword: str) -> list:
        """搜索书籍"""
        params = {
            'extend': '',
            'tab': '0',
            'gender': '0',
            'refresh_state': '8',
            'page': '1',
            'wd': keyword,
            'is_short_story_user': '0',
        }
        params['sign'] = self._generate_signature(params, self.SIGN_KEY)

        url = f'{self.BASE_URL_BC}/search/v1/words?{urlencode(params)}'
        r = self.session.get(url, headers=self._get_headers('0'), timeout=15)
        r.raise_for_status()
        data = r.json()
        books = data.get('data', {}).get('books', [])
        # 清理搜索高亮的HTML标签
        for b in books:
            if 'title' in b:
                b['title'] = _strip_html_tags(b['title'])
            if 'author' in b:
                b['author'] = _strip_html_tags(b['author'])
            if 'intro' in b:
                b['intro'] = _strip_html_tags(b['intro'])
        return books

    def fetch_book_info(self, book_id: str) -> dict:
        """获取书籍详情"""
        params = {
            'id': book_id,
            'imei_ip': '2937357107',
            'teeny_mode': '0',
        }
        params['sign'] = self._generate_signature(params, self.SIGN_KEY)

        url = f'{self.BASE_URL_BC}/api/v4/book/detail?{urlencode(params)}'
        r = self.session.get(url, headers=self._get_headers(book_id), timeout=15)
        r.raise_for_status()
        return r.json().get('data', {})

    def fetch_chapter_list(self, book_id: str) -> list:
        """获取章节目录，按 chapter_sort 排序"""
        params = {
            'chapter_ver': '0',
            'id': book_id,
        }
        params['sign'] = self._generate_signature(params, self.SIGN_KEY)

        url = f'{self.BASE_URL_KS}/api/v1/chapter/chapter-list?{urlencode(params)}'
        r = self.session.get(url, headers=self._get_headers(book_id), timeout=15)
        r.raise_for_status()
        data = r.json().get('data', {})
        chapters = data.get('chapter_lists', [])
        if isinstance(chapters, list):
            chapters.sort(key=lambda c: int(c.get('chapter_sort', 0)))
        return chapters

    def get_cache_zip_link(self, book_id: str) -> str:
        """获取缓存 ZIP 下载链接"""
        params = {
            'id': book_id,
            'source': '1',
            'type': '2',
            'is_vip': '1',
        }
        params['sign'] = self._generate_signature(params, self.SIGN_KEY)

        url = f'{self.BASE_URL_BC}/api/v1/book/download?{urlencode(params)}'
        r = self.session.get(url, headers=self._get_headers(book_id), timeout=15)
        r.raise_for_status()
        return r.json().get('data', {}).get('link', '')

    # ── AES 解密 ──────────────────────────────────────

    @staticmethod
    def decrypt_chapter_content(encrypted_content: str) -> str:
        """
        AES-128-CBC 解密章节内容
        密文前 16 字节是 IV，剩余为密文
        """
        encrypted_bytes = base64.b64decode(encrypted_content)
        iv = encrypted_bytes[:16]
        ciphertext = encrypted_bytes[16:]

        cipher = AES.new(QimaoApiClient.AES_KEY, AES.MODE_CBC, iv=iv)
        decrypted = cipher.decrypt(ciphertext)

        # 去除 PKCS7 padding
        return unpad(decrypted, 16).decode('utf-8', errors='replace')
