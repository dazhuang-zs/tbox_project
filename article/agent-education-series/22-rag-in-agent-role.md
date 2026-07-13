# 【AI Agent 系统教学 22】RAG 在 Agent 中的角色

> RAG 不是 Agent 的"附件"，而是 Agent 的"知识器官"。
> 但怎么把这个器官"接"到 Agent 身上，有很多种方式。

---

## 前言：RAG 不是"问知识库"那么简单

在 Agent 中，RAG 的角色远不止"搜索知识库"这么简单。它承担着多个核心功能：

1. **知识获取**：获取模型不知道或不确定的信息
2. **事实核查**：验证模型输出的事实准确性
3. **上下文补充**：为 Agent 决策提供背景信息
4. **记忆补充**：补充长期记忆中的信息
5. **工具支持**：为工具调用提供参数和上下文

理解 RAG 在 Agent 中的完整角色，才能设计出真正高效的 Agent 系统。

---

## 一、RAG 作为 Agent 的工具

### 1.1 最常用的集成方式

把 RAG 封装成一个工具，Agent 通过工具调用获取知识：

```python
@tool
def search_knowledge_base(query: str, k: int = 5) -> str:
    """
    搜索内部知识库，获取与查询相关的信息。
    当你需要获取公司内部知识、产品信息、技术文档时使用。
    
    Args:
        query: 搜索关键词
        k: 返回的文档数量
    """
    docs = retriever.retrieve(query, k=k)
    return format_docs(docs)
```

### 1.2 RAG 工具的触发时机

Agent 需要在合适的时机调用 RAG 工具。可以通过 System Prompt 来引导：

```python
system_prompt = """
你的行为规则：
1. 对于任何需要事实信息的问题，优先使用 search_knowledge_base 工具
2. 只有在你非常有把握的信息上，才凭记忆回答
3. 模棱两可时，使用工具
"""
```

### 1.3 多个 RAG 工具

不同场景需要不同的 RAG 工具：

```python
@tool("search_product_docs")
def search_product_docs(query: str):
    """搜索产品文档"""
    return product_retriever.retrieve(query)

@tool("search_tech_docs")
def search_tech_docs(query: str):
    """搜索技术文档"""
    return tech_retriever.retrieve(query)

@tool("search_policy")
def search_policy(query: str):
    """搜索公司政策"""
    return policy_retriever.retrieve(query)
```

---

## 二、RAG 与 Agent Memory 的关系

### 2.1 两者的区别

```
Agent Memory：存储"这个人说过什么"（个性化）
RAG：存储"知识库有什么"（通用知识）

              Memory                   RAG
存储内容：  对话历史、用户偏好         文档、知识库
更新频率：  每轮对话                   按需更新
数据量：    小（几万 token）           大（百万级）
访问方式：  按时间或语义检索           纯语义检索
持久性：    随会话结束                 永久
```

### 2.2 结合使用

```python
class AgentWithMemoryAndRAG:
    def __init__(self, memory, rag):
        self.memory = memory
        self.rag = rag
    
    def respond(self, user_input):
        # 1. 从记忆中检索相关历史
        relevant_history = self.memory.retrieve(user_input)
        
        # 2. 从 RAG 中检索相关知识
        relevant_knowledge = self.rag.retrieve(user_input)
        
        # 3. 构建上下文
        context = {
            "history": relevant_history,
            "knowledge": relevant_knowledge,
        }
        
        # 4. 生成回答
        response = self.generate(user_input, context)
        
        # 5. 更新记忆
        self.memory.store(user_input, response)
        
        return response
```

### 2.3 信息优先级

当 Memory 和 RAG 提供的信息冲突时：

```
优先级：Memory > RAG > 模型内部知识

原因：
- Memory 记录的是"这个用户说过的话"，最可信
- RAG 来自知识库，可信但可能过时
- 模型内部知识最不可靠（可能幻觉）
```

---

## 三、RAG 在 Agent 循环中的位置

