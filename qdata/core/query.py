"""
自然语言查询接口
通过自然语言查询找到对应的API并获取数据
"""
import logging
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from .manager import get_api_manager
from .selector import APISelector, select_api_by_keyword
from .mapper import to_quantus_dict
from ..providers.akshare import AkshareProvider
from ..providers.jqdata import JQDataProvider
from ..providers.tushare import TushareProvider

logger = logging.getLogger(__name__)


class NaturalLanguageQuery:
    """自然语言查询接口"""
    
    def __init__(self, provider: str = "akshare", use_ai: bool = True):
        """
        初始化自然语言查询接口
        
        参数:
            provider: 数据源名称 ('akshare', 'jqdata', 'tushare')
            use_ai: 是否使用AI进行API选择（True使用tool calling，False使用keyword搜索）
        """
        self.provider = provider.lower()
        self.use_ai = use_ai
        self.api_manager = get_api_manager(provider=self.provider)
        self.selector = APISelector(provider=self.provider) if use_ai else None
        
        # 初始化数据源提供者
        if self.provider == "akshare":
            self.data_provider = AkshareProvider()
        elif self.provider in ["jqdata", "joinquant", "jq"]:
            self.data_provider = JQDataProvider()
        elif self.provider in ["tushare", "ts"]:
            self.data_provider = TushareProvider()
        else:
            raise ValueError(f"不支持的数据源: {provider}")
    
    async def query(
        self,
        user_query: str,
        execute: bool = False
    ) -> Dict[str, Any]:
        """
        通过自然语言查询找到对应的API
        
        参数:
            user_query: 用户查询，例如 "获取600000的20日close数据"
            execute: 是否执行API调用获取数据
            
        返回:
            包含API信息和数据的字典
        """
        try:
            # 第一步：选择API
            if self.use_ai and self.selector:
                # 使用AI tool calling选择
                logger.info(f"使用AI选择API: {user_query}")
                api_result = await self.selector.select_api_by_tool_calling(user_query)
            else:
                # 使用keyword搜索
                logger.info(f"使用Keyword搜索API: {user_query}")
                keyword_results = select_api_by_keyword(user_query, provider=self.provider)
                if keyword_results:
                    # 选择第一个结果
                    api_result = {
                        "api_name": keyword_results[0]['api_name'],
                        "provider": self.provider,
                        "reason": "Keyword搜索匹配",
                        "api_doc": self.api_manager.find_api_documentation(keyword_results[0]['api_name']),
                        "suggested_params": {}
                    }
                else:
                    api_result = None
            
            if not api_result:
                return {
                    "success": False,
                    "error": "未找到合适的API",
                    "query": user_query
                }
            
            result = {
                "success": True,
                "query": user_query,
                "provider": self.provider,
                "api_name": api_result['api_name'],
                "reason": api_result.get('reason', ''),
                "api_doc": api_result.get('api_doc', {}),
                "suggested_params": api_result.get('suggested_params', {}),
            }
            
            # 第二步：如果需要执行，调用API获取数据
            if execute:
                data = await self._execute_api(
                    api_result['api_name'],
                    api_result.get('api_doc', {}),
                    api_result.get('suggested_params', {})
                )
                if data is not None:
                    # 转换为quantus_dict格式
                    quantus_data = to_quantus_dict(data, source=self.provider)
                    result["data"] = quantus_data
                    result["data_count"] = len(quantus_data)
                else:
                    result["execute_error"] = "API执行失败"
            
            return result
            
        except Exception as e:
            logger.error(f"自然语言查询失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": user_query
            }
    
    async def _execute_api(
        self,
        api_name: str,
        api_doc: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        """
        执行API调用
        
        参数:
            api_name: API名称
            api_doc: API文档
            params: API参数
            
        返回:
            返回的数据（DataFrame）
        """
        try:
            if self.provider == "akshare":
                import akshare as ak
                # 构建API调用
                api_func = getattr(ak, api_name, None)
                if not api_func:
                    logger.error(f"API函数不存在: {api_name}")
                    return None
                
                # 调用API
                if params:
                    result = api_func(**params)
                else:
                    result = api_func()
                
                if isinstance(result, pd.DataFrame):
                    return result
                else:
                    logger.warning(f"API返回类型不是DataFrame: {type(result)}")
                    return None
                    
            elif self.provider in ["jqdata", "joinquant", "jq"]:
                # TODO: 实现jqdata API调用
                logger.warning("jqdata API调用暂未实现")
                return None
                
            elif self.provider in ["tushare", "ts"]:
                # TODO: 实现tushare API调用
                logger.warning("tushare API调用暂未实现")
                return None
                
        except Exception as e:
            logger.error(f"执行API失败: {e}", exc_info=True)
            return None


# 便捷函数
async def query(
    user_query: str,
    provider: str = "akshare",
    use_ai: bool = True,
    execute: bool = False
) -> Dict[str, Any]:
    """
    通过自然语言查询找到对应的API（便捷函数）
    
    参数:
        user_query: 用户查询
        provider: 数据源名称
        use_ai: 是否使用AI选择
        execute: 是否执行API调用
        
    返回:
        查询结果
    """
    nlp_query = NaturalLanguageQuery(provider=provider, use_ai=use_ai)
    return await nlp_query.query(user_query, execute=execute)
