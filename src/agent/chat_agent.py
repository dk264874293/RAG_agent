'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-30 13:40:03
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-30 14:00:35
FilePath: /RAG_agent/src/agent/chat_agent.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool

load_dotenv()

model = ChatOpenAI(
    model = "gemini-2.5-flash",
    api_key = os.getenv("GEMINI_API_KEY"),
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/",
    temperature = 0.9,
)

response = model.invoke("我想要做一个关于咨询检索的RAG系统，请帮我做一个技术项目规划")
print(response)