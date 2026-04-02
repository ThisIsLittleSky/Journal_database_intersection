# -*- coding: utf-8 -*-
import configparser
import os
import sys


CONFIG_FILE_NAME = 'conf_Journal_database_intersection.conf'
DEFAULT_BASE_URL = 'https://api.deepseek.com'
DEFAULT_MODEL = 'deepseek-chat'


def get_runtime_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_path() -> str:
    return os.path.join(get_runtime_dir(), CONFIG_FILE_NAME)


def load_app_config() -> dict:
    parser = configparser.ConfigParser()
    config_path = get_config_path()
    if os.path.exists(config_path):
        parser.read(config_path, encoding='utf-8')

    return {
        'llm_enabled': parser.getboolean('llm', 'enabled', fallback=False),
        'llm_api_key': parser.get('llm', 'api_key', fallback='').strip(),
        'llm_base_url': parser.get('llm', 'base_url', fallback=DEFAULT_BASE_URL).strip(),
        'llm_model': parser.get('llm', 'model', fallback=DEFAULT_MODEL).strip(),
    }


def save_app_config(config: dict):
    parser = configparser.ConfigParser()
    parser['llm'] = {
        'enabled': 'true' if config.get('llm_enabled') else 'false',
        'api_key': str(config.get('llm_api_key', '') or '').strip(),
        'base_url': str(config.get('llm_base_url', DEFAULT_BASE_URL) or DEFAULT_BASE_URL).strip(),
        'model': str(config.get('llm_model', DEFAULT_MODEL) or DEFAULT_MODEL).strip(),
    }

    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        parser.write(f)


def build_llm_config(app_config: dict | None = None) -> dict:
    data = app_config or load_app_config()
    api_key = str(data.get('llm_api_key', data.get('api_key', '')) or '').strip()
    enabled_flag = data.get('llm_enabled')
    if enabled_flag is None:
        enabled_flag = data.get('enabled')
    enabled = bool(enabled_flag) and bool(api_key)
    return {
        'enabled': enabled,
        'api_key': api_key,
        'base_url': str(
            data.get('llm_base_url', data.get('base_url', DEFAULT_BASE_URL))
            or DEFAULT_BASE_URL
        ).strip(),
        'model': str(data.get('llm_model', data.get('model', DEFAULT_MODEL)) or DEFAULT_MODEL).strip(),
    }
