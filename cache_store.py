# -*- coding: utf-8 -*-
"""
JSON 缓存模块：将解析结果缓存到 data/cache.json，
以文件路径+修改时间为键，避免重复解析。
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'cache.json')


def _file_mtime(filepath: str) -> float:
    try:
        return os.path.getmtime(filepath)
    except OSError:
        return 0.0


def _cache_key(filepath: str) -> str:
    return f'{os.path.abspath(filepath)}::{_file_mtime(filepath)}'


def load_cache() -> dict:
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache: dict):
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get(filepath: str) -> dict | None:
    cache = load_cache()
    key = _cache_key(filepath)
    return cache.get(key)


def set(filepath: str, data: dict):
    cache = load_cache()
    key = _cache_key(filepath)
    cache[key] = data
    save_cache(cache)
    logger.debug(f'缓存已更新：{filepath}')
