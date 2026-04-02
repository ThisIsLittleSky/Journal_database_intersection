# -*- coding: utf-8 -*-
def build_line_chunks(
    lines: list[str],
    chunk_size: int,
    label_prefix: str = '片段',
) -> list[dict]:
    clean_lines = [str(line).strip() for line in lines if str(line).strip()]
    chunks = []
    for start in range(0, len(clean_lines), chunk_size):
        batch = clean_lines[start:start + chunk_size]
        if not batch:
            continue
        start_line = start + 1
        end_line = start + len(batch)
        chunks.append({
            'label': f'{label_prefix}{start_line}-{end_line}',
            'text': '\n'.join(batch),
        })
    return chunks


def build_page_chunks(pages: list[str], label_template: str = '第{index}页') -> list[dict]:
    chunks = []
    for index, page_text in enumerate(pages, start=1):
        text = str(page_text).strip()
        if not text:
            continue
        chunks.append({
            'label': label_template.format(index=index),
            'text': text,
        })
    return chunks
