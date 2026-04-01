# -*- coding: utf-8 -*-
"""
中国科技核心期刊目录PDF解析器。
PDF结构：每3行一组 - 序号、期刊代码、期刊名
前几行是标题（包含"中国科技"字样）
"""
import logging
import fitz  # PyMuPDF
from core.normalizer import normalize

logger = logging.getLogger(__name__)


def parse(filepath: str) -> dict:
    """
    返回 {'journals': [{'name': 原始刊名, 'key': 标准化刊名, 'source': '中国科技核心期刊'}]}
    """
    logger.info('中国科技核心期刊目录：开始解析...')
    
    doc = fitz.open(filepath)
    logger.info('总页数: ' + str(len(doc)))
    
    results = []
    seen_keys = set()
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text('text')
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        
        # 跳过标题行（包含"中国科技"字样的行）
        i = 0
        while i < len(lines) and i < 5:
            # 如果前几行包含"中国科技"，则跳过
            if '中国科技' in lines[i] or '核心期刊' in lines[i]:
                i += 1
            else:
                break
        
        # 处理剩余的行，每3行一组
        while i < len(lines):
            # 检查是否还有足够的行
            if i + 2 >= len(lines):
                break
            
            seq = lines[i]
            code = lines[i + 1]
            name = lines[i + 2]
            
            # 验证是否是有效的期刊条目
            # 序号应该是数字
            if not seq.isdigit():
                i += 1
                continue
            
            # 期刊代码应该是字母+数字组合（不是中文）
            if not code or not any(c.isalpha() for c in code):
                i += 1
                continue
            
            # 期刊名不应该太短
            if not name or len(name) < 2:
                i += 1
                continue
            
            # 清理期刊名
            name = name.strip()
            # 去除可能的前缀/后缀空格
            name = name.strip()
            
            # 跳过明显不是期刊名的内容
            skip_keywords = ['续表', '注：', '说明：', '附件', '附录']
            if any(kw in name for kw in skip_keywords):
                i += 3
                continue
            
            # 标准化并去重
            key = normalize(name)
            if key and key not in seen_keys:
                seen_keys.add(key)
                results.append({
                    'name': name,
                    'key': key,
                    'source': '中国科技核心期刊'
                })
            
            i += 3
    
    doc.close()
    
    logger.info('中国科技核心期刊目录：解析完成，有效期刊数 ' + str(len(results)))
    return {'journals': results}
