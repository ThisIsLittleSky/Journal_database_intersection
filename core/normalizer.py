# -*- coding: utf-8 -*-
"""
刊名标准化模块：统一全半角、去除书名号、空格、标点，用于跨库匹配。
"""
import re
import unicodedata


_FULLWIDTH_OFFSET = ord('Ａ') - ord('A')

def _fullwidth_to_halfwidth(s: str) -> str:
    result = []
    for ch in s:
        cp = ord(ch)
        if ord('！') <= cp <= ord('～'):
            result.append(chr(cp - 0xFEE0))
        elif ch == '　':
            result.append(' ')
        else:
            result.append(ch)
    return ''.join(result)


def normalize(name: str) -> str:
    if not name or not isinstance(name, str):
        return ''
    s = name.strip()
    # 去除书名号
    s = s.replace('《', '').replace('》', '').replace('〈', '').replace('〉', '')
    # 全角转半角
    s = _fullwidth_to_halfwidth(s)
    # 去除所有空白字符
    s = re.sub(r'\s+', '', s)
    # 统一括号
    s = s.replace('（', '(').replace('）', ')')
    # 英文大写（中文不受影响）
    s = s.upper()
    return s
