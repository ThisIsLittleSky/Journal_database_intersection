# -*- coding: utf-8 -*-
"""
日志配置：同时输出到控制台和文件，支持外部回调（用于 GUI 文本框）。
"""
import logging
import os
from datetime import datetime


class CallbackHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        msg = self.format(record)
        try:
            self.callback(msg)
        except Exception:
            pass


def setup(log_dir: str = None, callback=None) -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S')

    # 控制台
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # 文件
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'run_{ts}.log')
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)

    # GUI 回调
    if callback:
        cbh = CallbackHandler(callback)
        cbh.setLevel(logging.INFO)
        cbh.setFormatter(fmt)
        root.addHandler(cbh)

    return root
