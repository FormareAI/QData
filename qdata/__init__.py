"""
QData - 量化数据统一接口库
通过自然语言方式找到对应的数据接口，支持 akshare、jqdata、tushare 等多种数据源
"""
from .core.manager import APIManager, get_api_manager
from .core.selector import APISelector, select_api_by_keyword
from .core.mapper import (
    to_quantus_dict,
    ak_dict_to_quantus_dict,
    jq_dict_to_quantus_dict,
    ts_dict_to_quantus_dict,
    QUANTUS_DICT_SCHEMA,
)
from .providers.akshare import AkshareProvider
from .providers.jqdata import JQDataProvider
from .providers.tushare import TushareProvider
from .core.query import NaturalLanguageQuery, query

__version__ = "1.0.0"
__all__ = [
    # 核心管理器
    "APIManager",
    "get_api_manager",
    # AI选择器
    "APISelector",
    "select_api_by_keyword",
    # 数据转换器
    "to_quantus_dict",
    "ak_dict_to_quantus_dict",
    "jq_dict_to_quantus_dict",
    "ts_dict_to_quantus_dict",
    "QUANTUS_DICT_SCHEMA",
    # 数据源提供者
    "AkshareProvider",
    "JQDataProvider",
    "TushareProvider",
    # 自然语言查询
    "NaturalLanguageQuery",
    "query",
]