### 3.1 多种集成模式

**模式一：前置检索（推荐）**

```
用户输入 → RAG 检索 → 注入上下文 → Agent 推理 → 输出
```

RAG 在 Agent 推理之前完成，Agent 的上下文已经包含了检索结果。

**模式二：按需检索**

```
用户输入 → Agent 推理 → 需要信息 → 调用 RAG 工具 → 继续推理 → 输出
```

Agent 在推理过程中，发现需要更多信息时，主动调用 RAG 工具。

**模式三：后置验证**

```
用户输入 → Agent 推理 → 输出 → RAG 验证 → 修正 → 最终输出
```

Agent 先凭记忆回答，然后 RAG 检查是否有事实错误，修正后输出。

### 3.2 模式选择

```python
def select_rag_mode(task_type):
    """根据任务类型选择 RAG 集成模式"""
    if task_type == "factual_qa":
        # 事实问答：必须准确，前置检索
        return "pre_retrieval"
    
    elif task_type == "creative_task":
        # 创作任务：需要灵感，按需检索
        return "on_demand"
    
    elif task_type == "critical_decision":
        # 关键决策：不能出错，前置+后置双保险
        return "pre_and_post"
    
    else:
        return "on_demand"
```

### 3.3 完整示例

```python
class RAGAgent:
    def __init__(self, llm, retriever, memory):
        self.llm = llm
        self.retriever = retriever
        self.memory = memory
    
    def respond(self, user_input, mode="pre_retrieval"):
        if mode == "pre_retrieval":
            return self._pre_retrieval(user_input)
        elif mode == "on_demand":
            return self._on_demand(user_input)
        elif mode == "pre_and_post":
            return self._pre_and_post(user_input)
    
    def _pre_retrieval(self, user_input):
        # 1. 检索
        knowledge = self.retriever.retrieve(user_input)
        
        # 2. 注入上下文
        prompt = self._build_prompt(user_input, knowledge)
        
        # 3. 生成
        return self.llm.generate(prompt)
    
    def _on_demand(self, user_input):
        """Agent 在循环中自主决定是否检索"""
        system_prompt = """
        你是一个 AI Agent。如果你需要获取信息，可以使用 search_knowledge 工具。
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        
        # Agent 循环：根据工具调用结果决定是否继续检索
        for _ in range(5):
            response = self.llm.generate(messages)
            if self._has_tool_call(response):
                tool_result = self._execute_tool(response)
                messages.append({"role": "tool", "content": tool_result})
            else:
                return response
    
    def _pre_and_post(self, user_input):
        # 前置检索
        knowledge = self.retriever.retrieve(user_input)
        prompt = self._build_prompt(user_input, knowledge)
        response = self.llm.generate(prompt)
        
        # 后置验证
        verification = self._verify_with_rag(response, user_input)
        if verification["has_errors"]:
            response = self._correct_response(response, verification)
        
        return response
```

---

## 四、RAG 的高级集成模式

### 4.1 多级 RAG

```
用户输入
    ↓
第一级 RAG：快速检索（top-3，200ms，高精度）
    ↓
如果信息不足 → 第二级 RAG：深度检索（top-10，500ms，高召回）
    ↓
如果信息仍不足 → 第三级 RAG：多轮检索（多次检索，2s，全面）
    ↓
最终回答
```

### 4.2 RAG 与工具链

RAG 不是单独存在的，它是一个工具链的一部分：

```
用户输入
    ↓
查询改写（LLM）
    ↓
检索（向量数据库）
    ↓
重排序（重排序模型）
    ↓
上下文注入（Prompt 模板）
    ↓
生成（LLM）
    ↓
后验验证（RAG）
    ↓
输出
```

### 4.3 RAG 缓存

高频查询的检索结果可以缓存：

