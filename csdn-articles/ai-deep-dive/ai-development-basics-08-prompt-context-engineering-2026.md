# AI 开发基础（第8篇）：Prompt Engineering 与 Context Engineering - 与模型沟通的艺术

> **适合读者**：已读完第7篇（Multi-Agent），想深入理解如何有效控制模型输出  
> **预计阅读时间**：35分钟

---

## 前言：为什么前面7篇都绕不开"提示词"？

回顾一下，前7篇里我们已经用到了大量提示词：
- 第3篇Agent Loop：system prompt定义Agent行为
- 第4篇Reasoning："请一步步思考"触发CoT
- 第6篇Memory：把用户画像注入prompt
- 第7篇Multi-Agent：每个Agent有不同的system prompt

**提示词是你和LLM之间唯一的沟通方式。** 写不好提示词，模型再强也发挥不出来。

但"提示词工程"这个词现在有个更大的进化：**Context Engineering（上下文工程）**。

---

## 一、Prompt Engineering：让模型听懂你

### 1.1 提示词的三个层次

| 层次 | 说明 | 例子 |
|------|------|------|
| **指令** | 直接告诉模型做什么 | "翻译成英文" |
| **上下文** | 提供背景信息帮助理解 | "这是一份法律合同，请翻译" |
| **示例** | 给出期望的输入输出格式 | "输入：你好 → 输出：Hello" |

**好的提示词 = 清晰的指令 + 充足的上下文 + 典型的示例**

### 1.2 结构化提示词模板

```python
def build_prompt(task: str, context: str = "", examples: list = None, constraints: list = None):
    """构建结构化提示词"""
    parts = []
    
    # 指令
    parts.append(f"## 任务\n{task}")
    
    # 上下文
    if context:
        parts.append(f"## 背景\n{context}")
    
    # 示例
    if examples:
        parts.append("## 示例")
        for i, ex in enumerate(examples, 1):
            parts.append(f"### 示例{i}\n输入：{ex['input']}\n输出：{ex['output']}")
    
    # 约束
    if constraints:
        parts.append("## 约束")
        for c in constraints:
            parts.append(f"- {c}")
    
    return "\n\n".join(parts)


# 使用
prompt = build_prompt(
    task="将中文技术文章摘要翻译成英文，保持专业术语准确。",
    context="目标读者是国际开发者，文章关于AI Agent开发。",
    examples=[
        {"input": "本文介绍了Agent Loop的核心概念", "output": "This article introduces the core concepts of Agent Loop"},
    ],
    constraints=[
        "专业术语保留英文（如 Agent、RAG、MCP）",
        "不要意译，忠实原文",
        "输出格式为纯文本，不加额外说明",
    ],
)
```

### 1.3 高频提示词技巧

#### 技巧1：角色设定

```
你是一个有10年经验的Python高级工程师。你写的代码：
- 遵循PEP 8规范
- 有类型注解
- 有docstring
- 处理边界情况
```

**为什么有效**：LLM训练数据中有大量"高级工程师写的代码"和"初级工程师写的代码"。角色设定帮你锁定"高级"那一部分。

#### 技巧2：输出格式控制

```
请按以下JSON格式输出：
{
    "analysis": "分析结论",
    "confidence": 0.0-1.0的置信度,
    "suggestions": ["建议1", "建议2"]
}
```

**踩坑**：有时候LLM不严格按格式输出。加一句"只输出JSON，不要其他内容"可以改善。更可靠的方案是用Structured Output（第1篇提过的Function Calling方式）。

#### 技巧3：Few-Shot示例

```
## 分类任务

示例1：
输入：今天天气真好，心情不错
输出：{"sentiment": "positive", "category": "日常"}

示例2：
这个Bug我已经改了3遍了，还是不对
输出：{"sentiment": "negative", "category": "工作"}

现在请分类：
输入：新的AI模型发布了，比上一代快3倍
输出：
```

**经验**：3个示例通常就够了。太少（1个）模型可能过拟合那个模式，太多（10个）浪费Token。

#### 技巧4：负向提示

```
不要：
- 不要用Markdown标题
- 不要添加"这里是翻译结果"之类的说明
- 不要省略原文中的数字和日期

必须：
- 必须保持原文的段落结构
- 必须保留所有超链接
```

**经验**：负向提示比正向提示更有效。模型知道"不该做什么"后，犯错率明显降低。

---

## 二、Context Engineering：管理模型的全部输入

### 2.1 Prompt Engineering → Context Engineering

传统Prompt Engineering关注的是"你写的那段文字"。但模型的输入远不止你写的提示词：

