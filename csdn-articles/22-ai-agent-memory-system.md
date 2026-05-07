# 【AI Agent 内核】22 · 记忆系统深度解析：从短期缓存到长期学习的完整工程方案

> **标签**：`#AI Agent` `#记忆系统` `#RAG` `#向量数据库` `#工程实践`

> 大多数 Agent 教程告诉你"加上 Memory 模块就行了"。但真正的记忆系统远不止 `ConversationBufferMemory` 三行代码。本文从不装外行——我们直接拆开 Agent 记忆的黑箱，讲清楚三层记忆架构的设计决策、存储方案选型、以及生产环境中一定会踩的 5 个坑。

---

## 一、记忆不是存储，是检索

先打破一个认知误区：

```
❌ 错误认知：记忆 = 把对话存进数据库
✅ 正确认知：记忆 = 在正确的时间检索到正确的信息
```

一个 Agent 跟用户聊了 100 轮对话，存了 10 万字——但这不叫"有记忆"。只有当 Agent 在第 101 轮对话时，能准确回忆起"用户在第 23 轮说过他更喜欢函数式风格"，这才叫有记忆。

**记忆的核心不是写入，是衰减 + 检索。**

---

## 二、三层记忆架构

### 2.1 工作记忆（Working Memory）

```
生命周期：单次会话内
存储内容：当前对话的完整上下文
容量上限：模型上下文窗口（200K token）
```

**这不是你想的那样简单。**

直接把所有历史消息塞进 Prompt？3 个问题立刻出现：

| 问题 | 后果 |
|------|------|
| Token 爆炸 | 20 轮对话后上下文占 15K token，推理变慢 3x |
| 注意力稀释 | 模型在 100K token 中找关键信息，容易忽略重要细节 |
| 成本飙升 | GPT-4 每 10K token 输入 $0.03，长对话一次 $0.6+ |

**解决方案：混合窗口策略**

```python
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class MemoryConfig:
    full_context_rounds: int = 3      # 完整保留最近 3 轮
    summary_rounds: int = 20          # 3-20 轮压缩成摘要
    key_facts_max: int = 50           # 最多保留 50 条关键事实

class HybridMemoryManager:
    """混合窗口记忆管理器"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.key_facts: List[str] = []  # 关键事实池
    
    def manage_context(self, messages: List[Dict]) -> str:
        """构建优化后的上下文"""
        total = len(messages)
        
        # Layer 1: 最近 N 轮完整保留
        recent = messages[-self.config.full_context_rounds * 2:]
        
        # Layer 2: 中间轮次压缩为摘要
        if total > self.config.summary_rounds * 2:
            middle = messages[-(self.config.summary_rounds * 2):
                            -(self.config.full_context_rounds * 2)]
            summary = self._summarize(middle)
        else:
            summary = ""
        
        # Layer 3: 关键事实注入
        facts = "\n".join(f"[关键信息] {f}" for f in self.key_facts[-self.config.key_facts_max:])
        
        return self._assemble_context(recent, summary, facts)
    
    def _summarize(self, messages: List[Dict]) -> str:
        """调用 LLM 压缩对话为要点摘要"""
        prompt = f"""将以下对话压缩为关键要点，保留：
        1. 用户做出的决策
        2. 达成的共识
        3. 未完成的任务
        4. 用户的偏好和约束
        
        对话：
        {self._format_messages(messages)}
        """
        # 实际调用 LLM API
        return self._call_llm(prompt)
    
    def add_key_fact(self, fact: str):
        """添加一条不会丢失的关键信息"""
        self.key_facts.append(fact)
```

**策略选择矩阵**：

| 策略 | Token 效率 | 信息保真度 | 适用场景 |
|------|-----------|-----------|---------|
| 全量保留 | ❌ 差 | ✅ 100% | 短对话(<10轮) |
| 滑动窗口 | ⚠️ 中 | ⚠️ 丢失旧信息 | 实时流式对话 |
| 摘要压缩 | ✅ 好 | ⚠️ 细节丢失 | 长对话助手 |
| **混合窗口** | ✅ 最优 | ✅ 关键信息不丢 | 生产级 Agent |

---

### 2.2 短期记忆（Short-term Memory）

```
生命周期：跨会话，保留数天到数周
存储内容：会话摘要、用户偏好、临时决策
存储介质：向量数据库 + 元数据过滤
```

**核心挑战**：不是"能不能存"，而是"存进去之后能不能找到"。

**实现方案：双路检索**

