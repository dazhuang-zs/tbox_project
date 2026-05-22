# AI 开发基础（第5篇）：Skills 与 MCP - Agent 的能力扩展

> **适合读者**：已读完第4篇（Reasoning），想了解Agent能力模块化和标准化  
> **预计阅读时间**：30分钟

---

## 前言：Agent的"技能包"问题

第3篇我们给Agent加了工具（get_weather、search_poi）。工具少的时候还好，但如果Agent有20个工具，你的代码会变成什么样？

```python
# 20个工具的噩梦
tools = [tool_1, tool_2, ..., tool_20]
tool_map = {"tool_1": func_1, "tool_2": func_2, ..., "tool_20": func_20}
```

更麻烦的是：
- 不同项目要用不同的工具组合
- 工具的API变了，要改Agent代码
- 团队里其他人写了新工具，你想复用但格式不兼容

**Skills和MCP就是为了解决这个问题。**

---

## 一、Skills：可复用的能力单元

### 1.1 什么是Skill？

**Skill = 一组相关工具 + 使用说明 + 配置**

不是单个工具，而是一个"能力包"。比如：

| Skill | 包含的工具 | 说明 |
|-------|----------|------|
| 天气Skill | get_weather + get_forecast + get_weather_alert | 天气相关的一组能力 |
| 地图Skill | search_poi + get_route + get_geocode | 地图相关的一组能力 |
| 文档Skill | read_doc + write_doc + search_doc | 文档操作的一组能力 |

### 1.2 Skill的标准结构

```
weather-skill/
├── SKILL.md          # 技能说明（Agent读取这个来了解技能）
├── tools/
│   ├── get_weather.py
│   ├── get_forecast.py
│   └── weather_alert.py
└── config.json       # 配置（API Key、默认参数等）
```

**SKILL.md 是核心**。它告诉Agent这个Skill能做什么、怎么用：

```markdown
# 天气技能

## 描述
获取天气信息，支持实时天气、天气预报、天气预警。

## 工具列表
1. get_weather(city, date) - 获取实时天气
2. get_forecast(city, days) - 获取未来N天预报
3. weather_alert(city) - 获取天气预警

## 使用场景
- 用户问天气时自动触发
- 行程规划时查询目的地天气

## 注意事项
- forecast API免费版只支持7天
- 每分钟调用限制10次
```

### 1.3 在Agent中加载Skill

```python
import json
import importlib.util
from pathlib import Path

class SkillLoader:
    """技能加载器"""
    
    def __init__(self, skill_dirs: list[str]):
        self.tools = []
        self.tool_map = {}
        
        for skill_dir in skill_dirs:
            self._load_skill(skill_dir)
    
    def _load_skill(self, skill_dir: str):
        """加载一个Skill目录下的所有工具"""
        skill_path = Path(skill_dir)
        skill_md = skill_path / "SKILL.md"
        config_path = skill_path / "config.json"
        
        if not skill_md.exists():
            print(f"⚠️ 跳过 {skill_dir}：没有SKILL.md")
            return
        
        # 读取配置
        config = {}
        if config_path.exists():
            config = json.loads(config_path.read_text())
        
        # 读取工具定义
        tools_dir = skill_path / "tools"
        if tools_dir.exists():
            for tool_file in sorted(tools_dir.glob("*.py")):
                self._load_tool(tool_file, config)
    
    def _load_tool(self, tool_file: Path, config: dict):
        """加载单个工具文件"""
        spec = importlib.util.spec_from_file_location(
            tool_file.stem, tool_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 从模块中提取工具信息
        if hasattr(module, 'TOOL_DEF'):
            self.tools.append(module.TOOL_DEF)
        if hasattr(module, 'tool_func'):
            self.tool_map[module.TOOL_DEF['function']['name']] = module.tool_func
        
        print(f"  ✅ 加载工具: {module.TOOL_DEF['function']['name']}")


# 使用
loader = SkillLoader(["skills/weather", "skills/map"])
agent = run_agent(messages, loader.tools, loader.tool_map)
```

**好处**：
1. 工具按Skill分组，管理清晰
2. 新增Skill只需复制目录，不改Agent代码
3. 不同项目可以组合不同的Skill

---

## 二、MCP：连接模型与外部世界的标准协议

### 2.1 为什么需要MCP？

**问题**：每个大模型厂商的Function Calling格式不一样。

```python
# OpenAI的格式
{"type": "function", "function": {"name": "...", "parameters": {...}}}

# Anthropic Claude的格式
{"name": "...", "input_schema": {...}}

# DeepSeek的格式（兼容OpenAI，但有些差异）
# Google Gemini的格式（又是另一种）
```

