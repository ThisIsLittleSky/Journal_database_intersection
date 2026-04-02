# -*- coding: utf-8 -*-
import logging
import os

import cache_store
from core.models import JournalRecord, ParseResult
from core.parser_registry import build_default_registry

logger = logging.getLogger(__name__)

_DEFAULT_REGISTRY = None


def get_registry():
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = build_default_registry()
    return _DEFAULT_REGISTRY


def _build_source_name(filepath: str, raw_result: dict) -> str:
    source_name = raw_result.get('source_db') if isinstance(raw_result, dict) else ''
    if source_name:
        return str(source_name)
    journals = raw_result.get('journals', []) if isinstance(raw_result, dict) else []
    if journals:
        source_name = journals[0].get('source') or journals[0].get('source_db')
        if source_name:
            return str(source_name)
    return os.path.splitext(os.path.basename(filepath))[0]


def _coerce_result(filepath: str, parser_name: str, raw_result: dict) -> dict:
    source_name = _build_source_name(filepath, raw_result or {})
    journals = []
    raw_chunks = []
    raw_chunk_policy = str((raw_result or {}).get('raw_chunk_policy', '') or '').strip()
    structured_rows = []
    structured_input_type = str((raw_result or {}).get('structured_input_type', '') or '').strip()
    structured_input_version = str((raw_result or {}).get('structured_input_version', '') or '').strip()

    for item in (raw_result or {}).get('journals', []):
        raw_name = str(item.get('raw_name') or item.get('name') or '').strip()
        if not raw_name:
            continue
        normalized_name = str(item.get('normalized_name') or item.get('key') or raw_name).strip()
        key = str(item.get('key') or normalized_name or raw_name).strip()
        if not key:
            continue
        journal = JournalRecord(
            raw_name=raw_name,
            normalized_name=normalized_name,
            key=key,
            source_db=str(item.get('source_db') or item.get('source') or source_name),
            source_file=filepath,
            aliases=list(item.get('aliases', [])),
            meta=dict(item.get('meta', {})),
        )
        journals.append(journal)

    for item in (raw_result or {}).get('raw_chunks', []):
        text = str(item.get('text') or '').strip()
        if not text:
            continue
        raw_chunks.append({
            'label': str(item.get('label') or f'片段{len(raw_chunks) + 1}').strip(),
            'text': text,
        })

    for item in (raw_result or {}).get('structured_rows', []):
        if not isinstance(item, dict):
            continue
        candidate_name = str(item.get('candidate_name') or '').strip()
        if not candidate_name:
            continue
        cells = item.get('cells', {})
        if not isinstance(cells, dict):
            cells = {}
        structured_rows.append({
            'sheet': str(item.get('sheet') or '').strip(),
            'row_index': item.get('row_index'),
            'candidate_name': candidate_name,
            'cells': {
                str(key).strip(): str(value).strip()
                for key, value in cells.items()
                if str(key).strip() and str(value).strip()
            },
        })

    parse_result = ParseResult(
        source_file=filepath,
        source_db=source_name,
        file_type=os.path.splitext(filepath)[1].lower(),
        parser_name=parser_name,
        journals=journals,
        raw_text=str((raw_result or {}).get('raw_text', '')),
        raw_chunks=raw_chunks,
        raw_chunk_policy=raw_chunk_policy,
        structured_rows=structured_rows,
        structured_input_type=structured_input_type,
        structured_input_version=structured_input_version,
        warnings=[str(item) for item in (raw_result or {}).get('warnings', [])],
    )
    return parse_result.to_dict()


def parse_file(filepath: str, registry=None) -> dict:
    filepath = os.path.abspath(filepath)
    registry = registry or get_registry()
    parser = registry.resolve(filepath)
    file_ext = os.path.splitext(filepath)[1].lower()

    cached = cache_store.get(filepath)
    if (
        cached
        and cached.get('parser_name') == parser.name
        and cached.get('journals')
        and 'raw_chunks' in cached
        and (
            file_ext not in ('.xlsx', '.xls')
            or cached.get('raw_chunk_policy') == 'excel_rows_500_v1'
        )
        and (
            file_ext not in ('.xlsx', '.xls', '.csv')
            or (
                cached.get('structured_input_type') == 'tabular'
                and cached.get('structured_input_version') == 'tabular_candidates_v1'
                and 'structured_rows' in cached
            )
        )
    ):
        logger.info('  命中缓存，跳过重新解析')
        return _coerce_result(filepath, parser.name, cached)

    raw_result = parser.parse(filepath, {})
    result = _coerce_result(filepath, parser.name, raw_result)
    cache_store.set(filepath, result)
    return result
