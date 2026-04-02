# -*- coding: utf-8 -*-
import json
import logging
import os
import re

from core.llm_client import OpenAICompatibleClient
from core.normalizer import normalize
from core.text_chunking import build_line_chunks

logger = logging.getLogger(__name__)

_TEXT_SEGMENT_BATCH_SIZE = 30
_TABULAR_BATCH_SIZE = 500
_LIST_PREFIX = re.compile(r'^\s*\d+[\.\-、\)\]）\s]*')
_NON_MAIN_MARKERS = (
    '扩展版',
    '扩展刊',
    '网络版',
    '网络首发',
    '增刊',
    '英文版',
    '国际版',
    '专刊',
    '特刊',
)
_NON_MAIN_IN_PARENS = re.compile(
    r'[\(（][^()（）]{0,24}(?:' + '|'.join(_NON_MAIN_MARKERS) + r')[^()（）]{0,24}[\)）]'
)
_NON_MAIN_SUFFIX = re.compile(
    r'(?:' + '|'.join(_NON_MAIN_MARKERS) + r')\s*$'
)

_SYSTEM_PROMPT = (
    '你是期刊名单提取助手。从输入中提取明确出现的有效主刊名称。'
    '排除规则：扩展版、扩展刊、网络版、网络首发、增刊、英文版、国际版、专刊、特刊等非主刊版本直接排除，不要替换。'
    '输出规则：只输出JSON对象 {"文件名":["期刊1","期刊2"]}，不要重复，不要推测，不要解释。'
)


def enhance_parse_result(parse_result: dict, llm_config: dict) -> dict:
    if not llm_config.get('enabled'):
        return parse_result

    client = OpenAICompatibleClient(
        base_url=llm_config.get('base_url', ''),
        api_key=llm_config.get('api_key', ''),
        model=llm_config.get('model', ''),
    )

    input_mode = _get_input_mode(parse_result)
    batch_size = _get_batch_size(input_mode)
    names = _extract_names(client, parse_result, input_mode, batch_size)
    parse_result['journals'] = _build_records_from_names(names, parse_result)

    if parse_result['journals']:
        mode_label = '结构化候选记录' if input_mode == 'tabular' else '文本片段'
        _append_warning(parse_result, f'已使用LLM分析{mode_label}（每次最多{batch_size}条）')
        logger.info('  已使用LLM分析%s（每次最多%s条）', mode_label, batch_size)
    else:
        _append_warning(parse_result, 'LLM未识别到有效主刊名称')
    return parse_result


def _get_input_mode(parse_result: dict) -> str:
    if (
        str(parse_result.get('structured_input_type') or '').strip().lower() == 'tabular'
        and parse_result.get('structured_rows')
    ):
        return 'tabular'
    return 'text'


def _get_batch_size(input_mode: str) -> int:
    if input_mode == 'tabular':
        return _TABULAR_BATCH_SIZE
    return _TEXT_SEGMENT_BATCH_SIZE


def _extract_names(
    client: OpenAICompatibleClient,
    parse_result: dict,
    input_mode: str,
    batch_size: int,
) -> list[str]:
    items = _collect_tabular_rows(parse_result) if input_mode == 'tabular' else _collect_segments(parse_result)
    if not items:
        return []

    all_names = []
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        if input_mode == 'tabular':
            logger.info('  LLM结构化分析：第%s-%s条候选记录', start + 1, start + len(batch))
        else:
            logger.info(
                '  LLM分段分析：%s - %s',
                batch[0].get('label', f'片段{start + 1}'),
                batch[-1].get('label', f'片段{start + len(batch)}'),
            )
        all_names.extend(_extract_batch(client, parse_result, batch, input_mode))
    return _dedupe_names(all_names)


def _collect_tabular_rows(parse_result: dict) -> list[dict]:
    rows = []
    for item in parse_result.get('structured_rows', []):
        if not isinstance(item, dict):
            continue
        candidate_name = str(item.get('candidate_name') or '').strip()
        if not candidate_name:
            continue
        cells = item.get('cells', {})
        if not isinstance(cells, dict):
            cells = {}
        rows.append({
            'sheet': str(item.get('sheet') or '').strip(),
            'row_index': item.get('row_index'),
            'candidate_name': candidate_name,
            'cells': {
                str(key).strip(): str(value).strip()
                for key, value in cells.items()
                if str(key).strip() and str(value).strip()
            },
        })
    return rows


def _collect_segments(parse_result: dict) -> list[dict]:
    raw_chunks = []
    for item in parse_result.get('raw_chunks', []):
        text = str(item.get('text') or '').strip()
        if not text:
            continue
        raw_chunks.append({
            'label': str(item.get('label') or f'片段{len(raw_chunks) + 1}').strip(),
            'text': text,
        })
    if raw_chunks:
        return raw_chunks

    raw_text = str(parse_result.get('raw_text', '') or '').strip()
    if not raw_text:
        return []
    return build_line_chunks(raw_text.splitlines(), chunk_size=80, label_prefix='全文第')


