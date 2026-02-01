# 关键参数识别、金融专门 Tool Call 及 QData 核心库功能定位分析

## 文档信息

- **创建日期**: 2026-02-01
- **版本**: 2.0
- **目的**: 分析关键参数识别、金融专门 tool calling 以及 qdata 核心库的功能定位和职责划分
- **更新**: 添加业务知识库、标准化工具接入和整体业务框架设计
- **核心问题**:
  1. 如何将业务知识作为训练集，参考 Cursor 训练代码的方式，作为新的 tool_call 或 knowledge base
  2. 如何接入更多的标准化工具，能够更好的做好工具调用
  3. 整体的业务框架，结合分层识别框架
  4. 如何从大段 md 文本中提取关键词，转换成 API 或 tool_call，与业务知识库对接

---

## 1. 关键参数识别的位置分析

### 1.1 当前实现现状

#### 1.1.1 Demo 文件中的参数识别 (`*_demo.py`)

**位置**: `QData/examples/demo_*/py_ai_m2c_*_demo.py`

**当前实现**:
```python
# 从 markdown 内容中提取参数
import re
params = {}

# 提取股票代码
code_match = re.search(r'(\d{6})', markdown_content)
if code_match:
    params['symbol'] = code_match.group(1)

# 提取日期相关参数
if '20日' in markdown_content or ('20' in markdown_content and '日' in markdown_content):
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    params['start_date'] = start_date.strftime('%Y%m%d')
    params['end_date'] = end_date.strftime('%Y%m%d')
    params['period'] = 'daily'
    params['_limit_days'] = '20日'
```

**特点**:
- ✅ 简单直接，使用正则表达式提取
- ✅ 快速响应，无外部依赖
- ❌ 逻辑简单，无法处理复杂场景
- ❌ 硬编码规则，扩展性差
- ❌ 无法理解语义（如"最近20个交易日"）

#### 1.1.2 Tool Calling 中的参数识别

**位置**: `QData/qdata/core/selector.py` - `APISelector.select_api_by_tool_calling()`

**当前实现**:
```python
# AI tool calling 选择 API 时，会返回 suggested_params
result = {
    "api_name": api_name,
    "provider": self.provider,
    "reason": reason,
    "api_doc": api_doc,
    "suggested_params": {k: v for k, v in arguments.items() if k not in ['api_name', 'reason']}
}
```

**特点**:
- ✅ 智能理解用户意图
- ✅ 可以处理复杂语义
- ✅ 能够理解金融术语
- ❌ 依赖 AI 服务，有成本
- ❌ 响应时间较长
- ❌ 结果可能不稳定

#### 1.1.3 QData 库中的参数识别

**位置**: `QData/qdata/providers/akshare.py` - `AkshareProvider.detect_function()`

**当前实现**:
```python
def detect_function(self, markdown_content: str) -> Optional[Dict[str, Any]]:
    # 检测关键词
    akshare_keywords = ["股票", "行情", "历史数据", ...]
    
    # 检测股票代码
    code_pattern = r'[0-9]{6}'
    codes = re.findall(code_pattern, markdown_content)
    if codes:
        detected_info["params"]["symbol"] = codes[0]
    
    # 检测日期范围
    date_pattern = r'\d{4}[-/]\d{2}[-/]\d{2}|\d{8}'
    dates = re.findall(date_pattern, markdown_content)
    ...
```

**特点**:
- ✅ 数据源特定的识别逻辑
- ✅ 可复用，封装在库中
- ✅ 支持多种数据源
- ❌ 仍然是基于规则的简单匹配
- ❌ 无法处理复杂金融指标

### 1.2 问题分析

#### 问题 1: 职责不清晰

当前参数识别逻辑分散在三个地方：
- **Demo 文件**: 简单的正则提取
- **Tool Calling**: AI 智能提取（但主要用于 API 选择）
- **QData 库**: 数据源特定的检测

**问题**: 
- 没有统一的参数识别入口
- 逻辑重复，维护困难
- 无法保证一致性

#### 问题 2: 金融指标识别不足

当前实现无法准确识别和处理金融指标，例如：
- "20个交易日" vs "20个自然日"
- "最近一个月" vs "最近30个交易日"
- "MA5" (5日均线)
- "RSI(14)" (14日相对强弱指标)
- "成交量放大" (需要计算和比较)

**问题**:
- 简单的字符串匹配无法理解金融术语
- 无法区分交易日和自然日
- 无法处理技术指标

### 1.3 建议方案

#### 方案 A: 分层识别架构（1-2个月实施版本）

```
┌─────────────────────────────────────┐
│   Demo 层 (应用层)                    │
│   - 读取 markdown                    │
│   - 调用 QDataProcessor              │
│   - 生成最终代码                      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   QData 核心库 (业务逻辑层)           │
│   ├── TextParser (文本解析)          │
│   ├── KnowledgeBase (知识库)         │
│   ├── ParamMerger (参数整合)         │
│   └── CodeGenerator (代码生成)       │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Tool Calling (智能增强层)          │
│   ├── API 选择 Tool                   │
│   ├── 金融参数解析 Tool               │
│   └── 标准化工具注册表                │
└─────────────────────────────────────┘
```

**职责划分**:
1. **Demo 层**: 只负责调用和组装，不包含业务逻辑
2. **QData 核心库**: 提供统一的参数识别接口，封装金融指标处理
3. **Tool Calling**: 作为智能增强层，处理复杂语义理解

**1-2个月实施重点**:
- ✅ 建立基础知识库（JSON格式，无需向量数据库）
- ✅ 实现统一的 `QDataProcessor` 接口
- ✅ 集成知识库到 Tool Calling
- ✅ 简化 Demo 层，移除业务逻辑
- ⏳ 向量搜索和 RAG 增强（可选，后续阶段）

---

## 2. 金融专门 Tool Call 的必要性分析

### 2.1 当前 Tool Calling 的局限性

#### 2.1.1 通用 Tool Calling

**当前实现**: `APISelector.select_api_by_tool_calling()`

**功能**:
- 从候选 API 中选择最合适的
- 返回 API 名称和基本参数
- 提供选择理由

**局限性**:
- ❌ 无法理解金融术语（如"20个交易日"）
- ❌ 无法计算金融指标（如技术指标、交易日历）
- ❌ 参数建议不够精确（如日期范围计算）

#### 2.1.2 实际案例

**用户需求**: "获取600000的20日close数据"

**当前处理**:
1. Tool Calling 选择 API: `stock_zh_a_hist` ✅
2. 参数识别: 
   - `symbol`: "600000" ✅ (简单提取)
   - `start_date`: 30天前 ❌ (硬编码，不准确)
   - `end_date`: 今天 ✅
   - `_limit_days`: "20日" ✅ (标记，但需要后续处理)

**问题**:
- "20日" 被理解为 20 个自然日，而不是 20 个交易日
- 日期范围计算不准确（30天可能包含更多或更少的交易日）
- 需要额外的 `tail(20)` 来限制记录数

### 2.2 金融专门 Tool Call 的设计

#### 2.2.1 金融参数解析 Tool

**功能**: 专门解析金融相关的参数和指标

**Tool 定义**:
```python
{
    "type": "function",
    "function": {
        "name": "parse_financial_params",
        "description": "解析金融查询中的参数，包括股票代码、日期范围、技术指标等",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码（6位数字）"
                },
                "date_range": {
                    "type": "object",
                    "description": "日期范围",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["trading_days", "calendar_days", "date_range"],
                            "description": "日期类型：交易日、自然日或具体日期范围"
                        },
                        "value": {
                            "type": "integer",
                            "description": "天数或日期"
                        },
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"}
                    }
                },
                "indicators": {
                    "type": "array",
                    "description": "技术指标列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "period": {"type": "integer"}
                        }
                    }
                }
            }
        }
    }
}
```

