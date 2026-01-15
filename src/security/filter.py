"""
安全过滤器
"""
import hashlib
import re
from typing import Tuple, Dict, Optional, List


class SecurityError(Exception):
    """安全异常"""
    pass


class SecurityFilter:
    """安全过滤器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.max_input_length = self.config.get('max_input_length', 10000)
        self.enable_pii_detection = self.config.get('enable_pii_detection', True)
        self.enable_content_filter = self.config.get('enable_content_filter', True)
    
    async def filter_input(self, user_input: str, user_context: Optional[Dict] = None) -> Tuple[str, Dict]:
        """输入过滤"""
        user_context = user_context or {}
        
        # 1. 输入长度限制
        if len(user_input) > self.max_input_length:
            raise SecurityError("输入过长")
        
        # 2. 恶意输入检测
        if self._detect_prompt_injection(user_input):
            raise SecurityError("检测到潜在注入攻击")
        
        # 3. PII信息检测
        pii_info = {}
        if self.enable_pii_detection:
            pii_info = self._detect_pii(user_input)
            if pii_info:
                # 记录但不脱敏（根据策略）
                await self._log_pii_detection(user_context, pii_info)
        
        # 4. 内容过滤
        filtered_input = user_input
        if self.enable_content_filter:
            filtered_input = self._filter_content(user_input)
        
        # 5. 审计日志
        await self._log_input(
            user_id=user_context.get('user_id'),
            action='query',
            content_hash=hashlib.md5(filtered_input.encode()).hexdigest(),
            metadata=user_context
        )
        
        return filtered_input, {'pii_detected': bool(pii_info), 'pii_info': pii_info}
    
    async def filter_output(self, llm_output: str, context: Optional[Dict] = None) -> Tuple[str, Dict]:
        """输出过滤"""
        context = context or {}
        
        # 1. 有害内容检测
        harmful_content = self._detect_harmful(llm_output)
        if harmful_content:
            llm_output = "[内容已过滤]"
            await self._log_harmful_content(context, harmful_content)
        
        # 2. 事实核查（可选）
        if context.get('enable_fact_checking', False):
            factual_errors = await self._fact_check(llm_output, context)
            if factual_errors:
                llm_output += f"\n\n[注意: 检测到{len(factual_errors)}处潜在事实错误]"
        
        # 3. 输出审计
        await self._log_output(
            request_id=context.get('request_id'),
            content_hash=hashlib.md5(llm_output.encode()).hexdigest(),
            filter_results={'harmful_content_detected': bool(harmful_content)}
        )
        
        return llm_output, {'filtered': bool(harmful_content)}
    
    def _detect_prompt_injection(self, text: str) -> bool:
        """检测提示注入攻击"""
        # 常见注入模式
        injection_patterns = [
            r'ignore\s+(previous|above|all)\s+instructions?',
            r'forget\s+(previous|above|all)',
            r'you\s+are\s+now',
            r'act\s+as\s+if',
            r'pretend\s+to\s+be',
            r'disregard\s+(previous|above)',
        ]
        
        text_lower = text.lower()
        for pattern in injection_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _detect_pii(self, text: str) -> Dict:
        """检测PII信息"""
        pii_info = {}
        
        # 邮箱
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            pii_info['emails'] = emails
        
        # 手机号（中国）
        phone_pattern = r'1[3-9]\d{9}'
        phones = re.findall(phone_pattern, text)
        if phones:
            pii_info['phones'] = phones
        
        # 身份证号（中国）
        id_card_pattern = r'\d{17}[\dXx]'
        id_cards = re.findall(id_card_pattern, text)
        if id_cards:
            pii_info['id_cards'] = id_cards
        
        # 银行卡号（简化版）
        bank_card_pattern = r'\d{16,19}'
        bank_cards = re.findall(bank_card_pattern, text)
        if bank_cards:
            pii_info['bank_cards'] = bank_cards
        
        return pii_info
    
    def _filter_content(self, text: str) -> str:
        """内容过滤"""
        # 移除潜在的恶意脚本
        # 移除HTML标签（如果不需要）
        # 移除SQL注入模式等
        
        # 简单示例：移除HTML标签
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        return text
    
    def _detect_harmful(self, text: str) -> bool:
        """检测有害内容"""
        # 简化版：检测明显的有害关键词
        harmful_keywords = [
            '暴力', '色情', '赌博', '毒品',
            # 可以根据需要扩展
        ]
        
        text_lower = text.lower()
        for keyword in harmful_keywords:
            if keyword in text_lower:
                return True
        
        return False
    
    async def _fact_check(self, text: str, context: Dict) -> List[str]:
        """事实核查（占位符）"""
        # 实际应该调用事实核查服务
        return []
    
    async def _log_pii_detection(self, user_context: Dict, pii_info: Dict):
        """记录PII检测"""
        # 实际应该写入审计日志
        print(f"PII检测: 用户={user_context.get('user_id')}, PII={pii_info}")
    
    async def _log_input(self, user_id: Optional[str], action: str, content_hash: str, metadata: Dict):
        """记录输入日志"""
        # 实际应该写入审计日志
        print(f"输入审计: 用户={user_id}, 操作={action}, 哈希={content_hash}")
    
    async def _log_harmful_content(self, context: Dict, harmful_content: bool):
        """记录有害内容"""
        # 实际应该写入审计日志
        print(f"有害内容检测: 请求={context.get('request_id')}, 检测到有害内容={harmful_content}")
    
    async def _log_output(self, request_id: Optional[str], content_hash: str, filter_results: Dict):
        """记录输出日志"""
        # 实际应该写入审计日志
        print(f"输出审计: 请求={request_id}, 哈希={content_hash}, 过滤结果={filter_results}")
