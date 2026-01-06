'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-04 18:23:47
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 14:03:12
FilePath: /RAG_service/loader/pdf_loader.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AEi
'''
import contextlib
import io
import logging
import uuid
import os
from collections.abc import Iterator
from extractor.blob.blob import Blob

import pypdfium2
import pypdfium2.raw as pdfium_c

from extractor.extractor_base import BaseExtractor
from models.document import Document
from models.model import UploadFile

from extensions.ext_storage import storage

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

    MAX_MAGIC_LEN = max(len(m) for m,_,_ in IMAGE_FORMATS)

    def __init__(self, file_path: str, tenant_id: str, user_id: str, file_cache_key: str | None = None):
        """初始化"""
        self._file_path = file_path
        self._tenant_id = tenant_id
        self._user_id = user_id
        self._file_cache_key = file_cache_key 

    def extract(self):
        plaintext_file_exists = False
        if self._file_cache_key:
            with contextlib.suppress(FileNotFoundError):
                text = storage.load(self._file_cache_key).decode("utf-8")
                plaintext_file_exists = True
                return [
                    Document(page_content=text)
                ]
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

    def parse(self, blob:Blob) -> Iterator[Document]:
        with blob.as_bytes_io() as file_path:
            pdf_reader = pypdfium2.PdfDocument(file_path, autoclose=True)
            try:
                for page_number , page in enumerate(pdf_reader):
                    text_page = page.get_textpage()
                    content = text_page.get_text_range()
                    text_page.close()
                    image_content = self._extract_images(page)
                    if image_content:
                        content += "\n" + image_content
                    page.close()
                    metadata = {"source":blob.source,"page":page_number}
                    yield Document(page_content=content,metadata=metadata)
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

