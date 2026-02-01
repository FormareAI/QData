"""
JQData数据源提供者
"""
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from ..core.mapper import jq_dict_to_quantus_dict
from ..core.manager import APIManager, get_api_manager


class JQDataProvider:
    """JQData数据源提供者"""
    
    def __init__(self):
        """初始化JQData提供者"""
        self.api_manager = get_api_manager(provider="jqdata")
    
    def convert_to_quantus(self, jq_data: Union[pd.DataFrame, Dict[str, Any]]) -> pd.DataFrame:
        """
        将jqdata数据转换为quantus_dict格式
        
        参数:
            jq_data: jqdata返回的数据 (DataFrame或dict)
            
        返回:
            转换后的DataFrame (quantus_dict格式)
        """
        return jq_dict_to_quantus_dict(jq_data)
    
    def detect_function(self, markdown_content: str) -> Optional[Dict[str, Any]]:
        """
        从Markdown内容中检测是否需要使用jqdata函数
        
        参数:
            markdown_content: Markdown内容
            
        返回:
            如果检测到需要jqdata，返回包含API名称和参数的字典；否则返回None
        """
        # 检测关键词
        jqdata_keywords = [
            "jqdata", "joinquant", "get_price", "history",
            "股票", "行情", "历史数据"
        ]
        
        content_lower = markdown_content.lower()
        
        # 检查是否包含jqdata相关关键词
        has_keywords = any(keyword in content_lower for keyword in jqdata_keywords)
        
        if not has_keywords:
            return None
        
        detected_info = {
            "use_jqdata": True,
            "api_name": None,
            "params": {}
        }
        
        return detected_info
