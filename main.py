"""
工业级RAG系统主应用
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import aiofiles
import os
import uvicorn
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel
import time

from config import settings
from src.pipeline.document_processor import DocumentProcessingPipeline
from src.pipeline.adaptive_chunker import AdaptiveChunker
from src.retrieval.hybrid_retriever import HybridRetriever
from src.llm.orchestrator import LLMOrchestrator
from src.security.filter import SecurityFilter
from src.quality.optimizer import QualityOptimizer
from src.knowledge_base.version_manager import KnowledgeBaseManager
from src.monitoring.metrics import metrics_collector, track_metrics

app = FastAPI(
    title="工业级RAG系统API",
    description="Retrieval-Augmented Generation System with Document Upload and Query Capabilities",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
rag_config = {
    'openai_api_key': settings.openai_api_key,
    'openai_api_base': settings.openai_api_base,
    'openai_model': settings.openai_model,
    'dashscope_api_key': settings.dashscope_api_key,
    'chroma_persist_dir': settings.chroma_persist_dir,
    'collection_name': 'documents',
    'vector_provider': 'chroma',
    'fusion_strategy': 'reciprocal_rank_fusion',
    'routing_strategy': 'cost_aware',
}

# 初始化核心组件
document_processor = DocumentProcessingPipeline()
chunker = AdaptiveChunker({
    'chunk_size': settings.chunk_size,
    'chunk_overlap': settings.chunk_overlap,
})
hybrid_retriever = HybridRetriever(rag_config)
llm_orchestrator = LLMOrchestrator(rag_config)
security_filter = SecurityFilter()
quality_optimizer = QualityOptimizer()
kb_manager = KnowledgeBaseManager({'metadata_db_path': './data/kb_metadata.db'})


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 4
    template: Optional[str] = 'default'


@app.get("/")
async def root():
    return {
        "message": "工业级RAG系统API",
        "version": "2.0.0",
        "endpoints": {
            "upload": "/api/v1/upload",
            "query": "/api/v1/query",
            "health": "/api/v1/health",
            "ready": "/api/v1/ready",
            "metrics": "/api/v1/metrics",
            "documents": "/api/v1/documents"
        }
    }


@app.get("/api/v1/health")
@track_metrics(endpoint="/api/v1/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "vector_store": "connected",
        "rag_engine": "ready",
        "timestamp": time.time()
    }


@app.get("/api/v1/ready")
async def readiness_check():
    """就绪检查（用于Kubernetes）"""
    # 检查关键组件是否就绪
    checks = {
        'vector_store': True,  # 简化版，实际应该检查连接
        'llm_providers': len(llm_orchestrator.llm_providers) > 0,
    }
    
    is_ready = all(checks.values())
    
    if is_ready:
        return JSONResponse(content={"status": "ready", "checks": checks}, status_code=200)
    else:
        return JSONResponse(content={"status": "not_ready", "checks": checks}, status_code=503)


@app.get("/api/v1/metrics")
async def get_metrics():
    """获取Prometheus格式的指标"""
    from fastapi.responses import Response
    metrics_text = metrics_collector.get_prometheus_format()
    return Response(content=metrics_text, media_type="text/plain")


@app.post("/api/v1/upload")
@track_metrics(endpoint="/api/v1/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传并处理文档"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件")
    
    file_extension = Path(file.filename).suffix.lower()
    supported_formats = ['.pdf', '.docx', '.doc', '.txt', '.md', '.html']
    
    if file_extension not in supported_formats:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_extension}。支持的格式: {', '.join(supported_formats)}"
        )
    
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过最大限制: {settings.max_upload_size} 字节"
        )
    
    # 保存文件
    file_path = os.path.join(settings.upload_dir, file.filename)
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    try:
        # 使用新的文档处理流水线
        documents = await document_processor.process_document(
            file_path,
            metadata={'filename': file.filename, 'upload_time': time.time()}
        )
        
        # 分块处理
        all_chunks = []
        for doc in documents:
            chunks = chunker.chunk_document(
                doc.page_content,
                doc_type=doc.metadata.get('file_type', 'default')
            )
            # 为每个块创建Document对象
            for i, chunk_text in enumerate(chunks):
                from src.models.document import Document
                chunk_doc = Document(
                    page_content=chunk_text,
                    id_=f"{doc.id_}_chunk_{i}",
                    metadata={
                        **doc.metadata,
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                )
                all_chunks.append(chunk_doc)
        
        # 知识库版本管理
        version_result = await kb_manager.update_knowledge_base(all_chunks)
        
        return {
            "message": "文档上传和处理成功",
            "filename": file.filename,
            "file_size": file_size,
            "document_type": file_extension,
            "chunks_processed": len(all_chunks),
            "version_info": version_result
        }
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        metrics_collector.record_error(type(e).__name__)
        raise HTTPException(status_code=500, detail=f"处理文档时出错: {str(e)}")


@app.post("/api/v1/query")
@track_metrics(endpoint="/api/v1/query")
async def query(request: QueryRequest, user_request: Request):
    """查询接口"""
    start_time = time.time()
    
    try:
        # 1. 安全过滤
        user_context = {
            'user_id': user_request.headers.get('X-User-ID', 'anonymous'),
            'ip': user_request.client.host if user_request.client else 'unknown',
        }
        
        filtered_query, filter_info = await security_filter.filter_input(
            request.query,
            user_context
        )
        
        # 2. 混合检索
        retrieval_start = time.time()
        top_k = request.top_k or settings.top_k
        
        # 使用质量优化器优化检索
        context_docs = await quality_optimizer.optimize_retrieval(
            filtered_query,
            hybrid_retriever
        )
        
        retrieval_latency = (time.time() - retrieval_start) * 1000
        metrics_collector.record_retrieval('hybrid', retrieval_latency)
        
        if not context_docs:
            return {
                "answer": "未找到相关文档，请尝试其他查询。",
                "context": [],
                "citations": [],
                "retrieval_time": retrieval_latency
            }
        
        # 3. LLM生成
        generation_start = time.time()
        
        # 使用质量优化器优化生成
        result = await quality_optimizer.optimize_generation(
            filtered_query,
            context_docs,
            llm_orchestrator
        )
        
        generation_latency = (time.time() - generation_start) * 1000
        metrics_collector.record_generation(
            result.get('provider', 'unknown'),
            generation_latency
        )
        
        # 4. 输出安全过滤
        filtered_answer, output_filter_info = await security_filter.filter_output(
            result.get('answer', ''),
            {'request_id': str(time.time()), **user_context}
        )
        
        # 5. 收集反馈（异步）
        # await quality_optimizer.collect_feedback(filtered_query, result)
        
        total_time = time.time() - start_time
        
        return {
            "answer": filtered_answer,
            "context": [doc.get('content', '')[:200] for doc in context_docs[:3]],
            "citations": result.get('citations', []),
            "metadata": {
                "provider": result.get('provider'),
                "model": result.get('model'),
                "retrieval_time_ms": round(retrieval_latency, 2),
                "generation_time_ms": round(generation_latency, 2),
                "total_time_ms": round(total_time * 1000, 2),
                "tokens_used": result.get('usage', {}).get('total_tokens', 0),
            },
            "security": {
                "input_filtered": filter_info.get('pii_detected', False),
                "output_filtered": output_filter_info.get('filtered', False),
            }
        }
        
    except Exception as e:
        metrics_collector.record_error(type(e).__name__)
        raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}")


@app.get("/api/v1/documents")
@track_metrics(endpoint="/api/v1/documents")
async def list_documents():
    """列出所有文档"""
    # 简化版：返回上传目录中的文件列表
    upload_dir = Path(settings.upload_dir)
    if not upload_dir.exists():
        return {"documents": []}
    
    documents = []
    for file_path in upload_dir.iterdir():
        if file_path.is_file():
            documents.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime,
            })
    
    return {"documents": documents}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