#### 2.2.2 交易日历 Tool

**功能**: 计算交易日相关的日期

**Tool 定义**:
```python
{
    "type": "function",
    "function": {
        "name": "calculate_trading_days",
        "description": "计算交易日相关的日期范围",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "交易日数量"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期（可选，默认为今天）"
                },
                "market": {
                    "type": "string",
                    "enum": ["A股", "港股", "美股"],
                    "description": "市场类型"
                }
            },
            "required": ["days"]
        }
    }
}
```

**实现方式**:
- 可以调用交易日历 API（如 tushare、jqdata）
- 或者使用本地交易日历数据
- 返回准确的开始和结束日期

#### 2.2.3 技术指标识别 Tool

**功能**: 识别和解析技术指标

**Tool 定义**:
```python
{
    "type": "function",
    "function": {
        "name": "parse_technical_indicators",
        "description": "识别和解析技术指标",
        "parameters": {
            "type": "object",
            "properties": {
                "indicators": {
                    "type": "array",
                    "description": "技术指标列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "enum": ["MA", "EMA", "RSI", "MACD", "KDJ", "BOLL"],
                                "description": "指标名称"
                            },
                            "period": {"type": "integer"},
                            "params": {"type": "object"}
                        }
                    }
                }
            }
        }
    }
}
```

### 2.3 是否需要专门的金融 Tool Call？

#### 结论: **需要，但应该作为增强层**

**理由**:

1. **金融术语的复杂性**
   - "20个交易日" vs "20个自然日" 有本质区别
   - 需要交易日历支持
   - 技术指标需要专业解析

2. **提高准确性**
   - 当前硬编码的日期计算不准确
   - AI 可以理解语义，但需要专门的工具来执行

3. **可扩展性**
   - 未来可能需要支持更多金融指标
   - 专门的 Tool 便于维护和扩展

**建议架构**:
```
用户查询
    ↓
通用 Tool Calling (API 选择)
    ↓
金融专门 Tool Calling (参数解析)
    ├── 交易日历计算
    ├── 技术指标识别
    └── 金融参数验证
    ↓
QData 库 (参数整合和代码生成)
```

---

## 3. 业务知识库与 Tool Call 集成方案

### 3.1 业务知识库设计

#### 3.1.1 知识库结构

**位置**: `QData/qdata/knowledge/`

**目录结构**:
```
knowledge/
├── __init__.py
├── financial_terms.json      # 金融术语知识库
├── indicators.json           # 技术指标知识库
├── date_patterns.json        # 日期模式知识库
├── api_mappings.json         # API 映射知识库
└── examples/                 # 示例和训练数据
    ├── trading_days_examples.json
    ├── indicator_examples.json
    └── param_extraction_examples.json
```

#### 3.1.2 金融术语知识库 (`financial_terms.json`)

```json
{
    "trading_days": {
        "20个交易日": {
            "type": "trading_days",
            "value": 20,
            "description": "最近20个交易日的数据",
            "tool_call": "calculate_trading_days",
            "formula": "从当前日期往前推，排除周末和节假日，取最近20个交易日",
            "implementation": "tool_trade_days(days=20, market='A股')",
            "code_template": "result = result.tail(20)  # 取最近20个交易日"
        },
        "最近30个交易日": {
            "type": "trading_days",
            "value": 30,
            "description": "最近30个交易日的数据",
            "tool_call": "calculate_trading_days",
            "formula": "从当前日期往前推，排除周末和节假日，取最近30个交易日",
            "implementation": "tool_trade_days(days=30, market='A股')"
        }
    },
    "calendar_days": {
        "20个自然日": {
            "type": "calendar_days",
            "value": 20,
            "description": "最近20个自然日的数据",
            "formula": "从当前日期往前推20天（包括周末和节假日）",
            "implementation": "datetime.now() - timedelta(days=20)"
        },
        "最近一个月": {
            "type": "calendar_days",
            "value": 30,
            "description": "最近30个自然日的数据",
            "formula": "从当前日期往前推30天",
            "implementation": "datetime.now() - timedelta(days=30)"
        }
    }
}
```

#### 3.1.3 技术指标知识库 (`indicators.json`)

```json
{
    "MA": {
        "name": "MA",
        "full_name": "移动平均线 (Moving Average)",
        "description": "计算指定周期的移动平均线",
        "formula": "MA(n) = (close[0] + close[-1] + ... + close[-(n-1)]) / n",
        "tool_call": "calculate_ma",
        "implementation": {
            "python": "data['MA{n}'] = data['close'].rolling(window={n}).mean()",
            "steps": [
                "1. 获取最近n天的close数据",
                "2. 计算平均值: ma{n} = average(close[-{n}:0])",
                "3. 添加到数据列中"
            ]
        },
        "examples": {
            "MA5": {
                "period": 5,
                "description": "5日均线",
                "code": "data['MA5'] = data['close'].rolling(window=5).mean()"
            },
            "MA20": {
                "period": 20,
                "description": "20日均线",
                "code": "data['MA20'] = data['close'].rolling(window=20).mean()"
            }
        }
    },
    "RSI": {
        "name": "RSI",
        "full_name": "相对强弱指标 (Relative Strength Index)",
        "description": "计算RSI指标，用于判断超买超卖",
        "formula": "RSI(n) = 100 - (100 / (1 + RS))，其中 RS = 平均涨幅 / 平均跌幅",
        "tool_call": "calculate_rsi",
        "implementation": {
            "python": "def calculate_rsi(data, period=14):\n    delta = data['close'].diff()\n    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()\n    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()\n    rs = gain / loss\n    rsi = 100 - (100 / (1 + rs))\n    return rsi",
            "steps": [
                "1. 计算价格变化: delta = close.diff()",
                "2. 分离涨幅和跌幅",
                "3. 计算平均涨幅和平均跌幅",
                "4. 计算RS = 平均涨幅 / 平均跌幅",
                "5. 计算RSI = 100 - (100 / (1 + RS))"
            ]
        },
        "examples": {
            "RSI(14)": {
                "period": 14,
                "description": "14日相对强弱指标",
                "code": "data['RSI14'] = calculate_rsi(data, period=14)"
            }
        }
    },
    "volume_amplification": {
        "name": "成交量放大",
        "description": "判断成交量是否放大",
        "formula": "当前成交量 > 平均成交量 * 倍数",
        "tool_call": "detect_volume_amplification",
        "implementation": {
            "python": "avg_volume = data['volume'].rolling(window=20).mean()\ncurrent_volume = data['volume'].iloc[-1]\namplification = current_volume > avg_volume * 1.5",
            "steps": [
                "1. 计算最近n天的平均成交量",
                "2. 获取当前成交量",
                "3. 比较: 当前成交量 > 平均成交量 * 倍数（如1.5倍）"
            ]
        }
    }
}
```

#### 3.1.4 日期模式知识库 (`date_patterns.json`)

```json
{
    "patterns": [
        {
            "pattern": "最近(\\d+)个交易日",
            "regex": "最近(\\d+)个交易日",
            "type": "trading_days",
            "tool_call": "calculate_trading_days",
            "example": "最近20个交易日"
        },
        {
            "pattern": "(\\d+)个交易日",
            "regex": "(\\d+)个交易日",
            "type": "trading_days",
            "tool_call": "calculate_trading_days",
            "example": "20个交易日"
        },
        {
            "pattern": "最近(\\d+)个自然日",
            "regex": "最近(\\d+)个自然日",
            "type": "calendar_days",
            "tool_call": "calculate_calendar_days",
            "example": "最近20个自然日"
        },
        {
            "pattern": "最近一个月",
            "regex": "最近一个月",
            "type": "calendar_days",
            "value": 30,
            "tool_call": "calculate_calendar_days",
            "example": "最近一个月"
        }
    ]
}
```

