# -*- coding: utf-8 -*-
import html
from html.parser import HTMLParser
import logging
import os
import re

from core.normalizer import normalize

logger = logging.getLogger(__name__)

_BLOCK_TAGS = {
    'p', 'div', 'li', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'section', 'article', 'header', 'footer', 'br'
}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._skip_depth += 1
        if tag in _BLOCK_TAGS and self._parts and self._parts[-1] != '\n':
            self._parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in _BLOCK_TAGS and self._parts and self._parts[-1] != '\n':
            self._parts.append('\n')

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = html.unescape(data).strip()
        if text:
            self._parts.append(text)
            self._parts.append('\n')

    def get_text(self) -> str:
        text = ''.join(self._parts)
        text = re.sub(r'\n{2,}', '\n', text)
        return text.strip()


def _read_html(filepath: str) -> str:
    for encoding in ('utf-8', 'utf-8-sig', 'gbk', 'gb18030'):
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError('无法识别HTML文件编码')


def parse(filepath: str) -> dict:
    source_name = os.path.splitext(os.path.basename(filepath))[0]
    parser = _TextExtractor()
    parser.feed(_read_html(filepath))
    text = parser.get_text()

    seen = set()
    journals = []
    for line in text.splitlines():
        name = line.strip()
        if len(name) < 2 or name.isdigit():
            continue
        key = normalize(name)
        if not key or key in seen:
            continue
        seen.add(key)
        journals.append({'name': name, 'key': key, 'source': source_name})

    logger.info(f'HTML解析完成：{source_name}，有效期刊数 {len(journals)}')
    return {'source_db': source_name, 'journals': journals, 'raw_text': text[:12000]}