如果你写了一个工具，想同时给GPT-4、Claude、DeepSeek用，你得适配4种格式。

**MCP（Model Context Protocol）**就是为了解决这个"巴别塔"问题。

### 2.2 MCP是什么？

MCP是Anthropic在2024年底提出的**开放标准协议**，类似USB接口：

- **USB统一了硬件接口** → 一个U盘插任何电脑都能用
- **MCP统一了模型和工具的接口** → 一个工具接任何模型都能用

**核心概念**：

| 概念 | 说明 |
|------|------|
| **MCP Server** | 工具提供方（如天气API、数据库、文件系统） |
| **MCP Client** | 模型/Agent（如Claude Desktop、你的Agent代码） |
| **MCP Protocol** | 通信协议（JSON-RPC over stdio/SSE） |

### 2.3 MCP的工作原理

```
┌──────────┐     MCP Protocol      ┌──────────────┐
│  Agent    │ ◄──────────────────► │  MCP Server   │
│ (Client)  │   JSON-RPC 2.0       │  (天气服务)    │
└──────────┘                       └──────────────┘
      │
      │  同时连接多个Server
      ▼
┌──────────────┐
│  MCP Server   │
│  (文件系统)    │
└──────────────┘
```

**通信流程**：
```
1. Client → Server: "你有哪些工具？"（tools/list）
2. Server → Client: "我有 get_weather、get_forecast"
3. Client → Server: "调用 get_weather(city=北京)"（tools/call）
4. Server → Client: "结果：晴 18-30°C"
```

### 2.4 写一个MCP Server

用Python + FastMCP（官方库）：

```python
# weather_mcp_server.py
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("天气服务")

@mcp.tool()
async def get_weather(city: str, date: str = "今天") -> str:
    """获取城市天气信息
    
    Args:
        city: 城市名称
        date: 日期，默认"今天"
    """
    # 真实项目中这里调外部API
    weather_db = {
        "北京": {"今天": "晴 18-30°C", "明天": "多云 15-28°C"},
        "上海": {"今天": "阴 22-28°C", "明天": "小雨 20-25°C"},
    }
    result = weather_db.get(city, {}).get(date, f"{city}{date}：暂无数据")
    return f"{city}{date}的天气：{result}"


@mcp.tool()
async def get_weather_alert(city: str) -> str:
    """获取天气预警信息
    
    Args:
        city: 城市名称
    """
    # 模拟预警查询
    return f"{city}当前无天气预警"


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**运行**：
```bash
pip install mcp
python weather_mcp_server.py
```

就这么简单。**任何支持MCP的Client都可以调用这两个工具**，不管是Claude Desktop、Cursor、还是你自己的Agent。

### 2.5 在Agent中使用MCP Client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def create_mcp_tool_map(server_script: str):
    """从MCP Server获取工具列表"""
    server_params = StdioServerParameters(
        command="python",
        args=[server_script],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 获取工具列表
            tools_result = await session.list_tools()
            tools = []
            tool_map = {}
            
            for tool in tools_result.tools:
                # 转换为OpenAI格式
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    }
                })
                tool_map[tool.name] = tool
            
            return tools, session, tool_map


# 调用工具时
async def call_mcp_tool(session, tool_name: str, args: dict) -> str:
    """通过MCP调用工具"""
    result = await session.call_tool(tool_name, arguments=args)
    return result.content[0].text
```

### 2.6 MCP vs 直接Function Calling

| 对比项 | 直接Function Calling | MCP |
|--------|--------------------|-----|
| **格式适配** | 每个模型格式不同，需适配 | 统一协议，一次开发处处用 |
| **工具发现** | 手动注册 | 自动发现（tools/list） |
| **工具管理** | 工具代码和Agent代码耦合 | 独立进程，解耦 |
| **生态共享** | 工具不能跨项目复用 | MCP Server可以被任何Client使用 |
| **性能** | 直接调用，延迟低 | 进程间通信，略有延迟 |
| **部署** | 简单 | 需要启动Server进程 |

**什么时候用MCP**：
- 工具需要被多个Agent/模型复用 → MCP
- 团队协作，工具由不同人开发 → MCP
- 简单个人项目，一两个工具 → 直接Function Calling就够

---

## 三、真实项目：Skills + MCP 的组合使用

### 3.1 智能行程规划助手 v2

第一版（第3篇）：工具直接写在Agent代码里
第二版：用Skills组织 + MCP标准化

