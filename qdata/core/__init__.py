"""
QData 核心模块
包含API管理器、选择器和数据转换器
"""
from .manager import APIManager, get_api_manager
from .selector import APISelector, select_api_by_keyword
from .mapper import (
    to_quantus_dict,
    ak_dict_to_quantus_dict,
    jq_dict_to_quantus_dict,
    ts_dict_to_quantus_dict,
    QUANTUS_DICT_SCHEMA,
)

__all__ = [
    "APIManager",
    "get_api_manager",
    "APISelector",
    "select_api_by_keyword",
    "to_quantus_dict",
    "ak_dict_to_quantus_dict",
    "jq_dict_to_quantus_dict",
    "ts_dict_to_quantus_dict",
    "QUANTUS_DICT_SCHEMA",
]
