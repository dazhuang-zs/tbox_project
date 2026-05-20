# 强烈推荐收藏！MCP 协议深度解析：AI 工具的「USB-C」是怎么设计的——JSON-RPC选型、四层架构、stdio vs HTTP、安全攻防

> 给 Claude 写一套工具，给 GPT 写一套适配，给 DeepSeek 再写一套——这就是 MCP 要消灭的噩梦。Anthropic 在 2024 年底推出 Model Context Protocol，号称 AI 领域的 USB-C。本文扒开协议层，从 JSON-RPC 的选型逻辑讲到 Streamable HTTP 的协议升级，再给出生产级 MCP Server 的完整实现。

---

## 一、MCP 要解决什么问题

### 1.1 没有 MCP 的世界

```python
# 给 Claude 写工具
@claude_tool("get_weather")
def get_weather_for_claude(city): ...

# 给 GPT 写工具（不同的格式）
openai_tool = {
    "type": "function",
    "function": {"name": "get_weather", "parameters": {...}}
}

# 给 DeepSeek 写工具（又是一种格式）
deepseek_tool = {...}
```

三个 AI，三套代码。更糟的是：新出一个 AI 框架 → 再写一套。这个「N×M 适配问题」在软件工程里被各种标准协议解决过（HTTP、SQL、USB），AI 工具接入是最后一个没有标准的领域。

MCP 的解决方案很直接：**工具开发者写一个 MCP Server，所有支持 MCP 的 AI 应用都能用。**

### 1.2 MCP vs Function Calling vs API

| 维度 | Function Calling | 直接调 API | MCP |
|------|:--:|:--:|:--:|
| 标准化 | ❌ 厂商锁定 | ❌ 每次定制 | ✅ 开放协议 |
| 复用 | ❌ 一个模型一套 | ❌ 硬编码 | ✅ 写一次处处用 |
| 发现机制 | ❌ 手动定义 | ❌ 无 | ✅ 自描述 |
| 安全 | 🟡 代码内控制 | 🟡 代码内控制 | ✅ 协议级隔离 |

---

## 二、原理：为什么选 JSON-RPC 2.0

MCP 的通信层选择了 JSON-RPC 2.0 —— 一个 2010 年的老协议。为什么不是 gRPC？不是 REST？

### 2.1 JSON-RPC vs gRPC

```python
# JSON-RPC 2.0 请求（人类可读）
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "get_weather",
        "arguments": {"city": "北京"}
    }
}

# gRPC 请求（需要先定义 .proto 文件）
# syntax = "proto3";
# service WeatherService {
#   rpc GetWeather(WeatherRequest) returns (WeatherResponse);
# }
# message WeatherRequest { string city = 1; }
```

| 维度 | JSON-RPC 2.0 | gRPC |
|------|:--:|:--:|
| 可读性 | ✅ 纯文本，日志直接看 | ❌ 二进制，需要工具 |
| 开发成本 | ✅ 不需要 .proto | ❌ 需要定义→生成桩代码 |
| 类型安全 | ❌ 运行时校验 | ✅ 编译期检查 |
| 性能 | 🟡 文本序列化 | ✅ Protobuf 二进制 |
| 生态 | ✅ 几乎所有语言都有库 | 🟡 需要 protoc |

> MCP 选 JSON-RPC 的根本原因：**降低接入门槛。** 一个 Python 开发者不需要学 Protobuf 就能写 MCP Server。性能在这里不是瓶颈——工具调用的频率远低于模型推理。

### 2.2 JSON-RPC 2.0 消息结构

```python
# 四种消息类型
# 1. 请求（Request）—— 客户端 → 服务端
{"jsonrpc": "2.0", "method": "tools/list", "id": 1}

# 2. 响应（Response）—— 服务端 → 客户端
{"jsonrpc": "2.0", "id": 1, "result": {"tools": [...]}}

# 3. 错误（Error）
{"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}}

# 4. 通知（Notification）—— 不需要响应
{"jsonrpc": "2.0", "method": "notifications/initialized"}
```

