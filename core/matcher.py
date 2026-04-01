# -*- coding: utf-8 -*-
"""
集合运算模块：根据各来源期刊列表，计算N库交集、任意组合交集、单库独有。
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def compute(db_results: List[Dict]) -> Dict:
    """
    db_results: 最多10个元素的列表，每个元素是 parse() 返回的 dict
    返回:
    {
        'db_names': ['北大核心', 'CSSCI', 'CSCD'],
        'counts': {'北大核心': N, ...},
        'all_n': [{'name':..., 'key':..., 'sources': [...]}],  # 所有N库交集
        'combo_only': {  # 任意组合交集（不含所有N库）
            'A+B': [...],
            'A+B+C': [...],
            ...
        },
        'one_only': {  # 只在单一库中
            'A': [...],
            ...
        }
    }
    """
    db_map = {}  # source_name -> {key: journal_dict}
    for db in db_results:
        journals = db.get('journals', [])
        if not journals:
            continue
        source = db.get('source_db') or journals[0].get('source') or journals[0].get('source_db')
        db_map[source] = {j['key']: j for j in journals}

    db_names = list(db_map.keys())
    n_db = len(db_names)
    counts = {s: len(db_map[s]) for s in db_names}

    logger.info('各库有效期刊数：' + ', '.join(s + '=' + str(counts[s]) for s in db_names))

    key_sets = {s: set(db_map[s].keys()) for s in db_names}

    result = {
        'db_names': db_names,
        'counts': counts,
        'all_n': [],
        'combo_only': {},
        'two_only': {},
        'multi_only': {},
        'one_only': {},
    }

    if n_db == 1:
        s = db_names[0]
        result['one_only'][s] = _make_entries(key_sets[s], db_map, [s])
        return result

    all_keys = set()
    for keys in key_sets.values():
        all_keys |= keys

    combo_only = {}
    one_only = {name: [] for name in db_names}

    for key in sorted(all_keys):
        matched_sources = [name for name in db_names if key in db_map[name]]
        entry = _make_entry(key, db_map, matched_sources)
        if len(matched_sources) == n_db:
            result['all_n'].append(entry)
        elif len(matched_sources) == 1:
            one_only[matched_sources[0]].append(entry)
        else:
            combo_key = '+'.join(matched_sources)
            combo_only.setdefault(combo_key, []).append(entry)

    result['combo_only'] = {k: v for k, v in combo_only.items() if v}
    result['two_only'] = {
        k: v for k, v in result['combo_only'].items()
        if len(k.split('+')) == 2
    }
    result['multi_only'] = {
        k: v for k, v in result['combo_only'].items()
        if len(k.split('+')) >= 3
    }
    result['one_only'] = {k: v for k, v in one_only.items() if v}
    _log_stats(result)
    return result


def _make_entries(keys, db_map: Dict, sources: List) -> List[Dict]:
    return [_make_entry(key, db_map, sources) for key in sorted(keys)]


def _make_entry(key: str, db_map: Dict, sources: List) -> Dict:
    raw_name = key
    normalized_name = key
    aliases = []
    for source in sources:
        journal = db_map.get(source, {}).get(key)
        if not journal:
            continue
        raw_name = journal.get('raw_name') or journal.get('name') or raw_name
        normalized_name = journal.get('normalized_name') or journal.get('key') or normalized_name
        aliases = journal.get('aliases', [])
        break
    return {
        'name': raw_name,
        'raw_name': raw_name,
        'normalized_name': normalized_name,
        'key': key,
        'sources': list(sources),
        'aliases': aliases,
    }


def _log_stats(result: Dict):
    all_n = result.get('all_n', [])
    combo_only = result.get('combo_only', {})
    one_only = result.get('one_only', {})

    if all_n:
        n = len(result['db_names'])
        logger.info(str(n) + '库同时收录：' + str(len(all_n)) + ' 种')
        for e in all_n[:5]:  # 只打印前5个
            logger.info('  [' + str(n) + '库] ' + e["name"])
        if len(all_n) > 5:
            logger.info('  ...')

    for combo_key, entries in combo_only.items():
        logger.info(combo_key + ' 交集：' + str(len(entries)) + ' 种')
        for e in entries[:3]:
            logger.info('  [' + combo_key + '] ' + e["name"])
        if len(entries) > 3:
            logger.info('  ...')

    for src, entries in one_only.items():
        logger.info('仅在 ' + src + '：' + str(len(entries)) + ' 种')
