# AI 开发基础（第9篇）：Harness Engineering 与知识地图 - 管控整个 Agent 系统

> **适合读者**：已读完前8篇，想了解Agent系统的工程化管控和整体知识体系  
> **预计阅读时间**：35分钟

---

## 前言：从"能跑"到"可管控"

前8篇我们学会了构建一个完整能力的Agent：
- 第1-2篇：底层基础（API、KV Cache）
- 第3篇：核心能力（Agent Loop + Tool Use）
- 第4篇：推理能力（Reasoning + Planning）
- 第5篇：能力扩展（Skills + MCP）
- 第6篇：记忆系统（Memory + RAG）
- 第7篇：协作架构（Subagent + Multi-Agent）
- 第8篇：沟通艺术（Prompt + Context Engineering）

但一个能跑的Agent和一个生产可用的Agent系统之间，还有一个巨大的鸿沟：

**Harness Engineering 就是填补这个鸿沟的工程。**

---

## 一、Harness Engineering：什么是"缰绳"？

### 1.1 概念解释

**Harness** 原意是"马具中的缰绳"。"Harness Engineering"指的是对Agent系统的**管控、约束、监控**。

```
Agent就像一匹马。
没有缰绳：马随意跑，可能跑偏、可能撞到人
有缰绳：马在指定范围内跑，主人随时可以拉住

Harness就是Agent的"缰绳"。
```

### 1.2 五大管控维度

| 维度 | 问题 | 解决方案 |
|------|------|---------|
| **安全** | Agent执行了危险操作（删数据、发邮件） | 权限控制、审批流程、沙箱环境 |
| **成本** | Agent陷入循环，Token无限消耗 | 预算限制、超时控制、熔断机制 |
| **质量** | Agent输出质量不稳定 | 自动评分、人工审核、A/B测试 |
| **可观测性** | Agent出错了不知道哪一步出了问题 | 日志追踪、调用链路、状态快照 |
| **可恢复性** | Agent运行到一半崩溃，从头再来 | 状态持久化、断点续跑 |

---

## 二、安全管控

### 2.1 工具权限分级

```python
from enum import Enum

class PermissionLevel(Enum):
    """工具权限级别"""
    SAFE = "safe"           # 只读，无副作用（查天气、搜索）
    LOW_RISK = "low_risk"   # 低风险，可逆（写文件到指定目录、发草稿）
    HIGH_RISK = "high_risk" # 高风险，需审批（发邮件、删数据、发布上线）


TOOL_PERMISSIONS = {
    "get_weather": PermissionLevel.SAFE,
    "search_web": PermissionLevel.SAFE,
    "write_file": PermissionLevel.LOW_RISK,
    "save_draft": PermissionLevel.LOW_RISK,
    "send_email": PermissionLevel.HIGH_RISK,
    "delete_data": PermissionLevel.HIGH_RISK,
    "deploy": PermissionLevel.HIGH_RISK,
}


async def safe_tool_call(tool_name: str, args: dict) -> str:
    """安全的工具调用"""
    level = TOOL_PERMISSIONS.get(tool_name, PermissionLevel.HIGH_RISK)
    
    if level == PermissionLevel.SAFE:
        return await tool_map[tool_name](**args)
    
    elif level == PermissionLevel.LOW_RISK:
        # 低风险：记录日志，直接执行
        log_tool_call(tool_name, args, level)
        result = await tool_map[tool_name](**args)
        log_tool_result(tool_name, result, level)
        return result
    
    elif level == PermissionLevel.HIGH_RISK:
        # 高风险：需要人工审批
        log_tool_call(tool_name, args, level)
        
        # 发送审批请求
        approval = await request_human_approval(
            tool_name=tool_name,
            args=args,
            reason=f"高风险操作需要人工确认",
        )
        
        if approval.approved:
            result = await tool_map[tool_name](**args)
            log_tool_result(tool_name, result, level)
            return result
        else:
            return f"操作被用户拒绝：{approval.reason}"
```

