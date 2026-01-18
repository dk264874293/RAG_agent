"""
Pytest配置和共享fixture
"""

import pytest
import asyncio
from typing import Generator


@pytest.fixture
def event_loop() -> Generator:
    """为异步测试提供事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_text() -> str:
    """提供示例文本"""
    return "这是一个示例文本，用于测试文档处理流水线。这个文本包含多个句子，可以用于测试分块功能。"


@pytest.fixture
def sample_long_text() -> str:
    """提供长示例文本"""
    return """
    第一章：引言
    
    大语言模型（LLM）是人工智能领域的一项革命性技术。其发展可以追溯到早期的神经网络和自然语言处理研究。
    最初的模型，如循环神经网络（RNN），在处理长序列文本时遇到了梯度消失的问题。
    随后，长短期记忆网络（LSTM）在一定程度上缓解了这个问题，但仍然存在局限性。
    
    第二章：技术发展
    
    真正的突破来自于2017年提出的Transformer架构。
    Transformer模型完全基于自注意力机制（Self-Attention），能够并行处理文本序列，极大地提高了训练效率和模型性能。
    这为构建更大、更深的模型（如BERT和GPT系列）奠定了基础。
    
    第三章：应用领域
    
    BERT使用双向编码器，在理解上下文方面表现出色，而GPT则采用自回归解码器，在文本生成方面尤为强大。
    如今，LLM的应用已经渗透到各行各业。它们不仅能进行智能问答、内容创作和代码生成，
    还在医疗、金融和教育等领域展现出巨大潜力。
    """


@pytest.fixture
def sample_table_text() -> str:
    """提供表格示例文本"""
    return """姓名\t年龄\t城市
张三\t25\t北京
李四\t30\t上海
王五\t28\t广州"""


@pytest.fixture
def sample_code_text() -> str:
    """提供代码示例文本"""
    return '''def calculate_sum(numbers):
    """计算数字列表的总和"""
    total = 0
    for num in numbers:
        total += num
    return total

class DataProcessor:
    def __init__(self, data):
        self.data = data
    
    def process(self):
        """处理数据"""
        return [item * 2 for item in self.data]'''
