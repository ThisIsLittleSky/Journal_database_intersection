# -*- coding: utf-8 -*-
"""
CSCD PDF解析器。
文件格式：每页每个条目占3行：
  行1：序号 + 空格 + 刊名（如 "1 aBIOTECH"）
  行2：ISSN（如 "2096-6326"）
  行3：标识符（"核心库" 或 "扩展库"）
跨页/跨块的长刊名可能占多行，需合并直到找到 ISSN 行。
只保留标识符为"核心库"的条目。
"""
import re
import logging
import fitz  # PyMuPDF
from core.normalizer import normalize

logger = logging.getLogger(__name__)

# 匹配条目起始行：数字 + 空格 + 刊名（至少1个非空字符）
_ENTRY_START = re.compile(r'^(\d+)\s+(.+)$')
# ISSN 行：XXXX-XXXX（X为数字或大写X）
_ISSN_LINE = re.compile(r'^[\dXx]{4}-[\dXx]{4}$')
# 标识符行
_TAG_LINE = re.compile(r'^(核心库|扩展库)$')
# 页眉/跳过行关键词
_SKIP_PATTERNS = re.compile(r'^(序号|刊名|ISSN|标识符|\d{4}年|\d{4}—\d{4}|中国科学引文)')


def _collect_all_lines(filepath: str):
    """提取所有页的非空行，跳过固定页眉行。"""
    doc = fitz.open(filepath)
    all_lines = []
    for page in doc:
        text = page.get_text('text')
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if _SKIP_PATTERNS.match(ln):
                continue
            all_lines.append(ln)
    doc.close()
    return all_lines


def parse(filepath: str) -> dict:
    """
    返回 {'journals': [{'name': 原始刊名, 'key': 标准化刊名, 'source': 'CSCD'}]}
    """
    lines = _collect_all_lines(filepath)
    results = []
    seen_keys = set()
    total = 0
    skipped_ext = 0

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = _ENTRY_START.match(line)
        if not m:
            i += 1
            continue

        # 收集刊名（可能跨多行，直到遇到 ISSN 行）
        name_parts = [m.group(2).strip()]
        j = i + 1
        while j < n and not _ISSN_LINE.match(lines[j]):
            # 如果下一行是新条目起始，停止（说明本条目刊名只有一行）
            if _ENTRY_START.match(lines[j]) and j > i + 1:
                break
            name_parts.append(lines[j].strip())
            j += 1

        # j 现在指向 ISSN 行（或越界/新条目）
        tag = None
        if j < n and _ISSN_LINE.match(lines[j]):
            # j+1 应该是标识符行
            if j + 1 < n and _TAG_LINE.match(lines[j + 1]):
                tag = lines[j + 1]
                i = j + 2
            else:
                i = j + 1
        else:
            i = j

        name = ' '.join(p for p in name_parts if p)
        total += 1

        if tag == '扩展库':
            skipped_ext += 1
        else:
            key = normalize(name)
            if key and key not in seen_keys:
                seen_keys.add(key)
                results.append({'name': name, 'key': key, 'source': 'CSCD'})

    logger.info(
        f'CSCD：解析完成，总条目 {total}，跳过扩展库 {skipped_ext}，'
        f'有效核心库期刊数 {len(results)}'
    )
    return {'journals': results}
