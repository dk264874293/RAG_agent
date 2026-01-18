"""
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-04 18:23:47
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-07 07:45:41
FilePath: /RAG_service/loader/pdf_loader.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AEi
"""

import contextlib
import io
import logging
import uuid
import os
import hashlib
import asyncio
from collections.abc import Iterator
from typing import Optional, Dict, Any
from .blob.blob import Blob

import pypdfium2
import pypdfium2.raw as pdfium_c

from .extractor_base import BaseExtractor
from ..models.document import Document
from ..models.model import UploadFile

from ..extensions.ext_storage import storage
from .ocr_processor import OCRProcessor, OCRResult

logger = logging.getLogger(__name__)


class PdfExtractor(BaseExtractor):
    """
    PdfExtractor用于从PDF文件中提取文本和图像。

    Args:
        file_path: PDF文件的路径。
        tenant_id：工作区ID。
        user_id：执行提取的用户ID。
        file_cache_key：提取文本的可选缓存键。

    """

    # 片格式魔术字节（用于识别图片类型）：(魔术字节, 扩展名, MIME类型)
    IMAGE_FORMATS = [
        (b"\xff\xd8\xff", "jpg", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
        (b"\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a", "jp2", "image/jp2"),
        (b"GIF8", "gif", "image/gif"),
        (b"BM", "bmp", "image/bmp"),
        (b"II*\x00", "tiff", "image/tiff"),
        (b"MM\x00*", "tiff", "image/tiff"),
        (b"II+\x00", "tiff", "image/tiff"),
        (b"MM\x00+", "tiff", "image/tiff"),
    ]

    MAX_MAGIC_LEN = max(len(m) for m, _, _ in IMAGE_FORMATS)

    def __init__(
        self,
        file_path: str,
        tenant_id: str,
        user_id: str,
        file_cache_key: str | None = None,
    ):
        """初始化"""
        self._file_path = file_path
        self._tenant_id = tenant_id
        self._user_id = user_id
        self._file_cache_key = file_cache_key

    def extract(self) -> list:
        plaintext_file_exists = False
        if self._file_cache_key:
            with contextlib.suppress(FileNotFoundError):
                text = storage.load(self._file_cache_key).decode("utf-8")
                plaintext_file_exists = True
                return [Document(page_content=text)]
        documents = list(self.load())
        text_list = []
        for document in documents:
            text_list.append(document.page_content)
        text = "\n\n".join(text_list)
        if not plaintext_file_exists and self._file_cache_key:
            storage.save(self._file_cache_key, text.encode("utf-8"))
        print(f"documents --> {documents}")
        return documents

    def load(self) -> Iterator[Document]:
        blob = Blob.from_path(self._file_path)
        yield from self.parse(blob)

    def parse(self, blob: Blob) -> Iterator[Document]:
        with blob.as_bytes_io() as file_path:
            pdf_reader = pypdfium2.PdfDocument(file_path, autoclose=True)
            try:
                for page_number, page in enumerate(pdf_reader):
                    text_page = page.get_textpage()
                    content = text_page.get_text_range()
                    text_page.close()
                    image_content = self._extract_images(page)
                    if image_content:
                        content += "\n" + image_content
                    page.close()
                    metadata = {"source": blob.source, "page": page_number}
                    yield Document(page_content=content, metadata=metadata)
            finally:
                pdf_reader.close()

    def _extract_images(self, page):
        """
        从 PDF 页面提取图片并返回标记。
        注意：这是一个简化版本，不保存图片到数据库。

        参数：
            page: pypdfium2 页面对象。

        返回：
            包含图片提取标记的字符串。
        """
        image_content = []

        try:
            image_objects = page.get_objects(filter=(pdfium_c.FPDF_PAGEOBJ_IMAGE,))

            for obj in image_objects:
                try:
                    img_byte_arr = io.BytesIO()
                    obj.extract(img_byte_arr, fb_format="png")
                    img_bytes = img_byte_arr.getvalue()

                    if not img_bytes:
                        continue

                    # 目前，我们只记录找到了图片，不保存它
                    image_content.append("![从 PDF 页面提取的图片]")
                except Exception as e:
                    logger.warning("从 PDF 提取图片失败: %s", e)
                    continue

        except Exception as e:
            logger.warning("无法从 PDF 页面获取对象: %s", e)

        return "\n".join(image_content)


class EnhancedPdfExtractor(PdfExtractor):
    """
    增强版PDF提取器，集成OCR功能
    支持：
    - 图像OCR文本提取
    - A/B测试实验分组
    - OCR结果缓存
    """

    def __init__(
        self,
        file_path: str,
        tenant_id: str,
        user_id: str,
        file_cache_key: str | None = None,
        config: Optional[Dict] = None,
    ):
        """初始化增强版PDF提取器"""
        super().__init__(file_path, tenant_id, user_id, file_cache_key)
        self.config = config or {}

        # 初始化OCR处理器
        self.ocr_processor = None
        self._init_ocr_processor()

        # A/B测试变体（如果启用）
        self.experiment_variant = self._assign_experiment_variant()

        # 图片缓存（避免重复OCR处理相同图片）
        self.image_cache = {}

        logger.info(
            f"EnhancedPdfExtractor初始化: 文件={file_path}, 变体={self.experiment_variant}"
        )

    def _init_ocr_processor(self):
        """初始化OCR处理器"""
        try:
            # 从配置构建OCR处理器配置
            ocr_config = {
                "ocr_engine": self.config.get("ocr_engine", "paddleocr"),
                "ocr_languages": self.config.get("ocr_languages", ["ch", "en"]),
                "confidence_threshold": self.config.get(
                    "ocr_confidence_threshold", 0.6
                ),
                "fallback_to_cloud": self.config.get("fallback_to_cloud", True),
                "enable_ocr_cache": self.config.get("enable_ocr_cache", True),
                "cache_ttl_hours": self.config.get("cache_ttl_hours", 24),
                "min_image_size": self.config.get("min_image_size", 100),
                "max_image_size_mb": self.config.get("max_image_size_mb", 5),
                "api_keys": self.config.get("api_keys", {}),
            }

            self.ocr_processor = OCRProcessor(ocr_config)
            logger.info(f"OCR处理器初始化成功: 引擎={ocr_config['ocr_engine']}")

        except Exception as e:
            logger.error(f"OCR处理器初始化失败: {e}")
            # 即使OCR失败，仍可使用基础功能
            self.ocr_processor = None

    def _assign_experiment_variant(self) -> str:
        """分配A/B测试实验变体"""
        if not self.config.get("enable_ab_testing", False):
            # A/B测试未启用，使用默认变体
            return "control"

        # 这里可以调用专门的A/B测试模块
        # 暂时使用简单的随机分配
        import random

        experiment_groups = self.config.get(
            "experiment_groups", {"control": 0.5, "ocr_basic": 0.3, "ocr_enhanced": 0.2}
        )

        # 归一化权重
        total = sum(experiment_groups.values())
        if total <= 0:
            return "control"

        rand = random.random() * total
        cumulative = 0
        for variant, weight in experiment_groups.items():
            cumulative += weight
            if rand <= cumulative:
                return variant

        return "control"

    def _extract_images(self, page):
        """
        从 PDF 页面提取图片并执行OCR

        参数：
            page: pypdfium2 页面对象。

        返回：
            包含OCR文本的字符串。
        """
        # 根据实验变体决定处理方式
        if self.experiment_variant == "control":
            # 控制组：使用原始方法（仅标记图片）
            return super()._extract_images(page)

        # OCR处理组：提取图片并执行OCR
        image_content = []

        try:
            image_objects = page.get_objects(filter=(pdfium_c.FPDF_PAGEOBJ_IMAGE,))

            for obj_idx, obj in enumerate(image_objects):
                try:
                    img_byte_arr = io.BytesIO()
                    obj.extract(img_byte_arr, fb_format="png")
                    img_bytes = img_byte_arr.getvalue()

                    if not img_bytes:
                        continue

                    # 检查缓存
                    img_hash = hashlib.md5(img_bytes).hexdigest()
                    cached_result = self.image_cache.get(img_hash)

                    if cached_result:
                        logger.debug(f"使用缓存的OCR结果: 图片{obj_idx}")
                        ocr_text = cached_result
                    else:
                        # 执行OCR
                        ocr_text = self._perform_ocr(img_bytes, obj_idx)
                        # 缓存结果
                        self.image_cache[img_hash] = ocr_text

                    # 添加到内容
                    if ocr_text:
                        image_content.append(ocr_text)
                    else:
                        # OCR失败或没有文本，使用占位符
                        image_content.append("![从 PDF 页面提取的图片（OCR无文本）]")

                except Exception as e:
                    logger.warning("从 PDF 提取图片失败: %s", e)
                    continue

        except Exception as e:
            logger.warning("无法从 PDF 页面获取对象: %s", e)

        return "\n".join(image_content)

    def _perform_ocr(self, img_bytes: bytes, img_index: int) -> str:
        """执行OCR处理（同步包装）"""
        if not self.ocr_processor:
            logger.warning("OCR处理器未初始化，跳过图片OCR")
            return ""

        try:
            # 创建元数据
            metadata = {
                "image_index": img_index,
                "source_file": self._file_path,
                "tenant_id": self._tenant_id,
                "experiment_variant": self.experiment_variant,
            }

            # 处理异步OCR调用
            ocr_result = self._run_async_ocr(img_bytes, metadata)

            if ocr_result.error:
                logger.warning(f"图片{img_index} OCR失败: {ocr_result.error}")
                return ""

            if not ocr_result.is_valid():
                logger.warning(f"图片{img_index} OCR置信度低: {ocr_result.confidence}")
                # 仍然返回文本，但标记低置信度
                if ocr_result.text.strip():
                    return f"[低置信度OCR文本: {ocr_result.text}]"
                else:
                    return ""

            # 根据实验变体决定输出格式
            if self.experiment_variant == "ocr_basic":
                # 基础版：直接返回OCR文本
                return ocr_result.text
            elif self.experiment_variant == "ocr_enhanced":
                # 增强版：添加元信息
                return f"[OCR文本 (置信度: {ocr_result.confidence:.2f}, 引擎: {ocr_result.engine}): {ocr_result.text}]"
            else:
                return ocr_result.text

        except Exception as e:
            logger.error(f"图片{img_index} OCR处理异常: {e}")
            return ""

    def _run_async_ocr(self, img_bytes: bytes, metadata: Dict) -> OCRResult:
        """在同步上下文中运行异步OCR处理"""
        try:
            # 检查当前线程是否有正在运行的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果有运行中的事件循环，我们需要在新的线程中运行任务
                # 这里使用简单的同步等待（可能会阻塞）
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            self.ocr_processor.extract_text_from_image(
                                img_bytes, metadata
                            )
                        )
                    )
                    return future.result()
            except RuntimeError:
                # 没有运行中的事件循环，可以直接使用asyncio.run
                return asyncio.run(
                    self.ocr_processor.extract_text_from_image(img_bytes, metadata)
                )
        except Exception as e:
            logger.error(f"异步OCR执行失败: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                engine="error",
                processing_time_ms=0,
                error=str(e),
            )

    def get_ocr_stats(self) -> Dict[str, Any]:
        """获取OCR处理统计信息"""
        if not self.ocr_processor:
            return {"ocr_available": False}

        stats = self.ocr_processor.get_stats()
        stats.update(
            {
                "ocr_available": True,
                "experiment_variant": self.experiment_variant,
                "cached_images": len(self.image_cache),
                "config": {
                    "ocr_engine": self.config.get("ocr_engine", "paddleocr"),
                    "enable_ab_testing": self.config.get("enable_ab_testing", False),
                },
            }
        )
        return stats