```python
import chromadb
from chromadb.utils import embedding_functions
import json
from datetime import datetime, timedelta

class ShortTermMemory:
    """短期记忆管理器 — 双路检索"""
    
    def __init__(self, persist_dir: str = "./agent_memory"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name="short_term_memory",
            embedding_function=self.embed_fn,
            metadata={"hnsw:space": "cosine"}
        )
    
    def store(self, content: str, metadata: dict):
        """存储记忆片段"""
        memory_id = f"mem_{datetime.now().timestamp()}"
        
        self.collection.add(
            documents=[content],
            metadatas=[{
                **metadata,
                "timestamp": datetime.now().isoformat(),
                "ttl_days": metadata.get("ttl_days", 7),
                "importance": metadata.get("importance", "medium")
            }],
            ids=[memory_id]
        )
    
    def retrieve(self, query: str, top_k: int = 5, 
                 time_window_days: int = 7,
                 min_importance: str = "low") -> List[Dict]:
        """
        双路检索：语义相似度 + 元数据过滤
        
        Args:
            query: 查询文本
            top_k: 返回条数
            time_window_days: 时间窗口（7天内）
            min_importance: 最低重要度（low/medium/high）
        """
        cutoff = datetime.now() - timedelta(days=time_window_days)
        
        # 语义搜索
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k * 2,  # 多取一些，再过滤
            where={
                "timestamp": {"$gte": cutoff.isoformat()},
                "importance": {"$gte": min_importance}
            }
        )
        
        # 按时间衰减重排序
        scored = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            # 时间衰减因子（越旧权重越低）
            age_days = (datetime.now() - datetime.fromisoformat(meta["timestamp"])).days
            time_decay = 1.0 / (1.0 + age_days * 0.3)
            
            # 重要度加权
            importance_weight = {"low": 0.3, "medium": 0.6, "high": 1.0}[meta["importance"]]
            
            final_score = (1 - dist) * time_decay * importance_weight
            scored.append((doc, meta, final_score))
        
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:top_k]
    
    def expire_old_memories(self):
        """清理过期记忆"""
        cutoff = datetime.now() - timedelta(days=30)
        # ChromaDB 支持元数据过滤删除
        self.collection.delete(
            where={"timestamp": {"$lt": cutoff.isoformat()}}
        )
```

**为什么用双路检索而不是纯向量搜索？**

```
纯向量搜索：
  查询"用户喜欢什么代码风格"
  → 返回语义相关的所有结果
  → 可能返回 3 个月前的过时信息

双路检索：
  查询"用户喜欢什么代码风格"
  → 语义搜索 + 过滤（最近 7 天 + 重要度 >= medium）
  → 只返回新鲜且重要的信息
```

---

### 2.3 长期记忆（Long-term Memory）

```
生命周期：永久保留
存储内容：用户偏好、项目配置、领域知识、经验教训
存储介质：结构化数据库 + 知识图谱
```

**这是三层中最难做好的一层。** 核心问题不是存储，是**记忆的过时管理**。

```python
from typing import Optional
import sqlite3
import json
from datetime import datetime

class LongTermMemory:
    """长期记忆管理器 — 带过期验证"""
    
    def __init__(self, db_path: str = "./agent_ltm.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,         -- 'preference', 'project', 'fact', 'lesson'
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,     -- 置信度 0-1
                source TEXT,                     -- 来源（哪次对话/哪个事件）
                created_at TIMESTAMP,
                last_verified_at TIMESTAMP,
                expires_at TIMESTAMP,            -- NULL = 永不过期
                version INTEGER DEFAULT 1
            )
        """)
        
        # 项目配置表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS project_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TIMESTAMP,
                UNIQUE(project_name, key)
            )
        """)
    
    def set_preference(self, user_id: str, key: str, value: str, 
                       confidence: float = 0.8):
        """设置用户偏好"""
        existing = self.get_preference(user_id, key)
        
        if existing:
            # 更新已有偏好，提高置信度
            new_confidence = min(1.0, existing["confidence"] + 0.1)
            self.conn.execute("""
                UPDATE user_memory 
                SET value = ?, confidence = ?, last_verified_at = ?,
                    version = version + 1
                WHERE user_id = ? AND category = 'preference' AND key = ?
            """, (value, new_confidence, datetime.now(), user_id, key))
        else:
            # 新建偏好
            self.conn.execute("""
                INSERT INTO user_memory 
                (user_id, category, key, value, confidence, 
                 created_at, last_verified_at)
                VALUES (?, 'preference', ?, ?, ?, ?, ?)
            """, (user_id, key, value, confidence, 
                  datetime.now(), datetime.now()))
        
        self.conn.commit()
    
    def get_preference(self, user_id: str, key: str) -> Optional[Dict]:
        """获取用户偏好 — 包含置信度"""
        row = self.conn.execute("""
            SELECT value, confidence, last_verified_at
            FROM user_memory
            WHERE user_id = ? AND category = 'preference' AND key = ?
            ORDER BY last_verified_at DESC LIMIT 1
        """, (user_id, key)).fetchone()
        
        if row:
            return {
                "value": row[0],
                "confidence": row[1],
                "last_verified": row[2]
            }
        return None
    
    def verify_stale_memories(self, user_id: str, 
                               stale_days: int = 30) -> List[Dict]:
        """
        找出需要重新确认的过时记忆
        低置信度 + 长时间未验证 = 需要重新确认
        """
        cutoff = datetime.now().isoformat()
        rows = self.conn.execute("""
            SELECT key, value, confidence, last_verified_at
            FROM user_memory
            WHERE user_id = ?
              AND confidence < 0.7
              AND last_verified_at < date('now', ?)
        """, (user_id, f'-{stale_days} days')).fetchall()
        
        return [
            {"key": r[0], "value": r[1], "confidence": r[2]}
            for r in rows
        ]
    
    def learn_from_mistake(self, user_id: str, lesson: str):
        """
        从错误中学习 — 记录经验教训
        这是长期记忆最有价值的功能
        """
        self.conn.execute("""
            INSERT INTO user_memory
            (user_id, category, key, value, created_at, last_verified_at)
            VALUES (?, 'lesson', ?, ?, ?, ?)
        """, (user_id, f"lesson_{datetime.now().timestamp()}", 
              lesson, datetime.now(), datetime.now()))
        self.conn.commit()
```

