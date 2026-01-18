'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-10 15:59:36
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-10 16:13:26
FilePath: /RAG_agent/src/splitter/recursive_character_spliter.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=50, 
    chunk_overlap=5,
    length_function=len,
    separators=["\n", "。", ""]
)

text = """
为什么切片会导致上下文碎片化？
1. 连贯性丧失（Loss of Coherence）
当一个完整语义单元被强行打断，信息就变得不完整（语义就断了）。例如一个论点分布在两个区块中，单独看哪一块都无法准确理解原意，这对大模型的理解和生成造成干扰（输出内容不全，甚至误导用户。）。
2. 相关性稀释（Diluted Relevance）
如果一个区块混杂了无关内容，关键信息会被“稀释”，影响向量表示的准确性，进而降低检索排名。
3. 信息分散（Scattered Information）
对于需要多跳推理的复杂问题，相关信息可能分散在多个区块中。若未全部召回，RAG 就无法给出完整答案。
这些问题叠加后，直接引发“垃圾进，垃圾出”现象，甚至增加模型“幻觉”的风险。
"""

texts = text_splitter.create_documents([text])

for doc in texts:
    # print(f"chunk {i}:")
    print(doc.page_content)