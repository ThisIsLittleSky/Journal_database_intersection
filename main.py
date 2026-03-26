# -*- coding: utf-8 -*-
"""
主逻辑入口：根据文件类型自动选择解析器，计算交集，导出结果。
可独立命令行运行，也被 GUI 调用。
"""
import os
import logging

import cache_store
import logger_setup
from core import matcher, exporter

logger = logging.getLogger(__name__)


def _detect_parser(filepath: str):
    """根据文件名关键词自动选择解析器，返回解析函数。"""
    name = os.path.basename(filepath)
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.pdf':
        from parsers import cscd
        return cscd.parse

    if ext in ('.xlsx', '.xls'):
        name_lower = name.lower()
        # 北大核心关键词
        if any(k in name for k in ('北大', '核心期刊目录', 'beida')):
            from parsers import beida
            return beida.parse
        # CSSCI 关键词
        if any(k in name.upper() for k in ('CSSCI', '社会科学引文')):
            from parsers import cssci
            return cssci.parse
        # CSCD 关键词
        if any(k in name.upper() for k in ('CSCD', '科学引文数据库')):
            from parsers import cscd
            return cscd.parse

    raise ValueError(f'无法识别文件类型或数据库类型：{filepath}')


def run(filepaths: list, output_path: str, log_callback=None, log_dir: str = None):
    """
    filepaths: 1~3 个文件路径
    output_path: 输出 Excel 路径
    log_callback: 可选，GUI 日志回调
    log_dir: 可选，日志文件目录
    """
    # 初始化日志（如果尚未初始化）
    if not logging.getLogger().handlers:
        logger_setup.setup(log_dir=log_dir, callback=log_callback)
    elif log_callback:
        logger_setup.setup(log_dir=log_dir, callback=log_callback)

    logger.info('=' * 50)
    logger.info(f'开始分析，共 {len(filepaths)} 个文件')

    db_results = []
    for fp in filepaths:
        fp = os.path.abspath(fp)
        logger.info(f'处理文件：{os.path.basename(fp)}')

        # 尝试缓存
        cached = cache_store.get(fp)
        if cached:
            logger.info(f'  命中缓存，跳过重新解析')
            db_results.append(cached)
            continue

        try:
            parse_fn = _detect_parser(fp)
            result = parse_fn(fp)
            cache_store.set(fp, result)
            db_results.append(result)
        except Exception as e:
            logger.error(f'  解析失败：{e}')
            raise

    if not db_results:
        raise RuntimeError('没有成功解析任何文件')

    logger.info('开始计算交集...')
    result = matcher.compute(db_results)

    logger.info(f'导出结果到：{output_path}')
    exporter.export(result, output_path)

    logger.info('=' * 50)
    logger.info('分析完成！')
    return result


if __name__ == '__main__':
    import sys

    # 命令行用法：python main.py 文件1 文件2 文件3 输出路径
    if len(sys.argv) < 3:
        print('用法：python main.py <文件1> [文件2] [文件3] <输出Excel路径>')
        sys.exit(1)

    files = sys.argv[1:-1]
    out = sys.argv[-1]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logger_setup.setup(log_dir=os.path.join(script_dir, 'logs'))

    run(files, out)
