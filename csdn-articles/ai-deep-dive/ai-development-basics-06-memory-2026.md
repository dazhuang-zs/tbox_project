# AI 开发基础（第6篇）：Memory - 让 Agent 拥有记忆

> **适合读者**：已读完第5篇（Skills/MCP），想让Agent"记住"之前的交互  
> **预计阅读时间**：30分钟

---

## 前言：没有记忆的Agent

每次对话开始，LLM都是"白纸一张"。它不记得你昨天说了什么，不记得你喜欢什么，不记得上次任务做到哪里。

```
第1次对话：
用户：我是素食主义者
Agent：好的，我记住了

第2次对话（新会话）：
用户：帮我推荐北京好吃的餐厅
Agent：推荐全聚德烤鸭、东来顺涮羊肉...
```

**它"记住了"吗？没有。** 第2次对话是新会话，LLM的上下文窗口里没有任何第1次对话的信息。

**Memory机制就是解决这个问题。**

---

## 一、理解"记忆"的三个层次

### 1.1 上下文窗口 ≠ 记忆

很多人混淆了两个概念：

| | 上下文窗口 | 记忆 |
|--|----------|------|
| **生命周期** | 单次对话 | 跨对话持久化 |
| **容量** | 128K-200K Token | 理论无限 |
| **成本** | 每次都重新发送 | 只发送需要的部分 |
| **控制** | LLM自动处理 | 开发者管理 |

**上下文窗口是"工作记忆"，Memory是"长期记忆"。**

### 1.2 三层记忆架构

| 层次 | 名称 | 存储位置 | 生命周期 |
|------|------|---------|---------|
| **L1** | 对话历史（Working Memory） | messages数组 | 单次对话 |
| **L2** | 短期记忆（Session Memory） | Redis/文件 | 会话级（几小时到几天） |
| **L3** | 长期记忆（Long-term Memory） | 数据库/向量库 | 永久 |

```
用户输入
  ↓
[L1] 对话历史（本次对话的前几轮）
  ↓
[L2] 短期记忆（本次会话的关键信息摘要）
  ↓
[L3] 长期记忆（用户画像、历史偏好、知识库）
  ↓
LLM处理 → 回复
```

---

## 二、L1：对话历史管理

### 2.1 最简单的方式：全部发送

```python
messages = [
    {"role": "user", "content": "我是素食主义者"},
    {"role": "assistant", "content": "好的，记住了"},
    {"role": "user", "content": "推荐北京餐厅"},
    {"role": "assistant", "content": "推荐素心餐厅..."},
    {"role": "user", "content": "再推荐几个"},
]
```

问题：对话越来越长，Token越来越多，成本越来越高，最终超出上下文窗口。

### 2.2 Token预算控制

```python
def trim_messages(messages: list, max_tokens: int = 8000):
    """按Token预算裁剪消息，保留系统提示和最近的对话"""
    import tiktoken
    
    enc = tiktoken.encoding_for_model("gpt-4o-mini")
    
    # 保留系统提示
    system_msgs = [m for m in messages if m["role"] == "system"]
    other_msgs = [m for m in messages if m["role"] != "system"]
    
    # 从最新的消息开始保留，直到Token预算用完
    kept = []
    total_tokens = sum(len(enc.encode(m["content"])) for m in system_msgs)
    
    for msg in reversed(other_msgs):
        msg_tokens = len(enc.encode(msg["content"]))
        if total_tokens + msg_tokens > max_tokens:
            break
        kept.insert(0, msg)
        total_tokens += msg_tokens
    
    return system_msgs + kept
```

### 2.3 滑动窗口 + 摘要

**更聪明的做法**：旧的消息不是直接丢弃，而是压缩成摘要。

```python
async def summarize_messages(messages: list) -> str:
    """将旧消息压缩成摘要"""
    if not messages:
        return ""
    
    old_content = "\n".join([
        f"{'用户' if m['role']=='user' else '助手'}: {m['content']}"
        for m in messages
    ])
    
    summary_prompt = f"""将以下对话历史压缩成一段简洁的摘要，保留关键信息：
1. 用户提到的偏好和需求
2. 已完成和未完成的任务
3. 重要的决策和结论

对话历史：
{old_content}

摘要："""
    
    response = await llm.chat(summary_prompt)
    return response


async def managed_messages(messages: list, max_recent: int = 10):
    """管理消息：旧消息摘要 + 最近N轮完整保留"""
    if len(messages) <= max_recent:
        return messages
    
    old_msgs = messages[:-max_recent]
    recent_msgs = messages[-max_recent:]
    
    summary = await summarize_messages(old_msgs)
    
    return [
        {"role": "system", "content": f"之前的对话摘要：{summary}"},
        *recent_msgs
    ]
```

