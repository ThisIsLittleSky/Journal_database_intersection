# -*- coding: utf-8 -*-
"""
主逻辑入口：根据注册解析器自动处理多格式文件，计算交集，导出结果。
可独立命令行运行，也被 GUI 调用。
"""
import os
import logging

import logger_setup
from core import config as app_config
from core import exporter, ingestion, llm_extractor, matcher

logger = logging.getLogger(__name__)

def _ensure_unique_source_names(db_results: list[dict]) -> list[dict]:
    seen = {}
    for result in db_results:
        base_name = str(result.get('source_db') or os.path.splitext(
            os.path.basename(result.get('source_file', ''))
        )[0] or '未命名来源')
        seen[base_name] = seen.get(base_name, 0) + 1
        new_name = base_name if seen[base_name] == 1 else f'{base_name}({seen[base_name]})'
        result['source_db'] = new_name
        for journal in result.get('journals', []):
            journal['source'] = new_name
            journal['source_db'] = new_name
    return db_results


def run(
    filepaths: list,
    output_path: str,
    log_callback=None,
    log_dir: str = None,
    export_mode: str = 'compact',
    llm_config: dict | None = None,
):
    """
    filepaths: 1~10 个文件路径
    output_path: 输出 Excel 路径
    log_callback: 可选，GUI 日志回调
    log_dir: 可选，日志文件目录
    export_mode: compact | full
    llm_config: LLM配置，未传时读取本地conf
    """
    # 初始化日志（如果尚未初始化）
    if not logging.getLogger().handlers:
        logger_setup.setup(log_dir=log_dir, callback=log_callback)
    elif log_callback:
        logger_setup.setup(log_dir=log_dir, callback=log_callback)

    if not 1 <= len(filepaths) <= 10:
        raise ValueError('当前支持 1-10 个文件')

    logger.info('=' * 50)
    logger.info('开始分析，共 ' + str(len(filepaths)) + ' 个文件')

    resolved_llm_config = app_config.build_llm_config(llm_config)
    if resolved_llm_config.get('enabled'):
        logger.info('已启用LLM增强：' + resolved_llm_config.get('model', ''))
    else:
        logger.info('未启用LLM增强，将仅使用规则解析')

    registry = ingestion.get_registry()
    db_results = []
    for fp in filepaths:
        fp = os.path.abspath(fp)
        logger.info('处理文件：' + os.path.basename(fp))
        try:
            result = ingestion.parse_file(fp, registry=registry)
            result = llm_extractor.enhance_parse_result(result, resolved_llm_config)
            logger.info('  使用解析器：' + result.get('parser_name', 'unknown'))
            db_results.append(result)
        except Exception as e:
            logger.error('  解析失败：' + str(e))
            raise

    if not db_results:
        raise RuntimeError('没有成功解析任何文件')

    db_results = _ensure_unique_source_names(db_results)
    logger.info('开始计算交集...')
    result = matcher.compute(db_results)

    logger.info('导出结果到：' + output_path)
    exporter.export(result, output_path, mode=export_mode)

    logger.info('=' * 50)
    logger.info('分析完成！')
    return result


if __name__ == '__main__':
    import sys

    # 命令行用法：python main.py 文件1 [文件2 ... 文件10] 输出路径
    if len(sys.argv) < 3:
        print('用法：python main.py <文件1> [文件2] ... <输出Excel路径>')
        sys.exit(1)

    files = sys.argv[1:-1]
    out = sys.argv[-1]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logger_setup.setup(log_dir=os.path.join(script_dir, 'logs'))

    run(files, out)
