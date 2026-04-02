# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[('data', 'data')],
    hiddenimports=['openpyxl', 'fitz', 'parsers.csv_parser', 'parsers.excel_parser', 'parsers.pdf_parser', 'parsers.txt_parser', 'parsers.docx_parser', 'parsers.doc_parser', 'parsers.html_parser', 'core.normalizer', 'core.config', 'core.matcher', 'core.exporter', 'core.ingestion', 'core.parser_registry', 'core.llm_client', 'core.llm_extractor', 'core.ocr_service'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='JournalIntersectionTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['data\\1.ico'],
)