**效果**：10轮前的对话被压缩成一段摘要（几百Token），最近10轮完整保留。既省Token又不错过重要信息。

---

## 三、L2：短期记忆

### 3.1 用Redis存储会话记忆

```python
import json
import redis
from datetime import timedelta

class SessionMemory:
    """短期会话记忆（Redis实现）"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.client = redis.from_url(redis_url)
        self.ttl = timedelta(hours=24)  # 24小时过期
    
    def save_key_info(self, session_id: str, key_info: dict):
        """保存会话关键信息"""
        key = f"session:{session_id}:key_info"
        self.client.setex(key, self.ttl, json.dumps(key_info, ensure_ascii=False))
    
    def get_key_info(self, session_id: str) -> dict:
        """获取会话关键信息"""
        key = f"session:{session_id}:key_info"
        data = self.client.get(key)
        return json.loads(data) if data else {}
    
    def append_task(self, session_id: str, task: dict):
        """追加任务记录"""
        key = f"session:{session_id}:tasks"
        tasks = self.get_tasks(session_id)
        tasks.append(task)
        self.client.setex(key, self.ttl, json.dumps(tasks, ensure_ascii=False))
    
    def get_tasks(self, session_id: str) -> list:
        """获取任务列表"""
        key = f"session:{session_id}:tasks"
        data = self.client.get(key)
        return json.loads(data) if data else []


# 使用
memory = SessionMemory()

# 用户说"我是素食主义者"后
memory.save_key_info("session_001", {
    "diet": "素食",
    "city": "北京",
    "preferences": ["川菜", "火锅"],
})

# 下次对话时，把关键信息注入到system prompt
key_info = memory.get_key_info("session_001")
system_prompt = f"用户信息：{json.dumps(key_info, ensure_ascii=False)}"
```

### 3.2 真实项目经验

在智能行程规划项目中，用户可能分多次提供信息：
- 第1次：城市、日期
- 第2次：预算、人数
- 第3次：特殊需求（带小孩、无障碍）

用Redis保存这些信息，下次对话自动加载，用户不需要重复说。

**踩坑**：
- Redis连接池要配好，不然并发高了会报错
- TTL设置太短（1小时）导致用户中途去吃个饭回来信息就没了。后来改成24小时

---

## 四、L3：长期记忆

### 4.1 用户画像

长期记忆最常见的形式：记住用户的偏好和特征。

```python
import sqlite3

class UserProfile:
    """用户画像（SQLite实现）"""
    
    def __init__(self, db_path: str = "user_profiles.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()
    
    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                user_id TEXT PRIMARY KEY,
                preferences TEXT,    -- JSON: {"diet": "素食", "city": "北京"}
                history TEXT,        -- JSON: 最近10次任务摘要
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def update_preference(self, user_id: str, key: str, value: str):
        """更新用户偏好"""
        profile = self.get_profile(user_id)
        if not profile:
            profile = {"preferences": {}, "history": []}
        
        profile["preferences"][key] = value
        self.conn.execute(
            "INSERT OR REPLACE INTO user_profile (user_id, preferences, history) VALUES (?, ?, ?)",
            (user_id, json.dumps(profile["preferences"]), json.dumps(profile["history"]))
        )
        self.conn.commit()
    
    def get_profile(self, user_id: str) -> dict:
        """获取用户画像"""
        row = self.conn.execute(
            "SELECT preferences, history FROM user_profile WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return {
            "preferences": json.loads(row[0]) if row[0] else {},
            "history": json.loads(row[1]) if row[1] else [],
        }


# 使用
profile_db = UserProfile()

# 每次对话结束后提取关键偏好
def extract_preferences(user_input: str, user_id: str):
    """从用户输入中提取偏好（简单规则，实际可用LLM提取）"""
    preference_rules = {
        "素食": "diet",
        "不辣": "spicy_level",
        "预算": "budget_range",
    }
    
    for keyword, pref_key in preference_rules.items():
        if keyword in user_input:
            profile_db.update_preference(user_id, pref_key, keyword)
```

### 4.2 向量检索（RAG）

当长期记忆数据量大时，不能每次都全部发给LLM。用向量数据库检索相关记忆。

