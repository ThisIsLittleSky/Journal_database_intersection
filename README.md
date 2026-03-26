# 期刊数据库交集分析工具

分析中文期刊在北大核心、CSSCI、CSCD 三大数据库中的收录交集情况，并将结果导出为 Excel 工作簿。

---

## 功能概述

- 支持同时导入最多 3 个数据库文件（xlsx / pdf），自动识别数据库类型
- 自动排除 CSSCI 扩展版、CSCD 扩展库期刊，仅统计正式收录期刊
- 对刊名进行标准化处理（全角/半角统一、去除书名号、忽略大小写），提升匹配准确率
- 计算三库交集、任意两库交集、仅单库收录三个层级的分类结果
- 导出带样式的多工作表 Excel，并输出完整日志（含各库期刊数、各交集数、具体刊名）
- 提供带文件选择和实时日志的 Tkinter GUI，也可命令行直接调用
- 解析结果本地 JSON 缓存，相同文件二次运行无需重复解析
- 支持打包为独立 EXE（PyInstaller）

---

## 支持的数据库文件

| 数据库 | 文件格式 | 说明 |
|---|---|---|
| 北大核心期刊目录 | `.xlsx` | 单工作表，自动定位刊名列 |
| CSSCI 中文社会科学引文索引 | `.xlsx` | 多工作表按学科分类，自动排除扩展版列 |
| CSCD 中国科学引文数据库 | `.pdf` | 逐行解析，自动排除扩展库条目 |

文件名只要包含以下关键词之一，即可自动识别数据库类型，无需手动指定：

- 北大核心：`北大` / `核心期刊目录`
- CSSCI：`CSSCI` / `社会科学引文`
- CSCD：`CSCD` / `科学引文数据库`（或文件为 `.pdf`）

---

## 输出 Excel 结构

| 工作表名 | 内容 |
|---|---|
| 统计摘要 | 各库有效期刊数、各交集数量汇总 |
| 三库交集 | 同时被三个数据库收录的期刊 |
| 北大核心+CSSCI | 仅同时被北大核心和 CSSCI 收录（不含三库交集） |
| 北大核心+CSCD | 仅同时被北大核心和 CSCD 收录（不含三库交集） |
| CSSCI+CSCD | 仅同时被 CSSCI 和 CSCD 收录（不含三库交集） |
| 仅单库收录 | 只被一个数据库收录的期刊（含来源库列） |

---

## 项目结构

```
Journal_database_intersection/
├── parsers/
│   ├── beida.py          # 北大核心 xlsx 解析器
│   ├── cssci.py          # CSSCI xlsx 解析器
│   └── cscd.py           # CSCD PDF 解析器
├── core/
│   ├── normalizer.py     # 刊名标准化
│   ├── matcher.py        # 集合运算（三库/两库/单库）
│   └── exporter.py       # Excel 导出
├── data/
│   └── cache.json        # 解析结果缓存（自动生成）
├── logs/                 # 运行日志目录（自动生成）
├── cache_store.py        # 缓存读写模块
├── logger_setup.py       # 日志配置
├── main.py               # 主逻辑入口（可命令行运行）
├── gui.py                # Tkinter GUI
├── build.bat             # PyInstaller 打包脚本（Windows）
└── requirements.txt      # 依赖列表
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Windows（GUI 及打包脚本基于 Windows，核心逻辑跨平台）

### 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

`requirements.txt` 内容：

```
openpyxl>=3.1.0
PyMuPDF>=1.23.0
```

### 命令行运行

```bash
python main.py 文件1 [文件2] [文件3] 输出路径.xlsx
```

示例：

```bash
python main.py \
  "1.北大核心期刊目录2023版.xlsx" \
  "2.CSSCI2025-2026版.xlsx" \
  "3.CSCD来源期刊列表2025-2026.pdf" \
  "期刊交集分析结果.xlsx"
```

### GUI 运行

```bash
python gui.py
```

界面说明：
1. 分别为三个数据库文件点击「浏览…」选择文件（可以只选 1 或 2 个）
2. 选择输出目录（不选则默认输出到第一个文件所在目录）
3. 点击「开始分析」，日志实时显示在下方
4. 完成后弹窗提示，可一键打开输出文件所在目录

![GUI 界面示意](docs/gui_preview.png)

---

## 打包为 EXE

在项目根目录双击运行 `build.bat`，将自动调用 PyInstaller 生成单文件可执行程序，输出在 `dist/` 目录。

```
dist/
└── 期刊交集分析工具.exe
```

> 打包前需先激活虚拟环境并安装 `pyinstaller`：
> ```bash
> pip install pyinstaller
> ```

---

## 实际运行结果示例

以 2023 版北大核心（1987 种）、CSSCI 2025-2026（660 种主刊）、CSCD 2025-2026（1120 种核心库）为输入：

| 分类 | 期刊数 |
|---|---|
| 三库同时收录 | 28 种 |
| 仅北大核心 + CSSCI | 446 种 |
| 仅北大核心 + CSCD | 618 种 |
| 仅 CSSCI + CSCD | 0 种 |
| 仅单库收录 | 1555 种 |

> CSSCI 与 CSCD 无交集符合预期——CSSCI 收录人文社科期刊，CSCD 收录自然科学期刊，学科几乎不重叠。

---

## 注意事项

- 刊名匹配采用字符串精确匹配（标准化后），不做模糊匹配
- 如更新了数据库文件，删除 `data/cache.json` 可强制重新解析
- 本工具不内置任何数据库文件，需用户自行获取并提供原始文件

---

## License

MIT
