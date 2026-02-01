"""
使用 qdata 库的核心功能生成代码
1. keyword 查询方式生成 trend_line_keyword.py
2. MCP 方式（AI tool calling）生成 trend_line_keyword_mcp.py

这两个 demo 用于验证 qdata 库对于 md 转 code 的准确性
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加 QData 到路径
current_dir = Path(__file__).parent
# 从 examples/demo_trend_line 到 AIQuant/QData
qdata_dir = current_dir.parent.parent
sys.path.insert(0, str(qdata_dir.parent))

from QData.core.manager import get_api_manager
from QData.core.selector import select_api_by_keyword, APISelector
from QData.providers.akshare import AkshareProvider


def read_markdown(file_path: str) -> str:
    """读取 markdown 文件内容"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def generate_keyword_code(markdown_content: str, output_file: str):
    """
    使用 keyword 查询方式生成代码
    
    参数:
        markdown_content: markdown 文件内容
        output_file: 输出文件路径
    """
    print(f"\n=== 使用 Keyword 查询方式 ===")
    print(f"查询内容: {markdown_content}")
    
    # 使用 keyword 搜索 API
    keyword_results = select_api_by_keyword(markdown_content, provider="akshare")
    
    if not keyword_results:
        print("未找到匹配的 API")
        return
    
    # 选择第一个结果
    api_result = keyword_results[0]
    api_name = api_result['api_name']
    print(f"找到 API: {api_name}")
    print(f"描述: {api_result.get('description', '')}")
    
    # 获取 API 文档
    manager = get_api_manager(provider="akshare")
    api_doc = manager.find_api_documentation(api_name)
    
    if not api_doc:
        print(f"未找到 API 文档: {api_name}")
        return
    
    # 从 markdown 内容中提取参数
    import re
    params = {}
    
    # 提取股票代码
    code_match = re.search(r'(\d{6})', markdown_content)
    if code_match:
        params['symbol'] = code_match.group(1)
    
    # 提取日期相关参数（如果有）
    if '20日' in markdown_content or ('20' in markdown_content and '日' in markdown_content):
        # 计算最近20个交易日的数据
        # 由于无法直接获取交易日历，使用约30个自然日来覆盖20个交易日（考虑周末和节假日）
        from datetime import datetime, timedelta
        end_date = datetime.now()
        # 30个自然日大约包含20个交易日（按5个交易日/周计算）
        start_date = end_date - timedelta(days=30)
        params['start_date'] = start_date.strftime('%Y%m%d')
        params['end_date'] = end_date.strftime('%Y%m%d')
        params['period'] = 'daily'
        params['_limit_days'] = '20日'  # 标记需要限制为20条记录
    
    # 如果没有参数，使用 API 文档中的默认参数
    if not params and api_doc.get('params'):
        params = api_doc.get('params', {}).copy()
    
    # 生成代码
    provider = AkshareProvider()
    code = provider.generate_code(
        api_name=api_name,
        api_doc=api_doc,
        params=params
    )
    
    # 添加注释说明
    header = f'''"""
使用 Keyword 查询方式生成的代码
查询内容: {markdown_content}
找到的 API: {api_name}
"""
'''
    
    full_code = header + code
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_code)
    
    print(f"代码已生成: {output_file}")