### 2.2 输入/输出过滤

```python
def filter_output(text: str) -> str:
    """过滤输出中的敏感信息"""
    import re
    
    # 过滤可能包含的API Key
    text = re.sub(r'(api[_-]?key|token|secret)["\s]*[:=]["\s]*["\'][\w-]{20,}["\']', 
                   '[已脱敏]', text, flags=re.IGNORECASE)
    
    # 过滤手机号
    text = re.sub(r'1[3-9]\d{9}', '[手机号已脱敏]', text)
    
    # 过滤邮箱
    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '[邮箱已脱敏]', text)
    
    return text
```

---

## 三、成本管控

### 3.1 Token预算与熔断

```python
class TokenBudget:
    """Token预算管理"""
    
    def __init__(self, max_tokens: int, warn_at: float = 0.8):
        self.max_tokens = max_tokens
        self.warn_at = warn_at
        self.used_tokens = 0
    
    def consume(self, tokens: int) -> bool:
        """消耗Token，返回是否还有预算"""
        self.used_tokens += tokens
        
        if self.used_tokens >= self.max_tokens:
            print(f"🚫 Token预算用完：{self.used_tokens}/{self.max_tokens}")
            return False
        
        if self.used_tokens >= self.max_tokens * self.warn_at:
            print(f"⚠️ Token预算警告：已使用{self.used_tokens/self.max_tokens*100:.0f}%")
        
        return True
    
    @property
    def remaining(self) -> int:
        return self.max_tokens - self.used_tokens


# 在Agent Loop中使用
async def agent_loop_with_budget(messages, tools, budget: TokenBudget, max_rounds=10):
    for round_num in range(max_rounds):
        response = await llm_call(messages, tools)
        usage = response.usage
        
        if not budget.consume(usage.total_tokens):
            return "抱歉，本次对话的Token预算已用完。"
        
        # ... 正常Agent Loop逻辑
```

### 3.2 循环检测

Agent陷入死循环是成本爆炸的常见原因：

```python
def detect_loop(messages: list, window: int = 4) -> bool:
    """检测Agent是否在循环（重复相同内容）"""
    if len(messages) < window * 2:
        return False
    
    # 比较最近几轮的输出是否高度相似
    recent_assistant = [m["content"][:100] for m in messages if m["role"] == "assistant"][-window:]
    
    # 如果最近N轮输出的前100字符都一样，可能是在循环
    if len(set(recent_assistant)) <= 1 and len(recent_assistant) >= 2:
        return True
    
    return False


# 使用
if detect_loop(messages):
    print("⚠️ 检测到Agent循环，强制终止")
    break
```

### 3.3 超时控制

```python
import asyncio

async def call_with_timeout(coro, timeout_seconds: int = 30):
    """带超时的LLM调用"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        print(f"⏰ LLM调用超时（{timeout_seconds}秒）")
        return None
```

---

## 四、可观测性

### 4.1 调用链路追踪

```python
import uuid
import time
from dataclasses import dataclass, field


@dataclass
class AgentTrace:
    """Agent调用链路追踪"""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    spans: list = field(default_factory=list)
    
    def start_span(self, name: str, meta: dict = None):
        """开始一个追踪片段"""
        span = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "start": time.time(),
            "meta": meta or {},
        }
        self.spans.append(span)
        return span
    
    def end_span(self, span_id: str, result: str = None, error: str = None):
        """结束一个追踪片段"""
        for span in self.spans:
            if span["id"] == span_id:
                span["end"] = time.time()
                span["duration_ms"] = (span["end"] - span["start"]) * 1000
                span["result"] = result
                span["error"] = error
                break
    
    def summary(self) -> str:
        """生成追踪摘要"""
        lines = [f"追踪ID: {self.trace_id}"]
        for span in self.spans:
            duration = span.get("duration_ms", 0)
            status = "❌" if span.get("error") else "✅"
            lines.append(f"  {status} {span['name']} ({duration:.0f}ms)")
            if span.get("error"):
                lines.append(f"      错误: {span['error']}")
        return "\n".join(lines)


# 使用
trace = AgentTrace()

span = trace.start_span("LLM调用", {"model": "deepseek-chat", "prompt_tokens": 1500})
response = await llm_call(messages, tools)
trace.end_span(span["id"], result=response.choices[0].message.content[:100])

span = trace.start_span("工具调用", {"tool": "get_weather"})
result = await get_weather(city="北京")
trace.end_span(span["id"], result=result)

print(trace.summary())
# 输出：
# 追踪ID: a1b2c3d4
#   ✅ LLM调用 (1234ms)
#   ✅ 工具调用 (89ms)
```

