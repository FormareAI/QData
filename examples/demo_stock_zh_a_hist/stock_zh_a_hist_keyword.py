"""
使用 Keyword 查询方式生成的代码
查询内容: 获取600000的20日close数据
找到的 API: stock_zh_ah_daily
"""
import akshare as ak
import pandas as pd
import json
from datetime import date, datetime, timedelta


# Format date parameters for akshare
def format_date_param(date_str):
    """将日期字符串转换为akshare所需的'YYYYMMDD'格式"""
    import re
    if re.match(r'^\d{8}$', str(date_str)):
        return str(date_str)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_str)):
        return str(date_str).replace('-', '')
    try:
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y%m%d')
    except:
        return str(date_str)

result = ak.stock_zh_ah_daily(symbol='600000', start_date=format_date_param('20260112'), end_date=format_date_param('20260201'), period='daily')

# Process and format the result
if isinstance(result, pd.DataFrame):
    if len(result) > 0:
        result_dict = result.to_dict(orient='records')
        print(f'获取到 {len(result)} 条记录')
        print(result.head())
    else:
        print('未获取到数据')
else:
    print(f'结果类型: {type(result)}')
    print(result)