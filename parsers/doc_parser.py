# -*- coding: utf-8 -*-
import logging
import os
import re

from core.text_chunking import build_line_chunks

logger = logging.getLogger(__name__)

_PRINTABLE_TEXT = re.compile(r'[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9（）()·\.\-《》〈〉、·\s]{1,120}')


def _decode_text(filepath: str) -> str:
    with open(filepath, 'rb') as f:
        raw = f.read()
    if raw.startswith(b'{\\rtf'):
        text = raw.decode('latin1', errors='ignore')
        text = re.sub(r'\\par[d]? ?', '\n', text)
        text = re.sub(r'\\[a-z]+\d* ?', ' ', text)
        text = re.sub(r'[{}]', ' ', text)
        return re.sub(r'\s+', ' ', text).replace(' \n ', '\n')

    for encoding in ('utf-8', 'utf-16', 'gbk', 'gb18030', 'latin1'):
        try:
            text = raw.decode(encoding)
            meaningful_chars = sum(
                1 for ch in text
                if ch.strip() and ('\u4e00' <= ch <= '\u9fff' or ch.isalpha())
            )
            if meaningful_chars >= 2:
                return text
        except UnicodeDecodeError:
            continue

    text = raw.decode('latin1', errors='ignore')
    text = text.replace('\x00', '')
    matches = _PRINTABLE_TEXT.findall(text)
    return '\n'.join(match.strip() for match in matches if match.strip())


def parse(filepath: str) -> dict:
    source_name = os.path.splitext(os.path.basename(filepath))[0]
    text = _decode_text(filepath)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    seen = set()
    journals = []
    for line in lines:
        name = line.strip()
        if len(name) < 2 or name.isdigit():
            continue
        if name in seen:
            continue
        seen.add(name)
        journals.append({'name': name, 'key': name, 'source': source_name})
    logger.info(f'DOC兼容解析完成：{source_name}，有效期刊数 {len(journals)}')
    return {
        'source_db': source_name,
        'journals': journals,
        'raw_text': text[:12000],
        'raw_chunks': build_line_chunks(lines, chunk_size=80, label_prefix='DOC第'),
        'warnings': ['DOC 为兼容解析，复杂二进制文档可能需要另行转换为 DOCX'],
    }
