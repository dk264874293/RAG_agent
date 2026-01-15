"""
混合检索系统：向量 + 关键词 + 图检索
"""
import asyncio
from typing import List, Dict, Optional, Any
from ..models.document import Document


class HybridRetriever:
    """混合检索器：向量 + 关键词 + 图检索"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 1. 向量检索（语义相似度）
        self.vector_store = self._init_vector_store()
        
        # 2. 关键词检索（BM25/Elasticsearch）
        self.keyword_store = self._init_keyword_store()
        
        # 3. 图检索（知识图谱）- 可选
        self.graph_store = None
        if config.get('enable_graph_retrieval', False):
            self.graph_store = self._init_graph_store()
        
        # 4. 重排序模型
        self.reranker = self._init_reranker()
        
        # 5. 融合策略
        self.fusion_strategy = config.get('fusion_strategy', 'reciprocal_rank_fusion')
    
    def _init_vector_store(self):
        """初始化向量存储"""
        provider = self.config.get('vector_provider', 'chroma')
        
        if provider == 'chroma':
            try:
                import chromadb
                from chromadb.config import Settings
                client = chromadb.PersistentClient(
                    path=self.config.get('chroma_persist_dir', './data/chroma'),
                    settings=Settings(anonymized_telemetry=False)
                )
                collection = client.get_or_create_collection(
                    name=self.config.get('collection_name', 'documents'),
                    metadata={"hnsw:space": "cosine"}
                )
                return VectorStoreClient(collection, provider='chroma')
            except ImportError:
                raise ImportError("需要安装chromadb库")
        elif provider == 'pinecone':
            # Pinecone实现
            return VectorStoreClient(None, provider='pinecone')
        else:
            raise ValueError(f"不支持的向量存储提供者: {provider}")
    
    def _init_keyword_store(self):
        """初始化关键词存储"""
        es_hosts = self.config.get('es_hosts', None)
        
        # 如果没有配置 Elasticsearch，使用简单的内存BM25
        if not es_hosts:
            return SimpleBM25Store()
        
        try:
            from elasticsearch import AsyncElasticsearch
            
            # 确保 hosts 格式正确（需要包含 scheme）
            if isinstance(es_hosts, str):
                es_hosts = [es_hosts]
            
            # 如果 hosts 不包含 scheme，添加默认的 http://
            formatted_hosts = []
            for host in es_hosts:
                if isinstance(host, str) and not host.startswith(('http://', 'https://')):
                    formatted_hosts.append(f'http://{host}')
                else:
                    formatted_hosts.append(host)
            
            client = AsyncElasticsearch(hosts=formatted_hosts)
            return KeywordStoreClient(client, self.config.get('es_index', 'documents'))
        except (ImportError, Exception) as e:
            # 如果 Elasticsearch 不可用，使用简单的内存BM25
            print(f"警告: Elasticsearch 不可用，使用简单BM25存储: {e}")
            return SimpleBM25Store()
    
    def _init_graph_store(self):
        """初始化图存储"""
        # Neo4j或其他图数据库
        return None  # 占位符
    
    def _init_reranker(self):
        """初始化重排序模型"""
        model_name = self.config.get('reranker_model', 'BAAI/bge-reranker-large')
        return Reranker(model_name)
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[Dict]:
        """混合检索流程"""
        # 并行执行多种检索
        tasks = [
            self.vector_store.similarity_search(query, k=top_k*2),
            self.keyword_store.search(query, size=top_k*2),
        ]
        
        # 条件启用图检索
        if self.graph_store:
            tasks.append(self.graph_store.cypher_query(query))
        
        # 并行检索
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤异常结果
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        # 结果融合
        fused_results = self._fuse_results(valid_results)
        
        # 重排序
        if len(fused_results) > 0:
            reranked = await self.reranker.rerank(query, fused_results)
            return reranked[:top_k]
        
        return []
    
    def _fuse_results(self, results: List) -> List[Dict]:
        """结果融合策略"""
        if self.fusion_strategy == 'reciprocal_rank_fusion':
            return self._reciprocal_rank_fusion(results)
        elif self.fusion_strategy == 'weighted':
            return self._weighted_fusion(results)
        elif self.fusion_strategy == 'round_robin':
            return self._round_robin_fusion(results)
        else:
            return self._default_fusion(results)
    
    def _reciprocal_rank_fusion(self, results: List) -> List[Dict]:
        """倒数排名融合（RRF）"""
        rrf_scores = {}
        k = 60  # RRF常数
        
        for result_list in results:
            for rank, item in enumerate(result_list, 1):
                doc_id = item.get('id') or item.get('doc_id') or str(hash(item.get('content', '')))
                score = 1 / (k + rank)
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + score
                # 保存文档信息
                if doc_id not in rrf_scores or isinstance(rrf_scores[doc_id], (int, float)):
                    item['rrf_score'] = rrf_scores[doc_id]
                    rrf_scores[doc_id] = item
        
        # 按分数排序
        sorted_items = sorted(
            [item for item in rrf_scores.values() if isinstance(item, dict)],
            key=lambda x: x.get('rrf_score', 0),
            reverse=True
        )
        
        return sorted_items
    
    def _weighted_fusion(self, results: List) -> List[Dict]:
        """加权融合"""
        weights = self.config.get('fusion_weights', [0.7, 0.3])  # 向量检索权重更高
        fused = {}
        
        for i, result_list in enumerate(results):
            weight = weights[i] if i < len(weights) else 0.1
            for item in result_list:
                doc_id = item.get('id') or item.get('doc_id') or str(hash(item.get('content', '')))
                score = item.get('score', 0) * weight
                
                if doc_id not in fused:
                    fused[doc_id] = item.copy()
                    fused[doc_id]['fused_score'] = score
                else:
                    fused[doc_id]['fused_score'] += score
        
        return sorted(
            list(fused.values()),
            key=lambda x: x.get('fused_score', 0),
            reverse=True
        )
    
    def _round_robin_fusion(self, results: List) -> List[Dict]:
        """轮询融合"""
        fused = []
        max_len = max(len(r) for r in results) if results else 0
        
        for i in range(max_len):
            for result_list in results:
                if i < len(result_list):
                    item = result_list[i]
                    doc_id = item.get('id') or item.get('doc_id') or str(hash(item.get('content', '')))
                    # 检查是否已添加
                    if not any(d.get('id') == doc_id or d.get('doc_id') == doc_id for d in fused):
                        fused.append(item)
        
        return fused
    
    def _default_fusion(self, results: List) -> List[Dict]:
        """默认融合：简单合并去重"""
        seen = set()
        fused = []
        
        for result_list in results:
            for item in result_list:
                doc_id = item.get('id') or item.get('doc_id') or str(hash(item.get('content', '')))
                if doc_id not in seen:
                    seen.add(doc_id)
                    fused.append(item)
        
        return fused


class VectorStoreClient:
    """向量存储客户端"""
    
    def __init__(self, collection, provider='chroma'):
        self.collection = collection
        self.provider = provider
    
    async def similarity_search(self, query: str, k: int = 10) -> List[Dict]:
        """向量相似度搜索"""
        if self.provider == 'chroma':
            # 需要先获取查询的嵌入向量
            # 这里简化处理，实际应该调用嵌入模型
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=k
                )
                
                documents = []
                if results['ids'] and len(results['ids'][0]) > 0:
                    for i in range(len(results['ids'][0])):
                        documents.append({
                            'id': results['ids'][0][i],
                            'content': results['documents'][0][i] if results['documents'] else '',
                            'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                            'score': 1 - results['distances'][0][i] if results['distances'] else 0.0,
                        })
                
                return documents
            except Exception as e:
                print(f"向量检索错误: {e}")
                return []
        else:
            return []


class KeywordStoreClient:
    """关键词存储客户端（Elasticsearch）"""
    
    def __init__(self, client, index_name):
        self.client = client
        self.index_name = index_name
    
    async def search(self, query: str, size: int = 10) -> List[Dict]:
        """关键词搜索"""
        try:
            response = await self.client.search(
                index=self.index_name,
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["content^2", "title"],
                            "type": "best_fields"
                        }
                    },
                    "size": size
                }
            )
            
            documents = []
            for hit in response['hits']['hits']:
                documents.append({
                    'id': hit['_id'],
                    'content': hit['_source'].get('content', ''),
                    'metadata': hit['_source'].get('metadata', {}),
                    'score': hit['_score'],
                })
            
            return documents
        except Exception as e:
            print(f"关键词检索错误: {e}")
            return []


class SimpleBM25Store:
    """简单的BM25存储（内存实现）"""
    
    def __init__(self):
        self.documents = []
        self.index = {}
    
    async def search(self, query: str, size: int = 10) -> List[Dict]:
        """简单搜索（占位符）"""
        # 实际应该实现BM25算法
        return []


class Reranker:
    """重排序模型"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None  # 延迟加载
    
    async def rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        """重排序文档"""
        if not documents:
            return []
        
        # 简化版：如果有分数，按分数排序
        # 实际应该使用CrossEncoder模型
        if all('score' in doc or 'rrf_score' in doc or 'fused_score' in doc for doc in documents):
            return sorted(
                documents,
                key=lambda x: x.get('fused_score') or x.get('rrf_score') or x.get('score', 0),
                reverse=True
            )
        
        return documents