```
模型的完整输入（Context）=

  System Prompt          ← 你定义的Agent角色和行为
  + 对话历史              ← 之前的多轮对话
  + 工具定义              ← Function Calling的工具schema
  + RAG检索结果           ← 向量数据库检索的知识
  + 用户画像              ← 之前存储的用户偏好
  + 代码上下文            ← 如果在做代码相关任务
  + 任务状态              ← Multi-Agent的共享状态

= Context
```

**Context Engineering = 管理这所有输入的工程。** 不只是"写好提示词"，而是确保整个上下文都是高质量、相关的。

### 2.2 上下文窗口的预算管理

假设模型有128K Token的上下文窗口，你怎么分配？

| 组成部分 | 建议分配 | 说明 |
|---------|---------|------|
| System Prompt | ~2K | 角色定义+行为规则，够用就行 |
| 工具定义 | ~5-15K | 取决于工具数量和schema大小 |
| 用户画像 | ~1K | 偏好摘要 |
| RAG检索结果 | ~5-10K | 最相关的3-5段 |
| 对话历史 | 剩余空间 | 越多越好，但需要裁剪 |
| 用户输入 | ~1K | 当前问题 |
| 输出预留 | ~4K | 给模型留足回答空间 |

**代码实现**：

```python
class ContextManager:
    """上下文管理器"""
    
    def __init__(self, max_context_tokens: int = 120000):
        self.max_tokens = max_context_tokens
        self.reserved = {
            "system": 2000,
            "tools": 0,      # 动态计算
            "profile": 1000,
            "rag": 8000,
            "input": 1000,
            "output": 4000,
        }
    
    def calculate_budgets(self, tool_schemas: list, rag_results: list, 
                          history: list, profile: dict) -> dict:
        """计算各部分的Token预算"""
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o-mini")
        
        # 动态计算工具定义的大小
        tool_tokens = sum(
            len(enc.encode(json.dumps(t))) for t in tool_schemas
        )
        self.reserved["tools"] = tool_tokens
        
        # 已固定占用
        fixed = sum(self.reserved.values()) - self.reserved["tools"]
        available_for_history = self.max_tokens - fixed - tool_tokens - self.reserved["rag"]
        
        return {
            "system": self.reserved["system"],
            "tools": tool_tokens,
            "profile": self.reserved["profile"],
            "rag": self.reserved["rag"],
            "history": max(0, available_for_history),
            "input": self.reserved["input"],
            "output": self.reserved["output"],
        }
    
    def build_context(self, system_prompt: str, tool_schemas: list,
                      rag_results: list, history: list,
                      profile: dict, user_input: str) -> list:
        """构建完整的上下文"""
        budgets = self.calculate_budgets(tool_schemas, rag_results, history, profile)
        
        messages = []
        
        # System Prompt
        messages.append({"role": "system", "content": system_prompt})
        
        # 用户画像（注入到system prompt）
        if profile:
            messages[-1]["content"] += f"\n\n用户信息：{json.dumps(profile, ensure_ascii=False)}"
        
        # 对话历史（按预算裁剪）
        trimmed_history = self._trim_to_budget(history, budgets["history"])
        messages.extend(trimmed_history)
        
        # RAG结果
        if rag_results:
            rag_text = "参考信息：\n" + "\n".join(rag_results)
            messages.append({"role": "user", "content": rag_text})
            messages.append({"role": "assistant", "content": "好的，我已阅读参考信息。"})
        
        # 用户输入
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _trim_to_budget(self, messages: list, max_tokens: int) -> list:
        """裁剪消息到预算范围内"""
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o-mini")
        
        kept = []
        total = 0
        for msg in reversed(messages):
            tokens = len(enc.encode(msg["content"]))
            if total + tokens > max_tokens:
                break
            kept.insert(0, msg)
            total += tokens
        
        return kept
```

### 2.3 动态上下文

**高级用法**：根据用户输入动态决定需要什么上下文。

```python
async def dynamic_context(user_input: str, user_id: str) -> list:
    """动态构建上下文"""
    
    # 第1步：用一个小模型快速分析，判断需要哪些上下文
    analysis = await small_model_call(f"""分析用户输入，判断需要哪些上下文（多选）：
- history: 对话历史
- profile: 用户画像
- rag: 知识库检索
- tools: 工具调用

用户输入：{user_input}

只输出需要的上下文名称，逗号分隔。""")
    
    needed = [x.strip() for x in analysis.content.split(",")]
    messages = [{"role": "system", "content": "你是一个智能助手。"}]
    
    if "profile" in needed:
        profile = get_user_profile(user_id)
        if profile:
            messages[-1]["content"] += f"\n用户画像：{json.dumps(profile)}"
    
    if "history" in needed:
        messages.extend(get_recent_history(user_id, n=10))
    
    if "rag" in needed:
        results = await knowledge_search(user_input, top_k=3)
        if results:
            messages.append({"role": "user", "content": f"参考资料：\n" + "\n".join(results)})
            messages.append({"role": "assistant", "content": "已阅读参考资料。"})
    
    messages.append({"role": "user", "content": user_input})
    return messages
```

