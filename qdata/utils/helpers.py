"""
QData工具函数
提供通用的辅助函数
"""
import re
from typing import Any
from datetime import datetime
import pandas as pd


def format_date_param(date_str: str, target_format: str = "YYYYMMDD") -> str:
    """
    格式化日期参数
    
    参数:
        date_str: 日期字符串，支持多种格式
        target_format: 目标格式 ("YYYYMMDD" 或 "YYYY-MM-DD")
        
    返回:
        格式化后的日期字符串
    """
    # 检查是否已经是YYYYMMDD格式
    if re.match(r'^\d{8}$', str(date_str)):
        if target_format == "YYYY-MM-DD":
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return str(date_str)
    # 尝试转换YYYY-MM-DD格式
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_str)):
        if target_format == "YYYYMMDD":
            return str(date_str).replace('-', '')
        return str(date_str)
    # 尝试解析任何日期格式并转换
    try:
        dt = pd.to_datetime(date_str)
        if target_format == "YYYYMMDD":
            return dt.strftime('%Y%m%d')
        else:
            return dt.strftime('%Y-%m-%d')
    except:
        # 无法处理则原样返回
        return str(date_str)


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
    elif source in ["joinquant", "jqdata"]:
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


def get_current_date(value_format: str = "YYYYMMDD") -> str:
    """
    获取当前日期，以指定格式返回
    
    参数:
        value_format: 日期格式，默认为YYYYMMDD
        
    返回:
        格式化的当前日期字符串
    """
    now = datetime.now()
    if "YYYYMMDD" in value_format or re.match(r'^\d{8}$', value_format):
        return now.strftime('%Y%m%d')
    elif "YYYY-MM-DD" in value_format or re.match(r'^\d{4}-\d{2}-\d{2}$', value_format):
        return now.strftime('%Y-%m-%d')
    else:
        return now.strftime('%Y%m%d')
