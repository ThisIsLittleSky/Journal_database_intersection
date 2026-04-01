# -*- coding: utf-8 -*-
import csv
import logging
import os

from core.normalizer import normalize

logger = logging.getLogger(__name__)

_HEADER_KEYWORDS = ('刊名', '期刊', 'journal', 'title', 'source title')
_ENCODINGS = ('utf-8-sig', 'utf-8', 'gbk', 'gb18030')


def _load_rows(filepath: str) -> list[list[str]]:
    for encoding in _ENCODINGS:
        try:
            with open(filepath, 'r', encoding=encoding, newline='') as f:
                sample = f.read(2048)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample or ',')
                except csv.Error:
                    dialect = csv.excel
                return list(csv.reader(f, dialect))
        except UnicodeDecodeError:
            continue
    raise ValueError('无法识别CSV文件编码')


def _looks_like_name(value) -> bool:
    text = str(value or '').strip()
    if not text or len(text) < 2:
        return False
    if text.isdigit():
        return False
    return True


def _detect_name_column(rows: list[list[str]]) -> tuple[int, int]:
    for row_idx, row in enumerate(rows[:10]):
        for col_idx, cell in enumerate(row):
            text = str(cell or '').strip().lower()
            if any(keyword in text for keyword in _HEADER_KEYWORDS):
                return col_idx, row_idx + 1

    scores = {}
    for row in rows[:30]:
        for col_idx, cell in enumerate(row):
            if _looks_like_name(cell):
                scores[col_idx] = scores.get(col_idx, 0) + 1

    if not scores:
        return 0, 0
    best_col = max(scores.items(), key=lambda item: item[1])[0]
    return best_col, 0


def _build_preview(rows: list[list[str]], max_rows: int = 80) -> str:
    preview_lines = []
    for row in rows[:max_rows]:
        cells = [str(cell).strip() for cell in row if str(cell or '').strip()]
        if cells:
            preview_lines.append('\t'.join(cells))
    return '\n'.join(preview_lines)


def parse(filepath: str) -> dict:
    source_name = os.path.splitext(os.path.basename(filepath))[0]
    rows = _load_rows(filepath)
    if not rows:
        return {'source_db': source_name, 'journals': []}

    name_col_idx, data_start = _detect_name_column(rows)
    results = []
    seen_keys = set()

    for row in rows[data_start:]:
        if len(row) <= name_col_idx:
            continue
        value = row[name_col_idx]
        if not _looks_like_name(value):
            continue
        name = str(value).strip()
        key = normalize(name)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        results.append({'name': name, 'key': key, 'source': source_name})

    logger.info(f'CSV解析完成：{source_name}，有效期刊数 {len(results)}')
    return {
        'source_db': source_name,
        'journals': results,
        'raw_text': _build_preview(rows)[:12000],
    }
