@echo off
chcp 65001 >nul
echo ========================================
echo  Journal Database Intersection Tool - Build Script
echo ========================================

cd /d "%~dp0"

echo [1/3] Activating virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found, please run: python -m venv venv
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo [2/3] Installing PyInstaller...
pip install pyinstaller -q
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo [3/3] Building single-file EXE...
pyinstaller ^
    --onefile ^
    --windowed ^
    --noconsole ^
    --icon "data\1.ico" ^
    --name "JournalIntersectionTool" ^
    --add-data "data;data" ^
    --hidden-import openpyxl ^
    --hidden-import fitz ^
    --hidden-import parsers.csv_parser ^
    --hidden-import parsers.excel_parser ^
    --hidden-import parsers.pdf_parser ^
    --hidden-import parsers.txt_parser ^
    --hidden-import parsers.docx_parser ^
    --hidden-import parsers.doc_parser ^
    --hidden-import parsers.html_parser ^
    --hidden-import core.normalizer ^
    --hidden-import core.config ^
    --hidden-import core.matcher ^
    --hidden-import core.exporter ^
    --hidden-import core.ingestion ^
    --hidden-import core.parser_registry ^
    --hidden-import core.llm_client ^
    --hidden-import core.llm_extractor ^
    --hidden-import core.ocr_service ^
    gui.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed, please check error messages above
    pause
    exit /b 1
)

echo.
echo Build completed! EXE is located in dist\ directory.
pause
