# -*- coding: utf-8 -*-
import logging
import os

from openpyxl import load_workbook

from core.normalizer import normalize

logger = logging.getLogger(__name__)

_HEADER_KEYWORDS = ('刊名', '期刊', 'journal', 'title', 'source title')


def _looks_like_name(value) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text or len(text) < 2:
        return False
    if text.isdigit():
        return False
    return True


def _detect_name_column(rows: list[tuple]) -> tuple[int, int]:
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


def _build_preview(rows: list[tuple], max_rows: int = 60) -> str:
    preview_lines = []
    for row in rows[:max_rows]:
        cells = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
        if cells:
            preview_lines.append('\t'.join(cells))
    return '\n'.join(preview_lines)


def parse(filepath: str) -> dict:
    source_name = os.path.splitext(os.path.basename(filepath))[0]
    wb = load_workbook(filepath, read_only=True, data_only=True)
    results = []
    seen_keys = set()
    preview_chunks = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        preview = _build_preview(rows)
        if preview:
            preview_chunks.append(f'[{sheet_name}]\n{preview}')

        name_col_idx, data_start = _detect_name_column(rows)
        for row in rows[data_start:]:
            if row is None or len(row) <= name_col_idx:
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

    wb.close()
    logger.info(f'通用Excel解析完成：{source_name}，有效期刊数 {len(results)}')
    return {
        'source_db': source_name,
        'journals': results,
        'raw_text': '\n\n'.join(preview_chunks)[:12000],
    }
