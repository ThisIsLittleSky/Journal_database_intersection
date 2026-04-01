# -*- coding: utf-8 -*-
import logging

from core.llm_client import OpenAICompatibleClient
from core.normalizer import normalize

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    '你是期刊名单结构化助手。'
    '你的任务是从用户提供的文本或记录中提取期刊名称，并返回严格JSON。'
    '不要输出任何解释、markdown、代码块、注释，只输出JSON对象。'
)


def enhance_parse_result(parse_result: dict, llm_config: dict) -> dict:
    if not llm_config.get('enabled'):
        return parse_result

    parser_name = str(parse_result.get('parser_name', ''))
    if not parser_name.endswith('generic'):
        return parse_result

    client = OpenAICompatibleClient(
        base_url=llm_config.get('base_url', ''),
        api_key=llm_config.get('api_key', ''),
        model=llm_config.get('model', ''),
    )

    try:
        journals = list(parse_result.get('journals', []))
        raw_text = str(parse_result.get('raw_text', '') or '')

        if raw_text and (not journals or len(journals) < 3):
            extracted = _extract_from_text(client, parse_result)
            if extracted:
                parse_result['journals'] = extracted
                parse_result.setdefault('warnings', []).append('已使用LLM从原始文本补充抽取')
                logger.info('  已使用LLM补充抽取期刊名称')
                return parse_result

        if journals:
            normalized = _normalize_journals(client, parse_result)
            if normalized:
                parse_result['journals'] = normalized
                parse_result.setdefault('warnings', []).append('已使用LLM进行名称归一')
                logger.info('  已使用LLM进行名称归一')
    except Exception as exc:
        logger.warning('  LLM增强失败，已回退到规则结果：' + str(exc))
        parse_result.setdefault('warnings', []).append('LLM增强失败：' + str(exc))

    return parse_result


def _extract_from_text(client: OpenAICompatibleClient, parse_result: dict) -> list[dict]:
    source_name = parse_result.get('source_db') or parse_result.get('source_file') or '未知来源'
    raw_text = str(parse_result.get('raw_text', '') or '')[:12000]
    user_prompt = (
        '请从下面文本中识别期刊名称，并做别名归一。\n'
        '输出JSON格式：'
        '{"records":[{"raw_name":"原始名称","normalized_name":"标准名称","aliases":["别名1"]}]}\n'
        '如果无法识别，返回 {"records":[]}。\n'
        '来源：' + str(source_name) + '\n'
        '文本如下：\n' + raw_text
    )
    response = client.chat_json(_SYSTEM_PROMPT, user_prompt)
    return _build_records_from_response(response, parse_result)


def _normalize_journals(client: OpenAICompatibleClient, parse_result: dict) -> list[dict]:
    source_name = parse_result.get('source_db') or parse_result.get('source_file') or '未知来源'
    journals = parse_result.get('journals', [])
    normalized_results = []

    for start in range(0, len(journals), 50):
        batch = journals[start:start + 50]
        raw_names = [str(item.get('raw_name') or item.get('name') or '') for item in batch if item]
        user_prompt = (
            '请将下面的期刊名称列表做字段识别与别名归一，只保留真正的期刊名称。\n'
            '输出JSON格式：'
            '{"records":[{"raw_name":"原始名称","normalized_name":"标准名称","aliases":["别名1"]}]}\n'
            '必须覆盖输入中的每个有效期刊名称。\n'
            '来源：' + str(source_name) + '\n'
            '名称列表：\n' + '\n'.join(raw_names)
        )
        response = client.chat_json(_SYSTEM_PROMPT, user_prompt)
        batch_records = _build_records_from_response(response, parse_result, original_batch=batch)
        seen_raw_names = {item.get('raw_name') for item in batch_records}
        for original in batch:
            raw_name = str(original.get('raw_name') or original.get('name') or '').strip()
            if raw_name and raw_name not in seen_raw_names:
                cloned = dict(original)
                cloned['raw_name'] = raw_name
                cloned['normalized_name'] = str(
                    original.get('normalized_name') or original.get('key') or raw_name
                ).strip()
                cloned['meta'] = dict(original.get('meta', {}))
                cloned['meta']['llm_enhanced'] = False
                batch_records.append(cloned)
        normalized_results.extend(batch_records)

    deduped = []
    seen = set()
    for item in normalized_results:
        key = item.get('key')
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _build_records_from_response(response: dict, parse_result: dict, original_batch=None) -> list[dict]:
    source_name = parse_result.get('source_db') or parse_result.get('source_file') or '未知来源'
    source_file = parse_result.get('source_file', '')
    original_map = {}
    if original_batch:
        for item in original_batch:
            raw_name = str(item.get('raw_name') or item.get('name') or '').strip()
            if raw_name:
                original_map[raw_name] = item

    records = []
    for item in response.get('records', []):
        raw_name = str(item.get('raw_name') or '').strip()
        normalized_name = str(item.get('normalized_name') or raw_name).strip()
        if not raw_name and not normalized_name:
            continue
        if not raw_name:
            raw_name = normalized_name
        if not normalized_name:
            normalized_name = raw_name
        key = normalize(normalized_name)
        if not key:
            continue

        original = original_map.get(raw_name, {})
        meta = dict(original.get('meta', {}))
        meta['llm_enhanced'] = True

        aliases = item.get('aliases', [])
        if not isinstance(aliases, list):
            aliases = []

        records.append({
            'raw_name': raw_name,
            'normalized_name': normalized_name,
            'name': raw_name,
            'key': key,
            'source': source_name,
            'source_db': source_name,
            'source_file': source_file,
            'aliases': [str(alias).strip() for alias in aliases if str(alias).strip()],
            'meta': meta,
        })
    return records
