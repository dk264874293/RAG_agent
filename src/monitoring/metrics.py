"""
Prometheus监控指标
"""
from typing import Dict, Optional
import time
from functools import wraps


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics = {
            'request_count': {},
            'request_duration': {},
            'retrieval_latency': {},
            'generation_latency': {},
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': {},
        }
    
    def record_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """记录请求指标"""
        key = f"{method}:{endpoint}:{status_code}"
        if key not in self.metrics['request_count']:
            self.metrics['request_count'][key] = 0
        self.metrics['request_count'][key] += 1
        
        if endpoint not in self.metrics['request_duration']:
            self.metrics['request_duration'][endpoint] = []
        self.metrics['request_duration'][endpoint].append(duration)
    
    def record_retrieval(self, retriever_type: str, latency: float):
        """记录检索指标"""
        if retriever_type not in self.metrics['retrieval_latency']:
            self.metrics['retrieval_latency'][retriever_type] = []
        self.metrics['retrieval_latency'][retriever_type].append(latency)
    
    def record_generation(self, llm_provider: str, latency: float, tokens: int = 0):
        """记录生成指标"""
        if llm_provider not in self.metrics['generation_latency']:
            self.metrics['generation_latency'][llm_provider] = []
        self.metrics['generation_latency'][llm_provider].append(latency)
    
    def record_cache_hit(self):
        """记录缓存命中"""
        self.metrics['cache_hits'] += 1
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        self.metrics['cache_misses'] += 1
    
    def record_error(self, error_type: str):
        """记录错误"""
        if error_type not in self.metrics['errors']:
            self.metrics['errors'][error_type] = 0
        self.metrics['errors'][error_type] += 1
    
    def get_metrics(self) -> Dict:
        """获取所有指标"""
        return self.metrics.copy()
    
    def get_prometheus_format(self) -> str:
        """获取Prometheus格式的指标"""
        lines = []
        
        # 请求计数
        for key, count in self.metrics['request_count'].items():
            lines.append(f'rag_request_count_total{{endpoint="{key}"}} {count}')
        
        # 请求延迟（平均值）
        for endpoint, durations in self.metrics['request_duration'].items():
            avg_duration = sum(durations) / len(durations) if durations else 0
            lines.append(f'rag_request_duration_seconds{{endpoint="{endpoint}"}} {avg_duration}')
        
        # 检索延迟
        for retriever_type, latencies in self.metrics['retrieval_latency'].items():
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            lines.append(f'rag_retrieval_latency_ms{{retriever_type="{retriever_type}"}} {avg_latency}')
        
        # 生成延迟
        for llm_provider, latencies in self.metrics['generation_latency'].items():
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            lines.append(f'rag_generation_latency_ms{{llm_provider="{llm_provider}"}} {avg_latency}')
        
        # 缓存指标
        total_cache_requests = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = self.metrics['cache_hits'] / total_cache_requests if total_cache_requests > 0 else 0
        lines.append(f'rag_cache_hit_rate {cache_hit_rate}')
        lines.append(f'rag_cache_hits_total {self.metrics["cache_hits"]}')
        lines.append(f'rag_cache_misses_total {self.metrics["cache_misses"]}')
        
        # 错误计数
        for error_type, count in self.metrics['errors'].items():
            lines.append(f'rag_errors_total{{error_type="{error_type}"}} {count}')
        
        return '\n'.join(lines)


# 全局指标收集器
metrics_collector = MetricsCollector()


def track_metrics(endpoint: str = None):
    """指标追踪装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            method = 'GET'  # 默认
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                metrics_collector.record_error(type(e).__name__)
                raise
            finally:
                duration = time.time() - start_time
                endpoint_name = endpoint or func.__name__
                metrics_collector.record_request(endpoint_name, method, status_code, duration)
        
        return wrapper
    return decorator