async def generate_mcp_code_async(markdown_content: str, output_file: str):
    """
    使用 AI tool calling 方式生成代码（MCP方式）
    通过 AI 接口来判断最合适的取数接口，然后输出代码
    
    参数:
        markdown_content: markdown 文件内容
        output_file: 输出文件路径
    """
    print(f"\n=== 使用 AI Tool Calling 方式 (MCP) ===")
    print(f"查询内容: {markdown_content}")
    
    # 使用 AI tool calling 选择最合适的 API
    selector = APISelector(provider="akshare")
    api_result = await selector.select_api_by_tool_calling(markdown_content)
    
    if not api_result:
        print("AI 未找到合适的 API，回退到 keyword 搜索")
        # 回退到 keyword 搜索
        keyword_results = select_api_by_keyword(markdown_content, provider="akshare")
        if not keyword_results:
            print("未找到匹配的 API")
            return
        
        api_result = {
            "api_name": keyword_results[0]['api_name'],
            "reason": "Keyword搜索匹配（AI tool calling 失败）",
            "suggested_params": {}
        }
    
    api_name = api_result['api_name']
    print(f"AI 选择的 API: {api_name}")
    print(f"选择理由: {api_result.get('reason', '')}")
    
    # 获取 API 文档
    manager = get_api_manager(provider="akshare")
    api_doc = manager.find_api_documentation(api_name)
    
    if not api_doc:
        print(f"未找到 API 文档: {api_name}")
        return
    
    # 获取 AI 建议的参数
    params = api_result.get('suggested_params', {})
    
    # 使用 provider 的 detect_function 分析 markdown（作为补充）
    provider = AkshareProvider()
    detected_info = provider.detect_function(markdown_content)
    
    # 合并参数：优先使用 AI 建议的参数，然后补充 detect_function 的结果
    if detected_info and detected_info.get('params'):
        for key, value in detected_info['params'].items():
            if key not in params:
                params[key] = value
    
    # 从 markdown 内容中提取参数（作为最后补充）
    import re
    # 提取股票代码（如果 AI 没有提供）
    if 'symbol' not in params and 'code' not in params:
        code_match = re.search(r'(\d{6})', markdown_content)
        if code_match:
            params['symbol'] = code_match.group(1)
    
    # 提取日期相关参数（如果 AI 没有提供）
    if 'start_date' not in params and 'end_date' not in params:
        if '20日' in markdown_content or ('20' in markdown_content and '日' in markdown_content):
            # 计算最近20个交易日的数据
            # 由于无法直接获取交易日历，使用约30个自然日来覆盖20个交易日（考虑周末和节假日）
            from datetime import datetime, timedelta
            end_date = datetime.now()
            # 30个自然日大约包含20个交易日（按5个交易日/周计算）
            start_date = end_date - timedelta(days=30)
            params['start_date'] = start_date.strftime('%Y%m%d')
            params['end_date'] = end_date.strftime('%Y%m%d')
            params['period'] = 'daily'
            params['_limit_days'] = '20日'  # 标记需要限制为20条记录
    
    # 使用 generate_code 生成代码
    code = provider.generate_code(
        api_name=api_name,
        api_doc=api_doc,
        params=params
    )
    
    # 添加注释说明
    header = f'''"""
使用 AI Tool Calling 方式生成的代码 (MCP)
查询内容: {markdown_content}
AI 选择的 API: {api_name}
选择理由: {api_result.get('reason', '')}
AI 建议的参数: {api_result.get('suggested_params', {})}
检测到的信息: {detected_info}
"""
'''
    
    full_code = header + code
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_code)
    
    print(f"代码已生成: {output_file}")


def generate_mcp_code(markdown_content: str, output_file: str):
    """同步包装函数"""
    asyncio.run(generate_mcp_code_async(markdown_content, output_file))


def main():
    """主函数"""
    # 获取当前目录
    current_dir = Path(__file__).parent
    
    # 读取 markdown 文件
    md_file = current_dir / "trend_line.md"
    if not md_file.exists():
        print(f"错误: 找不到文件 {md_file}")
        return
    
    markdown_content = read_markdown(str(md_file))
    print(f"读取 markdown 内容: {markdown_content}")
    
    # 生成 keyword 方式代码
    keyword_file = current_dir / "trend_line_keyword.py"
    generate_keyword_code(markdown_content, str(keyword_file))
    
    # 生成 MCP 方式代码
    mcp_file = current_dir / "trend_line_keyword_mcp.py"
    generate_mcp_code(markdown_content, str(mcp_file))
    
    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
