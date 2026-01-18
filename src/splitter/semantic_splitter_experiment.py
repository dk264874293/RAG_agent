'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-08 11:22:07
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-08 12:15:37
FilePath: /RAG_agent/src/splitter/sematic_splitter.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AEfrom 
'''
import os
import re
from dotenv import load_dotenv
import numpy as np
import matplotlib.pyplot as plt
from llama_index.core import Settings, Document
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.google import GeminiEmbedding
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.core.utils import get_tokenizer
load_dotenv()
import time
from google.api_core.exceptions import ResourceExhausted

def make_api_call_with_retry():
    retries = 0
    max_retries = 3
    while retries < max_retries:
        try:
            # 您的Gemini API调用代码
            return response
        except ResourceExhausted as e:
            # 解析重试延迟时间
            retry_delay = 36  # 默认等待36秒
            if hasattr(e, 'retry_info') and hasattr(e.retry_info, 'delay'):
                retry_delay = e.retry_info.delay.seconds
            print(f"API速率限制，{retry_delay}秒后重试...")
            time.sleep(retry_delay)
            retries += 1
    raise Exception("达到最大重试次数，API调用失败")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
Settings.llm = OpenAILike(
    model="gemini-3-flash-preview",
    api_base="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=GEMINI_API_KEY,
    is_chat_model=True,
    temperature=0.1 # 添加温度参数，用于控制生成随机性
) 

# 2. 配置嵌入模型 (使用 DashScopeEmbedding 类)
# Settings.embed_model = GeminiEmbedding(
#     model_name="models/embedding-001",  # Gemini 嵌入模型
#     api_key=GEMINI_API_KEY,
# )

Settings.embed_model = DashScopeEmbedding(model_name="text-embedding-v2", api_key=DASHSCOPE_API_KEY, batch_size=10)

llama_tokenizer = get_tokenizer()

# --- 3. 定义一个能处理中文的自定义分句函数 ---
# 这个函数本身就是 SemanticSplitterNodeParser 所需要的"句子切分器"
def chinese_sentence_tokenizer(text: str) -> list[str]:
    sentences = re.findall(r'[^。！？…\n]+[。！？…\n]?', text)
    return [s.strip() for s in sentences if s.strip()]

# --- 4. 准备长文本 ---
long_text = (
    "大语言模型（LLM）是人工智能领域的一项革命性技术。其发展可以追溯到早期的神经网络和自然语言处理研究。最初的模型，如循环神经网络（RNN），在处理长序列文本时遇到了梯度消失的问题。随后，长短期记忆网络（LSTM）在一定程度上缓解了这个问题，但仍然存在局限性。\n\n"
    "真正的突破来自于2017年提出的Transformer架构。Transformer模型完全基于自注意力机制（Self-Attention），能够并行处理文本序列，极大地提高了训练效率和模型性能。这为构建更大、更深的模型（如BERT和GPT系列）奠定了基础。BERT使用双向编码器，在理解上下文方面表现出色，而GPT则采用自回归解码器，在文本生成方面尤为强大。\n\n"
    "如今，LLM的应用已经渗透到各行各业。它们不仅能进行智能问答、内容创作和代码生成，还在医疗、金融和教育等领域展现出巨大潜力。例如，在医疗领域，LLM可以帮助医生分析病历、提供诊断建议。在教育领域，它可以为学生提供个性化的辅导和学习资源。\n\n"
    "然而，LLM的发展也伴随着挑战。模型的偏见、幻觉问题以及高昂的计算成本都是亟待解决的难题。未来的研究方向可能包括提高模型的效率、增强其可解释性，并建立更负责任的人工智能治理框架。确保技术的普惠和安全是所有研究者共同的责任。"
)
document = Document(text=long_text)


def plot_similarity_and_chunks(splitter: SemanticSplitterNodeParser, title: str):
    # 使用我们自己的函数进行可视化部分的句子切分，这部分逻辑是正确的
    sentences = chinese_sentence_tokenizer(document.get_content())
    
    if len(sentences) < 2:
        print(f"错误：只找到了 {len(sentences)} 个句子，无法计算句子间的相似度。")
        return

    print(f"正在为 {len(sentences)} 个句子生成嵌入向量...")
    embeddings = Settings.embed_model.get_text_embedding_batch(sentences, show_progress=True)
    
    def cosine_similarity(v1, v2):
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    similarities = [cosine_similarity(embeddings[i], embeddings[i+1]) for i in range(len(embeddings) - 1)]
    breakpoint_threshold_val = np.percentile(similarities, splitter.breakpoint_percentile_threshold)
    print(f"计算出的相似度阈值为: {breakpoint_threshold_val:.4f}")

    # --- 可视化 ---
    plt.figure(figsize=(12, 6))
    plt.plot(similarities, marker='o', linestyle='-', label='相邻句子相似度')
    plt.axhline(y=breakpoint_threshold_val, color='r', linestyle='--', label=f'切分阈值 ({splitter.breakpoint_percentile_threshold}百分位)')
    plt.title(title, fontsize=16)
    plt.xlabel("句子连接处索引")
    plt.ylabel("余弦相似度")
    plt.legend()
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
    except Exception:
        print("无法设置中文字体 'SimHei'，图表中的中文可能显示为乱码。")
    plt.grid(True)
    plt.show()

    # --- 实际切分 ---
    # 这部分现在应该可以正常工作了
    nodes = splitter.get_nodes_from_documents([document])
    print("\n--- 切分结果 ---")
    for i, node in enumerate(nodes):
        print(f"====== 节点 {i+1} (长度: {len(llama_tokenizer(node.get_content()))} tokens) ======")
        print(node.get_content().strip())
        print("-" * 20)

# --- 5. 直接将我们编写的函数传递给 SemanticSplitterNodeParser

# 实验一：使用保守阈值 (95)
print("="*20 + " 实验一：使用保守阈值 (95) " + "="*20)
conservative_splitter = SemanticSplitterNodeParser(
    buffer_size=1, 
    breakpoint_percentile_threshold=95,
    embed_model=Settings.embed_model,
    sentence_splitter=chinese_sentence_tokenizer 
)
plot_similarity_and_chunks(conservative_splitter, "相似度与切分点 (阈值=95%)")


# 实验二：使用激进阈值 (5)
# print("\n" + "="*20 + " 实验二：使用激进阈值 (5) " + "="*20)
# aggressive_splitter = SemanticSplitterNodeParser(
#     buffer_size=1, 
#     breakpoint_percentile_threshold=5,
#     embed_model=Settings.embed_model,
#     sentence_splitter=chinese_sentence_tokenizer 
# )
# plot_similarity_and_chunks(aggressive_splitter, "相似度与切分点 (阈值=5%)")