'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 12:35:35
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-07 07:39:46
FilePath: /RAG_agent/src/extractor/extract_processor.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from .pdf_extractor import PdfExtractor
from ..models.document import Document
from pathlib import Path
from typing import List

class ExtractProcessor:
    def __init__(self, file_path:str):
        self.file_path = file_path

    def parse_document(self) -> List[Document]:
        path = Path(self.file_path)
        suffix = path.suffix.lower()
        
        if suffix == '.pdf':
            pdf_extractor = PdfExtractor(self.file_path,'1','1')
            return pdf_extractor.extract()
        else:
            raise ValueError(f"Unsupported file type: {suffix}")