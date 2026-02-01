"""
Akshare数据源提供者
"""
import re
from typing import Dict, List, Optional, Any, Union
from datetime import date, datetime, timedelta
import pandas as pd
from ..core.mapper import ak_dict_to_quantus_dict, to_quantus_dict
from ..core.manager import APIManager, get_api_manager


class AkshareProvider:
    """Akshare数据源提供者"""
    
    def __init__(self):
        """初始化Akshare提供者"""
        self.api_manager = get_api_manager(provider="akshare")
    
    def format_date_param(self, date_str: str) -> str:
        """
        将日期字符串转换为akshare所需的'YYYYMMDD'格式
        
        参数:
            date_str: 日期字符串，支持多种格式
            
        返回:
            YYYYMMDD格式的日期字符串
        """
        # 检查是否已经是YYYYMMDD格式
        if re.match(r'^\d{8}$', str(date_str)):
            return str(date_str)
        # 尝试转换YYYY-MM-DD格式
        elif re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_str)):
            return str(date_str).replace('-', '')
        # 尝试解析任何日期格式并转换
        try:
            dt = pd.to_datetime(date_str)
            return dt.strftime('%Y%m%d')
        except:
            # 无法处理则原样返回
            return str(date_str)
    
    def adjust_dateformat(self, date_str: str, date_target: str) -> str:
        """
        调整日期格式以匹配目标格式
        
        参数:
            date_str: 源日期字符串
            date_target: 目标日期格式示例
            
        返回:
            调整后的日期字符串
        """
        new_date_str = ""
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_target) and re.match(r'^\d{8}$', date_str):
            new_date_str = date_str[0:4] + "-" + date_str[4:6] + "-" + date_str[6:8]
        elif re.match(r'^\d{4}\d{2}\d{2}$', date_target) and re.match(r'^[\d-]{10}$', date_str):
            new_date_str = date_str[0:4] + date_str[5:7] + date_str[8:]
        else:
            new_date_str = date_str
        return new_date_str
    
    def adjust_codeformat(self, code_str: str, code_target: str) -> str:
        """
        调整股票代码格式以匹配目标格式
        
        参数:
            code_str: 源股票代码（6位数字）
            code_target: 目标格式示例
            
        返回:
            调整后的股票代码
        """
        new_code_str = ""
        # 600000.SH
        exchange = "sh"
        if len(code_str) == 6 and code_str[0:3] == "600":
            exchange = "sh"
        elif len(code_str) == 6 and code_str[0:3] == "000":
            exchange = "sz"
        elif len(code_str) == 6 and (code_str[0] == "9" or code_str[0] == "8" or code_str[0] == "4"):
            exchange = "bj"

        if len(code_target) == 9 and re.search(r'\d{6}.(SH|SZ|BJ)', code_target):
            return code_str + "." + exchange.upper()
        # SH.600000
        elif len(code_target) == 9 and re.search(r'(SH|SZ|BJ).\d{6}', code_target):
            return exchange.upper() + "." + code_str
        # sh600000
        elif len(code_target) == 8 and re.search(r'(sh|sz|bj)\d{6}', code_target):
            return exchange.lower() + code_str
        else:
            new_code_str = code_str
        return new_code_str
    
    def get_current_date(self, value_format: str = "YYYYMMDD") -> str:
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
    
    def check_params(self, params: Dict, api_doc: Optional[Dict] = None) -> Dict:
        """
        检查并调整参数格式，使其符合akshare API要求
        
        参数:
            params: 输入的参数字典
            api_doc: API文档（可选）
            
        返回:
            调整后的参数字典
        """
        if not api_doc or "params" not in api_doc:
            return params
        
        base_params = api_doc.get("params", {})
        input_params = params.copy()
        
        for key, value in base_params.items():
            if isinstance(value, str):
                # 处理日期参数
                if any(keyword in key.lower() for keyword in ["start", "begin", "from", "开始"]):
                    try:
                        from dateutil.relativedelta import relativedelta
                        # 获取上月的日期
                        now = datetime.now()
                        one_month_ago = now - relativedelta(months=1)
                        last_month_date = self.adjust_dateformat(one_month_ago.strftime('%Y-%m-%d'), value)
                    except ImportError:
                        # 如果没有dateutil，使用timedelta近似计算
                        now = datetime.now()
                        # 简单计算：减去30天作为近似值
                        one_month_ago = now - timedelta(days=30)
                        last_month_date = self.adjust_dateformat(one_month_ago.strftime('%Y-%m-%d'), value)
                    start = self.adjust_dateformat(input_params.get(key, last_month_date), value) if key in input_params else last_month_date
                    input_params[key] = start
                elif any(keyword in key.lower() for keyword in ["end", "to", "结束"]):
                    current_date = self.get_current_date(value)
                    end_date = self.adjust_dateformat(input_params.get(key, current_date), value) if key in input_params else current_date
                    input_params[key] = end_date
                # 处理股票代码参数
                elif any(keyword in key.lower() for keyword in ["symbol", "code", "股票代码"]):
                    code_str = self.adjust_codeformat(input_params.get(key, ""), value) if key in input_params else value
                    input_params[key] = code_str
            elif key not in input_params:
                input_params[key] = value
        
        return input_params
    
    def generate_code(
        self,
        api_name: str,
        api_doc: Optional[Dict] = None,
        params: Optional[Dict] = None,
        plot: bool = False
    ) -> str:
        """
        根据API文档生成akshare调用代码
        
        参数:
            api_name: akshare API名称
            api_doc: API文档字典（可选）
            params: API参数字典（可选）
            plot: 是否生成可视化代码（可选）
            
        返回:
            生成的Python代码字符串
        """
        code_lines = [
            "import akshare as ak",
            "import pandas as pd",
            "import json",
            "from datetime import date, datetime, timedelta",
            "",
            "",
            "# Format date parameters for akshare",
            "def format_date_param(date_str):",
            "    \"\"\"将日期字符串转换为akshare所需的'YYYYMMDD'格式\"\"\"",
            "    import re",
            "    if re.match(r'^\\d{8}$', str(date_str)):",
            "        return str(date_str)",
            "    elif re.match(r'^\\d{4}-\\d{2}-\\d{2}$', str(date_str)):",
            "        return str(date_str).replace('-', '')",
            "    try:",
            "        dt = pd.to_datetime(date_str)",
            "        return dt.strftime('%Y%m%d')",
            "    except:",
            "        return str(date_str)",
            "",
        ]
        
        if plot:
            code_lines.extend([
                "import plotly.graph_objects as go",
                "from plotly.subplots import make_subplots",
                ""
            ])
        
        # 判断是否为历史数据API
        is_historical_api = (
            "hist" in api_name.lower() or
            "daily" in api_name.lower() or
            (api_doc and "历史" in api_doc.get("content", "").lower())
        )
        
        # 处理参数
        if params:
            # 识别日期参数
            date_params = []
            if api_doc and api_doc.get("params"):
                for key in api_doc.get("params").keys():
                    if any(keyword in key.lower() for keyword in 
                           ["date", "日期", "time", "时间", "start", "end", "开始", "结束"]):
                        date_params.append(key)
            
            # 格式化参数（跳过内部标记参数）
            param_strs = []
            limit_count = None
            for key, value in params.items():
                # 跳过内部标记参数
                if key.startswith('_'):
                    if key == '_limit_days' and isinstance(value, str):
                        # 提取天数
                        import re
                        match = re.search(r'(\d+)日', str(value))
                        if match:
                            limit_count = int(match.group(1))
                    continue
                
                param_is_date = (
                    key in date_params or
                    any(date_keyword in key.lower() for date_keyword in
                        ["date", "time", "start", "end", "日期", "时间", "开始", "结束"])
                )
                
                if param_is_date and isinstance(value, str):
                    param_strs.append(f"{key}=format_date_param('{value}')")
                elif isinstance(value, str):
                    param_strs.append(f"{key}='{value}'")
                else:
                    param_strs.append(f"{key}={value}")
            
            param_str = ", ".join(param_strs)
            code_lines.append(f"result = ak.{api_name}({param_str})")
        else:
            code_lines.append(f"result = ak.{api_name}()")
        
        # 添加结果处理代码
        # 检查是否需要限制记录数（如"20日"数据）
        limit_count = None
        if params:
            # 检查是否有 _limit_days 标记
            if '_limit_days' in params:
                import re
                match = re.search(r'(\d+)日', str(params['_limit_days']))
                if match:
                    limit_count = int(match.group(1))
        
        code_lines.extend([
            "",
            "# Process and format the result",
            "if isinstance(result, pd.DataFrame):",
            "    if len(result) > 0:",
        ])
        
        if limit_count:
            code_lines.extend([
                f"        # 取最近 {limit_count} 条记录（最近 {limit_count} 个交易日）",
                f"        result = result.tail({limit_count})",
            ])
        
        code_lines.extend([
            "        result_dict = result.to_dict(orient='records')",
            f"        print(f'获取到 {{len(result)}} 条记录')",
            "        print(result.head())",
            "    else:",
            "        print('未获取到数据')",
            "else:",
            "    print(f'结果类型: {{type(result)}}')",
            "    print(result)",
        ])
        
        return "\n".join(code_lines)
    
    def detect_function(self, markdown_content: str) -> Optional[Dict[str, Any]]:
        """
        从Markdown内容中检测是否需要使用akshare函数
        
        参数:
            markdown_content: Markdown内容
            
        返回:
            如果检测到需要akshare，返回包含API名称和参数的字典；否则返回None
        """
        # 检测关键词
        akshare_keywords = [
            "股票", "行情", "历史数据", "实时数据", "财务数据", 
            "akshare", "ak.", "股票代码", "市值", "ROE"
        ]
        
        content_lower = markdown_content.lower()
        
        # 检查是否包含akshare相关关键词
        has_keywords = any(keyword in content_lower for keyword in akshare_keywords)
        
        if not has_keywords:
            return None
        
        # 尝试提取可能的API名称和参数
        detected_info = {
            "use_akshare": True,
            "api_name": None,  # 需要进一步分析或由LLM确定
            "params": {}
        }
        
        # 检测股票代码
        code_pattern = r'[0-9]{6}'
        codes = re.findall(code_pattern, markdown_content)
        if codes:
            detected_info["params"]["symbol"] = codes[0]
        
        # 检测日期范围
        date_pattern = r'\d{4}[-/]\d{2}[-/]\d{2}|\d{8}'
        dates = re.findall(date_pattern, markdown_content)
        if len(dates) >= 2:
            detected_info["params"]["start_date"] = dates[0]
            detected_info["params"]["end_date"] = dates[1]
        elif len(dates) == 1:
            detected_info["params"]["end_date"] = dates[0]
        
        return detected_info
    
    def convert_to_quantus(self, ak_data: Union[pd.DataFrame, Dict[str, Any]]) -> pd.DataFrame:
        """
        将akshare数据转换为quantus_dict格式
        
        参数:
            ak_data: akshare返回的数据 (DataFrame或dict)
            
        返回:
            转换后的DataFrame (quantus_dict格式)
        """
        return ak_dict_to_quantus_dict(ak_data)
