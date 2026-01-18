"""
测试自适应分块器
"""

import pytest
from src.pipeline.adaptive_chunker import AdaptiveChunker


class TestAdaptiveChunker:
    """测试AdaptiveChunker类"""

    def test_init_with_default_config(self):
        """测试默认配置初始化"""
        chunker = AdaptiveChunker()
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200
        assert chunker.use_llama_index_semantic == False

    def test_init_with_custom_config(self):
        """测试自定义配置初始化"""
        config = {
            "chunk_size": 500,
            "chunk_overlap": 50,
            "use_llama_index_semantic": True,
        }
        chunker = AdaptiveChunker(config)
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 50
        assert chunker.use_llama_index_semantic == True

    def test_chunk_document_fixed_strategy(self):
        """测试固定大小分块策略"""
        config = {"chunk_size": 100, "chunk_overlap": 0}
        chunker = AdaptiveChunker(config)

        text = "这是一个测试文本，用于测试分块功能。这个文本应该被分成多个块。"
        chunks = chunker.chunk_document(text, doc_type="default")

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk) > 0

    def test_chunk_document_recursive_strategy(self):
        """测试递归分块策略"""
        config = {"chunk_size": 50, "chunk_overlap": 10}
        chunker = AdaptiveChunker(config)

        text = "第一段。\n\n第二段更长一些，包含更多内容。\n\n第三段。"
        chunks = chunker.chunk_document(text, doc_type="legal_document")

        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_chunk_document_semantic_strategy(self):
        """测试语义分块策略（不使用LlamaIndex）"""
        config = {
            "chunk_size": 150,
            "chunk_overlap": 20,
            "use_llama_index_semantic": False,
        }
        chunker = AdaptiveChunker(config)

        text = "这是一个关于机器学习的文本。深度学习是机器学习的一个分支。自然语言处理是深度学习的应用领域。"
        chunks = chunker.chunk_document(text, doc_type="research_paper")

        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_chunk_document_tabular_strategy(self):
        """测试表格分块策略"""
        chunker = AdaptiveChunker()

        text = "姓名\t年龄\t城市\n张三\t25\t北京\n李四\t30\t上海"
        chunks = chunker.chunk_document(text, doc_type="financial_report")

        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_chunk_document_code_strategy(self):
        """测试代码分块策略"""
        chunker = AdaptiveChunker()

        text = """def hello_world():
    print("Hello, World!")

class MyClass:
    def __init__(self):
        self.value = 42"""

        chunks = chunker.chunk_document(text, doc_type="source_code")

        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_chunk_document_with_overlap(self):
        """测试带重叠的分块"""
        config = {"chunk_size": 50, "chunk_overlap": 20}
        chunker = AdaptiveChunker(config)

        text = "这是一个测试文本，用于测试重叠分块功能。"
        chunks = chunker.chunk_document(text, doc_type="default")

        if len(chunks) > 1:
            # 检查重叠（简化检查）
            assert len(chunks[0]) > 0
            assert len(chunks[1]) > 0

    def test_split_sentences(self):
        """测试句子分割功能"""
        chunker = AdaptiveChunker()

        text = "这是一个句子。这是另一个句子！这是第三个句子？"
        sentences = chunker._split_sentences(text)

        assert isinstance(sentences, list)
        assert len(sentences) == 3
        for sentence in sentences:
            assert "句子" in sentence

    def test_unsupported_doc_type_falls_back_to_default(self):
        """测试不支持的文档类型回退到默认策略"""
        chunker = AdaptiveChunker()

        text = "测试文本"
        chunks = chunker.chunk_document(text, doc_type="unknown_type")

        assert isinstance(chunks, list)
        assert len(chunks) > 0


if __name__ == "__main__":
    pytest.main([__file__])