### 3.2 知识库加载和管理

#### 3.2.1 知识库管理器 (`KnowledgeBase`)

```python
class KnowledgeBase:
    """业务知识库管理器"""
    
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir
        self.financial_terms = self._load_json("financial_terms.json")
        self.indicators = self._load_json("indicators.json")
        self.date_patterns = self._load_json("date_patterns.json")
        self.api_mappings = self._load_json("api_mappings.json")
    
    def _load_json(self, filename: str) -> Dict:
        """加载JSON知识库文件"""
        file_path = self.knowledge_dir / filename
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def match_financial_term(self, text: str) -> Optional[Dict]:
        """匹配金融术语"""
        # 匹配交易日
        for term, info in self.financial_terms.get("trading_days", {}).items():
            if term in text:
                return info
        
        # 匹配自然日
        for term, info in self.financial_terms.get("calendar_days", {}).items():
            if term in text:
                return info
        
        return None
    
    def match_indicator(self, text: str) -> Optional[Dict]:
        """匹配技术指标"""
        # 匹配MA指标
        ma_match = re.search(r'MA(\d+)', text, re.IGNORECASE)
        if ma_match:
            period = int(ma_match.group(1))
            indicator_info = self.indicators.get("MA", {}).copy()
            indicator_info['period'] = period
            indicator_info['matched_text'] = ma_match.group(0)
            return indicator_info
        
        # 匹配RSI指标
        rsi_match = re.search(r'RSI\((\d+)\)', text, re.IGNORECASE)
        if rsi_match:
            period = int(rsi_match.group(1))
            indicator_info = self.indicators.get("RSI", {}).copy()
            indicator_info['period'] = period
            indicator_info['matched_text'] = rsi_match.group(0)
            return indicator_info
        
        # 匹配其他指标
        for indicator_name, indicator_info in self.indicators.items():
            if indicator_name.lower() in text.lower():
                return indicator_info
        
        return None
    
    def match_date_pattern(self, text: str) -> Optional[Dict]:
        """匹配日期模式"""
        for pattern_info in self.date_patterns.get("patterns", []):
            regex = pattern_info.get("regex")
            if regex:
                match = re.search(regex, text)
                if match:
                    result = pattern_info.copy()
                    result['matched_groups'] = match.groups()
                    return result
        return None
```

### 3.3 从知识库生成 Tool Call

#### 3.3.1 Tool Call 生成器

```python
class ToolCallGenerator:
    """从知识库生成 Tool Call 定义"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
    
    def generate_financial_tools(self) -> List[Dict]:
        """从知识库生成金融相关的 Tool Call 定义"""
        tools = []
        
        # 交易日历工具
        tools.append({
            "type": "function",
            "function": {
                "name": "calculate_trading_days",
                "description": "计算交易日相关的日期范围。支持从知识库中获取交易日历信息。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "交易日数量"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "结束日期（可选，默认为今天）"
                        },
                        "market": {
                            "type": "string",
                            "enum": ["A股", "港股", "美股"],
                            "description": "市场类型"
                        }
                    },
                    "required": ["days"]
                }
            }
        })
        
        # 技术指标工具
        for indicator_name, indicator_info in self.kb.indicators.items():
            tools.append({
                "type": "function",
                "function": {
                    "name": f"calculate_{indicator_name.lower()}",
                    "description": f"{indicator_info.get('full_name', indicator_name)}: {indicator_info.get('description', '')}\n公式: {indicator_info.get('formula', '')}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period": {
                                "type": "integer",
                                "description": f"计算周期（如MA5的5，RSI(14)的14）"
                            },
                            "data_column": {
                                "type": "string",
                                "description": "数据列名（如'close'、'volume'）"
                            }
                        },
                        "required": ["period"]
                    }
                }
            })
        
        return tools
```

### 3.4 知识库与 Tool Calling 集成

#### 3.4.1 增强的 API Selector

```python
class EnhancedAPISelector(APISelector):
    """增强的 API 选择器，集成知识库"""
    
    def __init__(self, provider: str = "akshare", knowledge_base: Optional[KnowledgeBase] = None):
        super().__init__(provider)
        self.kb = knowledge_base or KnowledgeBase(Path(__file__).parent.parent / "knowledge")
        self.tool_generator = ToolCallGenerator(self.kb)
    
    async def select_api_by_tool_calling(
        self,
        user_query: str,
        max_candidates: int = 10
    ) -> Optional[Dict[str, Any]]:
        """增强的 API 选择，集成金融知识库"""
        
        # 1. 基础 API 选择（原有逻辑）
        api_result = await super().select_api_by_tool_calling(user_query, max_candidates)
        
        if not api_result:
            return None
        
        # 2. 从知识库匹配金融术语
        financial_term = self.kb.match_financial_term(user_query)
        if financial_term:
            # 如果匹配到交易日相关术语，调用交易日历工具
            if financial_term.get("type") == "trading_days":
                trading_days_result = await self._call_trading_days_tool(
                    days=financial_term.get("value"),
                    market="A股"
                )
                if trading_days_result:
                    api_result['suggested_params'].update(trading_days_result)
        
        # 3. 匹配技术指标
        indicator = self.kb.match_indicator(user_query)
        if indicator:
            api_result['indicators'] = [indicator]
            # 添加指标计算所需的参数
            if indicator.get("period"):
                api_result['suggested_params']['_indicator_period'] = indicator['period']
        
        return api_result
    
    async def _call_trading_days_tool(self, days: int, market: str = "A股") -> Optional[Dict]:
        """调用交易日历工具"""
        # 这里可以调用实际的交易日历 API 或使用本地数据
        # 返回准确的开始和结束日期
        from datetime import datetime, timedelta
        # 简化实现，实际应该使用交易日历
        end_date = datetime.now()
        # 估算：30个自然日约等于20个交易日
        estimated_days = int(days * 1.5)
        start_date = end_date - timedelta(days=estimated_days)
        
        return {
            "start_date": start_date.strftime('%Y%m%d'),
            "end_date": end_date.strftime('%Y%m%d'),
            "_limit_days": days,
            "_trading_days": True
        }
```

---

## 4. 标准化工具接入框架

### 4.1 工具注册机制

#### 4.1.1 工具接口定义

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class FinancialTool(ABC):
    """金融工具基类"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """返回 Tool Call 定义"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具调用"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """返回工具描述"""
        pass
```

#### 4.1.2 交易日历工具实现

```python
class TradingDaysTool(FinancialTool):
    """交易日历工具"""
    
    def __init__(self, market: str = "A股"):
        self.market = market
        # 可以接入 tushare、jqdata 等交易日历 API
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "calculate_trading_days",
                "description": "计算交易日相关的日期范围",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "交易日数量"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "结束日期（可选，默认为今天）"
                        },
                        "market": {
                            "type": "string",
                            "enum": ["A股", "港股", "美股"],
                            "description": "市场类型"
                        }
                    },
                    "required": ["days"]
                }
            }
        }
    
    async def execute(self, days: int, end_date: Optional[str] = None, market: str = "A股") -> Dict[str, Any]:
        """执行交易日历计算"""
        # 调用交易日历 API 或使用本地数据
        # 返回准确的开始和结束日期
        from datetime import datetime
        
        if end_date:
            end = datetime.strptime(end_date, '%Y%m%d')
        else:
            end = datetime.now()
        
        # 这里应该调用实际的交易日历 API
        # 简化实现
        start = self._calculate_trading_start_date(end, days, market)
        
        return {
            "start_date": start.strftime('%Y%m%d'),
            "end_date": end.strftime('%Y%m%d'),
            "trading_days": days,
            "market": market
        }
    
    def _calculate_trading_start_date(self, end_date: datetime, days: int, market: str) -> datetime:
        """计算交易日开始日期（简化实现）"""
        # 实际应该使用交易日历 API
        from datetime import timedelta
        # 估算：1.5倍自然日约等于交易日
        estimated_days = int(days * 1.5)
        return end_date - timedelta(days=estimated_days)
    
    def get_description(self) -> str:
        return "计算交易日相关的日期范围，支持A股、港股、美股"
