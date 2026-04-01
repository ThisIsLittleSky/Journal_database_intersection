# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import tempfile

import fitz


class OCRService:
    def __init__(self, executable: str | None = None):
        self.executable = executable or self._detect_executable()

    def _detect_executable(self) -> str | None:
        executable = shutil.which('tesseract')
        if executable:
            return executable
        try:
            result = subprocess.run(
                ['where.exe', 'tesseract'],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                if lines:
                    return lines[0]
        except Exception:
            return None
        return None

    def available(self) -> bool:
        return bool(self.executable)

    def extract_text_from_pdf(self, file_path: str, dpi: int = 200, lang: str = 'chi_sim+eng') -> str:
        if not self.available():
            raise RuntimeError('未检测到 tesseract，可执行 OCR 不可用')

        doc = fitz.open(file_path)
        scale = max(dpi / 72.0, 1.0)
        matrix = fitz.Matrix(scale, scale)
        text_parts = []

        with tempfile.TemporaryDirectory(prefix='journal_ocr_') as temp_dir:
            for page_index, page in enumerate(doc):
                image_path = os.path.join(temp_dir, f'page_{page_index + 1}.png')
                output_base = os.path.join(temp_dir, f'page_{page_index + 1}')
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                pix.save(image_path)
                cmd = [self.executable, image_path, output_base, '-l', lang]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or 'tesseract 执行失败')
                txt_path = output_base + '.txt'
                if os.path.exists(txt_path):
                    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text_parts.append(f.read())
        doc.close()
        return '\n'.join(part.strip() for part in text_parts if part.strip())
