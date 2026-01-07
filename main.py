'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 18:23:38
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-07 07:40:17
FilePath: /RAG_agent/main.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AEfrom 
'''
#, File, UploadFile, HTTPEXception
from fastapi import FastAPI, File, UploadFile, HTTPException
import aiofiles
import os
import uvicorn
# from fastapi.response import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.extractor.extract_processor import ExtractProcessor
# from pydantic import BaseModel
# from typing import List, Optional
# import aiofiles
# import os
import uvicorn
from pathlib import Path
from config import settings

app = FastAPI(
    title="RAG System API",
    description="Retrieval-Augmented Generation System with Document Upload and Query Capabilities",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "RAG System API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/v1/upload",
            "query": "/api/v1/query",
            "health": "/api/v1/health",
            "documents": "/api/v1/documents"
        }
    }

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "vector_store": "connected",
        "rag_engine": "ready"
    }

@app.post("/api/v1/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ['.pdf', '.docx', '.doc']:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. Only PDF and Word documents are supported."
        )
    
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {settings.max_upload_size} bytes"
        )
    
    file_path = os.path.join(settings.upload_dir, file.filename)
    print(f'file_path ->{file_path}')
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    try:
        extractor = ExtractProcessor(file_path = file_path)
        documents = extractor.parse_document()
        print('documents',documents)
        
        return {
            "message": "Document uploaded and processed successfully",
            "filename": file.filename,
            "file_size": file_size,
            "document_type": file_extension,
            "chunks_processed": len(documents)
        }
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)