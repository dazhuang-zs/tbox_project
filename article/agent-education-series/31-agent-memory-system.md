# 【AI Agent 系统教学 31】Agent 记忆系统深度解析

> 没有记忆的 Agent，每轮对话都是一次"初次见面"。
> 有记忆的 Agent，才能从"工具"进化为"伙伴"。

---

## 前言：记忆是 Agent 从"工具"到"伙伴"的分水岭

没有记忆的 Agent：

```
用户：我叫张三
Agent：你好，张三！
用户：我叫什么名字？
Agent：抱歉，我不记得你刚才说了什么。请问你叫什么名字？
```

有记忆的 Agent：

```
用户：我叫张三，喜欢简洁的回复
Agent：好的，张三！
用户：帮我查一下今天的新闻
Agent：张三，以下是今天的新闻摘要...
（记得用户的名字，回复更简洁）
```

**记忆，就是 Agent 的"持续性"——让 Agent 不仅知道"现在"，还知道"过去"。**

---

## 一、Agent 记忆的三层架构

### 1.1 三层记忆模型

```
┌─────────────────────────────────────┐
│  L1：工作记忆（上下文窗口）          │
│  当前对话内容、临时信息              │
│  容量：模型上下文窗口大小（4K-128K）  │
│  持久性：一次推理                    │
├─────────────────────────────────────┤
│  L2：短期记忆（会话记忆）            │
│  当前会话的历史、状态                │
│  容量：不限（但需要管理）            │
│  持久性：一次会话                    │
├─────────────────────────────────────┤
│  L3：长期记忆（持久记忆）            │
│  用户偏好、知识、经验                │
│  容量：不限（外部存储）              │
│  持久性：永久                        │
└─────────────────────────────────────┘
```

### 1.2 各层的关系

```
工作记忆（L1）：正在处理的信息
  ↓ 超出上下文窗口 → 压缩到短期记忆
短期记忆（L2）：本次会话的信息
  ↓ 会话结束 → 重要信息提升到长期记忆
长期记忆（L3）：跨会话的信息
  ↑ 需要时 → 检索到工作记忆
```

---

## 二、工作记忆（L1）：上下文窗口管理

### 2.1 工作记忆的特点

工作记忆就是模型的上下文窗口。它有两个硬约束：

1. **容量有限**：4K-128K token
2. **注意力不均匀**：中间信息容易被忽略

### 2.2 工作记忆的内容管理

```python
class WorkingMemory:
    """工作记忆管理"""
    def __init__(self, max_tokens=32000):
        self.max_tokens = max_tokens
        self.content = []
    
    def add(self, item, priority="normal"):
        """添加内容到工作记忆"""
        item_tokens = count_tokens(item)
        
        if self.total_tokens() + item_tokens > self.max_tokens:
            self._evict(priority)
        
        self.content.append(item)
    
    def _evict(self, current_priority):
        """淘汰低优先级内容"""
        # 优先级：system > tools > memory > history > results
        priority_order = ["results", "history", "memory", "tools", "system"]
        
        for p in priority_order:
            if p == current_priority:
                continue
            while self._has_priority(p):
                self._remove_oldest(p)
                if self.total_tokens() <= self.max_tokens * 0.8:
                    return
    
    def summarize(self):
        """压缩工作记忆为摘要"""
        prompt = f"请将以下对话压缩为 200 token 以内的摘要：\n{self.content}"
        return llm(prompt)
```

---

## 三、短期记忆（L2）：会话记忆

### 3.1 短期记忆的实现

```python
class ShortTermMemory:
    """短期记忆：会话级别的记忆"""
    def __init__(self):
        self.messages = []
        self.extracted_info = {}  # 从对话中提取的关键信息
        self.compressed = []      # 压缩后的历史
    
    def add_message(self, role, content):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        self._extract_info(role, content)
    
    def _extract_info(self, role, content):
        """从对话中提取关键信息"""
        prompt = f"""
        从以下对话中提取关键信息，以 JSON 格式返回：
        角色：{role}
        内容：{content}
        
        提取的信息：
        - 用户偏好
        - 提到的实体（人名、地名、产品名）
        - 任务状态
        - 重要决策
        """
        info = llm(prompt)
        self.extracted_info.update(info)
    
    def get_context(self, max_tokens=4000):
        """获取用于 Agent 推理的短期记忆上下文"""
        # 1. 提取的关键信息
        info_context = format_info(self.extracted_info)
        
        # 2. 最近的对话（保留最近 3 轮）
        recent = self.messages[-6:]  # 3 轮 = 6 条消息
        
        # 3. 压缩后的历史
        compressed = self.compressed[-3:]
        
        return info_context + recent + compressed
```

### 3.2 记忆压缩

```python
class MemoryCompressor:
    """记忆压缩策略"""
    def compress(self, messages, max_tokens=2000):
        """压缩对话历史"""
        # 策略 1：摘要压缩
        if len(messages) > 10:
            summary = self._summarize(messages[:-5])
            return summary + messages[-5:]
        
        # 策略 2：关键信息提取
        key_info = self._extract_key_info(messages)
        return key_info + messages[-3:]
    
    def _summarize(self, messages):
        prompt = f"请用 100 字以内总结以下对话：\n{messages}"
        return llm(prompt)
    
    def _extract_key_info(self, messages):
        prompt = f"""
        从以下对话中提取关键信息：
        {messages}
        
        输出格式（JSON）：
        {{
            "user_preferences": [],
            "completed_tasks": [],
            "key_decisions": [],
            "open_questions": []
        }}
        """
        return llm(prompt)
```

---

## 四、长期记忆（L3）：持久记忆

### 4.1 长期记忆的结构

