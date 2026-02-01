"""
API资源管理器
支持多数据源（akshare、jqdata、tushare）的API文档管理
"""
import os
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class APIManager:
    """API资源管理器，支持多数据源"""
    
    def __init__(self, provider: str = "akshare", resource_dir: Optional[str] = None):
        """
        初始化API管理器
        
        参数:
            provider: 数据源名称 ('akshare', 'jqdata', 'tushare')
            resource_dir: 资源目录路径，如果为None则使用默认路径
        """
        self.provider = provider.lower()
        
        if resource_dir is None:
            # 使用qdata目录下的资源
            current_file = Path(__file__)
            QData_root = current_file.parent.parent
            self.resource_dir = QData_root / "datalib" / self.provider / "stockapi"
            
            # 如果不存在，尝试查找其他位置
            if not self.resource_dir.exists():
                # 尝试OpenManus-AutoQuant的资源目录
                project_root = current_file.parent.parent.parent.parent
                openmanus_dir = project_root / "OpenManus-AutoQuant"
                if openmanus_dir.exists() and self.provider == "akshare":
                    self.resource_dir = openmanus_dir / "app" / "resource" / "stockapi"
        else:
            self.resource_dir = Path(resource_dir)
        
        if not self.resource_dir.exists():
            logger.warning(f"资源目录不存在: {self.resource_dir}")
            # 创建目录
            self.resource_dir.mkdir(parents=True, exist_ok=True)
    
    def find_api_documentation(self, api_name: str) -> Optional[Dict[str, Any]]:
        """
        查找指定API的详细文档
        
        参数:
            api_name: API名称，例如 'stock_zh_a_hist'
            
        返回:
            包含API文档的字典，如果未找到则返回None
        """
        if not self.resource_dir.exists():
            logger.error(f"资源目录不存在: {self.resource_dir}")
            return None
        
        # 尝试查找所有可能的文档位置
        potential_files = []
        
        # 直接搜索文件，寻找潜在文件列表
        try:
            for file in os.listdir(self.resource_dir):
                file_path = self.resource_dir / file
                if file_path.is_file() and file.endswith('.md'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if f"接口: {api_name}" in content:
                                potential_files.append(file_path)
                    except Exception as e:
                        logger.warning(f"读取文件失败 {file_path}: {e}")
                        continue
        except Exception as e:
            logger.error(f"遍历资源目录失败: {e}")
            return None
        
        if not potential_files:
            logger.warning(f"API '{api_name}' 文档未找到 (provider: {self.provider})")
            return None
        
        # 使用第一个匹配的文件
        file_path = potential_files[0]
        
        # 一个接口文件里可能有多个接口，比如 A股-历史行情数据.md
        # 接口描述范围: 开始：'##### ' 结束: ''
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content_all = f.read()
                content_list = content_all.split("##### ")
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return None
        
        # 查找文档内容
        content = ""
        for item in content_list:
            if api_name in item:
                content = item
                break
        
        params_input_section = ""
        params_output_section = ""
        # param_mode: 11, 作为params_input
        # param_mode: 21, 作为params_output
        param_mode = 0
        if content != "":
            lines = content.split('\n')
            header_found = False
            for i, line in enumerate(lines):
                header_found = True
                # 向后查找参数部分
                if param_mode == 11 and len(lines[i]) >= 1 and lines[i][0] == "|":
                    # 继续向后查找，直到下一个接口或文档结束
                    params_input_section += lines[i] + "\n"
                elif param_mode == 21 and len(lines[i]) >= 1 and lines[i][0] == "|":
                    # 继续向后查找，直到下一个接口或文档结束
                    params_output_section += lines[i] + "\n"
                elif "输入参数" in lines[i]:
                    param_mode = 10
                elif "输出参数" in lines[i]:
                    param_mode = 20
                elif "|-" in lines[i]:
                    param_mode += 1
            
            params_input_api_doc = self._parse_params_from_text(params_input_section)
            
            if header_found:
                return {
                    "name": api_name,
                    "provider": self.provider,
                    "file_path": str(file_path),
                    "content": content,
                    "params": params_input_api_doc
                }
        
        return None
    
    def _parse_params_from_text(self, params_text: str) -> Dict[str, Any]:
        """
        从参数文本中解析参数
        
        参数:
            params_text: 参数文本（markdown表格格式）
            
        返回:
            参数字典
        """
        dict1 = {}
        if not params_text:
            return dict1
        
        list1 = params_text.split("\n")
        # 过滤数组空值
        filtered_arr = [x for x in list1 if x is not None and x != '']
        
        for line in filtered_arr:
            # 跳过表头分隔行
            if "|-" in line or line.strip().startswith("|--"):
                continue
            
            # 解析表格行: | 名称 | 类型 | 描述 |
            line_list = [x.strip() for x in line.split("|") if x.strip()]
            if len(line_list) >= 2:
                key = line_list[0]
                # 尝试从描述中提取示例值
                example = ""
                if len(line_list) >= 3:
                    example = line_list[2]
                
                # 尝试从示例中提取默认值
                value = ""
                if "=" in example:
                    try:
                        # 提取类似 symbol='603777' 的值
                        match = re.search(r"(\w+)='([^']+)'", example)
                        if match:
                            value = match.group(2)
                        else:
                            # 尝试提取类似 symbol="603777" 的值
                            match = re.search(r'(\w+)="([^"]+)"', example)
                            if match:
                                value = match.group(2)
                    except:
                        pass
                
                dict1[key] = value if value else ""
        
        return dict1
    
    def list_available_apis(self) -> List[str]:
        """
        列出所有可用的API名称
        
        返回:
            API名称列表
        """
        api_names = []
        
        if not self.resource_dir.exists():
            return api_names
        
        try:
            for file in os.listdir(self.resource_dir):
                file_path = self.resource_dir / file
                if file_path.is_file() and file.endswith('.md'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 查找所有接口定义
                            matches = re.findall(r'接口:\s*(\w+)', content)
                            api_names.extend(matches)
                    except Exception as e:
                        logger.warning(f"读取文件失败 {file_path}: {e}")
                        continue
        except Exception as e:
            logger.error(f"遍历资源目录失败: {e}")
        
        # 去重并排序
        return sorted(list(set(api_names)))
    
    def search_apis_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        根据关键词搜索API
        
        参数:
            keyword: 搜索关键词
            
        返回:
            API信息列表
        """
        results = []
        
        if not self.resource_dir.exists():
            return results
        
        try:
            for file in os.listdir(self.resource_dir):
                file_path = self.resource_dir / file
                if file_path.is_file() and file.endswith('.md'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 查找所有接口定义
                            matches = re.findall(r'接口:\s*(\w+)', content)
                            for api_name in matches:
                                # 检查是否包含关键词
                                if keyword.lower() in api_name.lower() or keyword.lower() in content.lower():
                                    api_doc = self.find_api_documentation(api_name)
                                    if api_doc:
                                        results.append({
                                            "api_name": api_name,
                                            "provider": self.provider,
                                            "file": file,
                                            "description": self._extract_description(content, api_name)
                                        })
                    except Exception as e:
                        logger.warning(f"读取文件失败 {file_path}: {e}")
                        continue
        except Exception as e:
            logger.error(f"遍历资源目录失败: {e}")
        
        return results
    
    def _extract_description(self, content: str, api_name: str) -> str:
        """提取API描述"""
        # 查找接口描述
        pattern = rf'接口:\s*{api_name}.*?描述:\s*([^\n]+)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""


# 全局实例缓存
_api_managers: Dict[str, APIManager] = {}


def get_api_manager(provider: str = "akshare") -> APIManager:
    """
    获取全局APIManager实例
    
    参数:
        provider: 数据源名称 ('akshare', 'jqdata', 'tushare')
        
    返回:
        APIManager实例
    """
    provider = provider.lower()
    if provider not in _api_managers:
        _api_managers[provider] = APIManager(provider=provider)
    return _api_managers[provider]
