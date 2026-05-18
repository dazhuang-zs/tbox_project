# MCP 协议实战：给 AI 接上外部世界

> 给 Claude 写工具，给 GPT 写插件，给 DeepSeek 写适配……换一个 AI 就得重写一遍。MCP（Model Context Protocol）要解决的就是这个问题——写一个 Server，所有 AI 都能用。

---

## 一、没有 MCP 的世界

```python
# 给 Claude 写工具
@claude_tool
def get_weather(city): ...

# 给 GPT 写工具（语法不一样）
openai_tool = {
    "type": "function",
    "function": {"name": "get_weather", ...}
}

# 给 DeepSeek 写工具（又是另一种格式）
deepseek_tool = {...}
```

三个 AI，三套工具代码。MCP 说：**别重复造轮子了**。

---

## 二、MCP 怎么工作

```
┌──────────────────────────────────────────┐
│                 MCP Host                  │
│  (Claude Desktop / Cursor / VS Code)     │
│                                          │
│   ┌──────────────────────────────────┐   │
│   │          MCP Client              │   │
│   │   (Host 内部，管理连接)           │   │
│   └──────────┬───────────────────────┘   │
└──────────────┼───────────────────────────┘
               │  JSON-RPC 2.0
               │  (stdio 或 HTTP)
┌──────────────▼───────────────────────────┐
│              MCP Server                   │
│  ┌─────────┐ ┌────────┐ ┌─────────┐     │
│  │Resources│ │ Tools  │ │ Prompts │     │
│  └─────────┘ └────────┘ └─────────┘     │
│                                          │
│         ┌──────────────┐                 │
│         │  Data Source  │                │
│         │ (文件/数据库/API)│               │
│         └──────────────┘                 │
└──────────────────────────────────────────┘
```

**四大能力**：

| 能力 | 说明 | 示例 |
|------|------|------|
| **Resources** | 只读数据 | 文件内容、数据库查询结果 |
| **Tools** | 可执行动作 | 发邮件、创建文件、调 API |
| **Prompts** | 预设指令模板 | "审阅这段代码" |
| **Sampling** | Server 反向请求 LLM | 生成摘要 |

---

## 三、写你的第一个 MCP Server

```python
# 安装：pip install mcp

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("我的第一个 MCP Server")


@mcp.tool()
def get_weather(city: str) -> str:
    """获取指定城市的天气信息"""
    weather_db = {
        "北京": "晴，25°C，湿度 40%",
        "上海": "多云，28°C，湿度 65%",
    }
    return weather_db.get(city, f"未找到 {city} 的天气数据")


@mcp.tool()
def calculate(expression: str) -> str:
    """执行数学计算"""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"计算错误：{e}"


@mcp.resource("file://{path}")
def read_local_file(path: str) -> str:
    """读取本地文件内容"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取失败：{e}"


if __name__ == "__main__":
    mcp.run()  # 默认 stdio 模式
```

**保存为 `weather_server.py`**，就这么简单。

---

## 四、配置 Claude Desktop 使用它

编辑 Claude Desktop 配置文件：

```json
// macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
// Windows: %APPDATA%\Claude\claude_desktop_config.json
{
  "mcpServers": {
    "weather-server": {
      "command": "python",
      "args": ["/path/to/weather_server.py"]
    }
  }
}
```

重启 Claude Desktop，在对话中输入：

```
北京今天什么天气？
```

Claude 会自动调用 `get_weather("北京")`，拿到结果后回复。

---

## 五、生产级 MCP Server 写法

### 5.1 工具设计原则

```python
# ❌ 一个工具干三件事
@mcp.tool()
def file_operation(op: str, path: str, content: str = "") -> str:
    if op == "read": ...
    elif op == "write": ...
    elif op == "delete": ...

# ✅ 一个工具干一件事
@mcp.tool()
def read_file(path: str) -> str:
    """读取文件内容"""

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """写入文件"""

@mcp.tool()
def delete_file(path: str) -> str:
    """删除文件"""
```

> **原则**：单一职责、动词+名词命名、参数类型明确、描述写清楚。

### 5.2 HTTP 模式（远程部署）

```python
# pip install mcp[cli]

# 启动 HTTP 模式的 MCP Server
# mcp run weather_server.py --transport streamable-http --port 8080
```

配置 Claude Desktop 远程连接：

```json
{
  "mcpServers": {
    "weather-server": {
      "url": "http://your-server:8080/mcp",
      "transport": "streamable-http"
    }
  }
}
```

### 5.3 安全防护

```python
import os

@mcp.tool()
def read_file_safe(path: str) -> str:
    """安全读取文件（限制目录、大小）"""
    # 1. 路径遍历攻击防护
    safe_base = "/allowed/directory"
    full_path = os.path.normpath(os.path.join(safe_base, path))
    if not full_path.startswith(safe_base):
        return "拒绝：路径越界"

    # 2. 文件大小限制
    if os.path.getsize(full_path) > 10 * 1024 * 1024:  # 10MB
        return "拒绝：文件超过 10MB"

    # 3. 只读打开
    with open(full_path, "r") as f:
        return f.read()
```

