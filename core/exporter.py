# -*- coding: utf-8 -*-
"""
Excel导出模块：将匹配结果写入多工作表的Excel文件。
工作表：统计摘要 | 三库交集 | 两库交集（各对） | 仅单库
"""
import logging
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import Dict

logger = logging.getLogger(__name__)

# 颜色配置
_HEADER_FILL = PatternFill('solid', fgColor='2E75B6')
_HEADER_FONT = Font(bold=True, color='FFFFFF', size=11)
_SUBHEADER_FILL = PatternFill('solid', fgColor='D6E4F7')
_SUBHEADER_FONT = Font(bold=True, color='1F3864', size=10)
_BORDER_SIDE = Side(style='thin', color='AAAAAA')
_CELL_BORDER = Border(
    left=_BORDER_SIDE, right=_BORDER_SIDE,
    top=_BORDER_SIDE, bottom=_BORDER_SIDE
)
_ALT_FILL = PatternFill('solid', fgColor='F2F7FB')


def _style_header(cell):
    cell.fill = _HEADER_FILL
    cell.font = _HEADER_FONT
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = _CELL_BORDER


def _style_subheader(cell):
    cell.fill = _SUBHEADER_FILL
    cell.font = _SUBHEADER_FONT
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = _CELL_BORDER


def _style_data(cell, alt=False):
    if alt:
        cell.fill = _ALT_FILL
    cell.alignment = Alignment(vertical='center')
    cell.border = _CELL_BORDER


def _set_col_width(ws, col_idx, width):
    ws.column_dimensions[get_column_letter(col_idx)].width = width


def _write_journal_sheet(ws, entries, columns, title):
    """通用期刊列表写入。columns: list of (header, field_or_callable)"""
    ws.freeze_panes = 'A2'
    # 标题行
    for j, (header, _) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=j, value=header)
        _style_header(cell)

    for i, entry in enumerate(entries, 2):
        alt = (i % 2 == 0)
        for j, (_, field) in enumerate(columns, 1):
            if callable(field):
                value = field(entry)
            else:
                value = entry.get(field, '')
            cell = ws.cell(row=i, column=j, value=value)
            _style_data(cell, alt)

    # 自动列宽
    for j in range(1, len(columns) + 1):
        max_len = max(
            (len(str(ws.cell(r, j).value or '')) for r in range(1, ws.max_row + 1)),
            default=10
        )
        _set_col_width(ws, j, min(max_len + 4, 60))


def _write_summary_sheet(ws, result: Dict):
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20

    row = 1

    def write_header(text):
        nonlocal row
        cell = ws.cell(row=row, column=1, value=text)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        _style_header(cell)
        row += 1

    def write_row(label, value, alt=False):
        nonlocal row
        c1 = ws.cell(row=row, column=1, value=label)
        c2 = ws.cell(row=row, column=2, value=value)
        _style_data(c1, alt)
        _style_data(c2, alt)
        c2.alignment = Alignment(horizontal='center', vertical='center')
        row += 1

    write_header('各数据库有效期刊数')
    for i, (src, cnt) in enumerate(result['counts'].items()):
        write_row(f'  {src}（排除扩展版/扩展库）', cnt, i % 2 == 0)

    row += 1
    write_header('交集统计')

    all_three = result.get('all_three', [])
    if all_three:
        write_row('三库同时收录', len(all_three), True)

    for i, (pair_key, entries) in enumerate(result.get('two_only', {}).items()):
        write_row(f'仅{pair_key}共同收录', len(entries), i % 2 == 0)

    row += 1
    write_header('单库独有统计')
    for i, (src, entries) in enumerate(result.get('one_only', {}).items()):
        write_row(f'仅在{src}中收录', len(entries), i % 2 == 0)


def export(result: Dict, output_path: str):
    wb = Workbook()
    wb.remove(wb.active)

    # 1. 统计摘要
    ws_summary = wb.create_sheet('统计摘要')
    _write_summary_sheet(ws_summary, result)
    logger.info('已写入工作表：统计摘要')

    # 2. 三库交集
    all_three = result.get('all_three', [])
    if all_three:
        ws = wb.create_sheet('三库交集')
        _write_journal_sheet(ws, all_three, [
            ('序号', lambda e: all_three.index(e) + 1),
            ('刊名', 'name'),
            ('收录库', lambda e: ' + '.join(e['sources'])),
        ], '三库交集')
        logger.info(f'已写入工作表：三库交集（{len(all_three)} 种）')

    # 3. 两库交集
    for pair_key, entries in result.get('two_only', {}).items():
        if not entries:
            continue
        sheet_name = pair_key  # 如'北大核心+CSSCI'
        # sheet名称最长31字符
        if len(sheet_name) > 31:
            sheet_name = sheet_name[:31]
        ws = wb.create_sheet(sheet_name)
        _write_journal_sheet(ws, entries, [
            ('序号', lambda e: entries.index(e) + 1),
            ('刊名', 'name'),
            ('收录库', lambda e: ' + '.join(e['sources'])),
        ], pair_key)
        logger.info(f'已写入工作表：{pair_key}（{len(entries)} 种）')

    # 4. 仅单库
    one_entries_all = []
    for src, entries in result.get('one_only', {}).items():
        for e in entries:
            one_entries_all.append({'name': e['name'], 'key': e['key'], 'source': src})

    if one_entries_all:
        one_entries_all.sort(key=lambda x: (x['source'], x['name']))
        ws = wb.create_sheet('仅单库收录')
        _write_journal_sheet(ws, one_entries_all, [
            ('序号', lambda e: one_entries_all.index(e) + 1),
            ('刊名', 'name'),
            ('收录库', 'source'),
        ], '仅单库收录')
        logger.info(f'已写入工作表：仅单库收录（{len(one_entries_all)} 种）')

    wb.save(output_path)
    logger.info(f'Excel 已保存：{output_path}')