---

## 三、机制：MCP 四层架构逐层拆解

### 3.1 完整架构图

```
┌─────────────────────────────────────────┐
│               MCP Host                   │
│  Claude Desktop / Cursor / VS Code      │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │         MCP Client               │    │
│  │  1 个 Client ↔ 1 个 Server       │    │
│  │  管理连接生命周期                  │    │
│  └─────────────┬───────────────────┘    │
└────────────────┼────────────────────────┘
                 │  JSON-RPC 2.0
                 │
┌────────────────┼────────────────────────┐
│                ▼                        │
│           MCP Server                    │
│                                         │
│  ┌──────────┐ ┌────────┐ ┌─────────┐   │
│  │ Resources│ │ Tools  │ │ Prompts │   │
│  │(只读数据) │ │(可执行)│ │(指令模板)│   │
│  └──────────┘ └────────┘ └─────────┘   │
│                    │                    │
│            ┌───────▼───────┐            │
│            │  Data Source   │            │
│            │(文件/DB/API)   │            │
│            └───────────────┘            │
└─────────────────────────────────────────┘
```

### 3.2 四大能力详解

| 能力 | 类型 | 方向 | 示例 |
|------|:--:|:--:|------|
| **Resources** | 只读数据 | Server → Client | 文件内容、数据库查询结果 |
| **Tools** | 可执行 | Client → Server | 发邮件、创建文件、调 API |
| **Prompts** | 指令模板 | Server → Client | 「审阅这段代码」、「翻译成中文」 |
| **Sampling** | 反向推理 | Server → Client | Server 请求 Host 端的 LLM 做推理 |

### 3.3 生命周期

```
① 启动阶段
  Server 启动 → 等待 Client 连接
  Client 连接 → 发送 initialize 请求
  Server 返回能力列表（tools/resources/prompts）
  Client 发送 initialized 通知 → 进入运行态

② 运行阶段
  Client 发送 tools/call → Server 执行并返回
  Client 发送 resources/read → Server 返回数据

③ 关闭阶段
  Client 断开连接 → Server 清理资源
```

---

## 四、传输层：stdio vs Streamable HTTP

### 4.1 stdio：本地进程通信

```
Host 启动 MCP Server 作为子进程
    ↓
通过 stdin → 发 JSON-RPC 请求
通过 stdout ← 收 JSON-RPC 响应
```

```json
// Claude Desktop 配置：本地 stdio 模式
{
    "mcpServers": {
        "weather": {
            "command": "uv",
            "args": ["run", "weather_server.py"]
        }
    }
}
```

**优点**：零网络开销、不需要认证、极简部署。
**缺点**：只能本地用、Host 崩溃 Server 一起死、无法远程访问。

### 4.2 Streamable HTTP：2025 年 3 月的协议升级

原来的 HTTP + SSE 模式有问题：两个端点（`/sse` 监听 + `/messages` 发送），负载均衡器不兼容。Streamable HTTP 把两者合并：

```
旧：GET /sse（持久连接） + POST /messages（发消息）
新：POST /mcp（所有请求走同一个端点）
```

```python
# 启动 HTTP 模式
# mcp run weather_server.py --transport streamable-http --port 8080

# 客户端连接
{
    "mcpServers": {
        "weather": {
            "url": "http://your-server:8080/mcp",
            "transport": "streamable-http"
        }
    }
}
```

**关键改进**：每条请求可以独立鉴权（Bearer Token），天然兼容负载均衡器。

---

## 五、实战：生产级 MCP Server