```python
class LongTermMemory:
    """长期记忆：跨会话的持久记忆"""
    def __init__(self, vector_db, llm):
        self.vector_db = vector_db
        self.llm = llm
    
    def store(self, session_id, memory_item):
        """存储记忆"""
        # 1. 生成记忆摘要
        summary = self._summarize_memory(memory_item)
        
        # 2. 生成嵌入
        embedding = embed(summary)
        
        # 3. 存储到向量数据库
        self.vector_db.insert({
            "id": f"mem_{session_id}_{time.time()}",
            "type": memory_item["type"],
            "content": memory_item,
            "summary": summary,
            "embedding": embedding,
            "timestamp": time.time(),
            "importance": memory_item.get("importance", 0.5),
        })
    
    def retrieve(self, query, k=5, min_importance=0.3):
        """检索相关记忆"""
        query_embedding = embed(query)
        results = self.vector_db.search(query_embedding, k=k*2)
        
        # 按重要性过滤和排序
        results = [r for r in results if r["importance"] >= min_importance]
        results.sort(key=lambda r: r["importance"] * r["score"], reverse=True)
        
        return results[:k]
    
    def forget(self, older_than_days=30):
        """遗忘：删除过期的低重要性记忆"""
        cutoff = time.time() - older_than_days * 86400
        self.vector_db.delete(
            filter={"timestamp": {"lt": cutoff}, "importance": {"lt": 0.5}}
        )
```

### 4.2 记忆的重要性评分

```python
class MemoryImportanceScorer:
    """记忆重要性评分"""
    def score(self, memory_item):
        prompt = f"""
        评估以下记忆的重要性（0-1）：
        {memory_item}
        
        评分维度：
        1. 情感强度：是否涉及强烈情感
        2. 事实性：是否是重要事实
        3. 时效性：是否长期有效
        4. 关联性：是否与其他记忆相关
        5. 使用频率：是否被反复提及
        """
        return llm(prompt)  # 0-1 之间的分数
```

---

## 五、记忆的检索与使用

### 5.1 记忆检索策略

```python
class MemoryRetriever:
    """综合记忆检索"""
    def __init__(self, working_mem, short_term, long_term):
        self.wm = working_mem
        self.stm = short_term
        self.ltm = long_term
    
    def retrieve(self, query, context):
        """检索所有层次的记忆"""
        memories = []
        
        # 1. 工作记忆：当前上下文
        wm_items = self.wm.get_relevant_items(query)
        memories.extend(wm_items)
        
        # 2. 短期记忆：会话历史
        stm_items = self.stm.get_context(query)
        memories.extend(stm_items)
        
        # 3. 长期记忆：持久记忆
        ltm_items = self.ltm.retrieve(query, k=5)
        memories.extend(ltm_items)
        
        # 4. 排序和去重
        memories = self._deduplicate(memories)
        memories.sort(key=lambda m: m.get("relevance", 0), reverse=True)
        
        # 5. 限制上下文预算
        return self._limit_context(memories, max_tokens=2000)
```

### 5.2 记忆的自动触发

```python
class MemoryTrigger:
    """自动记忆触发"""
    def __init__(self, memory_system):
        self.memory = memory_system
    
    def on_user_input(self, user_input):
        """用户输入时触发"""
        # 检查是否需要检索长期记忆
        if self._needs_memory_retrieval(user_input):
            memories = self.memory.retrieve(user_input)
            return memories
        return []
    
    def on_task_complete(self, task, result):
        """任务完成时触发"""
        # 判断是否值得记住
        if self._is_worth_remembering(task, result):
            self.memory.store({
                "type": "task_result",
                "task": task,
                "result": result,
                "importance": self._calculate_importance(task, result),
            })
    
    def on_error(self, error):
        """错误发生时触发"""
        self.memory.store({
            "type": "error",
            "error": str(error),
            "importance": 0.8,  # 错误通常很重要
        })
```

---

## 六、2026 年记忆系统趋势

### 6.1 分层记忆融合

不再把 L1、L2、L3 分开管理，而是统一检索：

```
统一记忆 API：
  query → 在所有层次中检索
  结果按相关性和重要性排序
  自动决定哪些记忆提升/降级
```

### 6.2 记忆的自我进化

Agent 可以自己管理自己的记忆：

```
Agent 自动做：
  - 判断什么信息值得记住
  - 决定什么时候忘记
  - 对记忆进行重组和关联
  - 从记忆中提取模式
```

### 6.3 记忆共享

多 Agent 之间共享记忆：

```
Agent A 学会的知识 → 存入共享记忆库
Agent B 做类似任务 → 从共享记忆库检索
```

---

## 总结

| 记忆层次 | 存储位置 | 容量 | 持久性 | 管理方式 |
|---------|---------|------|--------|---------|
| 工作记忆（L1） | 上下文窗口 | 有限 | 一次推理 | 内容管理 |
| 短期记忆（L2） | 内存/会话 | 较大 | 一次会话 | 压缩管理 |
| 长期记忆（L3） | 外部存储 | 无限 | 永久 | 检索+遗忘 |
| 重要性 | 记忆权重 | - | - | 评分+筛选 |

**好的记忆系统，让 Agent 从"每次都重新开始"变成"越来越了解你"。**

下一篇文章，我们将深入**工具系统与 MCP 协议**。

---

**思考题**：
1. 你的 Agent 现在有"长期记忆"吗？如果有，是怎么实现的？
2. 记忆的"重要性评分"应该由模型决定还是由规则决定？为什么？
3. 如果 Agent 的记忆"太多"了，检索结果中大部分都不相关，你怎么办？

---

> 上一篇：[30] 从 Agent 到 Agentic Workflow
> 下一篇：[32] 工具系统与 MCP 协议
> 系列目录：[README.md](./README.md)