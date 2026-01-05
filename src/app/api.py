'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-30 14:08:37
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-30 14:11:06
FilePath: /RAG_agent/src/app/api.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from fastapi import FastAPI,Response

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