def _extract_batch(
    client: OpenAICompatibleClient,
    parse_result: dict,
    batch: list[dict],
    input_mode: str,
) -> list[str]:
    try:
        response = client.chat_json(_SYSTEM_PROMPT, _build_user_prompt(parse_result, batch, input_mode))
        return _extract_names_from_response(response, parse_result)
    except Exception as exc:
        if len(batch) == 1:
            label = _describe_single_batch_item(batch[0], input_mode)
            _append_warning(parse_result, f'{label} LLM分析失败，已跳过：{exc}')
            logger.warning('  %s LLM分析失败，已跳过：%s', label, exc)
            return []

        split_at = max(1, len(batch) // 2)
        logger.warning('  LLM批量分析失败，拆分重试：%s', exc)
        return (
            _extract_batch(client, parse_result, batch[:split_at], input_mode)
            + _extract_batch(client, parse_result, batch[split_at:], input_mode)
        )


def _describe_single_batch_item(item: dict, input_mode: str) -> str:
    if input_mode == 'tabular':
        sheet = str(item.get('sheet') or '表格').strip()
        row_index = item.get('row_index')
        if row_index:
            return f'{sheet} 第{row_index}行'
        return sheet
    return str(item.get('label') or '片段').strip()


def _build_user_prompt(parse_result: dict, batch: list[dict], input_mode: str) -> str:
    response_key = _expected_response_key(parse_result)
    if input_mode == 'tabular':
        return (
            f'文件名：{response_key}\n'
            '候选记录（candidate_name=候选刊名，cells=辅助字段）：\n'
            + json.dumps(batch, ensure_ascii=False, indent=2)
            + f'\n输出：{{"{response_key}":["有效主刊1","有效主刊2"]}}'
        )

    return (
        f'文件名：{response_key}\n'
        '文件片段：\n'
        + _format_batch_text(batch)
        + f'\n输出：{{"{response_key}":["有效主刊1","有效主刊2"]}}'
    )


def _format_batch_text(batch: list[dict]) -> str:
    parts = []
    for item in batch:
        label = str(item.get('label') or '片段').strip()
        text = str(item.get('text') or '').strip()
        if not text:
            continue
        parts.append(f'[{label}]\n{text}')
    return '\n\n'.join(parts)


def _extract_names_from_response(response, parse_result: dict) -> list[str]:
    expected_key = _expected_response_key(parse_result)

    if isinstance(response, list):
        _append_warning(parse_result, 'LLM未返回文件名字段，已按数组结果兼容解析')
        names = response
    elif isinstance(response, dict):
        if not response:
            return []
        if expected_key in response:
            names = response.get(expected_key, [])
        elif len(response) == 1:
            actual_key, names = next(iter(response.items()))
            if str(actual_key).strip() != expected_key:
                _append_warning(
                    parse_result,
                    f'LLM返回文件名字段为 {actual_key}，已按 {expected_key} 兼容解析',
                )
        else:
            raise RuntimeError('LLM返回了多个顶层字段')
    else:
        raise RuntimeError('LLM返回格式无效')

    if not isinstance(names, list):
        raise RuntimeError('LLM返回的期刊名称结果不是数组')

    cleaned_names = []
    excluded_names = []
    for item in names:
        name = _clean_returned_name(item)
        if not name:
            continue
        if _is_non_main_edition(name):
            excluded_names.append(name)
            continue
        cleaned_names.append(name)

    if excluded_names:
        suffix = ' 等' if len(excluded_names) > 5 else ''
        _append_warning(parse_result, '已过滤非主刊名称：' + '、'.join(excluded_names[:5]) + suffix)
    return _dedupe_names(cleaned_names)


def _expected_response_key(parse_result: dict) -> str:
    source_file = str(parse_result.get('source_file') or '').strip()
    if source_file:
        return os.path.basename(source_file)
    source_name = str(parse_result.get('source_db') or '').strip()
    return source_name or '结果'


def _clean_returned_name(value) -> str:
    text = str(value or '').strip()
    text = _LIST_PREFIX.sub('', text)
    text = text.strip('"\'“”‘’「」『』')
    text = ' '.join(text.split())
    return text.strip()


def _is_non_main_edition(name: str) -> bool:
    text = str(name or '').strip()
    if not text:
        return False
    return bool(_NON_MAIN_IN_PARENS.search(text) or _NON_MAIN_SUFFIX.search(text))


def _build_records_from_names(names: list[str], parse_result: dict) -> list[dict]:
    source_name = parse_result.get('source_db') or parse_result.get('source_file') or '未知来源'
    source_file = parse_result.get('source_file', '')
    records = []

    for name in names:
        if _is_non_main_edition(name):
            continue
        key = normalize(name)
        if not key:
            continue
        records.append({
            'raw_name': name,
            'normalized_name': name,
            'name': name,
            'key': key,
            'source': source_name,
            'source_db': source_name,
            'source_file': source_file,
            'aliases': [],
            'meta': {'llm_enhanced': True},
        })
    return _dedupe_records(records)


def _dedupe_names(names: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for name in names:
        key = normalize(name)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped


def _append_warning(parse_result: dict, message: str):
    warnings = parse_result.setdefault('warnings', [])
    if message not in warnings:
        warnings.append(message)


def _dedupe_records(records: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for item in records:
        key = str(item.get('key') or '').strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
