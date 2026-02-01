"""
数据源提供者模块
支持 akshare、jqdata、tushare 等多种数据源

这是 QData.providers 的重新导出，实际实现在 qdata.providers 中
"""
from ..qdata.providers.akshare import AkshareProvider
from ..qdata.providers.jqdata import JQDataProvider
from ..qdata.providers.tushare import TushareProvider

__all__ = [
    "AkshareProvider",
    "JQDataProvider",
    "TushareProvider",
]
