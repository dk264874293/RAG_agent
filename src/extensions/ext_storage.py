'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 07:20:39
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 21:38:01
FilePath: /RAG_agent/src/extensions/ext_storage.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import logging
import os
from collections.abc import Callable, Generator
from typing import Literal, Union, overload

from flask import Flask
from .storage.base_storage import BaseStorage
from .storage.storage_type import StorageType

logger = logging.getLogger(__name__)

class Storage:
    def init_app(self, app: Flask):
        storage_factory = self.get_storage_factory(StorageType.LOCAL)
        with app.app_context():
            self.storage_runner = storage_factory()

    def get_storage_factory(storage_type: StorageType) -> Callable[[], BaseStorage]:
        match storage_type:
            # 1. 本地文件存储（基于OpenDAL的fs协议）
            case StorageType.LOCAL:
                from extensions.storage.opendal_storage import OpenDALStorage
                # 获取项目根目录（当前运行文件所在的目录，可根据实际调整）
                # __file__ 是当前文件（如 storage.py）的绝对路径
                # os.path.dirname(__file__) 获取当前文件所在文件夹
                # os.path.abspath() 转为绝对路径，避免相对路径混乱
                project_root = os.path.abspath(os.path.dirname(__file__))
                # 拼接存储子文件夹（项目根目录/storage），避免根目录文件杂乱
                local_storage_path = os.path.join(project_root, "storage")
                # 确保文件夹存在（不存在则自动创建）
                os.makedirs(local_storage_path, exist_ok=True)
                # 返回带参数的工厂函数：指定本地文件协议和存储根路径
                return lambda: OpenDALStorage(scheme="fs", root=local_storage_path)
            # # 2. 阿里云OSS存储
            # case StorageType.ALIYUN_OSS:
            #     from extensions.storage.aliyun_oss_storage import AliyunOssStorage
            #     # 直接返回类（实例化参数由AliyunOssStorage内部从配置读取）
            #     return AliyunOssStorage
            # 未知存储类型
            case _:
                raise ValueError(f"仅支持 LOCAL/ALIYUN_OSS 存储类型，当前传入：{storage_type}")

    def save(self,filename:str,data:bytes):
        self.storage_runner.save(filename,data)

    @overload
    def load(self, filename:str, / , *,stream: Literal[False] = False) -> bytes: ...

    @overload
    def load(self, filename:str, / , *,stream: Literal[True]) -> Generator: ...

    def load(self, filename:str, / , *,stream: bool = False) -> Union[bytes,Generator]:
        if stream:
            return self.storage_runner.load_stream(filename)
        else:
            return self.storage_runner.load_once(filename)

    def load_once(self, filename:str) -> bytes:
        return self.storage_runner.load_once(filename)

    def load_stream(self, filename:str) -> Generator:
        return self.storage_runner.load_stream(filename)

    def download(self, filename,target_filepath):
        self.storage_runner.download(filename, target_filepath)

    def exists(self, filename):
        return self.storage_runner.exists(filename)

    def delete(self, filename:str):
        return self.storage_runner.delete(filename)

    def scan(self, path:str, files:bool = True, directories:bool = False) -> list[str]:
        return self.storage_runner.scan(path, files, directories)

storage = Storage()

def init_app(app: Flask):
    """供应用启动时调用的初始化入口"""
    storage.init_app(app)