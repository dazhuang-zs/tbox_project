# 【AI Agent 系统教学 14】从 Prompt 到 Context Engineering

> 当你的 Agent 上下文从 1K 涨到 128K，Prompt 技巧就不够用了。
> 你需要管理的不只是"提示词"，而是整个"上下文空间"。

---

## 前言：Agent 的上下文是"动态战场"

在单轮对话中，Prompt 技巧就够了。但在 Agent 的多轮对话中，上下文是**动态变化的**：

- 用户输入在变
- 工具调用结果在累积
- 对话历史在增长
- 记忆在注入
- 时间在流逝

你写的 System Prompt 只是"静态基座"，真正的挑战是**管理这个动态变化的上下文空间**。

这就是 Context Engineering。

---

## 一、Context Engineering 的定义

### 1.1 从 Prompt 到 Context

```
Prompt Engineering：优化"静态"的提示词内容
Context Engineering：管理"动态"的上下文空间
```

**Prompt Engineering 关心的是"写什么"**——措辞、格式、示例。

**Context Engineering 关心的是"放什么"**——哪些信息放进来、哪些不放、放在哪、什么时候放。

### 1.2 Context Engineering 的核心问题

```
1. 哪些信息必须放在上下文中？
2. 哪些信息可以压缩？
3. 哪些信息可以省略？
4. 信息放在什么位置？
5. 什么时候更新上下文？
6. 上下文满了怎么办？
```

---

## 二、上下文的组成

### 2.1 静态部分

```python
STATIC_CONTEXT = {
    "system_prompt": {
        "content": "你是一个 AI Agent...",
        "size": "2000 tokens",
        "position": "开头",
        "update_frequency": "从不",
    },
    "role_definition": {
        "content": "你的角色是...",
        "size": "500 tokens",
        "position": "System Prompt 之后",
        "update_frequency": "从不",
    },
    "tool_definitions": {
        "content": "你可以使用的工具列表",
        "size": "1000 tokens",
        "position": "角色定义之后",
        "update_frequency": "按需",
    },
}
```

### 2.2 动态部分

```python
DYNAMIC_CONTEXT = {
    "user_input": {
        "content": "用户当前输入",
        "size": "100-1000 tokens",
        "position": "上下文末尾",
        "update_frequency": "每轮",
    },
    "conversation_history": {
        "content": "之前的对话",
        "size": "0-5000 tokens",
        "position": "中间",
        "update_frequency": "每轮追加",
    },
    "tool_results": {
        "content": "工具调用返回的结果",
        "size": "0-3000 tokens",
        "position": "用户输入之前",
        "update_frequency": "每次工具调用后",
    },
    "memory": {
        "content": "从长期记忆检索的信息",
        "size": "0-1000 tokens",
        "position": "工具定义之后",
        "update_frequency": "按需检索",
    },
}
```

---

## 三、上下文管理策略

### 3.1 上下文窗口管理

当上下文超过模型的最大窗口时，需要决定**丢弃什么**：

```python
class ContextManager:
    def __init__(self, max_tokens=32000):
        self.max_tokens = max_tokens
        self.context = []
        self.total_tokens = 0
    
    def add(self, content, priority="normal"):
        """添加内容到上下文"""
        tokens = count_tokens(content)
        
        if self.total_tokens + tokens > self.max_tokens:
            self._evict(tokens)
        
        self.context.append(content)
        self.total_tokens += tokens
    
    def _evict(self, needed_tokens):
        """释放空间"""
        # 策略 1：丢弃最早的对话（FIFO）
        if self.strategy == "fifo":
            while self.total_tokens + needed_tokens > self.max_tokens:
                removed = self.context.pop(0)
                self.total_tokens -= count_tokens(removed)
        
        # 策略 2：丢弃优先级最低的内容
        elif self.strategy == "priority":
            priority_order = ["system", "tools", "memory", "history", "tool_results"]
            for p in reversed(priority_order):
                while self._has_priority(p) and self._needs_eviction(needed_tokens):
                    self._remove_priority(p)
        
        # 策略 3：压缩历史对话
        elif self.strategy == "compress":
            if self._has_compressible_content():
                compressed = self._compress_history()
                self._replace_history(compressed)
```

### 3.2 上下文压缩

**压缩方式**：

```python
def compress_conversation(history):
    """压缩对话历史"""
    # 方式 1：摘要压缩
    prompt = f"请用 100 token 以内总结以下对话：\n{history}"
    summary = llm(prompt)
    return summary
    
    # 方式 2：提取关键信息
    # 只保留：用户偏好、已完成任务、重要决策
    # 丢弃：寒暄、确认、重复
    
    # 方式 3：结构化存储
    # 把对话转为结构化格式
    compressed = {
        "user_preferences": {...},
        "completed_tasks": [...],
        "key_decisions": [...],
        "recent_3_turns": [...],
    }
    return json.dumps(compressed)
```

### 3.3 动态位置优化

不同信息放在不同位置，利用模型的注意力分布：

```python
def build_context(user_input, history, tools, memory):
    """
    上下文构建策略：
    
    位置 1（开头，最易被记住）：
    - System Prompt（核心角色定义）
    - 最重要的规则
    
    位置 2（次重要）：
    - 工具定义
    - 记忆信息
    
    位置 3（中间，容易被忽略）：
    - 压缩后的历史对话
    - 工具调用结果
    
    位置 4（末尾，影响力最大）：
    - 当前用户输入
    - 最近一次工具调用结果
    """
    context = [
        ("system", SYSTEM_PROMPT),           # 位置 1
        ("rules", CRITICAL_RULES),            # 位置 1
        ("tools", format_tools(tools)),       # 位置 2
        ("memory", format_memory(memory)),    # 位置 2
        ("history", compress(history)),       # 位置 3
        ("tool_results", recent_results),     # 位置 3
        ("input", user_input),                # 位置 4
    ]
    return context
```

