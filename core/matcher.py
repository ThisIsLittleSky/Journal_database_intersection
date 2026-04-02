# -*- coding: utf-8 -*-
"""
集合运算模块：根据各来源期刊列表，计算包含性质的集合交集统计。
"""
import logging
from itertools import combinations
from typing import Dict, List

logger = logging.getLogger(__name__)


def compute(db_results: List[Dict]) -> Dict:
    """
    db_results: 最多10个元素的列表，每个元素是 parse() 返回的 dict
    返回:
    {
        'db_names': ['北大核心', 'CSSCI', 'CSCD'],
        'counts': {'北大核心': N, ...},
        'intersections': {
            3: {'A+B+C': [...]},  # 3库交集
            2: {'A+B': [...], 'A+C': [...], 'B+C': [...]},  # 2库交集
        },
        'one_only': {'A': [...], ...}  # 单库独有（不在任何交集中）
    }
    """
    db_map = {}
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
        'intersections': {},
        'one_only': {},
    }

    if n_db == 1:
        s = db_names[0]
        result['one_only'][s] = _make_entries(key_sets[s], db_map, [s])
        return result

    all_keys = set()
    for keys in key_sets.values():
        all_keys |= keys

    for size in range(n_db, 1, -1):
        result['intersections'][size] = {}
        for combo in combinations(db_names, size):
            combo_key = '+'.join(combo)
            intersection = set.intersection(*[key_sets[name] for name in combo])
            result['intersections'][size][combo_key] = _make_entries(intersection, db_map, list(combo))

    all_intersection_keys = set()
    for size_dict in result['intersections'].values():
        for entries in size_dict.values():
            all_intersection_keys.update(e['key'] for e in entries)

    for name in db_names:
        only_keys = key_sets[name] - all_intersection_keys
        result['one_only'][name] = _make_entries(only_keys, db_map, [name])

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
    intersections = result.get('intersections', {})
    one_only = result.get('one_only', {})

    for size in sorted(intersections.keys(), reverse=True):
        for combo_key, entries in intersections[size].items():
            logger.info(combo_key + ' 交集：' + str(len(entries)) + ' 种')
            for e in entries[:3]:
                logger.info('  [' + combo_key + '] ' + e["name"])
            if len(entries) > 3:
                logger.info('  ...')

    for src, entries in one_only.items():
        logger.info('仅在 ' + src + '：' + str(len(entries)) + ' 种')
