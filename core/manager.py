"""
QData.core.manager 模块的重新导出
为了支持 from QData.core.manager import ... 的导入方式
"""
from ..qdata.core.manager import APIManager, get_api_manager

__all__ = ["APIManager", "get_api_manager"]