---

## 四、上下文窗口的"预算"管理

### 4.1 Token 预算分配

```python
class TokenBudget:
    """
    128K 上下文窗口的预算分配示例：
    """
    BUDGET = {
        "system_prompt": 2000,      # 1.6%
        "tool_definitions": 3000,   # 2.3%
        "memory": 2000,             # 1.6%
        "conversation_history": 10000,  # 7.8%
        "tool_results": 5000,       # 3.9%
        "current_input": 2000,      # 1.6%
        "reserved": 2000,           # 1.6%
        # 剩余 ~80% 留给模型生成
    }
    
    def check_budget(self, section, content):
        tokens = count_tokens(content)
        if tokens > self.BUDGET.get(section, 1000):
            # 超过预算，需要压缩
            return self.compress(content, self.BUDGET[section])
        return content
```

### 4.2 动态预算调整

根据任务类型动态调整预算：

```python
def adjust_budget(intent, budget):
    if intent == "code_generation":
        # 代码生成任务：需要更多工具定义
        budget["tool_definitions"] = 5000
        budget["conversation_history"] = 5000
    elif intent == "long_discussion":
        # 长对话任务：需要更多历史空间
        budget["tool_definitions"] = 1000
        budget["conversation_history"] = 15000
    elif intent == "search_heavy":
        # 搜索密集型任务：需要更多工具结果空间
        budget["tool_results"] = 10000
        budget["conversation_history"] = 5000
```

---

## 五、Agent 中的 Context Engineering 实战

### 5.1 完整上下文管理类

```python
class AgentContextEngine:
    def __init__(self, model_context_window=128000):
        self.window = model_context_window
        self.budget = TokenBudget()
        self.cache = ContextCache()
        self.compressor = ContextCompressor()
    
    def build_prompt(self, state):
        """构建当前 Agent 的完整上下文"""
        # 1. 静态部分
        system = self._get_system_prompt()
        tools = self._get_tool_definitions(state.active_tools)
        
        # 2. 动态部分
        memory = self._retrieve_memory(state.user_input)
        history = self._get_history(state)
        results = self._get_recent_results(state)
        user_input = state.user_input
        
        # 3. 组装上下文
        context_parts = [
            ("system", system),
            ("tools", tools),
            ("memory", memory),
            ("history", self.compressor.compress(history, self.budget["history"])),
            ("results", results),
            ("input", user_input),
        ]
        
        # 4. 检查预算
        for section, content in context_parts:
            if content:
                content = self.budget.check_budget(section, content)
        
        # 5. 构建最终 Prompt
        return self._assemble(context_parts)
    
    def _assemble(self, parts):
        prompt = []
        for section, content in parts:
            if content:
                prompt.append(f"=== {section.upper()} ===\n{content}")
        return "\n\n".join(prompt)
```

### 5.2 上下文缓存

复用未改变的上下文部分，减少重复计算：

```python
class ContextCache:
    def __init__(self, ttl=300):
        self.cache = {}
        self.ttl = ttl
    
    def get_cached_tools(self, tool_list):
        key = hash(tool_list)
        if key in self.cache and not self._expired(key):
            return self.cache[key]["formatted_tools"]
        
        formatted = self._format_tools(tool_list)
        self.cache[key] = {
            "formatted_tools": formatted,
            "timestamp": time.time(),
        }
        return formatted
```

---

## 六、Context Engineering 的常见陷阱

### 6.1 信息过载

```
❌ 把所有信息都塞进上下文
   用户偏好、历史对话、所有工具定义、所有记忆、当前输入...
   模型被淹没在信息中

✅ 精选信息，只放当前任务需要的
   当前输入 + 相关工具 + 最近的记忆 + 压缩后的历史
```

### 6.2 信息位置错误

```
❌ 把最重要的信息放在中间
   模型对中间信息的关注度最低

✅ 最重要的信息放在开头或末尾
   角色定义 → 开头
   用户输入 → 末尾
```

### 6.3 不及时更新

```
❌ 上下文一直累积，不加清理
   第 50 轮对话时，上下文全是历史信息

✅ 每轮对话都管理上下文
   压缩历史，清理无关信息，更新关键信息
```

### 6.4 忽略上下文变化

```
❌ 认为上下文是静态的
   写了 System Prompt，就不管了

✅ 监控上下文的变化
   检测 token 使用量、信息分布、注意力模式
```

---

## 总结

| 概念 | Prompt Engineering | Context Engineering |
|------|-------------------|-------------------|
| 关注点 | 内容质量 | 空间管理 |
| 核心问题 | 写什么？ | 放什么？不放什么？ |
| 优化目标 | 模型理解准确 | 模型注意力分配 |
| 管理方式 | 一次性设计 | 持续维护 |
| 工具 | 文本编辑器 | 上下文管理器 |

**Prompt Engineering 是艺术，Context Engineering 是工程。**

下一篇文章，我们将进入**模块三：RAG 技术深度解析**——从基础架构到高级策略，完整覆盖检索增强生成的技术体系。

---

**思考题**：
1. 你的 Agent 当前的上下文管理是怎样的？有没有做"预算管理"？
2. 如果模型上下文窗口是 128K，你会怎么分配预算？每个部分占多少？
3. 上下文压缩和上下文截断，在什么场景下用哪个？

---

> 上一篇：[13] 提示词攻击与防御
> 下一篇：[15] RAG 基础架构：检索-阅读-生成
> 系列目录：[README.md](./README.md)