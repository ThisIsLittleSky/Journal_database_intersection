@echo off
chcp 65001 >nul
echo ========================================
echo  期刊数据库交集分析工具 - 打包脚本
echo ========================================

cd /d "%~dp0"

echo [1/3] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [2/3] 安装 PyInstaller...
pip install pyinstaller -q

echo [3/3] 打包为单文件 EXE...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "期刊交集分析工具" ^
    --add-data "data;data" ^
    --hidden-import openpyxl ^
    --hidden-import fitz ^
    --hidden-import parsers.beida ^
    --hidden-import parsers.cssci ^
    --hidden-import parsers.cscd ^
    --hidden-import core.normalizer ^
    --hidden-import core.matcher ^
    --hidden-import core.exporter ^
    gui.py

echo.
echo 打包完成！EXE 位于 dist\ 目录。
pause
