# -*- coding: utf-8 -*-
import os

from parsers.base import BaseParser
from parsers import csv_parser, doc_parser, docx_parser, excel_parser, html_parser, pdf_parser, txt_parser


class FunctionParser(BaseParser):
    def __init__(self, name, supported_extensions, parse_func, keywords=None):
        self.name = name
        self.supported_extensions = tuple(ext.lower() for ext in supported_extensions)
        self._parse_func = parse_func
        self._keywords = tuple((keywords or ()))

    def can_handle(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_extensions:
            return False
        if not self._keywords:
            return True
        file_name = os.path.basename(file_path).lower()
        return any(keyword.lower() in file_name for keyword in self._keywords)

    def parse(self, file_path: str, context: dict | None = None) -> dict:
        return self._parse_func(file_path)


class ParserRegistry:
    def __init__(self):
        self._parsers = []

    def register(self, parser: BaseParser):
        self._parsers.append(parser)

    def resolve(self, file_path: str) -> BaseParser:
        for parser in self._parsers:
            if parser.can_handle(file_path):
                return parser
        raise ValueError('无法识别文件类型或数据库类型：' + file_path)


def build_default_registry() -> ParserRegistry:
    registry = ParserRegistry()

    registry.register(FunctionParser(
        name='excel_generic',
        supported_extensions=('.xlsx', '.xls'),
        parse_func=excel_parser.parse
    ))
    registry.register(FunctionParser(
        name='csv_generic',
        supported_extensions=('.csv',),
        parse_func=csv_parser.parse
    ))
    registry.register(FunctionParser(
        name='txt_generic',
        supported_extensions=('.txt',),
        parse_func=txt_parser.parse
    ))
    registry.register(FunctionParser(
        name='docx_generic',
        supported_extensions=('.docx',),
        parse_func=docx_parser.parse
    ))
    registry.register(FunctionParser(
        name='doc_generic',
        supported_extensions=('.doc', '.rtf'),
        parse_func=doc_parser.parse
    ))
    registry.register(FunctionParser(
        name='html_generic',
        supported_extensions=('.html', '.htm'),
        parse_func=html_parser.parse
    ))
    registry.register(FunctionParser(
        name='pdf_generic',
        supported_extensions=('.pdf',),
        parse_func=pdf_parser.parse
    ))
    return registry
