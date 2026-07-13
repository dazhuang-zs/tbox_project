# 【AI Agent 系统教学 32】工具系统与 MCP 协议

> 工具是 Agent 的"手"。MCP 是让这些"手"标准化、可互操作的协议。
> 2026 年，不懂 MCP 的 Agent 开发就像不懂 HTTP 的 Web 开发。

---

## 前言：工具系统的演进

Agent 的工具系统经历了三个阶段：

```
阶段 1：硬编码工具（2023）
  工具代码写在 Agent 代码里，耦合度高
  
阶段 2：插件化工具（2024）
  工具通过接口注册，可动态加载
  
阶段 3：MCP 协议（2025-2026）
  工具通过标准协议定义，跨平台、跨框架
```

---

## 一、工具系统的架构

### 1.1 核心组件

```python
class ToolSystem:
    """Agent 工具系统"""
    def __init__(self):
        self.registry = ToolRegistry()    # 工具注册中心
        self.executor = ToolExecutor()     # 工具执行器
        self.validator = ToolValidator()   # 工具验证器
        self.cache = ToolCache()           # 工具结果缓存
    
    def register_tool(self, tool):
        self.registry.register(tool)
    
    def execute(self, tool_call):
        # 1. 验证
        if not self.validator.validate(tool_call):
            return {"error": "工具调用验证失败"}
        
        # 2. 检查缓存
        cached = self.cache.get(tool_call)
        if cached:
            return cached
        
        # 3. 执行
        tool = self.registry.get(tool_call.name)
        result = self.executor.execute(tool, tool_call.args)
        
        # 4. 缓存结果
        self.cache.set(tool_call, result)
        
        return result
```

### 1.2 工具注册中心

```python
class ToolRegistry:
    """工具注册中心"""
    def __init__(self):
        self.tools = {}
        self.categories = {}
    
    def register(self, tool, category="general"):
        self.tools[tool.name] = tool
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(tool.name)
    
    def get_by_category(self, category):
        return [self.tools[name] for name in self.categories.get(category, [])]
    
    def get_tools_for_agent(self, agent_context):
        """根据 Agent 上下文选择工具"""
        relevant = []
        for tool in self.tools.values():
            if self._is_relevant(tool, agent_context):
                relevant.append(tool)
        return relevant
```

---

## 二、MCP 协议

### 2.1 什么是 MCP

MCP（Model Context Protocol）是 2025 年由 Anthropic 提出的**标准工具协议**，目标是让工具的定义和调用在不同模型、框架、语言之间互通。

```
MCP 的核心思想：
  工具 = 远程过程调用（RPC）
  模型 = 客户端
  工具服务器 = 服务端

MCP 协议定义：
  1. 工具如何定义（Schema）
  2. 工具如何调用（Request/Response）
  3. 工具如何发现（List）
  4. 错误如何处理（Error Codes）
```

### 2.2 MCP 工具定义

```python
# MCP 格式的工具定义
MCP_TOOL_SCHEMA = {
    "name": "get_weather",           # 工具名
    "description": "查询天气信息",    # 描述
    "inputSchema": {                  # 输入模式
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名",
            }
        },
        "required": ["city"],
    },
    "outputSchema": {                 # 输出模式
        "type": "object",
        "properties": {
            "temperature": {"type": "number"},
            "condition": {"type": "string"},
        },
    },
}
```

### 2.3 MCP 客户端

```python
class MCPClient:
    """MCP 协议客户端"""
    def __init__(self, server_url):
        self.server_url = server_url
        self.tools_cache = None
    
    def list_tools(self):
        """发现可用的工具"""
        if self.tools_cache:
            return self.tools_cache
        
        response = requests.post(f"{self.server_url}/tools/list")
        self.tools_cache = response.json()["tools"]
        return self.tools_cache
    
    def call_tool(self, tool_name, arguments):
        """调用工具"""
        response = requests.post(
            f"{self.server_url}/tools/call",
            json={
                "name": tool_name,
                "arguments": arguments,
            },
        )
        result = response.json()
        
        if result.get("isError"):
            raise ToolError(result["content"][0]["text"])
        
        return result["content"][0]["text"]
    
    def get_openai_format(self):
        """转换为 OpenAI 兼容格式"""
        tools = self.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["inputSchema"],
                },
            }
            for t in tools
        ]
```

### 2.4 MCP 服务器

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

class WeatherMCPServer:
    """MCP 工具服务器示例"""
    def __init__(self):
        self.server = Server("weather-server")
        self._register_tools()
    
    def _register_tools(self):
        @self.server.list_tools()
        async def list_tools():
            return [
                {
                    "name": "get_weather",
                    "description": "查询天气",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                        },
                        "required": ["city"],
                    },
                },
            ]
        
        @self.server.call_tool()
        async def call_tool(name, arguments):
            if name == "get_weather":
                result = await self._get_weather(arguments["city"])
                return {"content": [{"type": "text", "text": result}]}
    
    async def run(self):
        async with stdio_server() as (read, write):
            await self.server.run(read, write)
