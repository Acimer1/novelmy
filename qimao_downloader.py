"""
七猫(灵猫)小说下载器
从 Flutter lib/core/book_downloader.dart + epub_builder.dart 移植
"""

import io
import re
import zipfile
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from qimao_api import QimaoApiClient


class QimaoBookDownloader:
    """七猫小说下载器：ZIP下载→解压→AES解密→TXT/EPUB"""

    def __init__(self, api_client: QimaoApiClient = None):
        self.api = api_client or QimaoApiClient()
        self.session = requests.Session()

    # ── 主流程 ──────────────────────────────────────────

    def download_book(
        self,
        book_info: dict,
        chapters: list,
        fmt: str = 'txt',
        progress_callback=None,
    ) -> bytes:
        """
        下载完整小说，返回文件字节

        :param book_info: fetch_book_info 返回的书籍信息
        :param chapters:  fetch_chapter_list 返回的章节列表 (已排序)
        :param fmt:       'txt' 或 'epub'
        :param progress_callback: 可选回调 fn(progress_float, status_str)
        :return:          生成的文件字节
        """
        # book_info 结构: {book: {...}, id, title, type, comment}
        b = book_info.get('book', book_info)
        book_id = str(book_info.get('id', b.get('id', '')))
        book_title = b.get('title', '未知书名')
        author = b.get('author', '未知作者')
        intro = self._strip_html(b.get('intro', ''))
        cover_url = b.get('image_link', '')

        # 1. 获取 ZIP 链接
        if progress_callback:
            progress_callback(0.0, '正在获取下载链接...')
        zip_url = self.api.get_cache_zip_link(book_id)
        if not zip_url:
            raise Exception('获取下载链接失败: URL为空')

        # 2. 下载 ZIP
        if progress_callback:
            progress_callback(0.05, '正在下载缓存文件...')
        zip_bytes = self._download_zip(zip_url)

        # 3. 解压并解密各章节
        if progress_callback:
            progress_callback(0.4, '正在解压...')
        decrypted = self._extract_and_decrypt(zip_bytes, chapters, progress_callback)

        # 4. 按格式生成
        if progress_callback:
            progress_callback(0.7, f'正在生成{fmt.upper()}...')

        if fmt == 'epub':
            cover_bytes = self._download_image(cover_url)
            result = self._generate_epub(book_title, author, intro, chapters, decrypted, cover_bytes)
        else:
            result = self._generate_txt(book_title, author, intro, chapters, decrypted)

        if progress_callback:
            progress_callback(1.0, '下载完成!')

        return result

    # ── ZIP 下载 ────────────────────────────────────────

    def _download_zip(self, url: str) -> bytes:
        """下载 ZIP 文件到内存"""
        r = self.session.get(url, timeout=300, stream=True)
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        chunks = []
        downloaded = 0
        for chunk in r.iter_content(chunk_size=8192):
            chunks.append(chunk)
            downloaded += len(chunk)
        return b''.join(chunks)

    # ── 解压 & 解密 ─────────────────────────────────────

    def _extract_and_decrypt(self, zip_bytes: bytes, chapters: list, progress_cb=None) -> dict:
        """解压 ZIP，对每个文件 AES 解密，返回 {chapter_id: plaintext}"""
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        files = [f for f in zf.namelist() if not f.endswith('/')]
        total = len(files)

        decrypted = {}
        for i, name in enumerate(files):
            chapter_id = Path(name).stem  # 文件名去掉扩展名 = 章节ID
            encrypted_text = zf.read(name).decode('utf-8', errors='replace')
            try:
                plain = self.api.decrypt_chapter_content(encrypted_text)
            except Exception:
                plain = encrypted_text  # 解密失败保留原文

            decrypted[chapter_id] = plain

            if progress_cb:
                progress_cb(0.4 + (i / max(total, 1)) * 0.3, f'解密章节 {i+1}/{total}')

        return decrypted

    # ── TXT 生成 ────────────────────────────────────────

    def _generate_txt(self, title: str, author: str, intro: str,
                      chapters: list, decrypted: dict) -> bytes:
        """生成单文件 TXT"""
        buf = io.StringIO()
        buf.write(f'{title}\n作者: {author}\n')

        if intro:
            buf.write(f'\n简介:\n{intro}\n')

        buf.write('\n' + '=' * 50 + '\n\n')

        for ch in chapters:
            ch_id = str(ch.get('id', ''))
            ch_title = ch.get('title', '未知章节')
            content = decrypted.get(ch_id, '')

            buf.write(f'\n{ch_title}\n\n')
            buf.write(content)
            buf.write('\n\n' + '-' * 30 + '\n')

        return buf.getvalue().encode('utf-8')

    # ── EPUB 生成 ───────────────────────────────────────

    def _generate_epub(self, title: str, author: str, intro: str,
                       chapters: list, decrypted: dict,
                       cover_bytes: Optional[bytes] = None) -> bytes:
        """
        构建符合 EPUB 2.0 规范的 ZIP 文件
        关键: mimetype 必须第一个写入且不压缩
        """
        buf = io.BytesIO()
        zf = zipfile.ZipFile(buf, 'w')

        # --- mimetype (第一个, 不压缩) ---
        zf.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip',
                    compress_type=zipfile.ZIP_STORED)

        # --- META-INF/container.xml ---
        zf.writestr('META-INF/container.xml', self._build_container_xml(),
                    compress_type=zipfile.ZIP_DEFLATED)

        # --- OEBPS/css/styles.css ---
        zf.writestr('OEBPS/css/styles.css', self._EPUB_CSS,
                    compress_type=zipfile.ZIP_DEFLATED)

        # --- OEBPS/images/cover.jpg ---
        has_cover = bool(cover_bytes)
        if has_cover:
            zf.writestr('OEBPS/images/cover.jpg', cover_bytes,
                        compress_type=zipfile.ZIP_DEFLATED)

        # --- OEBPS/cover.xhtml ---
        zf.writestr('OEBPS/cover.xhtml', self._build_cover_xhtml(has_cover),
                    compress_type=zipfile.ZIP_DEFLATED)

        # --- 各章节 XHTML ---
        for i, ch in enumerate(chapters):
            ch_id = str(ch.get('id', ''))
            ch_title = ch.get('title', f'第{i+1}章')
            content = decrypted.get(ch_id, '')

            xhtml = self._build_chapter_xhtml(ch_title, content)
            zf.writestr(f'OEBPS/chapter{i+1}.xhtml', xhtml,
                        compress_type=zipfile.ZIP_DEFLATED)

        # --- OEBPS/content.opf ---
        book_uid = f'book-{chapters[0].get("id", "0") if chapters else "0"}'
        zf.writestr('OEBPS/content.opf',
                    self._build_opf(title, author, book_uid, len(chapters), has_cover),
                    compress_type=zipfile.ZIP_DEFLATED)

        # --- OEBPS/toc.ncx ---
        zf.writestr('OEBPS/toc.ncx',
                    self._build_ncx(title, author, book_uid, chapters, has_cover),
                    compress_type=zipfile.ZIP_DEFLATED)

        zf.close()
        return buf.getvalue()

    # ── EPUB XML 构建方法 ──────────────────────────────

    def _build_container_xml(self) -> str:
        return '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''

    def _build_cover_xhtml(self, has_cover: bool) -> str:
        img_tag = '<img alt="封面" src="images/cover.jpg" style="max-width:100%;"/>' if has_cover else ''
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>封面</title>
<link rel="stylesheet" type="text/css" href="css/styles.css"/>
</head>
<body style="text-align:center; padding:0; margin:0;">
{img_tag}
</body>
</html>'''

    def _build_chapter_xhtml(self, ch_title: str, content: str) -> str:
        escaped_title = self._escape_xml(ch_title)
        paragraphs = ''.join(
            f'<p>{self._escape_xml(p)}</p>\n'
            for p in content.split('\n')
            if p.strip()
        )
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{escaped_title}</title>
<link rel="stylesheet" type="text/css" href="css/styles.css"/>
</head>
<body>
<h2>{escaped_title}</h2>
{paragraphs}
</body>
</html>'''

    def _build_opf(self, title: str, author: str, book_uid: str,
                   chapter_count: int, has_cover: bool) -> str:
        """构建 content.opf"""
        ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
        ET.register_namespace('', 'http://www.idpf.org/2007/opf')

        package = ET.Element('package', {
            'version': '2.0',
            'unique-identifier': 'bookid',
            'xmlns': 'http://www.idpf.org/2007/opf',
        })

        # metadata
        metadata = ET.SubElement(package, 'metadata', {
            'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
            'xmlns:opf': 'http://www.idpf.org/2007/opf',
        })
        ET.SubElement(metadata, 'dc:title').text = self._escape_xml(title)
        ET.SubElement(metadata, 'dc:creator', {'opf:role': 'aut'}).text = self._escape_xml(author)
        ET.SubElement(metadata, 'dc:language').text = 'zh-CN'
        ET.SubElement(metadata, 'dc:identifier', {'id': 'bookid'}).text = book_uid
        ET.SubElement(metadata, 'dc:publisher').text = '灵猫小说下载器'

        if has_cover:
            ET.SubElement(metadata, 'meta', {'name': 'cover', 'content': 'cover-image'})

        # manifest
        manifest = ET.SubElement(package, 'manifest')
        ET.SubElement(manifest, 'item', {
            'id': 'ncx', 'href': 'toc.ncx',
            'media-type': 'application/x-dtbncx+xml',
        })
        ET.SubElement(manifest, 'item', {
            'id': 'css', 'href': 'css/styles.css',
            'media-type': 'text/css',
        })
        if has_cover:
            ET.SubElement(manifest, 'item', {
                'id': 'cover-image', 'href': 'images/cover.jpg',
                'media-type': 'image/jpeg',
            })
            ET.SubElement(manifest, 'item', {
                'id': 'cover', 'href': 'cover.xhtml',
                'media-type': 'application/xhtml+xml',
            })
        for i in range(chapter_count):
            ET.SubElement(manifest, 'item', {
                'id': f'chapter{i+1}', 'href': f'chapter{i+1}.xhtml',
                'media-type': 'application/xhtml+xml',
            })

        # spine
        spine = ET.SubElement(package, 'spine', {'toc': 'ncx'})
        if has_cover:
            ET.SubElement(spine, 'itemref', {'idref': 'cover', 'linear': 'no'})
        for i in range(chapter_count):
            ET.SubElement(spine, 'itemref', {'idref': f'chapter{i+1}'})

        # guide
        if has_cover:
            guide = ET.SubElement(package, 'guide')
            ET.SubElement(guide, 'reference', {
                'type': 'cover', 'title': '封面', 'href': 'cover.xhtml',
            })

        return ET.tostring(package, encoding='unicode', xml_declaration=True)

    def _build_ncx(self, title: str, author: str, book_uid: str,
                   chapters: list, has_cover: bool) -> str:
        """构建 toc.ncx"""
        ET.register_namespace('', 'http://www.daisy.org/z3986/2005/ncx/')

        ncx = ET.Element('ncx', {
            'version': '2005-1',
            'xmlns': 'http://www.daisy.org/z3986/2005/ncx/',
        })

        head = ET.SubElement(ncx, 'head')
        ET.SubElement(head, 'meta', {'name': 'dtb:uid', 'content': book_uid})
        ET.SubElement(head, 'meta', {'name': 'dtb:depth', 'content': '1'})
        ET.SubElement(head, 'meta', {'name': 'dtb:totalPageCount', 'content': '0'})
        ET.SubElement(head, 'meta', {'name': 'dtb:maxPageNumber', 'content': '0'})

        doc_title = ET.SubElement(ncx, 'docTitle')
        ET.SubElement(doc_title, 'text').text = self._escape_xml(title)

        doc_author = ET.SubElement(ncx, 'docAuthor')
        ET.SubElement(doc_author, 'text').text = self._escape_xml(author)

        nav_map = ET.SubElement(ncx, 'navMap')
        play_order = 1

        if has_cover:
            self._add_nav_point(nav_map, play_order, '封面', 'cover.xhtml')
            play_order += 1

        for i, ch in enumerate(chapters):
            ch_title = ch.get('title', f'第{i+1}章')
            self._add_nav_point(nav_map, play_order, ch_title, f'chapter{i+1}.xhtml')
            play_order += 1

        return ET.tostring(ncx, encoding='unicode', xml_declaration=True)

    def _add_nav_point(self, nav_map, order: int, label: str, src: str):
        nav_point = ET.SubElement(nav_map, 'navPoint', {
            'id': f'navpoint-{order}',
            'playOrder': str(order),
        })
        nav_label = ET.SubElement(nav_point, 'navLabel')
        ET.SubElement(nav_label, 'text').text = self._escape_xml(label)
        ET.SubElement(nav_point, 'content', {'src': src})

    # ── 工具方法 ────────────────────────────────────────

    @staticmethod
    def _escape_xml(text: str) -> str:
        """XML 转义"""
        if not text:
            return ''
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))

    @staticmethod
    def _strip_html(text: str) -> str:
        """去除 HTML 标签"""
        if not text:
            return ''
        return re.sub(r'<[^>]*>', '', text)

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """安全文件名"""
        return re.sub(r'[\\/:*?"<>|]', '_', name)

    def _download_image(self, url: str) -> Optional[bytes]:
        """下载封面图片"""
        if not url:
            return None
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                return r.content
        except Exception:
            pass
        return None

    # ── EPUB CSS ────────────────────────────────────────

    _EPUB_CSS = '''@page {
    margin: 5px;
}

body {
    font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    line-height: 1.8;
    padding: 1em;
}

h2 {
    text-align: center;
    font-size: 1.3em;
    margin: 1.5em 0 1em 0;
    font-weight: bold;
}

p {
    text-indent: 2em;
    margin: 0.3em 0;
}

.first-para {
    text-indent: 2em;
}

img {
    max-width: 100%;
    height: auto;
}
'''