```
smart-trip-planner/
├── agent/
│   ├── main.py              # Agent主程序
│   └── skill_loader.py      # Skill加载器
├── skills/
│   ├── weather/
│   │   ├── SKILL.md
│   │   ├── config.json
│   │   ├── weather_server.py  # MCP Server
│   │   └── tools/
│   ├── map/
│   │   ├── SKILL.md
│   │   ├── config.json
│   │   └── map_server.py      # MCP Server（封装高德API）
│   ├── restaurant/
│   │   ├── SKILL.md
│   │   └── restaurant_server.py
│   └── calendar/
│       ├── SKILL.md
│       └── calendar_server.py
└── configs/
    └── production.json       # 生产环境配置
```

**好处**：
1. **新增能力**：加一个skill目录就行，不改Agent代码
2. **团队协作**：张三负责天气Skill，李四负责地图Skill，互不干扰
3. **复用**：天气Skill可以直接给另一个项目用
4. **测试**：每个Skill独立测试

### 3.2 动态加载Skill

```python
import asyncio
from pathlib import Path

class SmartAgent:
    """支持动态加载Skill的Agent"""
    
    def __init__(self):
        self.tools = []
        self.sessions = {}
    
    async def load_skill(self, skill_dir: str):
        """加载一个Skill（通过MCP连接）"""
        skill_path = Path(skill_dir)
        server_script = skill_path / "server.py"
        
        if not server_script.exists():
            print(f"⚠️ {skill_dir} 没有server.py，跳过")
            return
        
        tools, session, tool_map = await create_mcp_tool_map(str(server_script))
        self.tools.extend(tools)
        self.sessions.update(tool_map)
        print(f"✅ 加载Skill: {skill_path.name}（{len(tools)}个工具）")
    
    async def run(self, user_input: str):
        """运行Agent"""
        if not self.tools:
            print("⚠️ 没有加载任何Skill")
            return
        
        # 使用加载的所有工具运行Agent Loop
        messages = [
            {"role": "system", "content": "你是一个智能助手。"},
            {"role": "user", "content": user_input},
        ]
        
        # ... Agent Loop（同第3篇）


# 使用
async def main():
    agent = SmartAgent()
    await agent.load_skill("skills/weather")
    await agent.load_skill("skills/map")
    await agent.load_skill("skills/restaurant")
    
    await agent.run("北京明天天气怎么样？帮我找附近的火锅店")

asyncio.run(main())
```

---

## 四、MCP生态现状

### 4.1 主流工具对MCP的支持

| 工具/平台 | MCP支持情况 |
|----------|-----------|
| **Claude Desktop** | 原生支持，官方推荐 |
| **Cursor** | 支持，用于代码编辑 |
| **Windsurf** | 支持 |
| **LangChain** | 通过langchain-mcp-adapters支持 |
| **OpenClaw** | 原生支持 |
| **自建Agent** | 通过mcp Python SDK支持 |

### 4.2 热门MCP Server

| Server | 功能 |
|--------|------|
| filesystem | 文件读写 |
| github | GitHub操作（Issue、PR、代码） |
| postgres/sqlite | 数据库查询 |
| brave-search | 网络搜索 |
| slack | Slack消息操作 |
| puppeteer | 浏览器自动化 |

这些Server都是开源的，直接`pip install`或`npx`就能用。

---

## 五、本章总结

**你学到了什么**：

1. **Skills**：把相关工具打包成一个能力单元，方便管理和复用
2. **MCP**：统一的工具调用协议，一次开发处处用，类似"USB接口"
3. **MCP Server**：用FastMCP几行代码就能写一个，任何MCP Client都能调用
4. **Skills + MCP结合**：Skill作为组织单位，MCP作为通信协议，两者互补
5. **动态加载**：Agent运行时按需加载Skill，灵活组合

**关键公式**：
```
Skill = 工具组 + 说明文档 + 配置
MCP = 统一的Client-Server通信协议
Skills + MCP = 模块化 + 标准化
```

**下一篇预告**：
- 第6篇：Memory - 让 Agent 拥有记忆
- 你会学到：短期记忆、长期记忆、RAG、对话管理

---

## 参考资料

1. MCP官方规范：https://modelcontextprotocol.io/
2. MCP Python SDK：https://github.com/modelcontextprotocol/python-sdk
3. Anthropic MCP公告：https://www.anthropic.com/news/model-context-protocol
4. FastMCP文档：https://github.com/jlowin/fastmcp

---

**上一篇**：第4篇 Reasoning 与 Planning  
**下一篇**：第6篇 Memory
