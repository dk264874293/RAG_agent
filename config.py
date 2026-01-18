"""
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 21:43:00
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-07 08:14:50
FilePath: /RAG_agent/config.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Dict, List
from pathlib import Path


class Settings(BaseSettings):
    openai_api_key: str
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-3.5-turbo"
    openai_embedding_model: str = "text-embedding-ada-002"
    gemini_api_key: str  # 新增字段
    mineru_api_key: str  # 新增字段
    dashscope_api_key: str  # 新增字段

    chroma_persist_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    max_upload_size: int = 10485760

    # 分块配置
    chunk_size: int = 512
    chunk_overlap: int = 50
    use_llama_index_semantic: bool = False
    chunking_strategy: str = "fixed"  # fixed, recursive, semantic, tabular, code
    doc_type_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "research_paper": "semantic",
            "legal_document": "recursive",
            "technical_doc": "fixed",
            "financial_report": "tabular",
            "source_code": "code",
            "default": "fixed",
        }
    )

    # 检索配置
    top_k: int = 4
    retrieval_fusion_strategy: str = (
        "reciprocal_rank_fusion"  # reciprocal_rank_fusion, weighted, round_robin
    )

    # LLM配置
    temperature: float = 0.7
    llm_provider: str = "openai"  # openai, dashscope, gemini
    llm_model: str = "gpt-3.5-turbo"

    # 安全配置
    enable_file_security_check: bool = True
    max_file_size_mb: int = 10
    allowed_file_types: List[str] = Field(
        default_factory=lambda: [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".md",
            ".html",
            ".pptx",
            ".xlsx",
        ]
    )

    # OCR配置
    enable_pdf_ocr: bool = True
    ocr_engine: str = "paddleocr"  # paddleocr, tesseract, gemini, dashscope
    fallback_to_cloud: bool = True  # 本地OCR失败时降级到云API
    ocr_languages: List[str] = Field(default_factory=lambda: ["ch", "en"])
    ocr_confidence_threshold: float = 0.6

    # 图片处理配置
    extract_images: bool = True
    save_extracted_images: bool = False
    min_image_size: int = 100  # 最小图片像素面积
    max_image_size_mb: int = 5  # 最大图片大小

    # 缓存配置
    enable_ocr_cache: bool = True
    cache_ttl_hours: int = 24
    max_cache_size_mb: int = 1024  # 1GB缓存限制
    cache_dir: str = "./data/cache"

    # A/B测试配置
    enable_ab_testing: bool = False
    ab_test_traffic_percentage: float = 0.1  # 10%流量用于实验
    experiment_groups: Dict[str, float] = Field(
        default_factory=lambda: {
            "control": 0.5,  # 原版PDF提取
            "ocr_basic": 0.3,  # 基础OCR版
            "ocr_enhanced": 0.2,  # 增强OCR版（预处理+后处理）
        }
    )
    evaluation_data_dir: str = "./data/evaluation"

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
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.evaluation_data_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
