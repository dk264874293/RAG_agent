"""
RAG质量优化器
"""
from typing import List, Dict, Optional
from ..retrieval.hybrid_retriever import HybridRetriever
from ..llm.orchestrator import LLMOrchestrator


class QualityOptimizer:
    """RAG质量优化器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.query_expansion = QueryExpansion()
        self.answer_verifier = AnswerVerifier()
        self.feedback_collector = FeedbackCollector()
    
    async def optimize_retrieval(self, query: str, retriever: HybridRetriever) -> List[Dict]:
        """检索优化策略"""
        # 1. 查询扩展
        expanded_queries = await self.query_expansion.expand(query)
        
        # 2. 多查询并行检索
        all_results = []
        for expanded_query in expanded_queries:
            results = await retriever.retrieve(expanded_query, top_k=5)
            all_results.extend(results)
        
        # 3. 去重和重排序
        unique_results = self._deduplicate_results(all_results)
        reranked_results = await retriever.reranker.rerank(query, unique_results)
        
        return reranked_results[:10]
    
    async def optimize_generation(self, query: str, context: List[Dict], llm_orchestrator: LLMOrchestrator) -> Dict:
        """生成优化策略"""
        # 1. 生成多个候选答案
        candidates = []
        for template in ['default', 'technical', 'concise']:
            try:
                answer = await llm_orchestrator.generate(
                    query=query,
                    context=context,
                    template=template,
                    generation_config={'temperature': 0.7}  # 增加多样性
                )
                candidates.append(answer)
            except Exception as e:
                print(f"生成候选答案失败 (template={template}): {e}")
        
        # 2. 答案验证
        verified_candidates = []
        for candidate in candidates:
            verification = await self.answer_verifier.verify(
                query=query,
                answer=candidate.get('answer', ''),
                context=context
            )
            if verification['is_valid']:
                candidate['verification_score'] = verification['score']
                verified_candidates.append(candidate)
        
        # 3. 选择最佳答案
        if verified_candidates:
            best_answer = max(
                verified_candidates,
                key=lambda x: x.get('verification_score', 0)
            )
        else:
            # 回退到默认答案
            best_answer = candidates[0] if candidates else {}
        
        # 4. 答案精炼
        refined_answer = await self._refine_answer(best_answer, query, context)
        
        return refined_answer
    
    async def _refine_answer(self, answer: Dict, query: str, context: List[Dict]) -> Dict:
        """答案精炼"""
        # 简化版：直接返回
        # 实际可以添加：去除冗余、改善格式等
        return answer
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """去重结果"""
        seen = set()
        unique = []
        
        for result in results:
            doc_id = result.get('id') or result.get('doc_id') or str(hash(result.get('content', '')))
            if doc_id not in seen:
                seen.add(doc_id)
                unique.append(result)
        
        return unique
    
    async def collect_feedback(self, query: str, answer: Dict, user_feedback: Optional[Dict] = None):
        """收集反馈用于持续优化"""
        feedback_data = {
            'query': query,
            'answer': answer.get('answer', ''),
            'context_used': answer.get('context', []),
            'retrieval_scores': answer.get('retrieval_scores', {}),
            'generation_metrics': answer.get('generation_metrics', {}),
            'user_feedback': user_feedback,
        }
        
        await self.feedback_collector.record(feedback_data)
        
        # 自动检测难例
        if self._is_hard_case(feedback_data):
            await self._add_to_hard_case_pool(feedback_data)
    
    def _is_hard_case(self, feedback_data: Dict) -> bool:
        """判断是否为难例"""
        # 简化版：根据用户反馈判断
        user_feedback = feedback_data.get('user_feedback', {})
        if user_feedback.get('rating', 0) < 3:  # 评分低于3分
            return True
        return False
    
    async def _add_to_hard_case_pool(self, feedback_data: Dict):
        """添加到难例池"""
        # 简化版：占位符
        print(f"添加到难例池: {feedback_data.get('query')}")


class QueryExpansion:
    """查询扩展"""
    
    async def expand(self, query: str) -> List[str]:
        """扩展查询"""
        # 简化版：返回原始查询和同义词查询
        # 实际应该使用同义词库或LLM生成扩展查询
        expanded = [query]
        
        # 可以添加同义词扩展
        # expanded.append(self._add_synonyms(query))
        
        return expanded


class AnswerVerifier:
    """答案验证器"""
    
    async def verify(self, query: str, answer: str, context: List[Dict]) -> Dict:
        """验证答案"""
        # 简化版：基本验证
        is_valid = True
        score = 0.8  # 默认分数
        
        # 检查答案是否为空
        if not answer or len(answer.strip()) < 10:
            is_valid = False
            score = 0.0
        
        # 检查答案是否与上下文相关（简化版）
        # 实际应该使用更复杂的验证逻辑
        
        return {
            'is_valid': is_valid,
            'score': score,
            'reason': '基本验证通过' if is_valid else '答案过短或无效'
        }


class FeedbackCollector:
    """反馈收集器"""
    
    async def record(self, feedback_data: Dict):
        """记录反馈"""
        # 简化版：打印日志
        # 实际应该写入数据库或消息队列
        print(f"反馈记录: {feedback_data.get('query')}")
