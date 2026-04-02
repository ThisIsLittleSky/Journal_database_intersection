# -*- coding: utf-8 -*-
import logging
import os
import re

from core.text_chunking import build_line_chunks

logger = logging.getLogger(__name__)

_ENCODINGS = ('utf-8-sig', 'utf-8', 'gbk', 'gb18030', 'utf-16')
_LEADING_NOISE = re.compile(r'^\s*\d+[\.\-、\)\]）\s]*')


def _read_text(filepath: str) -> str:
    for encoding in _ENCODINGS:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError('无法识别TXT文件编码')


def _clean_line(line: str) -> str:
    line = line.strip()
    line = _LEADING_NOISE.sub('', line)
    if '\t' in line:
        parts = [part.strip() for part in line.split('\t') if part.strip()]
        line = parts[0] if parts else ''
    return line


def parse(filepath: str) -> dict:
    source_name = os.path.splitext(os.path.basename(filepath))[0]
    text = _read_text(filepath)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    results = []
    seen_names = set()

    for raw_line in lines:
        name = _clean_line(raw_line)
        if len(name) < 2 or name.isdigit():
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        results.append({'name': name, 'key': name, 'source': source_name})

    logger.info(f'TXT解析完成：{source_name}，有效期刊数 {len(results)}')
    return {
        'source_db': source_name,
        'journals': results,
        'raw_text': text[:5000],
        'raw_chunks': build_line_chunks(lines, chunk_size=80, label_prefix='TXT第'),
    }
