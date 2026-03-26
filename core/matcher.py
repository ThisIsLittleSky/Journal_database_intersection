# -*- coding: utf-8 -*-
"""
集合运算模块：根据各库期刊列表，计算三库交集、两库交集、单库。
输入：各库解析结果（list of dict，含 key/name/source）
输出：分类结果字典
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def compute(db_results: List[Dict]) -> Dict:
    """
    db_results: 最多3个元素的列表，每个元素是 parse() 返回的 dict
    返回:
    {
        'db_names': ['北大核心', 'CSSCI', 'CSCD'],
        'counts': {'北大核心': N, ...},
        'all_three': [{'name':..., 'key':..., 'sources': [...]}],
        'two_only': {
            '北大核心+CSSCI': [...],
            '北大核心+CSCD': [...],
            'CSSCI+CSCD': [...],
        },
        'one_only': {
            '北大核心': [...],
            'CSSCI': [...],
            'CSCD': [...],
        }
    }
    """
    # 构建每个库的 key->原始名 映射
    db_map = {}  # source_name -> {key: name}
    for db in db_results:
        journals = db.get('journals', [])
        if not journals:
            continue
        source = journals[0]['source']
        db_map[source] = {j['key']: j['name'] for j in journals}

    db_names = list(db_map.keys())
    counts = {s: len(db_map[s]) for s in db_names}

    logger.info('各库有效期刊数：' + ', '.join(f'{s}={counts[s]}' for s in db_names))

    key_sets = {s: set(db_map[s].keys()) for s in db_names}

    result = {
        'db_names': db_names,
        'counts': counts,
        'all_three': [],
        'two_only': {},
        'one_only': {},
    }

    if len(db_names) == 1:
        s = db_names[0]
        result['one_only'][s] = _make_entries(key_sets[s], db_map, [s])
        return result

    if len(db_names) == 2:
        s0, s1 = db_names[0], db_names[1]
        both = key_sets[s0] & key_sets[s1]
        pair_key = f'{s0}+{s1}'
        result['two_only'][pair_key] = _make_entries(both, db_map, [s0, s1])
        result['one_only'][s0] = _make_entries(key_sets[s0] - both, db_map, [s0])
        result['one_only'][s1] = _make_entries(key_sets[s1] - both, db_map, [s1])
        _log_stats(result)
        return result

    # 3个库
    s0, s1, s2 = db_names[0], db_names[1], db_names[2]
    all_three_keys = key_sets[s0] & key_sets[s1] & key_sets[s2]

    pairs = [
        (s0, s1), (s0, s2), (s1, s2)
    ]
    two_only = {}
    for pa, pb in pairs:
        both = (key_sets[pa] & key_sets[pb]) - all_three_keys
        pair_key = f'{pa}+{pb}'
        two_only[pair_key] = _make_entries(both, db_map, [pa, pb])

    one_only = {}
    for s in db_names:
        others = [x for x in db_names if x != s]
        exclusive = key_sets[s]
        for o in others:
            exclusive = exclusive - key_sets[o]
        one_only[s] = _make_entries(exclusive, db_map, [s])

    result['all_three'] = _make_entries(all_three_keys, db_map, db_names)
    result['two_only'] = two_only
    result['one_only'] = one_only

    _log_stats(result)
    return result


def _make_entries(keys, db_map, sources) -> List[Dict]:
    entries = []
    for key in sorted(keys):
        # 取第一个拥有该key的source的原始名
        name = None
        for s in sources:
            if key in db_map.get(s, {}):
                name = db_map[s][key]
                break
        if name is None:
            name = key
        entries.append({'name': name, 'key': key, 'sources': list(sources)})
    return entries


def _log_stats(result: Dict):
    all_three = result.get('all_three', [])
    two_only = result.get('two_only', {})
    one_only = result.get('one_only', {})

    if all_three:
        logger.info(f'三库交集：{len(all_three)} 种')
        for e in all_three:
            logger.info(f'  [三库] {e["name"]}')

    for pair_key, entries in two_only.items():
        logger.info(f'{pair_key} 交集（不含三库）：{len(entries)} 种')
        for e in entries:
            logger.info(f'  [{pair_key}] {e["name"]}')

    for src, entries in one_only.items():
        logger.info(f'仅在 {src}：{len(entries)} 种')
