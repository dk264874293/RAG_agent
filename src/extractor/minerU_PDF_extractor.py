'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 15:04:39
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 15:23:14
FilePath: /RAG_agent/src/extractor/MinerU_PDF_extractor.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%A
'''
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

token = os.getenv("MINERU_API_KEY")
url = "https://mineru.net/api/v4/extract/task"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

def set_mineru_data():
    
    data = {
        "url": "https://bagejj.oss-cn-heyuan.aliyuncs.com/project/contract/25CF0071_E6_8E_A5_E6_A0_B7_35cc4b260823bbca74c39ee223a1f46b_1.pdf",
        "model_version": "vlm"
    }
    res = httpx.post(url,headers=header,json=data)
    print(res.status_code)
    print(res.json())
    print(res.json()["data"])

def get_mineru_data():
    task_url = url + "/" + "f42afd3f-080e-42e9-b77c-24c760466fd7"
    res = httpx.get(task_url, headers=header)
    print(res.status_code)
    print(res.json())
    print(res.json()["data"])

if __name__ == "__main__":
    get_mineru_data()