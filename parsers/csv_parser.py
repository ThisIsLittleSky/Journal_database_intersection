# -*- coding: utf-8 -*-
import csv
import logging
import os

from core.text_chunking import build_line_chunks

logger = logging.getLogger(__name__)

_HEADER_KEYWORDS = ('刊名', '期刊', 'journal', 'title', 'source title')
_ENCODINGS = ('utf-8-sig', 'utf-8', 'gbk', 'gb18030')
_MAX_STRUCTURED_FIELDS = 6
_MAX_CELL_TEXT = 160
_TABULAR_INPUT_VERSION = 'tabular_candidates_v1'


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


def _build_row_lines(rows: list[list[str]]) -> list[str]:
    lines = []
    for row in rows:
        cells = [str(cell).strip() for cell in row if str(cell or '').strip()]
        if cells:
            lines.append('\t'.join(cells))
    return lines


def _get_header_name(headers: list[str], col_idx: int) -> str:
    if col_idx < len(headers) and headers[col_idx]:
        return headers[col_idx]
    return f'col_{col_idx + 1}'


def _build_headers(rows: list[list[str]], data_start: int) -> list[str]:
    max_cols = max((len(row) for row in rows[:30]), default=0)
    headers = [f'col_{idx + 1}' for idx in range(max_cols)]
    if data_start <= 0 or data_start > len(rows):
        return headers

    header_row = rows[data_start - 1]
    return [
        str(header_row[idx]).strip() if idx < len(header_row) and str(header_row[idx]).strip() else headers[idx]
        for idx in range(max_cols)
    ]


def _clean_cell_text(value, max_length: int = _MAX_CELL_TEXT) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    text = ' '.join(text.split())
    return text[:max_length]


def _build_structured_cells(headers: list[str], row: list[str], name_col_idx: int) -> dict:
    pairs = []

    if len(row) > name_col_idx:
        candidate_text = _clean_cell_text(row[name_col_idx])
        if candidate_text:
            pairs.append((_get_header_name(headers, name_col_idx), candidate_text))

    for col_idx, value in enumerate(row):
        if col_idx == name_col_idx:
            continue
        text = _clean_cell_text(value)
        if not text:
            continue
        pairs.append((_get_header_name(headers, col_idx), text))
        if len(pairs) >= _MAX_STRUCTURED_FIELDS:
            break

    return {key: value for key, value in pairs[:_MAX_STRUCTURED_FIELDS]}


def parse(filepath: str) -> dict:
    source_name = os.path.splitext(os.path.basename(filepath))[0]
    rows = _load_rows(filepath)
    if not rows:
        return {
            'source_db': source_name,
            'journals': [],
            'structured_rows': [],
            'structured_input_type': 'tabular',
            'structured_input_version': _TABULAR_INPUT_VERSION,
        }

    name_col_idx, data_start = _detect_name_column(rows)
    headers = _build_headers(rows, data_start)
    results = []
    seen_names = set()
    structured_rows = []

    for row_index, row in enumerate(rows[data_start:], start=data_start + 1):
        if len(row) <= name_col_idx:
            continue
        value = row[name_col_idx]
        if not _looks_like_name(value):
            continue
        name = str(value).strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        results.append({'name': name, 'key': name, 'source': source_name})
        structured_rows.append({
            'sheet': 'CSV',
            'row_index': row_index,
            'candidate_name': name,
            'cells': _build_structured_cells(headers, row, name_col_idx),
        })

    logger.info(f'CSV解析完成：{source_name}，有效期刊数 {len(results)}')
    row_lines = _build_row_lines(rows)
    return {
        'source_db': source_name,
        'journals': results,
        'raw_text': _build_preview(rows)[:12000],
        'raw_chunks': build_line_chunks(row_lines, chunk_size=40, label_prefix='CSV第'),
        'structured_rows': structured_rows,
        'structured_input_type': 'tabular',
        'structured_input_version': _TABULAR_INPUT_VERSION,
    }