```python
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("dev-assistant")


# ── Tools ──
@mcp.tool()
async def search_stackoverflow(query: str, limit: int = 3) -> str:
    """搜索 Stack Overflow 相关问题"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.stackexchange.com/2.3/search",
            params={
                "order": "desc", "sort": "relevance",
                "intitle": query, "site": "stackoverflow",
                "pagesize": limit
            },
            timeout=10
        )
        data = resp.json()
        results = []
        for item in data.get("items", []):
            results.append(f"【{item['score']}票】{item['title']}\n{item.get('link', '')}")
        return "\n\n".join(results) if results else "未找到相关结果"


@mcp.tool()
def generate_commit_message(diff: str) -> str:
    """根据 git diff 生成规范的 commit message"""
    # 实际项目中这里调 LLM
    return f"根据 diff 生成 commit message: {diff[:50]}..."

# ── Security Eggs ──
import os

@mcp.tool()
def read_file_safe(path: str) -> str:
    """安全读取文件（限制目录和大小）"""
    BASE_DIR = os.path.expanduser("~/projects")
    full_path = os.path.normpath(os.path.join(BASE_DIR, path))

    # 路径遍历防护
    if not full_path.startswith(BASE_DIR):
        return "拒绝访问：路径越界"

    # 文件大小限制
    if os.path.getsize(full_path) > 5 * 1024 * 1024:  # 5MB
        return "拒绝访问：文件过大"

    with open(full_path, "r") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run()  # 默认 stdio，开发用
    # mcp.run(transport="streamable-http", port=8080)  # 生产用
```

---

## 六、安全：MCP Server 的防线

### 6.1 路径遍历防护

```python
# ❌ 危险：LLM 可以传 ../../etc/passwd
@mcp.tool()
def read_file(path: str) -> str:
    return open(path).read()

# ✅ 安全：限制在指定目录
BASE = "/safe/data"

@mcp.tool()
def read_file_safe(path: str) -> str:
    resolved = os.path.normpath(os.path.join(BASE, path))
    if not resolved.startswith(BASE):
        return "拒绝"
    return open(resolved).read()
```

### 6.2 生产部署：Docker 隔离

```dockerfile
FROM python:3.12-slim
RUN pip install mcp httpx
COPY server.py /app/
WORKDIR /app
CMD ["python", "server.py"]
```

```bash
# 只读文件系统 + 无网络访问 → 就算 LLM 发疯也炸不了宿主机
docker run --rm --read-only --network none my-mcp-server
```

### 6.3 速率限制

```python
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_calls: int = 60, window: int = 60):
        self.max = max_calls
        self.window = window
        self.calls = defaultdict(list)

    def allow(self, tool_name: str) -> bool:
        now = time.time()
        self.calls[tool_name] = [t for t in self.calls[tool_name] if t > now - self.window]
        if len(self.calls[tool_name]) >= self.max:
            return False
        self.calls[tool_name].append(now)
        return True

limiter = RateLimiter(max_calls=30)  # 每个工具每分钟最多 30 次

@mcp.tool()
async def search_web(query: str) -> str:
    if not limiter.allow("search_web"):
        return "请求过于频繁，请稍后再试"
    # ...
```

---

## 七、总结

| 层级 | 选型 | 原因 |
|------|------|------|
| 应用层 | MCP vs 自定义 | 标准化 > 定制 |
| 通信层 | JSON-RPC 2.0 vs gRPC | 可读性 + 低门槛 > 性能 |
| 传输层 | stdio vs Streamable HTTP | 开发用 stdio，生产用 HTTP |
| 安全层 | Docker 隔离 + 速率限制 | 永远不信任 LLM 的输入 |

> MCP 的核心洞察：**AI 工具接入需要标准化，就像 HTTP 标准化了网页传输。** 写一次 MCP Server，所有 AI 都能用——这就是它的全部价值。

---

> 🔖 下一篇：**《Skill 机制深度解析：AI 的能力插件系统》**——从 CLAUDE.md 到社区 Skill 生态。

*标签：#MCP #ModelContextProtocol #Agent #AI工具 #安全 #程序员必读*