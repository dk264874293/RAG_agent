'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 12:46:36
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 14:04:43
FilePath: /RAG_agent/src/extractor/test.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from extractor.pdf_extractor import PdfExtractor


if __name__ == "__main__":
    extractor = PdfExtractor(
        "https://bagejj.oss-cn-heyuan.aliyuncs.com/templates/25AA0425%E5%88%86%E6%9E%90%E8%AE%B0%E5%BD%95_b21e138650fbb6d38d60122221dcb464_1.pdf",
        tenant_id="1",
        user_id="1")
    extractor.extract()