'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 07:20:39
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 07:20:52
FilePath: /RAG_agent/src/extensions/ext_storage.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import logging
from collections.abc import Callable, Generator
from typing import Literal, Union, overload

from flask import Flask

logger = logging.getLogger(__name__)

class Storage:
    def init_app(self, app: Flask):
        storage_factory = self.get_storage_factory()
        with app.app_context():
            self.storage_runner = storage_factory()

    def get_storage_factory():
        pass

    def save(self):
        pass

    def load(self):
        pass

    def load_once(self):
        pass

    def load_stream(self):
        pass

    def download(self):
        pass

    def exists(self):
        pass

    def delete(self):
        pass

    def scan(self):
        pass

storage = Storage()

def init_app(app: Flask):
    """供应用启动时调用的初始化入口"""
    storage.init_app(app)