```

#### 4.1.3 技术指标工具实现

```python
class IndicatorTool(FinancialTool):
    """技术指标工具"""
    
    def __init__(self, indicator_name: str, knowledge_base: KnowledgeBase):
        self.indicator_name = indicator_name
        self.kb = knowledge_base
        self.indicator_info = knowledge_base.indicators.get(indicator_name, {})
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": f"calculate_{self.indicator_name.lower()}",
                "description": f"{self.indicator_info.get('full_name', self.indicator_name)}: {self.indicator_info.get('description', '')}\n公式: {self.indicator_info.get('formula', '')}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "integer",
                            "description": f"计算周期"
                        },
                        "data_column": {
                            "type": "string",
                            "description": "数据列名（如'close'、'volume'）"
                        }
                    },
                    "required": ["period"]
                }
            }
        }
    
    async def execute(self, period: int, data_column: str = "close") -> Dict[str, Any]:
        """执行技术指标计算"""
        return {
            "indicator": self.indicator_name,
            "period": period,
            "data_column": data_column,
            "formula": self.indicator_info.get("formula", ""),
            "implementation": self.indicator_info.get("implementation", {}).get("python", ""),
            "code_template": self._generate_code_template(period, data_column)
        }
    
    def _generate_code_template(self, period: int, data_column: str) -> str:
        """生成代码模板"""
        implementation = self.indicator_info.get("implementation", {}).get("python", "")
        if implementation:
            return implementation.format(n=period, period=period, data_column=data_column)
        return f"# 计算{self.indicator_name}({period})"
    
    def get_description(self) -> str:
        return self.indicator_info.get("description", "")
```

#### 4.1.4 工具注册表

```python
class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, FinancialTool] = {}
    
    def register(self, name: str, tool: FinancialTool):
        """注册工具"""
        self.tools[name] = tool
    
    def get_tool(self, name: str) -> Optional[FinancialTool]:
        """获取工具"""
        return self.tools.get(name)
    
    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取所有工具的 Tool Call 定义"""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        tool = self.get_tool(name)
        if tool:
            import asyncio
            return asyncio.run(tool.execute(**kwargs))
        return {}
```

### 4.2 工具接入示例

```python
# 初始化工具注册表
registry = ToolRegistry()

# 注册交易日历工具
trading_days_tool = TradingDaysTool(market="A股")
registry.register("calculate_trading_days", trading_days_tool)

# 注册技术指标工具
kb = KnowledgeBase(Path("knowledge"))
ma_tool = IndicatorTool("MA", kb)
registry.register("calculate_ma", ma_tool)

rsi_tool = IndicatorTool("RSI", kb)
registry.register("calculate_rsi", rsi_tool)

# 在 Tool Calling 中使用
tools = registry.get_all_tool_definitions()
```

---

## 5. 整体业务框架设计

### 5.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                   应用层 (Demo)                          │
│   - 读取 Markdown 文件                                   │
│   - 调用 QDataProcessor                                  │
│   - 保存生成的代码                                       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              QData 核心库 (业务逻辑层)                    │
│   QDataProcessor                                         │
│   ├── 文本解析层 (TextParser)                            │
│   │   ├── 关键词提取                                      │
│   │   ├── 实体识别 (股票代码、日期等)                     │
│   │   └── 语义理解                                       │
│   ├── 知识库层 (KnowledgeBase)                            │
│   │   ├── 金融术语匹配                                    │
│   │   ├── 技术指标识别                                    │
│   │   └── API 映射                                       │
│   ├── Tool Calling 层                                    │
│   │   ├── API 选择 Tool                                  │
│   │   ├── 金融参数解析 Tool                               │
│   │   └── 标准化工具调用                                  │
│   ├── 参数整合层 (ParamMerger)                           │
│   │   ├── 参数合并和优先级处理                             │
│   │   ├── 参数验证                                        │
│   │   └── 参数转换                                        │
│   └── 代码生成层 (CodeGenerator)                          │
│       ├── 根据 API 和参数生成代码                          │
│       ├── 处理金融指标计算                                │
│       └── 添加注释和说明                                  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│            Tool Calling 层 (智能增强层)                    │
│   ├── API 选择 Tool (已有)                               │
│   ├── 金融参数解析 Tool (新增)                            │
│   ├── 交易日历计算 Tool (新增)                            │
│   ├── 技术指标识别 Tool (新增)                            │
│   └── 标准化工具注册表 (新增)                             │
└─────────────────────────────────────────────────────────┘
```

### 5.2 文本解析流程

#### 5.2.1 文本解析器 (`TextParser`)

```python
class TextParser:
    """文本解析器，从 Markdown 中提取关键信息"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
    
    def parse(self, text: str) -> Dict[str, Any]:
        """解析文本，提取关键信息"""
        result = {
            "symbols": [],
            "date_ranges": [],
            "indicators": [],
            "keywords": [],
            "entities": {}
        }
        
        # 1. 提取股票代码
        result["symbols"] = self._extract_symbols(text)
        
        # 2. 匹配金融术语（从知识库）
        financial_term = self.kb.match_financial_term(text)
        if financial_term:
            result["date_ranges"].append(financial_term)
        
        # 3. 匹配日期模式
        date_pattern = self.kb.match_date_pattern(text)
        if date_pattern:
            result["date_ranges"].append(date_pattern)
        
        # 4. 匹配技术指标
        indicator = self.kb.match_indicator(text)
        if indicator:
            result["indicators"].append(indicator)
        
        # 5. 提取关键词
        result["keywords"] = self._extract_keywords(text)
        
        # 6. 实体识别（可以使用 NER 模型）
        result["entities"] = self._extract_entities(text)
        
        return result
    
    def _extract_symbols(self, text: str) -> List[str]:
        """提取股票代码"""
        pattern = r'\b(\d{6})\b'
        matches = re.findall(pattern, text)
        return list(set(matches))
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        # 金融相关关键词
        financial_keywords = ["股票", "行情", "历史", "实时", "收盘", "开盘", "成交量"]
        for keyword in financial_keywords:
            if keyword in text:
                keywords.append(keyword)
        return keywords
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """提取实体（可以使用 NER 模型增强）"""
        entities = {
            "dates": [],
            "numbers": [],
            "financial_terms": []
        }
        
        # 提取日期
        date_pattern = r'\d{4}[-/]\d{2}[-/]\d{2}|\d{8}'
        entities["dates"] = re.findall(date_pattern, text)
        
        # 提取数字
        number_pattern = r'\d+'
        entities["numbers"] = re.findall(number_pattern, text)
        
        return entities
