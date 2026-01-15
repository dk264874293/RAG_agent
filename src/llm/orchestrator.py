"""
LLM编排器：支持多种模型和策略
"""
from typing import List, Dict, Optional, Any
import os
from datetime import datetime


class LLMOrchestrator:
    """LLM编排器：支持多种模型和策略"""
    
    PROMPT_TEMPLATES = {
        'default': """
基于以下上下文回答问题。
如果上下文信息不足，请明确说明。
请用中文回答，并引用相关上下文。

上下文：
{context}

问题：{query}

回答：
""",
        
        'technical': """
你是一个技术专家，请基于以下技术文档回答问题。
要求：准确、详细、有引用。

技术文档：
{context}

技术问题：{query}

技术回答：
""",
        
        'concise': """
请基于上下文给出简洁明了的回答。
最多不超过3句话。

上下文：
{context}

问题：{query}

简短回答：
"""
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.llm_providers = {}
        self._init_providers()
        
        # 路由策略
        self.routing_strategy = config.get('routing_strategy', 'cost_aware')
        
        # 模型配置
        self.model_configs = {
            'openai': {
                'model': config.get('openai_model', 'gpt-3.5-turbo'),
                'max_tokens': 2000,
                'temperature': 0.1,
                'cost_per_1k': 0.03  # USD
            },
            'anthropic': {
                'model': 'claude-3-sonnet',
                'max_tokens': 2000,
                'temperature': 0.1,
                'cost_per_1k': 0.015
            },
            'dashscope': {
                'model': config.get('dashscope_model', 'qwen-plus'),
                'max_tokens': 2000,
                'temperature': 0.1,
                'cost_per_1k': 0.01
            }
        }
    
    def _init_providers(self):
        """初始化LLM提供者"""
        # OpenAI
        if self.config.get('openai_api_key'):
            self.llm_providers['openai'] = OpenAIClient(
                api_key=self.config.get('openai_api_key'),
                base_url=self.config.get('openai_api_base', 'https://api.openai.com/v1')
            )
        
        # DashScope (阿里云)
        if self.config.get('dashscope_api_key'):
            self.llm_providers['dashscope'] = DashScopeClient(
                api_key=self.config.get('dashscope_api_key')
            )
        
        # 本地模型（如果有）
        if self.config.get('local_model_path'):
            self.llm_providers['local'] = LocalLLMClient(
                model_path=self.config.get('local_model_path'),
                device=self.config.get('device', 'cuda')
            )
    
    async def generate(self, query: str, context: List[Dict], **kwargs) -> Dict:
        """生成回答"""
        # 1. 选择LLM提供者
        provider_name = self._select_provider(query, context, kwargs)
        
        if provider_name not in self.llm_providers:
            raise ValueError(f"LLM提供者 {provider_name} 不可用")
        
        provider = self.llm_providers[provider_name]
        
        # 2. 构建增强提示
        template = kwargs.get('template', 'default')
        prompt = self._build_rag_prompt(query, context, template)
        
        # 3. 调用LLM生成
        config = self.model_configs.get(provider_name, {}).copy()
        config.update(kwargs.get('generation_config', {}))
        
        response = await provider.generate(
            prompt=prompt,
            **config
        )
        
        # 4. 后处理
        processed_response = self._postprocess(response, context)
        
        # 5. 构建返回结果
        return {
            'answer': processed_response,
            'provider': provider_name,
            'model': config.get('model', 'unknown'),
            'usage': response.get('usage', {}),
            'citations': self._extract_citations(processed_response, context),
            'timestamp': datetime.now().isoformat()
        }
    
    def _select_provider(self, query: str, context: List[Dict], kwargs: Dict) -> str:
        """选择LLM提供者"""
        # 如果明确指定了提供者
        if 'provider' in kwargs:
            return kwargs['provider']
        
        # 根据路由策略选择
        if self.routing_strategy == 'cost_aware':
            # 成本感知：选择最便宜的可用提供者
            if 'dashscope' in self.llm_providers:
                return 'dashscope'
            elif 'openai' in self.llm_providers:
                return 'openai'
            else:
                return list(self.llm_providers.keys())[0] if self.llm_providers else 'openai'
        elif self.routing_strategy == 'quality_first':
            # 质量优先：选择最好的模型
            if 'openai' in self.llm_providers:
                return 'openai'
            elif 'anthropic' in self.llm_providers:
                return 'anthropic'
            else:
                return list(self.llm_providers.keys())[0] if self.llm_providers else 'openai'
        else:
            # 默认使用第一个可用提供者
            return list(self.llm_providers.keys())[0] if self.llm_providers else 'openai'
    
    def _build_rag_prompt(self, query: str, context: List[Dict], template: str, max_contexts: int = 5) -> str:
        """构建RAG提示模板"""
        if template not in self.PROMPT_TEMPLATES:
            template = 'default'
        
        # 限制上下文数量
        context_str = "\n\n".join([
            f"[文档{i+1}] {doc.get('content', doc.get('page_content', ''))[:1000]}...\n"
            f"来源: {doc.get('metadata', {}).get('source', '未知')}"
            for i, doc in enumerate(context[:max_contexts])
        ])
        
        return self.PROMPT_TEMPLATES[template].format(
            query=query,
            context=context_str
        )
    
    def _postprocess(self, response: Dict, context: List[Dict]) -> str:
        """后处理响应"""
        answer = response.get('content', response.get('text', ''))
        
        # 可以添加更多后处理逻辑
        # 例如：去除重复、格式化等
        
        return answer.strip()
    
    def _extract_citations(self, answer: str, context: List[Dict]) -> List[Dict]:
        """提取引用"""
        citations = []
        for i, doc in enumerate(context):
            source = doc.get('metadata', {}).get('source', f'文档{i+1}')
            citations.append({
                'index': i + 1,
                'source': source,
                'content_preview': doc.get('content', doc.get('page_content', ''))[:200]
            })
        
        return citations


class OpenAIClient:
    """OpenAI客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def generate(self, prompt: str, **kwargs) -> Dict:
        """生成文本"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            
            model = kwargs.get('model', 'gpt-3.5-turbo')
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=kwargs.get('max_tokens', 2000),
                temperature=kwargs.get('temperature', 0.1)
            )
            
            return {
                'content': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        except ImportError:
            raise ImportError("需要安装openai库")
        except Exception as e:
            raise Exception(f"OpenAI API调用失败: {e}")


class DashScopeClient:
    """DashScope客户端（阿里云）"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    async def generate(self, prompt: str, **kwargs) -> Dict:
        """生成文本"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            
            model = kwargs.get('model', 'qwen-plus')
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=kwargs.get('max_tokens', 2000),
                temperature=kwargs.get('temperature', 0.1)
            )
            
            return {
                'content': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        except ImportError:
            raise ImportError("需要安装openai库")
        except Exception as e:
            raise Exception(f"DashScope API调用失败: {e}")


class LocalLLMClient:
    """本地LLM客户端"""
    
    def __init__(self, model_path: str, device: str = 'cuda'):
        self.model_path = model_path
        self.device = device
        self.model = None  # 延迟加载
    
    async def generate(self, prompt: str, **kwargs) -> Dict:
        """生成文本（占位符）"""
        # 实际应该加载本地模型
        return {
            'content': '[本地模型生成结果]',
            'usage': {}
        }
