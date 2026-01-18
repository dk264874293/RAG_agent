"""
测试文档处理流水线
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.pipeline.document_processor import (
    DocumentProcessingPipeline,
    UnsupportedFormatError,
)


class TestDocumentProcessingPipeline:
    """测试DocumentProcessingPipeline类"""

    def test_init_with_default_config(self):
        """测试默认配置初始化"""
        pipeline = DocumentProcessingPipeline()
        assert isinstance(pipeline.config, dict)
        assert len(pipeline.supported_formats) > 0

    def test_init_with_custom_config(self):
        """测试自定义配置初始化"""
        config = {"custom_setting": "value"}
        pipeline = DocumentProcessingPipeline(config)
        assert pipeline.config["custom_setting"] == "value"

    def test_detect_format(self):
        """测试文件格式检测"""
        pipeline = DocumentProcessingPipeline()

        test_cases = [
            ("document.pdf", ".pdf"),
            ("document.docx", ".docx"),
            ("document.txt", ".txt"),
            ("document.html", ".html"),
            ("document.md", ".md"),
            ("document.pptx", ".pptx"),
            ("document.xlsx", ".xlsx"),
        ]

        for filename, expected_ext in test_cases:
            assert pipeline._detect_format(filename) == expected_ext

    def test_detect_format_with_path(self):
        """测试带路径的文件格式检测"""
        pipeline = DocumentProcessingPipeline()
        assert pipeline._detect_format("/path/to/document.pdf") == ".pdf"

    @pytest.mark.asyncio
    async def test_process_document_unsupported_format(self):
        """测试处理不支持的文件格式"""
        pipeline = DocumentProcessingPipeline()

        with pytest.raises(UnsupportedFormatError):
            await pipeline.process_document("document.unsupported", {})

    @pytest.mark.asyncio
    @patch("aiofiles.open")
    async def test_process_text_file(self, mock_aiofiles_open):
        """测试处理文本文件"""
        pipeline = DocumentProcessingPipeline()

        # 模拟aiofiles行为
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value="文本文件内容")
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

        result = await pipeline.process_document("test.txt", {"custom": "metadata"})

        assert isinstance(result, list)
        assert len(result) == 1
        document = result[0]
        assert document.page_content == "文本文件内容"
        assert document.metadata["filename"] == "test.txt"
        assert document.metadata["file_type"] == ".txt"
        assert document.metadata["custom"] == "metadata"

    @pytest.mark.asyncio
    @patch("src.pipeline.document_processor.asyncio.to_thread")
    async def test_process_pdf_file(self, mock_to_thread):
        """测试处理PDF文件"""
        pipeline = DocumentProcessingPipeline()

        # 模拟PdfExtractor.extract返回的文档
        mock_document = Mock()
        mock_document.page_content = "PDF内容"

        # 模拟asyncio.to_thread
        mock_to_thread.return_value = [mock_document]

        result = await pipeline.process_document("test.pdf", {})

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].page_content == "PDF内容"
        mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.pipeline.document_processor.asyncio.to_thread")
    async def test_process_docx_file(self, mock_to_thread):
        """测试处理Word文件"""
        pipeline = DocumentProcessingPipeline()

        # 模拟WordExtractor.extract返回的文档
        mock_document = Mock()
        mock_document.page_content = "Word内容"

        # 模拟asyncio.to_thread
        mock_to_thread.return_value = [mock_document]

        result = await pipeline.process_document("test.docx", {})

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].page_content == "Word内容"
        mock_to_thread.assert_called_once()

    def test_clean_content(self):
        """测试文本清洗功能"""
        pipeline = DocumentProcessingPipeline()

        test_cases = [
            ("  前后空格  ", "前后空格"),
            ("多个    空格", "多个 空格"),
            ("特殊\n\t字符", "特殊 字符"),
        ]

        for input_text, expected in test_cases:
            assert pipeline._clean_content(input_text) == expected

    @pytest.mark.asyncio
    async def test_enhance_metadata(self):
        """测试元数据增强功能"""
        pipeline = DocumentProcessingPipeline()

        # 创建一个临时文件用于测试
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("测试内容")
            temp_path = f.name

        try:
            metadata = {"original": "data"}
            enhanced = await pipeline._enhance_metadata(metadata, temp_path, ".txt")

            assert enhanced["original"] == "data"
            assert enhanced["source"] == temp_path
            assert enhanced["filename"] == os.path.basename(temp_path)
            assert enhanced["file_type"] == ".txt"
            assert enhanced["file_size"] > 0
            assert enhanced["file_hash"] is not None
        finally:
            os.unlink(temp_path)

    def test_unsupported_format_error(self):
        """测试不支持格式异常"""
        error = UnsupportedFormatError("不支持的文件格式: .xyz")
        assert str(error) == "不支持的文件格式: .xyz"


if __name__ == "__main__":
    pytest.main([__file__])