```

### 5.3 统一的处理流程

#### 5.3.1 QDataProcessor 完整实现

```python
class QDataProcessor:
    """统一的参数处理和代码生成接口"""
    
    def __init__(
        self,
        provider: str = "akshare",
        use_ai: bool = True,
        knowledge_base_path: Optional[Path] = None
    ):
        self.provider = provider
        self.use_ai = use_ai
        
        # 初始化知识库
        if knowledge_base_path is None:
            knowledge_base_path = Path(__file__).parent.parent / "knowledge"
        self.kb = KnowledgeBase(knowledge_base_path)
        
        # 初始化文本解析器
        self.text_parser = TextParser(self.kb)
        
        # 初始化工具注册表
        self.tool_registry = ToolRegistry()
        self._register_standard_tools()
        
        # 初始化 API 选择器
        self.selector = EnhancedAPISelector(provider=provider, knowledge_base=self.kb)
        
        # 初始化数据源提供者
        if provider == "akshare":
            self.data_provider = AkshareProvider()
        else:
            raise ValueError(f"不支持的数据源: {provider}")
    
    def _register_standard_tools(self):
        """注册标准化工具"""
        # 交易日历工具
        trading_tool = TradingDaysTool(market="A股")
        self.tool_registry.register("calculate_trading_days", trading_tool)
        
        # 技术指标工具
        for indicator_name in ["MA", "RSI", "MACD", "KDJ"]:
            if indicator_name in self.kb.indicators:
                indicator_tool = IndicatorTool(indicator_name, self.kb)
                self.tool_registry.register(f"calculate_{indicator_name.lower()}", indicator_tool)
    
    async def process_query(
        self,
        query: str,
        use_ai: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        处理用户查询，返回 API 信息和参数
        
        完整流程:
        1. 文本解析：提取关键信息
        2. API 选择：使用 Tool Calling 选择 API
        3. 参数解析：使用知识库和 Tool Calling 解析参数
        4. 参数整合：合并和验证参数
        5. 返回完整信息
        """
        use_ai = use_ai if use_ai is not None else self.use_ai
        
        # 步骤 1: 文本解析
        parsed_info = self.text_parser.parse(query)
        
        # 步骤 2: API 选择
        if use_ai:
            api_result = await self.selector.select_api_by_tool_calling(query)
        else:
            # 使用 keyword 搜索
            keyword_results = select_api_by_keyword(query, provider=self.provider)
            if keyword_results:
                api_result = {
                    "api_name": keyword_results[0]['api_name'],
                    "provider": self.provider,
                    "reason": "Keyword搜索匹配",
                    "api_doc": self.selector.api_manager.find_api_documentation(keyword_results[0]['api_name']),
                    "suggested_params": {}
                }
            else:
                api_result = None
        
        if not api_result:
            return {
                "success": False,
                "error": "未找到合适的API",
                "query": query
            }
        
        # 步骤 3: 参数解析和整合
        params = await self._parse_and_merge_params(query, parsed_info, api_result)
        
        # 步骤 4: 参数验证
        validated_params = self.data_provider.check_params(params, api_result.get('api_doc', {}))
        
        return {
            "success": True,
            "api_info": api_result,
            "params": validated_params,
            "parsed_info": parsed_info,
            "indicators": parsed_info.get("indicators", [])
        }
    
    async def _parse_and_merge_params(
        self,
        query: str,
        parsed_info: Dict[str, Any],
        api_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析和合并参数"""
        params = {}
        
        # 1. 优先使用 AI 建议的参数
        params.update(api_result.get('suggested_params', {}))
        
        # 2. 从文本解析结果中提取参数
        # 股票代码
        if parsed_info.get("symbols"):
            if 'symbol' not in params:
                params['symbol'] = parsed_info["symbols"][0]
        
        # 日期范围
        if parsed_info.get("date_ranges"):
            date_range = parsed_info["date_ranges"][0]
            if date_range.get("type") == "trading_days":
                # 调用交易日历工具
                trading_result = await self.tool_registry.tools["calculate_trading_days"].execute(
                    days=date_range.get("value"),
                    market="A股"
                )
                params.update({
                    "start_date": trading_result.get("start_date"),
                    "end_date": trading_result.get("end_date"),
                    "_limit_days": date_range.get("value"),
                    "_trading_days": True
                })
            elif date_range.get("type") == "calendar_days":
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=date_range.get("value", 30))
                params.update({
                    "start_date": start_date.strftime('%Y%m%d'),
                    "end_date": end_date.strftime('%Y%m%d')
                })
        
        # 3. 使用 detect_function 补充
        detected_info = self.data_provider.detect_function(query)
        if detected_info and detected_info.get('params'):
            for key, value in detected_info['params'].items():
                if key not in params:
                    params[key] = value
        
        return params
    
    def generate_code(
        self,
        api_info: Dict[str, Any],
        params: Dict[str, Any],
        indicators: Optional[List[Dict]] = None
    ) -> str:
        """
        生成最终代码
        
        包括:
        1. API 调用代码
        2. 金融指标计算代码（如果有）
        3. 数据后处理代码
        """
        # 基础代码生成
        code = self.data_provider.generate_code(
            api_name=api_info['api_name'],
            api_doc=api_info.get('api_doc', {}),
            params=params
        )
        
        # 添加技术指标计算代码
        if indicators:
            indicator_code = self._generate_indicator_code(indicators)
            # 在结果处理之前插入指标计算
            code = self._insert_indicator_code(code, indicator_code)
        
        return code
    
    def _generate_indicator_code(self, indicators: List[Dict]) -> str:
        """生成技术指标计算代码"""
        code_lines = []
        
        for indicator in indicators:
            indicator_name = indicator.get('name')
            period = indicator.get('period')
            
            if indicator_name == "MA":
                code_lines.append(f"# 计算{period}日均线")
                code_lines.append(f"result['MA{period}'] = result['close'].rolling(window={period}).mean()")
            elif indicator_name == "RSI":
                code_lines.append(f"# 计算{period}日RSI指标")
                code_lines.append("delta = result['close'].diff()")
                code_lines.append("gain = (delta.where(delta > 0, 0)).rolling(window={}).mean()".format(period))
                code_lines.append("loss = (-delta.where(delta < 0, 0)).rolling(window={}).mean()".format(period))
                code_lines.append("rs = gain / loss")
                code_lines.append(f"result['RSI{period}'] = 100 - (100 / (1 + rs))")
        
        return "\n".join(code_lines)
    
    def _insert_indicator_code(self, base_code: str, indicator_code: str) -> str:
        """在基础代码中插入指标计算代码"""
        # 在结果处理之前插入
        if "# Process and format the result" in base_code:
            parts = base_code.split("# Process and format the result")
            return parts[0] + indicator_code + "\n\n# Process and format the result" + parts[1]
        return base_code + "\n\n" + indicator_code
```

### 5.4 知识库维护框架

#### 5.4.1 知识库更新机制

```python
class KnowledgeBaseManager:
    """知识库管理器，支持动态更新"""
    
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir
        self.kb = KnowledgeBase(knowledge_dir)
    
    def add_financial_term(self, term: str, info: Dict[str, Any]):
        """添加金融术语"""
        term_type = info.get("type", "trading_days")
        if term_type not in self.kb.financial_terms:
            self.kb.financial_terms[term_type] = {}
        self.kb.financial_terms[term_type][term] = info
        self._save_json("financial_terms.json", self.kb.financial_terms)
    
    def add_indicator(self, indicator_name: str, info: Dict[str, Any]):
        """添加技术指标"""
        self.kb.indicators[indicator_name] = info
        self._save_json("indicators.json", self.kb.indicators)
    
    def add_date_pattern(self, pattern: Dict[str, Any]):
        """添加日期模式"""
        if "patterns" not in self.kb.date_patterns:
            self.kb.date_patterns["patterns"] = []
        self.kb.date_patterns["patterns"].append(pattern)
        self._save_json("date_patterns.json", self.kb.date_patterns)
    
    def _save_json(self, filename: str, data: Dict):
        """保存 JSON 文件"""
        file_path = self.knowledge_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