```

---

## 三、工具链设计

### 3.1 工具链模式

```python
class ToolChain:
    """工具链：多个工具按顺序组合"""
    def __init__(self):
        self.steps = []
    
    def add_step(self, tool_name, param_mapping):
        """
        添加工具链步骤
        param_mapping: 如何将上一步的结果映射到当前步骤的参数
        """
        self.steps.append({
            "tool": tool_name,
            "param_mapping": param_mapping,
        })
    
    def execute(self, initial_params, registry):
        """执行整个工具链"""
        current_params = initial_params
        results = []
        
        for step in self.steps:
            tool = registry.get(step["tool"])
            # 参数映射
            mapped_params = step["param_mapping"](current_params, results)
            # 执行
            result = tool.execute(mapped_params)
            results.append(result)
            current_params = result
        
        return results[-1]
```

### 3.2 工具组合模式

```python
# 模式 1：顺序链
# 搜索 → 提取 → 总结
search_chain = ToolChain()
search_chain.add_step("search_web", lambda p, r: {"query": p["query"]})
search_chain.add_step("extract_content", lambda p, r: {"url": r[0]["url"]})
search_chain.add_step("summarize", lambda p, r: {"text": r[1]["content"]})

# 模式 2：并行组合
# 同时查天气和新闻
parallel_tools = ["get_weather", "get_news"]
results = asyncio.gather(*[execute(t, p) for t in parallel_tools])

# 模式 3：条件路由
# 根据结果选择下一步
if result["type"] == "weather":
    next_tool = "recommend_outfit"
else:
    next_tool = "general_response"
```

---

## 四、工具缓存

### 4.1 缓存策略

```python
class ToolCache:
    """工具结果缓存"""
    def __init__(self, ttl=300):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, tool_call):
        key = self._make_key(tool_call)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["result"]
            else:
                del self.cache[key]
        return None
    
    def set(self, tool_call, result):
        key = self._make_key(tool_call)
        self.cache[key] = {
            "result": result,
            "timestamp": time.time(),
        }
    
    def _make_key(self, tool_call):
        """生成缓存键"""
        return f"{tool_call.name}:{hash(json.dumps(tool_call.args, sort_keys=True))}"
```

---

## 五、工具安全

### 5.1 权限控制

```python
class ToolPermissionManager:
    """工具权限管理"""
    def __init__(self):
        self.permissions = {
            "read_file": {"level": "read", "allowed_paths": ["/data/"]},
            "write_file": {"level": "write", "allowed_paths": ["/tmp/"]},
            "execute_code": {"level": "dangerous", "sandbox": True},
            "send_email": {"level": "write", "max_recipients": 1},
            "delete_file": {"level": "dangerous", "require_confirm": True},
        }
    
    def check_permission(self, tool_name, args, user_role):
        config = self.permissions.get(tool_name)
        if not config:
            return False, "未知工具"
        
        if config["level"] == "dangerous" and user_role != "admin":
            return False, "需要管理员权限"
        
        if config.get("require_confirm"):
            return "confirm", f"确认执行 {tool_name}？"
        
        return True, None
```

### 5.2 沙箱执行

```python
class SandboxExecutor:
    """沙箱执行工具"""
    def execute_code(self, code, timeout=5):
        """在沙箱中执行代码"""
        import subprocess
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/tmp/sandbox/",
            env={"PATH": "/usr/bin"},
        )
        return result.stdout or result.stderr
```

---

## 六、2026 年工具系统趋势

### 6.1 MCP 成为标准

2026 年，MCP 正在成为 Agent 工具的标准协议。几乎所有主流框架都支持 MCP。

### 6.2 工具市场

Agent 可以从"工具市场"发现和安装工具：

```
工具市场 → 搜索"天气" → 安装天气 MCP 服务器
          → 搜索"邮件" → 安装邮件 MCP 服务器
          → 工具自动注册到 Agent
```

### 6.3 工具即服务

工具不再是"代码"，而是"服务"：

```
工具 = MCP 服务器
Agent → MCP 协议 → 工具服务器（云端/本地）
```

---

## 总结

| 概念 | 说明 |
|------|------|
| 工具系统 | Agent 的工具注册、执行、缓存、验证 |
| MCP 协议 | 工具定义和调用的标准协议 |
| 工具链 | 多个工具按顺序/并行组合 |
| 工具缓存 | 缓存工具结果，避免重复调用 |
| 工具安全 | 权限控制、沙箱执行 |

**MCP 让 Agent 的工具系统从"私有 API"走向"标准协议"。**

下一篇文章，我们将深入**Agent 规划与推理**。

---

**思考题**：
1. 你的 Agent 现在支持 MCP 吗？如果不支持，迁移成本高吗？
2. 工具缓存对哪些类型的工具最有价值？哪些工具不适合缓存？
3. 如果工具超过了 50 个，你怎么管理和组织？

---

> 上一篇：[31] Agent 记忆系统深度解析
> 下一篇：[33] Agent 规划与推理
> 系列目录：[README.md](./README.md)