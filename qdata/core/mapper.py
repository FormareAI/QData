"""
统一数据字典转换器
实现 akshare、jqdata、tushare 数据格式到 quantus_dict 的统一转换
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ==================== Quantus统一数据字典定义 ====================

QUANTUS_DICT_SCHEMA = {
    # 基础字段
    "date": "交易日期 (datetime或str)",
    "code": "股票代码 (str, 统一格式)",
    "name": "股票名称 (str, 可选)",
    
    # 价格字段
    "open": "开盘价 (float)",
    "close": "收盘价 (float)",
    "high": "最高价 (float)",
    "low": "最低价 (float)",
    "pre_close": "前收盘价 (float, 可选)",
    
    # 成交量字段
    "volume": "成交量 (int/float, 单位: 股)",
    "amount": "成交额 (float, 单位: 元)",
    
    # 技术指标字段
    "pct_change": "涨跌幅 (float, 单位: %)",
    "change": "涨跌额 (float, 单位: 元)",
    "amplitude": "振幅 (float, 单位: %, 可选)",
    "turnover": "换手率 (float, 单位: %, 可选)",
    
    # 扩展字段
    "market": "市场标识 (str, 可选: XSHG/XSHE)",
    "industry": "行业 (str, 可选)",
    "market_cap": "市值 (float, 可选)",
    "circulating_market_cap": "流通市值 (float, 可选)",
}


# ==================== 字段映射字典 ====================

# akshare -> quantus_dict 字段映射
AKSHARE_TO_QUANTUS_MAP = {
    # 基础字段
    "日期": "date",
    "股票代码": "code",
    "代码": "code",
    "名称": "name",
    "股票简称": "name",
    
    # 价格字段
    "开盘": "open",
    "开盘价": "open",
    "收盘": "close",
    "收盘价": "close",
    "最高": "high",
    "最高价": "high",
    "最低": "low",
    "最低价": "low",
    "前收盘": "pre_close",
    "昨收": "pre_close",
    
    # 成交量字段
    "成交量": "volume",
    "成交额": "amount",
    "成交金额": "amount",
    
    # 技术指标字段
    "涨跌幅": "pct_change",
    "涨跌额": "change",
    "振幅": "amplitude",
    "换手率": "turnover",
    
    # 扩展字段
    "总市值": "market_cap",
    "流通市值": "circulating_market_cap",
    "行业": "industry",
}

# joinquant -> quantus_dict 字段映射
JOINQUANT_TO_QUANTUS_MAP = {
    # 基础字段
    "time": "date",
    "date": "date",
    "code": "code",
    "sec_code": "code",
    "name": "name",
    "display_name": "name",
    
    # 价格字段
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "pre_close": "pre_close",
    
    # 成交量字段
    "volume": "volume",
    "money": "amount",
    "amount": "amount",
    
    # 技术指标字段
    "pct_change": "pct_change",
    "change_pct": "pct_change",
    "change": "change",
    "amplitude": "amplitude",
    "turnover": "turnover",
    "turnover_ratio": "turnover",
    
    # 扩展字段
    "market_cap": "market_cap",
    "total_market_cap": "market_cap",
    "circulating_market_cap": "circulating_market_cap",
    "industry": "industry",
}

# tushare -> quantus_dict 字段映射
TUSHARE_TO_QUANTUS_MAP = {
    # 基础字段
    "trade_date": "date",
    "ts_code": "code",
    "name": "name",
    
    # 价格字段
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "pre_close": "pre_close",
    
    # 成交量字段
    "vol": "volume",
    "amount": "amount",
    
    # 技术指标字段
    "pct_chg": "pct_change",
    "change": "change",
    "amplitude": "amplitude",
    "turnover": "turnover",
    
    # 扩展字段
    "market_cap": "market_cap",
    "circ_mv": "circulating_market_cap",
}


# ==================== 转换函数 ====================

def normalize_code(code: str, source: str = "akshare") -> str:
    """
    标准化股票代码格式
    
    参数:
        code: 原始股票代码
        source: 数据源 (akshare/jqdata/tushare)
        
    返回:
        标准化的股票代码 (格式: 000001.XSHE 或 600000.XSHG)
    """
    if pd.isna(code) or code is None:
        return ""
    
    code_str = str(code).strip()
    
    # 处理akshare格式: 可能是 "000001" 或 "sh600000" 或 "600000"
    if source == "akshare":
        # 移除市场前缀
        if code_str.startswith(("sh", "sz", "SH", "SZ")):
            code_str = code_str[2:]
        
        # 确保是6位数字
        if len(code_str) == 6 and code_str.isdigit():
            # 判断市场
            if code_str.startswith(("60", "68", "90")):
                return f"{code_str}.XSHG"
            elif code_str.startswith(("00", "30")):
                return f"{code_str}.XSHE"
            else:
                return code_str
    
    # 处理joinquant格式: 通常是 "000001.XSHE" 或 "600000.XSHG"
    elif source == "joinquant" or source == "jqdata":
        if "." in code_str:
            return code_str
        else:
            # 如果没有市场后缀，尝试添加
            if len(code_str) == 6 and code_str.isdigit():
                if code_str.startswith(("60", "68", "90")):
                    return f"{code_str}.XSHG"
                elif code_str.startswith(("00", "30")):
                    return f"{code_str}.XSHE"
    
    # 处理tushare格式: 通常是 "000001.SZ" 或 "600000.SH"
    elif source == "tushare":
        if "." in code_str:
            # 转换 .SH -> .XSHG, .SZ -> .XSHE
            code_str = code_str.replace(".SH", ".XSHG").replace(".SZ", ".XSHE")
            return code_str
        else:
            # 如果没有市场后缀，尝试添加
            if len(code_str) == 6 and code_str.isdigit():
                if code_str.startswith(("60", "68", "90")):
                    return f"{code_str}.XSHG"
                elif code_str.startswith(("00", "30")):
                    return f"{code_str}.XSHE"
    
    return code_str


def normalize_date(date_value: Any) -> str:
    """
    标准化日期格式
    
    参数:
        date_value: 日期值 (可能是datetime, date, str等)
        
    返回:
        标准化的日期字符串 (格式: YYYY-MM-DD)
    """
    if pd.isna(date_value) or date_value is None:
        return ""
    
    # 如果是字符串
    if isinstance(date_value, str):
        # 处理 YYYYMMDD 格式
        if len(date_value) == 8 and date_value.isdigit():
            return f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:8]}"
        # 处理 YYYY-MM-DD 格式
        elif len(date_value) == 10 and "-" in date_value:
            return date_value
        # 尝试解析
        try:
            dt = pd.to_datetime(date_value)
            return dt.strftime("%Y-%m-%d")
        except:
            return date_value
    
    # 如果是datetime或date对象
    try:
        if hasattr(date_value, "strftime"):
            return date_value.strftime("%Y-%m-%d")
        elif hasattr(date_value, "date"):
            return date_value.date().strftime("%Y-%m-%d")
    except:
        pass
    
    # 尝试用pandas解析
    try:
        dt = pd.to_datetime(date_value)
        return dt.strftime("%Y-%m-%d")
    except:
        return str(date_value)


def convert_volume(volume: Any, source: str = "akshare") -> float:
    """
    转换成交量单位 (统一为股)
    
    参数:
        volume: 成交量值
        source: 数据源
        
    返回:
        成交量 (单位: 股)
    """
    if pd.isna(volume) or volume is None:
        return 0.0
    
    try:
        vol = float(volume)
        
        # akshare的成交量单位通常是"手" (1手=100股)
        if source == "akshare":
            # 检查字段名，如果是"成交量"通常是手，需要乘以100
            # 这里假设传入的已经是股，如果实际是手，需要在调用时处理
            return vol
        
        # joinquant的成交量单位通常是股
        elif source in ["joinquant", "jqdata"]:
            return vol
        
        # tushare的成交量单位通常是手
        elif source == "tushare":
            # tushare的vol字段通常是手，需要乘以100
            return vol * 100
        
        return vol
    except:
        return 0.0


def ak_dict_to_quantus_dict(
    ak_data: Union[pd.DataFrame, Dict[str, Any]],
    code_field: Optional[str] = None,
    date_field: Optional[str] = None
) -> pd.DataFrame:
    """
    将akshare数据转换为quantus_dict格式
    
    参数:
        ak_data: akshare返回的数据 (DataFrame或dict)
        code_field: 股票代码字段名 (如果为None则自动检测)
        date_field: 日期字段名 (如果为None则自动检测)
        
    返回:
        转换后的DataFrame (quantus_dict格式)
    """
    try:
        # 转换为DataFrame
        if isinstance(ak_data, dict):
            df = pd.DataFrame([ak_data])
        elif isinstance(ak_data, pd.DataFrame):
            df = ak_data.copy()
        else:
            raise ValueError(f"不支持的数据类型: {type(ak_data)}")
        
        if df.empty:
            return pd.DataFrame()
        
        # 创建结果DataFrame
        result = pd.DataFrame()
        
        # 字段映射
        field_map = AKSHARE_TO_QUANTUS_MAP
        
        # 自动检测字段
        if code_field is None:
            for col in df.columns:
                if col in ["股票代码", "代码", "code"]:
                    code_field = col
                    break
        
        if date_field is None:
            for col in df.columns:
                if col in ["日期", "date", "时间"]:
                    date_field = col
                    break
        
        # 转换每个字段
        for ak_field, quantus_field in field_map.items():
            if ak_field in df.columns:
                if quantus_field == "code":
                    # 标准化股票代码
                    result[quantus_field] = df[ak_field].apply(
                        lambda x: normalize_code(x, source="akshare")
                    )
                elif quantus_field == "date":
                    # 标准化日期
                    result[quantus_field] = df[ak_field].apply(normalize_date)
                elif quantus_field == "volume":
                    # 转换成交量
                    result[quantus_field] = df[ak_field].apply(
                        lambda x: convert_volume(x, source="akshare")
                    )
                else:
                    # 直接复制
                    result[quantus_field] = df[ak_field]
        
        # 如果没有找到代码字段，尝试使用code_field参数
        if "code" not in result.columns and code_field:
            result["code"] = df[code_field].apply(
                lambda x: normalize_code(x, source="akshare")
            )
        
        # 如果没有找到日期字段，尝试使用date_field参数
        if "date" not in result.columns and date_field:
            result["date"] = df[date_field].apply(normalize_date)
        
        # 确保必要的字段存在
        required_fields = ["date", "code", "open", "close", "high", "low"]
        for field in required_fields:
            if field not in result.columns:
                logger.warning(f"缺少必要字段: {field}")
        
        return result
        
    except Exception as e:
        logger.error(f"akshare数据转换失败: {e}", exc_info=True)
        raise


def jq_dict_to_quantus_dict(
    jq_data: Union[pd.DataFrame, Dict[str, Any]],
    code_field: Optional[str] = None,
    date_field: Optional[str] = None
) -> pd.DataFrame:
    """
    将joinquant数据转换为quantus_dict格式
    
    参数:
        jq_data: joinquant返回的数据 (DataFrame或dict)
        code_field: 股票代码字段名 (如果为None则自动检测)
        date_field: 日期字段名 (如果为None则自动检测)
        
    返回:
        转换后的DataFrame (quantus_dict格式)
    """
    try:
        # 转换为DataFrame
        if isinstance(jq_data, dict):
            df = pd.DataFrame([jq_data])
        elif isinstance(jq_data, pd.DataFrame):
            df = jq_data.copy()
        else:
            raise ValueError(f"不支持的数据类型: {type(jq_data)}")
        
        if df.empty:
            return pd.DataFrame()
        
        # 创建结果DataFrame
        result = pd.DataFrame()
        
        # 字段映射
        field_map = JOINQUANT_TO_QUANTUS_MAP
        
        # 自动检测字段
        if code_field is None:
            for col in df.columns:
                if col in ["code", "sec_code"]:
                    code_field = col
                    break
        
        if date_field is None:
            for col in df.columns:
                if col in ["date", "time"]:
                    date_field = col
                    break
        
        # 转换每个字段
        for jq_field, quantus_field in field_map.items():
            if jq_field in df.columns:
                if quantus_field == "code":
                    # 标准化股票代码
                    result[quantus_field] = df[jq_field].apply(
                        lambda x: normalize_code(x, source="joinquant")
                    )
                elif quantus_field == "date":
                    # 标准化日期
                    result[quantus_field] = df[jq_field].apply(normalize_date)
                elif quantus_field == "volume":
                    # 转换成交量
                    result[quantus_field] = df[jq_field].apply(
                        lambda x: convert_volume(x, source="joinquant")
                    )
                else:
                    # 直接复制
                    result[quantus_field] = df[jq_field]
        
        # 如果没有找到代码字段，尝试使用code_field参数
        if "code" not in result.columns and code_field:
            result["code"] = df[code_field].apply(
                lambda x: normalize_code(x, source="joinquant")
            )
        
        # 如果没有找到日期字段，尝试使用date_field参数
        if "date" not in result.columns and date_field:
            result["date"] = df[date_field].apply(normalize_date)
        
        # 确保必要的字段存在
        required_fields = ["date", "code", "open", "close", "high", "low"]
        for field in required_fields:
            if field not in result.columns:
                logger.warning(f"缺少必要字段: {field}")
        
        return result
        
    except Exception as e:
        logger.error(f"joinquant数据转换失败: {e}", exc_info=True)
        raise


def ts_dict_to_quantus_dict(
    ts_data: Union[pd.DataFrame, Dict[str, Any]],
    code_field: Optional[str] = None,
    date_field: Optional[str] = None
) -> pd.DataFrame:
    """
    将tushare数据转换为quantus_dict格式
    
    参数:
        ts_data: tushare返回的数据 (DataFrame或dict)
        code_field: 股票代码字段名 (如果为None则自动检测)
        date_field: 日期字段名 (如果为None则自动检测)
        
    返回:
        转换后的DataFrame (quantus_dict格式)
    """
    try:
        # 转换为DataFrame
        if isinstance(ts_data, dict):
            df = pd.DataFrame([ts_data])
        elif isinstance(ts_data, pd.DataFrame):
            df = ts_data.copy()
        else:
            raise ValueError(f"不支持的数据类型: {type(ts_data)}")
        
        if df.empty:
            return pd.DataFrame()
        
        # 创建结果DataFrame
        result = pd.DataFrame()
        
        # 字段映射
        field_map = TUSHARE_TO_QUANTUS_MAP
        
        # 自动检测字段
        if code_field is None:
            for col in df.columns:
                if col in ["ts_code", "code"]:
                    code_field = col
                    break
        
        if date_field is None:
            for col in df.columns:
                if col in ["trade_date", "date"]:
                    date_field = col
                    break
        
        # 转换每个字段
        for ts_field, quantus_field in field_map.items():
            if ts_field in df.columns:
                if quantus_field == "code":
                    # 标准化股票代码
                    result[quantus_field] = df[ts_field].apply(
                        lambda x: normalize_code(x, source="tushare")
                    )
                elif quantus_field == "date":
                    # 标准化日期
                    result[quantus_field] = df[ts_field].apply(normalize_date)
                elif quantus_field == "volume":
                    # 转换成交量 (tushare的vol是手，需要乘以100)
                    result[quantus_field] = df[ts_field].apply(
                        lambda x: convert_volume(x, source="tushare")
                    )
                elif quantus_field == "pct_change":
                    # tushare的pct_chg可能已经是百分比，需要确认
                    result[quantus_field] = df[ts_field]
                else:
                    # 直接复制
                    result[quantus_field] = df[ts_field]
        
        # 如果没有找到代码字段，尝试使用code_field参数
        if "code" not in result.columns and code_field:
            result["code"] = df[code_field].apply(
                lambda x: normalize_code(x, source="tushare")
            )
        
        # 如果没有找到日期字段，尝试使用date_field参数
        if "date" not in result.columns and date_field:
            result["date"] = df[date_field].apply(normalize_date)
        
        # 确保必要的字段存在
        required_fields = ["date", "code", "open", "close", "high", "low"]
        for field in required_fields:
            if field not in result.columns:
                logger.warning(f"缺少必要字段: {field}")
        
        return result
        
    except Exception as e:
        logger.error(f"tushare数据转换失败: {e}", exc_info=True)
        raise


def to_quantus_dict(
    data: Union[pd.DataFrame, Dict[str, Any]],
    source: str = "akshare",
    **kwargs
) -> pd.DataFrame:
    """
    通用转换函数，根据source参数选择转换方式
    
    参数:
        data: 输入数据 (DataFrame或dict)
        source: 数据源 ("akshare", "jqdata", "tushare")
        **kwargs: 其他参数传递给具体转换函数
        
    返回:
        转换后的DataFrame (quantus_dict格式)
    """
    source_lower = source.lower()
    if source_lower == "akshare":
        return ak_dict_to_quantus_dict(data, **kwargs)
    elif source_lower in ["joinquant", "jq", "jqdata"]:
        return jq_dict_to_quantus_dict(data, **kwargs)
    elif source_lower in ["tushare", "ts"]:
        return ts_dict_to_quantus_dict(data, **kwargs)
    else:
        raise ValueError(f"不支持的数据源: {source}")


# ==================== 辅助函数 ====================

def get_field_mapping(source: str) -> Dict[str, str]:
    """
    获取字段映射字典
    
    参数:
        source: 数据源 ("akshare", "jqdata", "tushare")
        
    返回:
        字段映射字典
    """
    source_lower = source.lower()
    if source_lower == "akshare":
        return AKSHARE_TO_QUANTUS_MAP.copy()
    elif source_lower in ["joinquant", "jq", "jqdata"]:
        return JOINQUANT_TO_QUANTUS_MAP.copy()
    elif source_lower in ["tushare", "ts"]:
        return TUSHARE_TO_QUANTUS_MAP.copy()
    else:
        raise ValueError(f"不支持的数据源: {source}")


def validate_quantus_dict(data: pd.DataFrame) -> bool:
    """
    验证数据是否符合quantus_dict格式
    
    参数:
        data: 待验证的DataFrame
        
    返回:
        是否符合格式 (bool)
    """
    if not isinstance(data, pd.DataFrame):
        return False
    
    required_fields = ["date", "code", "open", "close", "high", "low"]
    
    for field in required_fields:
        if field not in data.columns:
            logger.warning(f"缺少必要字段: {field}")
            return False
    
    return True