### 4.2 状态快照

```python
def save_state_snapshot(state: dict, trace_id: str, round_num: int):
    """保存Agent状态快照（用于调试和恢复）"""
    import json
    from datetime import datetime
    
    snapshot = {
        "trace_id": trace_id,
        "round": round_num,
        "timestamp": datetime.now().isoformat(),
        "messages": state["messages"],
        "tool_calls": state["tool_calls"],
    }
    
    filepath = f"traces/{trace_id}_round_{round_num}.json"
    with open(filepath, "w") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
```

---

## 五、可恢复性

### 5.1 状态持久化

```python
import json
import sqlite3
from datetime import datetime


class AgentCheckpoint:
    """Agent检查点：用于断点续跑"""
    
    def __init__(self, db_path: str = "agent_checkpoints.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                session_id TEXT,
                round_num INTEGER,
                messages TEXT,
                state TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, round_num)
            )
        """)
        self.conn.commit()
    
    def save(self, session_id: str, round_num: int, messages: list, state: dict):
        """保存检查点"""
        self.conn.execute(
            "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?, ?)",
            (session_id, round_num, json.dumps(messages), json.dumps(state), datetime.now().isoformat())
        )
        self.conn.commit()
    
    def load(self, session_id: str, round_num: int = None) -> tuple:
        """加载检查点"""
        if round_num:
            row = self.conn.execute(
                "SELECT messages, state FROM checkpoints WHERE session_id=? AND round_num=?",
                (session_id, round_num)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT messages, state FROM checkpoints WHERE session_id=? ORDER BY round_num DESC LIMIT 1",
                (session_id,)
            ).fetchone()
        
        if row:
            return json.loads(row[0]), json.loads(row[1])
        return None, None


# 使用：Agent每次完成一轮后保存检查点
checkpoint = AgentCheckpoint()

# 断点续跑
messages, state = checkpoint.load(session_id="abc123")
if messages:
    print(f"从第{state.get('round', 0)}轮恢复")
    # 继续Agent Loop
```

---

## 六、AI 开发知识地图

### 6.1 9篇内容的关系图

```
                    ┌─────────────┐
                    │  LLM API    │  第1篇：入口
                    │  (调用基础)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  KV Cache   │  第2篇：性能原理
                    │  (推理优化)  │
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │     Agent Loop + Tool    │  第3篇：核心
              │     (让模型能做事)        │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  Reasoning + Planning   │  第4篇：思考
              │  (让模型想清楚再动手)    │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   Skills + MCP          │  第5篇：能力扩展
              │   (模块化 + 标准化)      │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   Memory + RAG          │  第6篇：记忆
              │   (记住用户 + 检索知识)  │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  Subagent + Multi-Agent │  第7篇：协作
              │  (分工 + 多智能体)       │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │ Prompt + Context Eng.   │  第8篇：沟通
              │ (管理模型的全部输入)     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │ Harness + 知识地图       │  第9篇：管控
              │ (安全/成本/可观测/恢复)   │
              └─────────────────────────┘
```

### 6.2 核心概念关联