```python
import numpy as np
from numpy.linalg import norm

class SimpleVectorMemory:
    """简单向量记忆（小规模可用，生产环境用Chroma/FAISS）"""
    
    def __init__(self, embedding_func):
        self.memories = []  # [{"text": "...", "embedding": [...], "meta": {...}}]
        self.embedding_func = embedding_func
    
    async def add(self, text: str, meta: dict = None):
        """添加记忆"""
        embedding = await self.embedding_func(text)
        self.memories.append({
            "text": text,
            "embedding": embedding,
            "meta": meta or {},
        })
    
    async def search(self, query: str, top_k: int = 5) -> list:
        """检索相关记忆"""
        query_embedding = await self.embedding_func(query)
        
        scored = []
        for mem in self.memories:
            similarity = np.dot(query_embedding, mem["embedding"]) / (
                norm(query_embedding) * norm(mem["embedding"])
            )
            scored.append((similarity, mem))
        
        scored.sort(reverse=True)
        return [m for _, m in scored[:top_k]]


# 使用
async def build_memory_context(query: str, user_id: str) -> str:
    """构建带记忆的上下文"""
    # 1. 用户画像
    profile = profile_db.get_profile(user_id)
    
    # 2. 向量检索相关记忆
    related_memories = await vector_memory.search(query)
    
    context = ""
    if profile and profile["preferences"]:
        context += f"用户偏好：{json.dumps(profile['preferences'])}\n"
    
    if related_memories:
        context += "相关历史信息：\n"
        for mem in related_memories:
            context += f"- {mem['text']}\n"
    
    return context
```

**RAG（Retrieval-Augmented Generation）** 就是这个流程：
```
用户问题 → 向量检索相关记忆 → 把记忆注入Prompt → LLM生成回答
```

---

## 五、Memory与RAG的关系

### 5.1 它们不是同一个东西

| | Memory | RAG |
|--|--------|-----|
| **本质** | 记住信息 | 检索信息 |
| **数据来源** | 用户交互产生的信息 | 外部知识库（文档、网页） |
| **目的** | 个性化（记住"你"） | 增强知识（知道"更多"） |
| **存储** | 用户级别的偏好/历史 | 领域级别的文档/知识 |

**类比**：
- Memory = 你的日记本（记录你自己的事）
- RAG = 你的参考书（查外部资料）

### 5.2 它们可以结合

```python
async def build_full_context(user_id: str, query: str) -> str:
    """构建完整上下文：用户画像 + 对话历史 + 外部知识"""
    
    parts = []
    
    # L1: 对话历史（最近N轮）
    recent = get_recent_messages(user_id, n=10)
    if recent:
        parts.append(f"最近对话：\n{format_messages(recent)}")
    
    # L2: 会话摘要
    summary = get_session_summary(user_id)
    if summary:
        parts.append(f"会话摘要：{summary}")
    
    # L3: 用户画像
    profile = profile_db.get_profile(user_id)
    if profile:
        parts.append(f"用户画像：{json.dumps(profile['preferences'])}")
    
    # RAG: 外部知识检索
    knowledge = await knowledge_base.search(query, top_k=3)
    if knowledge:
        parts.append("相关知识：\n" + "\n".join(knowledge))
    
    return "\n\n".join(parts)
```

---

## 六、本章总结

**你学到了什么**：

1. **三层记忆架构**：L1对话历史、L2短期记忆（Redis）、L3长期记忆（数据库/向量库）
2. **上下文管理**：滑动窗口 + 摘要，旧消息不丢，Token不超标
3. **用户画像**：用SQLite/JSON存储用户偏好，跨会话保持个性化
4. **RAG**：向量检索相关记忆/知识，注入Prompt增强回答质量
5. **Memory vs RAG**：Memory记住"你"，RAG知道"更多"，两者结合效果最好

**关键公式**：
```
完整上下文 = 对话历史 + 会话摘要 + 用户画像 + 外部知识
Memory = 个性化（记住你的偏好）
RAG = 增强知识（检索外部资料）
```

**下一篇预告**：
- 第7篇：Subagent 与 Multi-Agent - 分而治之，多智能体协作

---

## 参考资料

1. MemGPT论文：https://arxiv.org/abs/2310.08560
2. RAG原论文：https://arxiv.org/abs/2005.11401
3. LangChain Memory文档：https://python.langchain.com/docs/how_to/memory/
4. Chroma向量数据库：https://www.trychroma.com/

---

**上一篇**：第5篇 Skills 与 MCP  
**下一篇**：第7篇 Subagent 与 Multi-Agent
