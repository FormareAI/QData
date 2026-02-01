"""
QData.providers.akshare 模块的重新导出
为了支持 from QData.providers.akshare import ... 的导入方式
"""
from ..qdata.providers.akshare import AkshareProvider

__all__ = ["AkshareProvider"]
