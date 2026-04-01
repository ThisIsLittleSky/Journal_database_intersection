# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
import os


class BaseParser(ABC):
    name = 'base'
    supported_extensions = ()

    def can_handle(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions

    @abstractmethod
    def parse(self, file_path: str, context: dict | None = None) -> dict:
        raise NotImplementedError
