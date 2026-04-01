# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class JournalRecord:
    raw_name: str
    normalized_name: str
    key: str
    source_db: str
    source_file: str = ''
    aliases: List[str] = field(default_factory=list)
    meta: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'raw_name': self.raw_name,
            'normalized_name': self.normalized_name,
            'name': self.raw_name,
            'key': self.key,
            'source': self.source_db,
            'source_db': self.source_db,
            'source_file': self.source_file,
            'aliases': list(self.aliases),
            'meta': dict(self.meta),
        }


@dataclass
class ParseResult:
    source_file: str
    source_db: str
    file_type: str
    parser_name: str
    journals: List[JournalRecord] = field(default_factory=list)
    raw_text: str = ''
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'source_file': self.source_file,
            'source_db': self.source_db,
            'file_type': self.file_type,
            'parser_name': self.parser_name,
            'journals': [journal.to_dict() for journal in self.journals],
            'raw_text': self.raw_text,
            'warnings': list(self.warnings),
        }