#### 5.4.2 训练数据管理

```python
class TrainingDataManager:
    """训练数据管理器"""
    
    def __init__(self, examples_dir: Path):
        self.examples_dir = examples_dir
    
    def add_example(self, category: str, example: Dict[str, Any]):
        """添加训练示例"""
        file_path = self.examples_dir / f"{category}_examples.json"
        
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                examples = json.load(f)
        else:
            examples = []
        
        examples.append(example)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(examples, f, ensure_ascii=False, indent=2)
    
    def load_examples(self, category: str) -> List[Dict]:
        """加载训练示例"""
        file_path = self.examples_dir / f"{category}_examples.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
```

---

## 6. 完整使用示例

### 6.1 Demo 层简化实现

```python
async def main():
    """简化的 Demo 实现"""
    # 读取 markdown
    markdown_content = read_markdown("stock_zh_a_hist.md")
    
    # 创建处理器（自动加载知识库）
    processor = QDataProcessor(
        provider="akshare",
        use_ai=True,
        knowledge_base_path=Path("knowledge")
    )
    
    # 处理查询
    result = await processor.process_query(markdown_content)
    
    if not result.get("success"):
        print(f"处理失败: {result.get('error')}")
        return
    
    # 生成代码
    code = processor.generate_code(
        api_info=result['api_info'],
        params=result['params'],
        indicators=result.get('indicators', [])
    )
    
    # 保存代码
    save_code(code, "output.py")
    print("代码生成完成！")
```

### 6.2 知识库使用示例

```python
# 初始化知识库管理器
kb_manager = KnowledgeBaseManager(Path("knowledge"))

# 添加新的金融术语
kb_manager.add_financial_term("最近一周", {
    "type": "trading_days",
    "value": 5,
    "description": "最近5个交易日",
    "tool_call": "calculate_trading_days",
    "formula": "从当前日期往前推，排除周末和节假日，取最近5个交易日"
})

# 添加新的技术指标
kb_manager.add_indicator("BOLL", {
    "name": "BOLL",
    "full_name": "布林带 (Bollinger Bands)",
    "description": "计算布林带指标",
    "formula": "中轨 = MA(n), 上轨 = 中轨 + k*标准差, 下轨 = 中轨 - k*标准差",
    "implementation": {
        "python": "data['BOLL_MID'] = data['close'].rolling(window={n}).mean()\ndata['BOLL_STD'] = data['close'].rolling(window={n}).std()\ndata['BOLL_UPPER'] = data['BOLL_MID'] + 2 * data['BOLL_STD']\ndata['BOLL_LOWER'] = data['BOLL_MID'] - 2 * data['BOLL_STD']"
    }
})
```

---

## 7. 总结和建议

### 7.1 关键参数识别的位置

**建议**: **统一在 QData 核心库中实现，通过知识库增强**

**实现方式**:
- QData 库提供统一的 `TextParser` 接口
- 使用知识库匹配金融术语和技术指标
- Demo 文件只负责调用，不包含业务逻辑
- Tool Calling 作为智能增强层

### 7.2 金融专门 Tool Call

**建议**: **需要，基于知识库动态生成**

**实现方式**:
- 从知识库自动生成 Tool Call 定义
- 提供标准化工具接口
- 支持工具注册和扩展
- 集成到 QData 核心库

### 7.3 整体业务框架

**建议**: **分层架构，知识库驱动**

**架构**:
```
Demo 层 (应用层)
    ↓ 调用
QData 核心库 (业务逻辑层)
    ├── 文本解析层 (TextParser)
    ├── 知识库层 (KnowledgeBase)
    ├── Tool Calling 层 (集成知识库)
    ├── 参数整合层 (ParamMerger)
    └── 代码生成层 (CodeGenerator)
    ↓ 使用
Tool Calling (智能增强层)
    ├── API 选择 Tool
    ├── 金融参数解析 Tool (从知识库生成)
    └── 标准化工具注册表
```

**知识库维护**:
- JSON 格式存储，易于维护
- 支持动态添加和更新
- 提供训练数据管理
- 版本控制和备份

### 7.4 实施建议（1-2个月快速实施计划）

#### 阶段 1: 知识库基础建设（第1-2周）⭐ 核心优先级

**目标**: 建立可用的知识库，支持基础金融术语和技术指标识别

**任务清单**:
1. ✅ 创建知识库目录结构 `QData/qdata/knowledge/`
2. ✅ 定义 JSON 格式规范（参考文档中的示例）
3. ✅ 填充基础数据：
   - `financial_terms.json`: 至少包含 "20个交易日"、"最近一个月" 等常用术语
   - `indicators.json`: 至少包含 MA、RSI 两个指标
   - `date_patterns.json`: 日期匹配模式
4. ✅ 实现 `KnowledgeBase` 类（基础版本，无需向量搜索）
   - 文件位置: `QData/qdata/core/knowledge_base.py`
   - 功能: 加载 JSON、匹配术语、匹配指标

**验收标准**:
- 知识库可以正确加载和匹配 "20个交易日"
- 可以识别 "MA5"、"RSI(14)" 等技术指标

#### 阶段 2: 文本解析和工具集成（第3-4周）⭐ 核心优先级

**目标**: 实现文本解析器和工具注册机制

**任务清单**:
1. ✅ 实现 `TextParser` 类
   - 文件位置: `QData/qdata/core/text_parser.py`
   - 功能: 提取股票代码、匹配知识库术语、识别技术指标
2. ✅ 实现 `ToolRegistry` 工具注册表
   - 文件位置: `QData/qdata/core/tool_registry.py`
   - 功能: 注册、获取、执行工具
3. ✅ 实现基础标准化工具：
   - `TradingDaysTool`: 交易日历工具（简化版，使用估算算法）
   - `IndicatorTool`: 技术指标工具（基于知识库）
   - 文件位置: `QData/qdata/core/financial_tools.py`
4. ✅ 从知识库生成 Tool Call 定义
   - 在 `ToolCallGenerator` 中实现

**验收标准**:
- 可以从 "获取600000的20个交易日数据" 中提取股票代码和交易日信息
- 工具注册表可以正确注册和执行工具

#### 阶段 3: 重构 QDataProcessor（第5-6周）⭐ 核心优先级

**目标**: 实现统一的处理接口，简化 Demo 层

**任务清单**:
1. ✅ 实现 `QDataProcessor` 类
   - 文件位置: `QData/qdata/core/processor.py`
   - 功能: 整合文本解析、知识库、Tool Calling、代码生成
2. ✅ 集成各组件：
   - 集成 `TextParser`
   - 集成 `KnowledgeBase`
   - 集成 `ToolRegistry`
   - 集成 `EnhancedAPISelector`（增强的 API 选择器）
3. ✅ 实现参数整合逻辑 `ParamMerger`
   - 合并 AI 建议参数、文本解析参数、知识库匹配结果
4. ✅ 简化 Demo 文件
   - 移除所有业务逻辑
   - 只保留调用 `QDataProcessor` 的代码

**验收标准**:
- Demo 文件代码量减少 50% 以上
- 可以成功生成 `stock_zh_a_hist_keyword.py` 和 `stock_zh_a_hist_mcp.py`
- 生成的代码参数准确（特别是交易日计算）

#### 阶段 4: 测试和优化（第7-8周）⭐ 核心优先级

**目标**: 确保核心功能稳定可用

