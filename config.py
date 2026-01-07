'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 21:43:00
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-07 08:14:50
FilePath: /RAG_agent/config.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    openai_api_key: str
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-3.5-turbo"
    openai_embedding_model: str = "text-embedding-ada-002"
    gemini_api_key: str  # 新增字段
    mineru_api_key: str  # 新增字段
    openai_api_base: str = "https://api.openai.com/v1"
    dashscope_api_key: str  # 新增字段
    

    chroma_persist_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    max_upload_size: int = 10485760
    
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 4
    temperature: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # super().__init__()
        self._create_directories()
    
    def _create_directories(self):
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