---

## 六、MCP 常见 Server 推荐

| MCP Server | 用途 |
|-----------|------|
| **@anthropic/mcp-server-filesystem** | 读写本地文件 |
| **@anthropic/mcp-server-github** | 操作 GitHub（Issue/PR/仓库） |
| **@anthropic/mcp-server-postgres** | 查询 PostgreSQL |
| **Playwright MCP** | 浏览器自动化 |
| **Brave Search MCP** | 网络搜索 |

> MCP Hub：https://mcp-cn.com 有 74+ 个中文 MCP Server。

---

## 七、MCP vs Function Calling vs LangChain Tools

| 维度 | Function Calling | LangChain Tool | MCP |
|------|:--:|:--:|:--:|
| 复用性 | ❌ 绑定 LLM | ❌ 绑定 LangChain | ✅ 一次开发处处用 |
| 标准化 | ❌ 各厂商不同 | ❌ LangChain 专属 | ✅ 开放协议 |
| 远程调用 | ❌ | 需要额外代码 | ✅ 原生支持 HTTP |
| 适合场景 | 单次开发 | LangChain 项目 | 跨平台工具 |

> MCP 不是要替代 Function Calling，而是提供工具接入的**标准化方式**。

---

## 八、总结

1. **MCP = AI 工具的 USB-C**——写一个 Server，所有 AI 都能用
2. **Python 写 MCP Server 只需 3 行装饰器**——FastMCP 极简
3. **本地用 stdio，远程用 HTTP**——两种传输模式覆盖所有场景
4. **工具设计要单一职责**——不要让 LLM 猜一个工具多种用途

---

## 九、生产实战：MCP Server 上线的检查清单

### 9.1 权限隔离——MCP Server 的安全底线

MCP Server 在本地运行时，默认拥有当前用户的全部文件权限。一个 LLM 调了你的 MCP Server，等于有了你的系统权限：

```bash
# 最安全的方式：Docker 隔离运行
# Dockerfile.mcp
FROM python:3.12-slim
RUN pip install mcp
COPY my_server.py /app/
WORKDIR /app
CMD ["python", "my_server.py"]

# 启动时限制文件系统访问
# 只允许读写 /safe_data 目录
docker run --rm \
  -v /safe_data:/safe_data:rw \
  --read-only \
  --network none \
  my-mcp-server
```

> **经验**：不要在生产环境用 `python my_server.py` 直接跑。MCP Server 跑在 Docker 里，限制文件系统和网络访问，就算 LLM 发疯也炸不了宿主机。

### 9.2 高频调用的性能陷阱

一个 Agent 可能在一轮对话中连续调用 10+ 次 MCP 工具。如果 MCP Server 每次都要冷启动，延迟不可接受：

```python
# ❌ 每个请求重连数据库
def get_user(id: str) -> str:
    db = connect_to_db()  # 慢
    result = db.query(id)
    db.close()
    return result

# ✅ 启动时建立连接池，复用
class DatabasePool:
    def __init__(self):
        self.pool = create_connection_pool(min_size=2, max_size=10)
    
    def get_user(self, id: str) -> str:
        with self.pool.get_connection() as conn:
            return conn.query(id)

db_pool = DatabasePool()  # 全局单例

@mcp.tool()
def get_user(id: str) -> str:
    return db_pool.get_user(id)
```

### 9.3 MCP Server 的版本兼容

MCP 协议还在快速演进。2025 年 3 月从 HTTP+SSE 升级到 Streamable HTTP。你的 Server 可能突然不兼容新版 Claude Desktop：

```python
# 用 __version__ 标记协议版本，方便排查
# 如果 Claude Desktop 更新后连不上，先检查协议版本
mcp = FastMCP("my-server", version="1.0.0")

# 锁定 mcp 依赖版本，避免自动升级踩坑
# requirements.txt
mcp==1.8.0
```

### 9.4 调试：看不到 MCP Server 的报错

MCP stdio 模式的报错不会出现在终端里——它藏在日志文件中：

```bash
# Claude Desktop 的 MCP 日志
tail -f ~/Library/Logs/Claude/mcp*.log

# 或者用 MCP Inspector 调试
npx @modelcontextprotocol/inspector python my_server.py
```

### 9.5 测试 MCP Server

```python
import pytest
from mcp import Client

@pytest.mark.asyncio
async def test_get_weather():
    async with Client("python my_server.py") as client:
        result = await client.call_tool("get_weather", {"city": "北京"})
        assert "晴" in result or "雨" in result or "多云" in result
```

---

> 下一篇：**《Multi-Agent 协作：CrewAI 实战》**——让 PM Agent、开发 Agent、测试 Agent 一起干活。

*系列文章：00-总纲 → ①-LLM 原理 → ②-Prompt 工程 → ③-Function Calling → ④-RAG → ⑤-Agent 模式 → ⑥-LangGraph → ⑦-MCP → ⑧-Multi-Agent*