**任务清单**:
1. ✅ 编写单元测试
   - 测试知识库匹配
   - 测试文本解析
   - 测试参数整合
2. ✅ 端到端测试
   - 测试完整的代码生成流程
   - 验证生成的代码可以运行
3. ✅ 优化和修复
   - 修复发现的 bug
   - 优化参数提取准确度
   - 改进错误处理

**验收标准**:
- 所有核心功能通过测试
- 生成的代码可以成功运行
- 文档完整，便于后续维护

#### 可选增强（时间允许时）:

**简化版 RAG 增强**（参考方案B，但无需向量数据库）:
- 使用简单的关键词匹配 + 知识库示例
- 在 Tool Calling 时，从知识库中查找相似示例
- 基于示例增强 prompt，提高准确性

**实施优先级**:
- ⭐⭐⭐ 必须完成（核心功能）
- ⭐⭐ 重要但不紧急（可以后续迭代）
- ⭐ 可选增强（时间允许时）

**里程碑检查点**:
- **Week 2**: 知识库可以加载和匹配 ✅
- **Week 4**: 文本解析器可以提取关键信息 ✅
- **Week 6**: QDataProcessor 可以生成代码 ✅
- **Week 8**: 端到端测试通过，代码可以运行 ✅

---

## 8. 参考实现

### 8.1 当前代码位置

- **Demo 文件**: `QData/examples/demo_*/py_ai_m2c_*_demo.py`
- **Tool Calling**: `QData/qdata/core/selector.py`
- **参数检测**: `QData/qdata/providers/akshare.py` - `detect_function()`
- **代码生成**: `QData/qdata/providers/akshare.py` - `generate_code()`

### 8.2 建议的新接口和文件

- **知识库目录**: `QData/qdata/knowledge/`
  - `financial_terms.json` - 金融术语知识库
  - `indicators.json` - 技术指标知识库
  - `date_patterns.json` - 日期模式知识库
  - `api_mappings.json` - API 映射知识库

- **核心接口**: `QData/qdata/core/processor.py` - `QDataProcessor`
- **文本解析**: `QData/qdata/core/text_parser.py` - `TextParser`
- **知识库管理**: `QData/qdata/core/knowledge_base.py` - `KnowledgeBase`, `KnowledgeBaseManager`
- **工具注册**: `QData/qdata/core/tool_registry.py` - `ToolRegistry`, `FinancialTool`
- **标准化工具**: `QData/qdata/core/financial_tools.py`
  - `TradingDaysTool` - 交易日历工具
  - `IndicatorTool` - 技术指标工具

---

## 9. 业务知识库与 Tool Call 集成详细方案

### 9.1 参考 Cursor 训练代码的方式

#### 9.1.1 Cursor 的知识库机制

**Cursor 的工作原理**:
1. **代码上下文理解**: 分析当前代码库的结构和模式
2. **知识库索引**: 建立代码、文档、注释的索引
3. **语义搜索**: 通过向量搜索找到相关代码示例
4. **模式学习**: 从历史代码中学习编码模式

**参考实现**:
```python
class KnowledgeBaseIndexer:
    """知识库索引器，参考 Cursor 的方式"""
    
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir
        self.embeddings = {}  # 向量索引
        self.examples = []     # 示例数据
    
    def index_financial_term(self, term: str, examples: List[Dict]):
        """索引金融术语及其使用示例"""
        # 1. 存储示例数据
        for example in examples:
            self.examples.append({
                "term": term,
                "input": example.get("input"),
                "output": example.get("output"),
                "code": example.get("code"),
                "tool_call": example.get("tool_call")
            })
        
        # 2. 生成向量嵌入（用于语义搜索）
        term_embedding = self._generate_embedding(term)
        self.embeddings[term] = term_embedding
    
    def search_similar_terms(self, query: str, top_k: int = 5) -> List[Dict]:
        """语义搜索相似的金融术语"""
        query_embedding = self._generate_embedding(query)
        
        # 计算相似度
        similarities = []
        for term, embedding in self.embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append({
                "term": term,
                "similarity": similarity,
                "examples": [e for e in self.examples if e["term"] == term]
            })
        
        # 返回最相似的 top_k 个
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]
```

#### 9.1.2 训练数据格式

**训练数据示例** (`knowledge/examples/trading_days_examples.json`):
```json
[
    {
        "input": "获取600000的20个交易日数据",
        "output": {
            "type": "trading_days",
            "value": 20,
            "tool_call": "calculate_trading_days",
            "params": {"days": 20, "market": "A股"}
        },
        "code": "result = result.tail(20)  # 取最近20个交易日",
        "tool_call": {
            "name": "calculate_trading_days",
            "arguments": {"days": 20, "market": "A股"}
        },
        "metadata": {
            "source": "user_query",
            "verified": true,
            "accuracy": 0.95
        }
    }
]
```

### 9.2 从大段 Markdown 文本提取关键词

#### 9.2.1 文本解析流程

```
大段 Markdown 文本
    ↓
文本预处理（分段、清理、标准化）
    ↓
关键词提取层（规则匹配、知识库匹配、实体识别）
    ↓
语义理解层（意图识别、上下文理解、关系抽取）
    ↓
工具调用映射（API 选择、参数提取、指标识别）
    ↓
生成 Tool Call 或 API 调用
```

#### 9.2.2 高级文本解析器

```python
class AdvancedTextParser:
    """高级文本解析器，支持大段 Markdown 文本"""
    
    def parse_markdown(self, markdown_text: str) -> Dict[str, Any]:
        """解析大段 Markdown 文本"""
        # 1. 分段处理
        sections = self._split_into_sections(markdown_text)
        
        # 2. 逐段解析
        result = {
            "sections": [],
            "entities": {},
            "keywords": [],
            "api_calls": [],
            "tool_calls": [],
            "indicators": []
        }
        
        for section in sections:
            section_result = self._parse_section(section)
            result["sections"].append(section_result)
            # 合并结果...
        
        return result
```

### 9.3 知识库维护框架

#### 9.3.1 知识库版本管理

```python
class KnowledgeBaseVersionManager:
    """知识库版本管理器"""
    
    def create_version(self, description: str) -> str:
        """创建新版本并备份"""
        # 备份当前知识库
        # 更新版本记录
        pass
```

---

## 10. 完整业务框架实现

### 10.1 整体架构图

```
应用层 (Demo)
    ↓
QData 核心库 (业务逻辑层)
    ├── 文本解析层 (AdvancedTextParser)
    ├── 知识库层 (KnowledgeBase + Indexer)
    ├── Tool Calling 集成层
    ├── 参数整合层 (ParamMerger)
    └── 代码生成层 (CodeGenerator)
    ↓
Tool Calling (智能增强层)
    ├── API 选择 Tool
    ├── 金融参数解析 Tool (从知识库生成)
    └── 标准化工具注册表
```

### 10.2 完整处理流程

```python
class QDataProcessor:
    """完整的 QData 处理器"""
    
    async def process_markdown(self, markdown_text: str) -> Dict[str, Any]:
        """
        处理大段 Markdown 文本
        
        完整流程:
        1. 文本解析：分段、提取关键信息
        2. 知识库匹配：匹配金融术语和技术指标
        3. API 选择：使用 Tool Calling 选择 API
        4. 参数解析：使用知识库和 Tool Calling 解析参数
        5. 参数整合：合并和验证参数
        6. 代码生成：生成最终代码
        """
        # 步骤 1: 高级文本解析
        parsed_result = self.text_parser.parse_markdown(markdown_text)
        
        # 步骤 2-6: 处理流程...
        pass
```

---

## 11. 实施路线图（1-2个月版本）

### 快速实施计划（8周）