```python
class RAGCache:
    def __init__(self, ttl=3600, max_size=1000):
        self.cache = {}
        self.ttl = ttl
        self.max_size = max_size
    
    def get(self, query):
        """获取缓存的检索结果"""
        key = self._normalize(query)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["results"]
        return None
    
    def set(self, query, results):
        """缓存检索结果"""
        key = self._normalize(query)
        if len(self.cache) >= self.max_size:
            # 淘汰最旧的
            oldest = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest]
        
        self.cache[key] = {
            "results": results,
            "timestamp": time.time(),
        }
    
    def _normalize(self, query):
        """标准化查询，提高缓存命中率"""
        return query.strip().lower()
```

---

## 五、RAG 的局限性在 Agent 中的表现

### 5.1 检索延迟

```
Agent 多轮对话中，每次都需要检索：
- 第一次检索：200ms（还好）
- 第二十次检索：200ms（累积到 4s）

解决方案：
- 缓存高频查询
- 只在必要时检索
- 使用更快的检索引擎
```

### 5.2 检索结果不稳定

```
同一次会话中，同一个查询：
- 第一次检索：结果 A
- 第二次检索：结果 B（因为索引更新了）

解决方案：
- 会话级别的检索结果缓存
- 固化索引（检索期间不更新）
```

### 5.3 RAG 与 Agent 自主性的冲突

```
RAG 提供"标准答案"，但 Agent 需要"自主决策"。

冲突：
- 用户问"这个 bug 怎么修？"
- RAG 检索到"标准修复方案"
- Agent 应该完全按照 RAG 回答，还是可以有自己的判断？

最佳实践：
- 事实信息：严格遵循 RAG
- 决策建议：RAG 提供参考，Agent 自主判断
```

---

## 六、2026 年 RAG 在 Agent 中的新趋势

### 6.1 Agentic RAG

Agent 不再是一个"消费者"被动接收 RAG 结果，而是主动管理 RAG：

```
Agent 管理 RAG 的：
- 数据源选择
- 检索策略
- 检索时机
- 结果融合
- 质量评估
```

### 6.2 多模态 RAG Agent

Agent 不只是检索文本，还能检索：

```
- 图像（截图分析）
- 表格（数据分析）
- 代码（代码检索）
- 语音（语音检索）
- 视频（视频摘要）
```

### 6.3 实时 RAG Agent

知识库实时更新，Agent 实时感知：

```
1. 知识库更新了
2. Agent 自动感知到变化
3. 下次相关查询时，使用最新数据
4. 不需要重新部署或重启
```

---

## 总结

| 集成模式 | 触发时机 | 优点 | 缺点 |
|---------|---------|------|------|
| 前置检索 | 推理前 | 简单、可靠 | 缺乏灵活性 |
| 按需检索 | 推理中 | 灵活、节省 | 需要 Agent 主动调用 |
| 后置验证 | 推理后 | 双重保险 | 增加延迟 |
| 多级 RAG | 分级 | 质量高 | 成本高 |

**RAG 和 Agent 的关系不是"用"和"被用"，而是"共生"的。**

**模块三总结**：我们已经完成了 RAG 技术深度解析的 8 篇文章。从基础架构、嵌入模型、检索策略、查询增强、高级 RAG、Graph RAG、评估优化到 Agent 集成，覆盖了 RAG 的完整技术体系。

**下一篇**：进入模块四——**Agent 范式与架构**。我们将从 Agent 的定义开始，深入 ReAct、Plan-and-Execute、Reflexion 等主流范式，以及 Function Calling 和编排框架。

---

**思考题**：
1. 你的 Agent 中，RAG 是前置检索还是按需检索？为什么？
2. 如果 RAG 检索到的信息与 Agent 的"记忆"冲突，你怎么办？
3. 你会在 Agent 中用"后置验证"模式吗？什么场景下值得增加这个延迟？

---

> 上一篇：[21] RAG 评估与优化
> 下一篇：[23] 从 LLM 到 Agent：Agent 的定义与本质
> 系列目录：[README.md](./README.md)