```
Agent = LLM + Loop + Tools + Memory + Reasoning + Skills

LLM        ← 第1篇（API调用）、第2篇（KV Cache性能）
Loop       ← 第3篇（Agent Loop）、第7篇（Multi-Agent协作）
Tools      ← 第3篇（Tool Use）、第5篇（Skills/MCP标准化）
Memory     ← 第6篇（三层记忆 + RAG）
Reasoning  ← 第4篇（CoT + ReAct + Plan-and-Execute）
Skills     ← 第5篇（能力模块化）、第7篇（角色分工）
Prompt     ← 第8篇（提示词 + 上下文工程）
Harness    ← 第9篇（安全/成本/可观测/恢复）
```

### 6.3 学习路径建议

**入门路径**（1-2周）：
```
第1篇 LLM API → 第3篇 Agent Loop → 动手写一个简单Agent
```

**进阶路径**（3-4周）：
```
第4篇 Reasoning → 第5篇 Skills/MCP → 第6篇 Memory
→ 给Agent加上推理能力、工具、记忆
```

**高级路径**（5-6周）：
```
第7篇 Multi-Agent → 第8篇 Context Engineering → 第9篇 Harness
→ 构建生产级Agent系统
```

### 6.4 每篇的核心收获

| 篇章 | 一句话总结 |
|------|----------|
| 第1篇 | LLM API是所有上层框架的底层，理解参数比会调框架更重要 |
| 第2篇 | KV Cache让推理快2-3倍，但它吃显存，PagedAttention是标准解法 |
| 第3篇 | Agent Loop = LLM判断→工具调用→结果返回→继续循环，50行代码就能跑 |
| 第4篇 | CoT让模型"写出来再回答"，推理模型自带推理能力但贵且慢 |
| 第5篇 | MCP是工具调用的"USB接口"，一次开发处处用 |
| 第6篇 | Memory记住"你"，RAG知道"更多"，两者结合效果最好 |
| 第7篇 | 先单Agent跑通，发现瓶颈再拆Subagent，复杂场景用Multi-Agent |
| 第8篇 | Context Engineering > Prompt Engineering，管理全部输入而不是只写提示词 |
| 第9篇 | 生产环境必须有安全管控、成本限制、可观测性和断点恢复 |

---

## 七、下一步学什么？

学完这9篇，你已经掌握了AI应用开发的核心知识。接下来可以深入的方向：

| 方向 | 推荐资源 |
|------|---------|
| **Agent框架实战** | LangGraph、CrewAI、AutoGen |
| **RAG深度优化** | 混合检索、重排序、知识图谱 |
| **模型微调** | LoRA、QLoRA（低成本微调） |
| **部署运维** | vLLM、TGI、Triton Inference Server |
| **多模态** | 视觉Agent、语音Agent、视频理解 |
| **评估体系** | LLM-as-Judge、人工评估、A/B测试 |

---

## 八、本章总结

**你学到了什么**：

1. **Harness Engineering**：安全管控（权限分级）、成本管控（Token预算+循环检测+超时）、可观测性（调用链路追踪）、可恢复性（状态持久化+断点续跑）
2. **知识地图**：9篇内容从底层API到系统管控的完整知识体系
3. **学习路径**：入门（API+Loop）→ 进阶（推理+Skills+Memory）→ 高级（Multi-Agent+Context+Harness）
4. **核心公式**：Agent = LLM + Loop + Tools + Memory + Reasoning + Skills

**最后一句话**：

AI应用开发的核心不是"调API"，而是**理解Agent如何思考、如何行动、如何记忆、如何协作、如何被管控**。掌握了这些，你就能构建真正有用的Agent系统。

---

## 参考资料

1. Anthropic Building Effective Agents：https://www.anthropic.com/research/building-effective-agents
2. LangGraph文档：https://langchain-ai.github.io/langgraph/
3. OpenAI Safety Best Practices：https://platform.openai.com/docs/guides/safety
4. Prompt Security：https://owasp.org/www-project-top-10-for-large-language-model-applications/

---

**上一篇**：第8篇 Prompt Engineering 与 Context Engineering  
**系列完结** 🎉