#### Week 1-2: 知识库基础 ⭐⭐⭐
- [ ] 创建 `QData/qdata/knowledge/` 目录
- [ ] 编写 `financial_terms.json`（至少10个常用术语）
- [ ] 编写 `indicators.json`（MA、RSI）
- [ ] 编写 `date_patterns.json`
- [ ] 实现 `KnowledgeBase` 类（基础版）
- [ ] 编写单元测试

**交付物**: 可用的知识库和加载器

#### Week 3-4: 文本解析和工具 ⭐⭐⭐
- [ ] 实现 `TextParser` 类
- [ ] 实现 `ToolRegistry` 类
- [ ] 实现 `TradingDaysTool`（简化版）
- [ ] 实现 `IndicatorTool`
- [ ] 实现 `ToolCallGenerator`
- [ ] 编写单元测试

**交付物**: 文本解析器和工具注册表

#### Week 5-6: 核心处理器 ⭐⭐⭐
- [ ] 实现 `QDataProcessor` 类
- [ ] 实现 `ParamMerger` 参数整合
- [ ] 集成所有组件
- [ ] 重构 Demo 文件（简化）
- [ ] 编写集成测试

**交付物**: 统一的处理接口

#### Week 7-8: 测试和优化 ⭐⭐⭐
- [ ] 端到端测试
- [ ] 修复 bug
- [ ] 性能优化
- [ ] 文档完善
- [ ] 代码审查

**交付物**: 稳定可用的代码生成系统

### 后续优化（3-6个月）

#### 简化版 RAG 增强（参考方案B）
- 在知识库中添加示例数据
- 在 Tool Calling 时匹配相似示例
- 基于示例增强 prompt

#### 向量搜索升级（可选）
- 引入向量数据库（Qdrant/Chroma）
- 实现语义搜索
- 参考方案B的完整实现

### 关键决策点

**Week 2 检查点**:
- 知识库是否可用？
- 是否需要调整格式？

**Week 4 检查点**:
- 文本解析准确度如何？
- 工具是否正常工作？

**Week 6 检查点**:
- 生成的代码是否正确？
- Demo 层是否已简化？

**Week 8 检查点**:
- 是否达到验收标准？
- 是否需要延期？

---

## 12. 参考实现

### 12.1 当前代码位置

- **Demo 文件**: `QData/examples/demo_*/py_ai_m2c_*_demo.py`
- **Tool Calling**: `QData/qdata/core/selector.py`
- **参数检测**: `QData/qdata/providers/akshare.py` - `detect_function()`
- **代码生成**: `QData/qdata/providers/akshare.py` - `generate_code()`

### 12.2 建议的新接口和文件

- **知识库目录**: `QData/qdata/knowledge/`
  - `financial_terms.json` - 金融术语知识库
  - `indicators.json` - 技术指标知识库
  - `date_patterns.json` - 日期模式知识库
  - `api_mappings.json` - API 映射知识库
  - `versions.json` - 版本管理
  - `examples/` - 训练数据目录

- **核心接口**: `QData/qdata/core/processor.py` - `QDataProcessor`
- **文本解析**: `QData/qdata/core/text_parser.py` - `AdvancedTextParser`
- **知识库管理**: `QData/qdata/core/knowledge_base.py`
  - `KnowledgeBase` - 知识库加载和匹配
  - `KnowledgeBaseManager` - 知识库管理
  - `KnowledgeBaseIndexer` - 向量索引和语义搜索
- **工具注册**: `QData/qdata/core/tool_registry.py`
  - `ToolRegistry` - 工具注册表
  - `FinancialTool` - 工具基类
- **标准化工具**: `QData/qdata/core/financial_tools.py`
  - `TradingDaysTool` - 交易日历工具
  - `IndicatorTool` - 技术指标工具
  - `ToolCallGenerator` - 从知识库生成 Tool Call

---

---

## 13. 基于方案B的改进建议（1-2个月实施）

### 13.1 参考方案B的简化实现

基于方案B文档的分析，以下是适合1-2个月实施的简化改进：

#### 13.1.1 简化版知识库增强（无需向量数据库）

**当前方案A**: 使用 JSON 文件存储知识库
**改进建议**: 添加示例数据支持，用于相似匹配

```python
# 在 KnowledgeBase 中添加示例匹配
class KnowledgeBase:
    def find_similar_examples(self, query: str, top_k: int = 3) -> List[Dict]:
        """查找相似的示例（简化版，使用关键词匹配）"""
        # 不使用向量搜索，使用简单的关键词匹配
        similar_examples = []
        
        # 从 examples 目录加载示例
        examples = self._load_examples()
        
        # 简单的关键词匹配
        query_keywords = set(self._extract_keywords(query))
        for example in examples:
            example_keywords = set(self._extract_keywords(example.get("input", "")))
            similarity = len(query_keywords & example_keywords) / len(query_keywords | example_keywords)
            if similarity > 0.3:  # 阈值
                similar_examples.append({
                    "example": example,
                    "similarity": similarity
                })
        
        # 按相似度排序
        similar_examples.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_examples[:top_k]
```

#### 13.1.2 增强 Tool Calling Prompt

**改进**: 在 Tool Calling 时，使用知识库示例增强 prompt

```python
class EnhancedAPISelector(APISelector):
    async def select_api_by_tool_calling(self, user_query: str, ...):
        # 1. 从知识库查找相似示例
        similar_examples = self.kb.find_similar_examples(user_query, top_k=2)
        
        # 2. 构建增强的 prompt
        enhanced_prompt = self._build_enhanced_prompt(user_query, similar_examples)
        
        # 3. 执行 Tool Calling（使用增强的 prompt）
        return await super().select_api_by_tool_calling(enhanced_prompt, ...)
    
    def _build_enhanced_prompt(self, query: str, examples: List[Dict]) -> str:
        """构建增强的 prompt"""
        prompt = f"用户查询: {query}\n\n"
        
        if examples:
            prompt += "相关示例:\n"
            for i, ex_info in enumerate(examples, 1):
                example = ex_info["example"]
                prompt += f"\n示例 {i}:\n"
                prompt += f"输入: {example.get('input')}\n"
                prompt += f"输出: {example.get('output')}\n"
                if example.get('tool_call'):
                    prompt += f"工具调用: {example.get('tool_call')}\n"
        
        prompt += "\n请参考以上示例，选择最合适的 API 并提取参数。"
        return prompt
```

### 13.2 实施优先级调整

**必须完成（核心功能）**:
1. ✅ 知识库基础（JSON格式）
2. ✅ 文本解析器
3. ✅ 工具注册表
4. ✅ QDataProcessor 统一接口
5. ✅ 简化 Demo 层

**重要但不紧急**:
1. ⭐⭐ 示例数据收集和匹配
2. ⭐⭐ Prompt 增强
3. ⭐⭐ 参数验证和错误处理

**可选增强（后续阶段）**:
1. ⭐ 向量数据库集成
2. ⭐ 完整的 RAG 实现
3. ⭐ Agent 框架

### 13.3 与方案B的对比

| 特性 | 方案A（1-2个月） | 方案B（3-6个月） |
|------|----------------|----------------|
| 知识库存储 | JSON 文件 | 向量数据库 |
| 相似度匹配 | 关键词匹配 | 向量相似度 |
| 示例搜索 | 简单匹配 | 语义搜索 |
| 实施复杂度 | ⭐⭐ | ⭐⭐⭐⭐ |
| 响应速度 | 快 | 中等 |
| 准确性 | 良好 | 优秀 |

**建议**: 先实施方案A，验证核心功能，后续再升级到方案B。

---

**文档结束**