**长期记忆的关键设计决策**：

| 决策点 | 方案 | 原因 |
|--------|------|------|
| 置信度机制 | 每次确认 +0.1，长期未验证 -0.05/天 | 记忆需要"加强"和"衰减" |
| 过期验证 | 低置信度 + 30 天未验证 → 主动询问用户 | 防止基于过时信息做决策 |
| 来源追溯 | 每条记忆记录来源 | 调试时知道"这个信息从哪来的" |
| 版本控制 | 每次更新 version+1 | 支持记忆回滚 |

---

## 三、三层记忆的协同工作流

```
新会话开始
    ↓
┌─────────────────────────────┐
│ Step 1: 加载长期记忆          │
│  → 用户偏好（代码风格、语言）   │
│  → 项目配置（技术栈、部署方式） │
│  → 经验教训（以前踩过的坑）    │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│ Step 2: 检索相关短期记忆       │
│  → 最近 7 天的会话摘要        │
│  → 最近的决策和共识           │
│  → 未完成的任务               │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│ Step 3: 构建工作记忆上下文     │
│  → 长期记忆（注入）           │
│  → 短期记忆（注入）           │
│  → 当前对话（完整）           │
│  → 关键事实池（注入）         │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│ Step 4: 对话进行中            │
│  → 每轮追加到工作记忆         │
│  → 检测关键信息 → 加入事实池   │
│  → 上下文超阈值 → 触发摘要压缩  │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│ Step 5: 会话结束              │
│  → 生成会话摘要 → 写入短期记忆  │
│  → 提取新的偏好/决策 → 更新长期记忆│
│  → 清理工作记忆               │
└─────────────────────────────┘
```

---

## 四、生产环境必踩的 5 个坑

### 坑 1：记忆膨胀

```
症状：Agent 运行 2 周后，短期记忆数据库达到 5GB
根因：没有设置 TTL（过期时间）和存储上限
解法：
  - 每条记忆设 TTL（默认 7 天）
  - 总容量上限（如 1000 条）
  - 达到上限时按"重要性 × 时间衰减"自动淘汰
```

### 坑 2：记忆污染

```
症状：Agent 开始重复错误的"记忆"
根因：低质量的对话被当成事实存储
解法：
  - 只存储"用户主动确认"的信息（不是每句话都存）
  - 对自动提取的记忆标记 confidence < 0.5
  - 定期运行 verify_stale_memories() 清理
```

### 坑 3：检索失效

```
症状：Agent 说"我没找到相关信息"，但明明存了
根因：向量搜索的语义匹配不准确（不同表述方式搜不到）
解法：
  - 双路检索（语义 + 关键词）
  - BM25 + 向量混合搜索
  - 增加元数据过滤缩小搜索空间
```

### 坑 4：上下文污染

```
症状：Agent 的回答被旧记忆"带偏"
根因：长期记忆注入过多，稀释了当前任务的上下文
解法：
  - 按需检索，不要全量注入
  - 记忆注入总量控制在总上下文的 20% 以内
  - 给不同记忆来源加"优先级权重"
```

### 坑 5：跨会话一致性

```
症状：同一用户开两个窗口，两个 Agent 给出矛盾的回答
根因：短期记忆写入有延迟，两个会话读到不一致的状态
解法：
  - 短期记忆写入必须是同步的
  - 使用乐观锁或版本号防止并发覆盖
  - 关键偏好存在长期记忆（事务写入）
```

---

## 五、记忆系统选型速查

| 你的场景 | 推荐方案 |
|----------|---------|
| 单次对话助手 | 只保留最近 10 轮完整上下文 |
| 客服机器人（24h 内有效） | 工作记忆 + 短期记忆（Redis） |
| 个人 AI 助手（长期用） | 三层全上 + ChromaDB(短期) + SQLite(长期) |
| 企业级 Agent 平台 | 三层 + PostgreSQL(pgvector) + 分布式缓存 |

**最后一句**：记忆系统的核心不是"存得下"，是"找得对、该忘就忘"。一个会选择性遗忘的 Agent，比一个什么都记得的 Agent 可靠得多。

---

*你的 Agent 记忆系统用的什么方案？踩过哪个坑？评论区聊聊 👇*
