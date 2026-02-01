"""
API智能选择器
通过AI tool calling方式选择最合适的API接口，支持多数据源
"""
import json
import logging
from typing import Dict, List, Optional, Any
from .manager import APIManager, get_api_manager
from utils.openrouter import get_model_name
from constants.ai_field import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class APISelector:
    """通过AI tool calling选择最合适的API接口，支持多数据源"""
    
    def __init__(self, provider: str = "akshare", model: str = "qwen/qwen-2.5-72b-instruct"):
        """
        初始化AI选择器
        
        参数:
            provider: 数据源名称 ('akshare', 'jqdata', 'tushare')
            model: 使用的AI模型
        """
        self.provider = provider.lower()
        self.model = model
        self.api_manager = get_api_manager(provider=self.provider)
        self.client = None
        
        if OPENROUTER_API_KEY and OPENROUTER_API_KEY != "sk-or-v1":
            self.client = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
        else:
            logger.warning("OPENROUTER_API_KEY未配置，无法使用AI选择功能")
    
    def _build_api_tools(self, candidate_apis: List[Dict[str, Any]]) -> List[Dict]:
        """
        构建tool calling的工具定义
        
        参数:
            candidate_apis: 候选API列表
            
        返回:
            tool定义列表
        """
        tools = []
        
        for api_info in candidate_apis:
            api_name = api_info.get('api_name', '')
            description = api_info.get('description', '')
            
            # 获取API文档以获取参数信息
            api_doc = self.api_manager.find_api_documentation(api_name)
            params_info = api_doc.get('params', {}) if api_doc else {}
            
            # 构建参数定义
            properties = {}
            required = []
            
            for param_name, param_value in params_info.items():
                properties[param_name] = {
                    "type": "string",
                    "description": f"参数 {param_name}" + (f" (默认值: {param_value})" if param_value else "")
                }
                # 根据实际情况决定是否必需
                if param_name in ['symbol', 'code', 'ts_code']:
                    required.append(param_name)
            
            tool = {
                "type": "function",
                "function": {
                    "name": f"select_api_{api_name}",
                    "description": f"选择API: {api_name} - {description}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "api_name": {
                                "type": "string",
                                "description": f"API名称: {api_name}",
                                "enum": [api_name]
                            },
                            "reason": {
                                "type": "string",
                                "description": "选择此API的原因"
                            },
                            **properties
                        },
                        "required": ["api_name", "reason"] + required
                    }
                }
            }
            tools.append(tool)
        
        return tools
    
    async def select_api_by_tool_calling(
        self,
        user_query: str,
        max_candidates: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        通过tool calling方式选择最合适的API
        
        参数:
            user_query: 用户查询，例如 "获取600000的20日close数据"
            max_candidates: 最大候选API数量
            
        返回:
            选中的API信息，包含api_name和参数
        """
        if not self.client:
            logger.error("OpenAI客户端未初始化，无法使用tool calling")
            return None
        
        try:
            # 第一步：通过关键词搜索候选API
            logger.info(f"搜索候选API，查询: {user_query}, provider: {self.provider}")
            
            # 提取关键词
            keywords = self._extract_keywords(user_query)
            candidate_apis = []
            
            for keyword in keywords:
                results = self.api_manager.search_apis_by_keyword(keyword)
                candidate_apis.extend(results)
            
            # 去重
            seen = set()
            unique_apis = []
            for api in candidate_apis:
                api_name = api.get('api_name', '')
                if api_name and api_name not in seen:
                    seen.add(api_name)
                    unique_apis.append(api)
            
            # 限制候选数量
            candidate_apis = unique_apis[:max_candidates]
            
            if not candidate_apis:
                logger.warning(f"未找到候选API (provider: {self.provider})")
                return None
            
            logger.info(f"找到 {len(candidate_apis)} 个候选API")
            
            # 第二步：构建tool calling工具
            tools = self._build_api_tools(candidate_apis)
            
            # 第三步：调用AI进行选择
            system_prompt = f"""你是一个专业的股票数据API选择专家。根据用户的需求，从候选API中选择最合适的API接口。

数据源: {self.provider}

要求：
1. 仔细分析用户需求，理解需要获取什么类型的数据
2. 比较候选API的功能和特点
3. 选择最匹配用户需求的API
4. 提供选择理由
5. 如果用户需求中包含参数信息（如股票代码、日期等），请在reason中说明"""
            
            user_prompt = f"""用户需求：{user_query}

请从以下候选API中选择最合适的API：
{json.dumps([{'api_name': api.get('api_name'), 'description': api.get('description', '')[:100]} for api in candidate_apis], ensure_ascii=False, indent=2)}

请选择一个最合适的API，并说明选择理由。"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            model_name = get_model_name(self.model)
            logger.info(f"调用AI模型进行API选择: {model_name}")
            
            completion = await self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                tool_choice="required",  # 强制要求调用工具
                temperature=0.3,
            )
            
            # 解析响应
            if not completion or not completion.choices or len(completion.choices) == 0:
                logger.error("AI响应异常")
                return None
            
            response = completion.choices[0].message
            
            if not response.tool_calls or len(response.tool_calls) == 0:
                logger.warning("AI未返回tool call")
                return None
            
            # 获取第一个tool call
            tool_call = response.tool_calls[0]
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            # 提取API名称
            api_name = arguments.get('api_name')
            reason = arguments.get('reason', '')
            
            logger.info(f"AI选择了API: {api_name}, 理由: {reason}")
            
            # 获取完整的API文档
            api_doc = self.api_manager.find_api_documentation(api_name)
            
            if not api_doc:
                logger.warning(f"未找到API文档: {api_name}")
                return None
            
            # 构建返回结果
            result = {
                "api_name": api_name,
                "provider": self.provider,
                "reason": reason,
                "api_doc": api_doc,
                "suggested_params": {k: v for k, v in arguments.items() if k not in ['api_name', 'reason']}
            }
            
            return result
            
        except Exception as e:
            logger.error(f"AI选择API失败: {e}", exc_info=True)
            return None
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        从用户查询中提取关键词
        
        参数:
            query: 用户查询
            
        返回:
            关键词列表
        """
        keywords = []
        query_lower = query.lower()
        
        # 常见关键词映射
        keyword_mapping = {
            '历史': ['历史', '历史行情', '历史数据'],
            '实时': ['实时', '实时行情', '实时数据'],
            '行情': ['行情', '行情数据'],
            'close': ['收盘', '收盘价', 'close'],
            'open': ['开盘', '开盘价', 'open'],
            'high': ['最高', '最高价', 'high'],
            'low': ['最低', '最低价', 'low'],
            'volume': ['成交量', 'volume'],
            'amount': ['成交额', 'amount'],
        }
        
        # 提取关键词
        for key, values in keyword_mapping.items():
            for value in values:
                if value in query_lower:
                    keywords.append(value)
                    break
        
        # 如果没有找到关键词，使用通用搜索
        if not keywords:
            keywords = ['历史行情', '行情数据']
        
        return keywords


def select_api_by_keyword(query: str, provider: str = "akshare") -> List[Dict[str, Any]]:
    """
    通过关键词搜索API（传统方式）
    
    参数:
        query: 用户查询
        provider: 数据源名称 ('akshare', 'jqdata', 'tushare')
        
    返回:
        API列表
    """
    manager = get_api_manager(provider=provider)
    
    # 提取关键词
    keywords = []
    query_lower = query.lower()
    
    # 优先匹配更精确的关键词
    if 'a股' in query_lower or 'a股历史' in query_lower or ('历史' in query_lower and 'a' in query_lower):
        keywords.append('A股历史行情')
        keywords.append('历史行情')
    elif '历史' in query_lower or '历史数据' in query_lower:
        keywords.append('历史行情')
    elif '实时' in query_lower or '实时数据' in query_lower:
        keywords.append('实时行情')
    else:
        keywords.append('行情数据')
    
    # 搜索API
    results = []
    for keyword in keywords:
        results.extend(manager.search_apis_by_keyword(keyword))
    
    # 去重并优先选择更匹配的API
    seen = set()
    unique_results = []
    for result in results:
        api_name = result.get('api_name', '')
        if api_name and api_name not in seen:
            seen.add(api_name)
            unique_results.append(result)
    
    # 如果查询中包含股票代码（6位数字），优先选择 stock_zh_a_hist
    import re
    if re.search(r'\d{6}', query):
        # 重新排序，将 stock_zh_a_hist 相关的API排在前面
        stock_zh_a_hist_results = [r for r in unique_results if 'stock_zh_a_hist' in r.get('api_name', '')]
        other_results = [r for r in unique_results if 'stock_zh_a_hist' not in r.get('api_name', '')]
        unique_results = stock_zh_a_hist_results + other_results
    
    return unique_results
