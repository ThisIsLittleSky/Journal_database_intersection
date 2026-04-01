# -*- coding: utf-8 -*-
import logging
import os
import xml.etree.ElementTree as ET
import zipfile

from core.normalizer import normalize

logger = logging.getLogger(__name__)

_WORD_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def _extract_text(filepath: str) -> str:
    with zipfile.ZipFile(filepath, 'r') as zf:
        xml_bytes = zf.read('word/document.xml')
    root = ET.fromstring(xml_bytes)
    paragraphs = []
    for para in root.findall('.//w:p', _WORD_NS):
        fragments = []
        for node in para.findall('.//w:t', _WORD_NS):
            if node.text:
                fragments.append(node.text)
        line = ''.join(fragments).strip()
        if line:
            paragraphs.append(line)
    return '\n'.join(paragraphs)


def parse(filepath: str) -> dict:
    source_name = os.path.splitext(os.path.basename(filepath))[0]
    text = _extract_text(filepath)
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
    logger.info(f'DOCX解析完成：{source_name}，有效期刊数 {len(journals)}')
    return {'source_db': source_name, 'journals': journals, 'raw_text': text[:12000]}
