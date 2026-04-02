# -*- coding: utf-8 -*-
import logging
import os
import re

import fitz
from core.ocr_service import OCRService
from core.text_chunking import build_page_chunks

logger = logging.getLogger(__name__)

_SKIP_LINE = re.compile(
    r'^(第?\s*\d+\s*页|page\s*\d+|\d+/\d+|issn[:：]?\s*[\dxX-]+|doi[:：])$',
    re.IGNORECASE
)
_LEADING_INDEX = re.compile(r'^\s*\d+[\.\-、\)\]）\s]*')


def _extract_pages(filepath: str) -> list[str]:
    doc = fitz.open(filepath)
    pages = []
    for page in doc:
        text = page.get_text('text')
        pages.append(text.strip())
    doc.close()
    return pages


def _filter_candidate_lines(lines: list[str]) -> list[str]:
    filtered = []
    for raw_line in lines:
        line = _LEADING_INDEX.sub('', raw_line).strip()
        if _is_candidate(line):
            filtered.append(line)
    return filtered


def _is_candidate(line: str) -> bool:
    if len(line) < 2 or len(line) > 120:
        return False
    if _SKIP_LINE.match(line):
        return False
    if line.isdigit():
        return False
    if not any('\u4e00' <= ch <= '\u9fff' or ch.isalpha() for ch in line):
        return False
    return True


def parse(filepath: str) -> dict:
    source_name = os.path.splitext(os.path.basename(filepath))[0]
    pages = _extract_pages(filepath)
    lines = [line.strip() for page in pages for line in page.splitlines() if line.strip()]
    ocr_used = False

    candidate_lines = _filter_candidate_lines(lines)
    if len(candidate_lines) < 3:
        ocr_service = OCRService()
        if ocr_service.available():
            logger.info('通用PDF文本层较弱，尝试OCR识别...')
            try:
                ocr_text = ocr_service.extract_text_from_pdf(filepath)
                if ocr_text.strip():
                    pages = [page.strip() for page in ocr_text.split('\f') if page.strip()]
                    if not pages:
                        pages = [ocr_text.strip()]
                    lines = [line.strip() for page in pages for line in page.splitlines() if line.strip()]
                    candidate_lines = _filter_candidate_lines(lines)
                    ocr_used = True
            except Exception as exc:
                logger.warning('PDF OCR失败，继续使用原始文本层：' + str(exc))
        else:
            logger.warning('未检测到tesseract，扫描版PDF可能无法完整识别')

    results = []
    seen_names = set()

    for line in candidate_lines:
        if line in seen_names:
            continue
        seen_names.add(line)
        results.append({'name': line, 'key': line, 'source': source_name})

    logger.info(f'通用PDF解析完成：{source_name}，有效期刊数 {len(results)}')
    return {
        'source_db': source_name,
        'journals': results,
        'raw_text': '\n'.join(lines[:500]),
        'raw_chunks': build_page_chunks(pages),
        'warnings': ['已启用OCR识别'] if ocr_used else [],
    }
