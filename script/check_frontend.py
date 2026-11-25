"""确认 Flask 首页引用的正式 JS 和 CSS 均已随包发布。"""
from html.parser import HTMLParser
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / 'web_static'


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.styles = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('type') == 'module':
            self.scripts.append(attrs.get('src', ''))
        if tag == 'link' and 'stylesheet' in attrs.get('rel', '').split():
            self.styles.append(attrs.get('href', ''))


def ready():
    assets = Assets()
    try:
        assets.feed((STATIC / 'index.html').read_text(encoding='utf-8'))
        return bool(assets.scripts and assets.styles) and all(
            url.startswith('/web_static/app/') and (STATIC / url.removeprefix('/web_static/')).is_file()
            for url in assets.scripts + assets.styles
        )
    except (OSError, UnicodeError):
        return False


if __name__ == '__main__':
    raise SystemExit(0 if ready() else 1)
