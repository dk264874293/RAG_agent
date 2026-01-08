'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-07 20:18:03
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-07 21:12:21
FilePath: /RAG_agent/src/splitter/window_sentence_spliter.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import os
from llama_index.core import VectorStoreIndex, Settings, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.core import Document as LlamaDocument
from src.extractor.pdf_extractor import PdfExtractor

# --- 配置阿里云 DashScope API Key ---
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# DashScope 的 OpenAI 兼容模式的 base_url
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# --- 初始化 LlamaIndex 全局设置 ---
Settings.llm = OpenAILike(
    model="qwen-plus",
    api_base=DASHSCOPE_BASE_URL,
    api_key=DASHSCOPE_API_KEY,
    is_chat_model=True,
    temperature=0.1
) 

Settings.embed_model = DashScopeEmbedding(
    model_name="text-embedding-v4", 
    api_key=DASHSCOPE_API_KEY,     
)

def demonstrate_sliding_window_splitter(documents, chunk_size, chunk_overlap):
    """
    演示 LlamaIndex 中保持句子完整性的滑动窗口切片。
    
    Args:
        documents (list[Document]): 待切分的文档列表。
        chunk_size (int): 每个切块的目标 Token 数量。
        chunk_overlap (int): 相邻切块之间重叠的 Token 数量。
    """
    print(f"\n{'='*50}")
    print(f"正在演示【滑动窗口切片】...")
    print(f"切块大小 (chunk_size): {chunk_size}")
    print(f"重叠大小 (chunk_overlap): {chunk_overlap}")
    print(f"{'='*50}\n")

    # --- 第一步：创建切分器 ---
    # SentenceSplitter 优先保持句子完整性，再考虑大小
    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    # --- 第二步：执行切分 ---
    # 获取切分后的节点（切块）
    nodes = splitter.get_nodes_from_documents(documents)

    # --- 第三步：打印切分结果，展示重叠效果 ---
    print("\n--- 切分后生成的原始切块：---")
    print(f"文档被切分为 {len(nodes)} 个切块。")
    for i, node in enumerate(nodes, 1):
        content = node.get_content().strip()
        print(f"\n【切块 {i}】 (长度: {len(content)} 字符):")
        print("-" * 50)
        print(f"内容:\n\"{content}\"")
        print("-" * 50)

    # --- 简单的切分效果分析：观察相邻切块的重叠部分 ---
    print("\n--- 关键点：观察相邻切块的重叠部分 ---")
    if len(nodes) > 1:
        # 为了更好地展示重叠，我们只截取重叠部分的内容
        # 由于是句子级别的切分，重叠部分是完整的句子
        overlap_content_end_of_chunk1 = nodes[0].get_content()[-chunk_overlap:].strip()
        overlap_content_start_of_chunk2 = nodes[1].get_content()[:chunk_overlap].strip()
        print(f"切块 1 的末尾 ({chunk_overlap} 字符): \"...{overlap_content_end_of_chunk1}\"")
        print(f"切块 2 的开头 ({chunk_overlap} 字符): \"{overlap_content_start_of_chunk2}...\"")
        print(f"\n你可以看到，切块 1 的末尾与切块 2 的开头存在重叠，这就是 chunk_overlap 的作用。")
    else:
        print("文档太短，未能生成多个切块。请使用更长的文档以观察效果。")

    print(f"\n滑动窗口切片测试完成。")
    print(f"{'='*50}\n")

# --- 示例文档（包含多个句子）---
# 使用一个更长的、内容连续的文档，以便更好地演示切分和重叠
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "test.pdf")
extractor = PdfExtractor(file_path = file_path,tenant_id = "1",user_id = "1")
custom_documents = extractor.extract()
documents = []
for doc in custom_documents:
    # 转换为LlamaIndex的Document，使用page_content作为text字段
    llama_doc = LlamaDocument(
        text=doc.page_content,
        metadata=doc.metadata
    )
    documents.append(llama_doc)

# --- 调用滑动窗口切片演示函数 ---
# 调整 chunk_size 和 chunk_overlap 观察不同效果
demonstrate_sliding_window_splitter(documents, chunk_size=500, chunk_overlap=65)