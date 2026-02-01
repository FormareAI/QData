# QData - 量化数据统一接口库

## 概述

QData 是一个专门针对量化数据源的统一接口库，支持通过自然语言方式找到对应的数据接口。支持 akshare、jqdata、tushare 等多种数据源。

## 目录结构

```
qdata/
├── __init__.py              # 统一入口
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── manager.py          # API资源管理器
│   ├── selector.py         # AI智能选择器
│   └── mapper.py           # 数据字典转换器
├── providers/               # 数据源提供者
│   ├── __init__.py
│   ├── akshare.py          # Akshare提供者
│   ├── jqdata.py           # JQData提供者
│   └── tushare.py          # Tushare提供者
├── utils/                   # 工具函数
│   ├── __init__.py
│   └── helpers.py          # 辅助函数
├── akshare/                 # Akshare资源
│   ├── api_overview.md
│   └── stockapi/           # API文档
├── jqdata/                  # JQData资源
├── tushare/                 # Tushare资源
└── docs/                    # 文档
```

## 核心功能

### 1. API资源管理 (core/manager.py)

管理多数据源的API文档，支持查找、搜索等功能。

```python
from QData.core.manager import get_api_manager

# 获取akshare API管理器
manager = get_api_manager(provider="akshare")

# 查找API文档
api_doc = manager.find_api_documentation("stock_zh_a_hist")

# 搜索API
results = manager.search_apis_by_keyword("历史行情")

# 列出所有API
apis = manager.list_available_apis()
```

### 2. AI智能选择 (core/selector.py)

通过AI tool calling方式智能选择最合适的API。

```python
from QData.core.selector import APISelector

# 创建选择器
selector = APISelector(provider="akshare")

# 通过AI选择API
result = await selector.select_api_by_tool_calling("获取600000的20日close数据")

if result:
    print(f"选择的API: {result['api_name']}")
    print(f"选择理由: {result['reason']}")
    print(f"建议参数: {result['suggested_params']}")
```

### 3. 数据字典转换 (core/mapper.py)

将不同数据源的数据格式统一转换为 quantus_dict 格式。

```python
from QData.core.mapper import to_quantus_dict, ak_dict_to_quantus_dict

# 通用转换
quantus_data = to_quantus_dict(data, source="akshare")

# 特定数据源转换
quantus_data = ak_dict_to_quantus_dict(ak_data)
```

### 4. 数据源提供者 (providers/)

为每个数据源提供专门的接口和工具函数。

```python
from QData.providers.akshare import AkshareProvider

provider = AkshareProvider()

# 检测是否需要使用akshare
info = provider.detect_function(markdown_content)

# 转换为quantus格式
quantus_data = provider.convert_to_quantus(ak_data)

# 生成代码
code = provider.generate_code(api_name, api_doc, params)
```

## 使用示例

### 示例1: 通过自然语言查找API

```python
from QData import APISelector, get_api_manager

# 方式1: 使用AI智能选择
selector = APISelector(provider="akshare")
result = await selector.select_api_by_tool_calling("获取600000的20日close数据")

# 方式2: 使用关键词搜索
manager = get_api_manager(provider="akshare")
results = manager.search_apis_by_keyword("历史行情")
```

### 示例2: 获取数据并转换

```python
import akshare as ak
from QData.core.mapper import ak_dict_to_quantus_dict

# 获取akshare数据
ak_data = ak.stock_zh_a_hist(
    symbol="600000",
    period="daily",
    start_date="20250101",
    end_date="20250131"
)

# 转换为统一格式
data = ak_dict_to_quantus_dict(ak_data)

# 提取close数据
close_data = data[['date', 'code', 'close']].tail(20)
print(close_data)
```

### 示例3: 多数据源支持

```python
from QData import get_api_manager, to_quantus_dict

# 支持多个数据源
providers = ["akshare", "jqdata", "tushare"]

for provider in providers:
    manager = get_api_manager(provider=provider)
    apis = manager.list_available_apis()
    print(f"{provider}: {len(apis)} 个API")
```

## 数据源支持

### Akshare

- **资源目录**: `qdata/akshare/stockapi/`
- **API文档**: Markdown格式
- **数据格式**: 支持转换为 quantus_dict

### JQData

- **资源目录**: `qdata/jqdata/`
- **API文档**: 待完善
- **数据格式**: 支持转换为 quantus_dict

### Tushare

- **资源目录**: `qdata/tushare/`
- **API文档**: 待完善
- **数据格式**: 支持转换为 quantus_dict

## Quantus统一数据字典格式

所有数据源的数据都会转换为统一的 quantus_dict 格式：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| date | str | 交易日期 (YYYY-MM-DD) |
| code | str | 股票代码 (000001.XSHE格式) |
| open | float | 开盘价 |
| close | float | 收盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| volume | float | 成交量 (股) |
| amount | float | 成交额 (元) |
| pct_change | float | 涨跌幅 (%) |
| change | float | 涨跌额 (元) |

## 迁移指南

### 从旧版本迁移

旧代码：
```python
from utils.stockapi_manager import get_stockapi_manager
from utils.data_dict_mapper import ak_dict_to_quantus_dict
```

新代码：
```python
from QData.core.manager import get_api_manager
from QData.core.mapper import ak_dict_to_quantus_dict

# 获取管理器（需要指定provider）
manager = get_api_manager(provider="akshare")
```

### 向后兼容

为了保持向后兼容，`utils` 模块中的旧导入仍然可用，但会重定向到 `qdata`：

```python
# 旧代码仍然可以工作
from utils.data_dict_mapper import ak_dict_to_quantus_dict
```

## 最佳实践

1. **优先使用qdata统一接口**
   - 使用 `qdata.core.manager` 管理API
   - 使用 `qdata.core.mapper` 转换数据
   - 使用 `qdata.providers` 获取数据源特定功能

2. **根据场景选择数据源**
   - akshare: 免费，数据丰富
   - jqdata: 需要账号，数据质量高
   - tushare: 需要积分，专业数据

3. **使用统一数据格式**
   - 所有数据转换为 quantus_dict 格式
   - 便于后续处理和计算

4. **智能选择API**
   - 简单场景使用关键词搜索
   - 复杂场景使用AI tool calling

## 测试

运行测试文件：

```bash
cd AIQuant
python ttt/test_ai_stockapi.py
```

测试内容包括：
- API文档查找
- API列表和搜索
- AI智能选择
- 数据获取和转换
- 多数据源支持