**好处**：不是每次都塞满所有上下文。简单问题少塞，复杂问题多塞，Token利用率更高。

---

## 三、提示词工程 vs 上下文工程的区别

| | Prompt Engineering | Context Engineering |
|--|-------------------|-------------------|
| **关注点** | 你写的提示词文本 | 模型的全部输入 |
| **范围** | system prompt + 用户消息 | prompt + history + tools + RAG + profile + ... |
| **目标** | 让模型理解你的意图 | 让模型在最优上下文中工作 |
| **技术** | 角色设定、Few-Shot、CoT | Token预算管理、动态裁剪、RAG检索、记忆注入 |
| **类比** | 写好一篇演讲稿 | 准备好演讲的全部环境（灯光、音响、观众背景） |

**Context Engineering是Prompt Engineering的升级版。** 它告诉你：不只是"写好提示词"，而是管理好模型能看到的所有信息。

---

## 四、真实项目经验

### 4.1 CSDN文章生成的上下文管理

```python
async def article_context(topic: str) -> list:
    """文章生成的上下文构建"""
    messages = [
        {
            "role": "system",
            "content": """你是一个技术文章写作专家。
写作规范：
- 代码必须完整可运行
- 数据必须有来源
- 有真实踩坑经验
- 面向中级开发者
- 3000-5000字"""
        }
    ]
    
    # 检索相关文章（作为风格参考）
    related = await search_my_articles(topic, top_k=2)
    if related:
        ref_text = "你的历史文章风格参考：\n"
        for article in related:
            ref_text += f"- {article['title']}\n"
        messages.append({"role": "user", "content": ref_text})
        messages.append({"role": "assistant", "content": "好的，我会参考这些文章的风格。"})
    
    # 搜索竞品文章（了解别人怎么写的）
    competitors = await search_web(topic, top_k=3)
    if competitors:
        comp_text = "竞品文章概要：\n"
        for c in competitors:
            comp_text += f"- {c['title']}: {c['summary']}\n"
        messages.append({"role": "user", "content": comp_text})
        messages.append({"role": "assistant", "content": "好的，我会参考但保持原创。"})
    
    messages.append({"role": "user", "content": f"请写一篇关于：{topic}"})
    return messages
```

### 4.2 提示词版本管理

**生产环境必须做的**：

```
prompts/
├── v1/
│   ├── agent_system.txt
│   ├── coder_system.txt
│   └── reviewer_system.txt
├── v2/
│   ├── agent_system.txt
│   ├── coder_system.txt
│   └── reviewer_system.txt
└── CHANGELOG.md   # 记录每次改了什么、为什么改
```

```python
import hashlib

def prompt_hash(prompt: str) -> str:
    """计算提示词hash，用于追踪版本"""
    return hashlib.md5(prompt.encode()).hexdigest()[:8]

# 每次LLM调用记录使用的提示词版本
log_entry = {
    "prompt_hash": prompt_hash(system_prompt),
    "prompt_version": "v2",
    "input": user_input,
    "output": response.content,
    "tokens": response.usage.total_tokens,
    "timestamp": "2026-05-22T08:00:00Z",
}
```

**踩坑**：改了提示词后效果变差，但忘了改了什么。版本管理+hash追踪可以避免这个问题。

---

## 五、本章总结

**你学到了什么**：

1. **Prompt Engineering四技巧**：角色设定、输出格式控制、Few-Shot示例、负向提示
2. **Context Engineering**：不只是写好提示词，而是管理模型的所有输入
3. **Token预算管理**：按优先级分配上下文窗口空间
4. **动态上下文**：根据输入判断需要哪些上下文，不浪费Token
5. **提示词版本管理**：生产环境必须追踪提示词变更

**关键公式**：
```
Context = System Prompt + History + Tools + RAG + Profile + Input
Context Engineering = Token预算分配 + 动态裁剪 + 相关性检索
```

**下一篇预告**：
- 第9篇：Harness Engineering 与知识地图 - 管控整个Agent系统

---

## 参考资料

1. OpenAI Prompt Guide：https://platform.openai.com/docs/guides/prompt-engineering
2. Anthropic Prompt Guide：https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering
3. Prompt Patterns论文：https://arxiv.org/abs/2102.07484
4. Context Engineering综述：https://www.anthropic.com/research/building-effective-agents

---

**上一篇**：第7篇 Subagent 与 Multi-Agent  
**下一篇**：第9篇 Harness Engineering 与知识地图
