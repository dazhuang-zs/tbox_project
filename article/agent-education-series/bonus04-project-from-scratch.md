# 【AI Agent 系统教学】番外篇 04：从零搭建完整 Agent 项目

> 前面的 46 篇讲了理论，3 篇番外讲了论文、框架和踩坑。
> 这一篇，我们动手做一个完整的 Agent 项目。

---

## 项目概述

**项目**：一个"个人知识助手"Agent

**功能**：
1. 回答用户关于知识库的问题（RAG）
2. 搜索网络获取最新信息
3. 记住用户偏好
4. 多轮对话

**技术栈**：Python + LangGraph + Qwen 2.5 API + ChromaDB

**代码量**：约 300 行

---

## 第一步：项目结构

```
agent-project/
├── main.py              # 主入口
├── agent.py             # Agent 核心
├── tools.py             # 工具定义
├── memory.py            # 记忆系统
├── knowledge.py         # 知识库（RAG）
├── config.py            # 配置
├── requirements.txt     # 依赖
└── data/                # 知识库数据
    └── knowledge_base/
```

---

## 第二步：配置

```python
# config.py
import os

class Config:
    # LLM API
    LLM_API_KEY = os.getenv("LLM_API_KEY", "your-api-key")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # Agent 参数
    MAX_STEPS = 10
    TIMEOUT_SECONDS = 30
    MAX_TOKENS = 32000
    
    # 知识库
    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 50
    TOP_K = 3
    
    # 记忆
    MEMORY_DB_PATH = "agent_memory.db"
    MAX_HISTORY_TOKENS = 8000
```

---

## 第三步：工具定义

```python
# tools.py
import json
import requests
from datetime import datetime

class Tools:
    @staticmethod
    def search_web(query: str) -> str:
        """搜索网络获取最新信息"""
        try:
            # 使用 DuckDuckGo 搜索（无需 API Key）
            url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(url, timeout=5)
            data = response.json()
            results = data.get("Results", [])[:3]
            return json.dumps([{
                "title": r["Text"],
                "url": r["FirstURL"],
            } for r in results], ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"搜索失败：{str(e)}"})
    
    @staticmethod
    def get_current_time() -> str:
        """获取当前时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def calculate(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"计算错误：{str(e)}"
```

---

## 第四步：记忆系统

```python
# memory.py
import sqlite3
import json
from datetime import datetime

class Memory:
    def __init__(self, db_path="agent_memory.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()
        self.session_messages = []
    
    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                preferences TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def add_message(self, role, content):
        self.session_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
    
    def get_session_context(self, max_tokens=8000):
        """获取当前会话上下文"""
        # 策略：保留最近的消息，如果超过 token 限制，压缩较早的对话
        messages = self.session_messages[-20:]  # 最多保留 20 条
        
        total_tokens = sum(len(m["content"]) for m in messages)
        if total_tokens > max_tokens:
            # 压缩：保留系统提示和最近的 5 条消息
            return messages[-5:]
        
        return messages
    
    def save_preference(self, user_id, key, value):
        prefs = self.load_preferences(user_id)
        prefs[key] = value
        self.conn.execute(
            "INSERT OR REPLACE INTO user_preferences (user_id, preferences) VALUES (?, ?)",
            (user_id, json.dumps(prefs))
        )
        self.conn.commit()
    
    def load_preferences(self, user_id):
        cursor = self.conn.execute(
            "SELECT preferences FROM user_preferences WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return json.loads(row[0]) if row else {}
```

---

## 第五步：知识库（RAG）

```python
# knowledge.py
import os
import chromadb
from chromadb.utils import embedding_functions

class KnowledgeBase:
    def __init__(self, persist_dir="./data/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=embedding_functions.DefaultEmbeddingFunction(),
        )
    
    def add_documents(self, documents, metadata_list=None):
        """添加文档到知识库"""
        ids = [f"doc_{i}" for i in range(len(documents))]
        self.collection.add(
            documents=documents,
            metadatas=metadata_list or [{} for _ in documents],
            ids=ids,
        )
    
    def search(self, query, k=3):
        """搜索知识库"""
        results = self.collection.query(
            query_texts=[query],
            n_results=k,
        )
        
        if not results["documents"]:
            return []
        
        return [
            {
                "content": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            }
            for i, doc in enumerate(results["documents"][0])
        ]
```

---

## 第六步：Agent 核心

```python
# agent.py
from openai import OpenAI
import json

class PersonalKnowledgeAgent:
    def __init__(self, config, tools, memory, knowledge_base):
        self.client = OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self.model = config.LLM_MODEL
        self.tools = tools
        self.memory = memory
        self.kb = knowledge_base
        self.config = config
        self.user_id = "default"
    
    def run(self, user_input):
        """运行 Agent"""
        # 1. 检索知识库
        relevant_docs = self.kb.search(user_input, k=self.config.TOP_K)
        
        # 2. 加载用户偏好
        preferences = self.memory.load_preferences(self.user_id)
        
        # 3. 构建 System Prompt
        system_prompt = self._build_system_prompt(preferences, relevant_docs)
        
        # 4. 获取会话上下文
        context = self.memory.get_session_context(self.config.MAX_HISTORY_TOKENS)
        
        # 5. 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            *context,
            {"role": "user", "content": user_input},
        ]
        
        # 6. Agent 循环
        for step in range(self.config.MAX_STEPS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._get_tool_definitions(),
                tool_choice="auto",
            )
            
            message = response.choices[0].message
            
            if not message.tool_calls:
                # 没有工具调用，返回最终结果
                self.memory.add_message("user", user_input)
                self.memory.add_message("assistant", message.content)
                return message.content
            
            # 执行工具调用
            for tool_call in message.tool_calls:
                result = self._execute_tool(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
        
        return "达到最大步数，任务未完成"
    
    def _build_system_prompt(self, preferences, relevant_docs):
        prompt = f"""
你是一个个人知识助手，可以回答用户的问题。

用户偏好：
{json.dumps(preferences, ensure_ascii=False, indent=2)}

相关知识库信息：
{self._format_docs(relevant_docs) if relevant_docs else "（无相关知识）"}

行为规则：
1. 优先使用知识库信息回答
2. 知识库信息不足时，使用搜索工具获取最新信息
3. 记住用户的偏好和习惯
4. 回答简洁、准确
5. 不知道就说不知道，不要编造
"""
        return prompt
    
    def _get_tool_definitions(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "搜索网络获取最新信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "获取当前时间",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "计算数学表达式",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string", "description": "数学表达式"}
                        },
                        "required": ["expression"],
                    },
                },
            },
        ]
    
    def _execute_tool(self, tool_call):
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        
        tool_map = {
            "search_web": self.tools.search_web,
            "get_current_time": self.tools.get_current_time,
            "calculate": self.tools.calculate,
        }
        
        func = tool_map.get(name)
        if not func:
            return json.dumps({"error": f"未知工具：{name}"})
        
        try:
            result = func(**args)
            return result
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def _format_docs(self, docs):
        return "\n\n".join([d["content"] for d in docs])
```

---

## 第七步：主入口

```python
# main.py
from config import Config
from tools import Tools
from memory import Memory
from knowledge import KnowledgeBase
from agent import PersonalKnowledgeAgent

def main():
    config = Config()
    tools = Tools()
    memory = Memory(config.MEMORY_DB_PATH)
    kb = KnowledgeBase()
    
    # 初始化知识库（如果还没有数据）
    # kb.add_documents(["你的知识库文档..."])
    
    agent = PersonalKnowledgeAgent(config, tools, memory, kb)
    
    print("🤖 个人知识助手已启动！输入 'quit' 退出。\n")
    
    while True:
        user_input = input("\n你：")
        if user_input.lower() == "quit":
            break
        
        response = agent.run(user_input)
        print(f"\n助手：{response}")

if __name__ == "__main__":
    main()
```

---

## 第八步：部署

### 本地运行

```bash
# 安装依赖
pip install openai chromadb requests

# 运行
python main.py
```

### 生产部署

```python
# 使用 FastAPI 封装为 API 服务
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
agent = PersonalKnowledgeAgent(config, tools, memory, kb)

class Query(BaseModel):
    user_input: str
    user_id: str = "default"

@app.post("/chat")
async def chat(query: Query):
    agent.user_id = query.user_id
    response = agent.run(query.user_input)
    return {"response": response}
```

---

## 扩展方向

这个项目可以从以下方向扩展：

```
1. 多 Agent 协作
   - 添加"研究员 Agent"和"写手 Agent"
   - 研究 Agent 负责搜索，写手 Agent 负责组织

2. 持久化
   - 使用 PostgreSQL 替代 SQLite
   - 添加 Redis 缓存

3. 监控
   - 添加 LangSmith 追踪
   - 记录每次调用的 token 消耗和耗时

4. 多模态
   - 添加图片理解能力
   - 添加语音输入输出

5. 个性化
   - 完善用户画像系统
   - 添加学习型个性化
```

---

## 总结

这个项目在 300 行代码内实现了：

| 功能 | 实现 | 代码行数 |
|------|------|---------|
| 工具调用 | Function Calling | 50 行 |
| 知识库 RAG | ChromaDB | 40 行 |
| 记忆系统 | SQLite | 50 行 |
| Agent 循环 | 手动实现 | 60 行 |
| 工具定义 | 3 个工具 | 30 行 |
| 主入口 | CLI 交互 | 30 行 |

**建议**：先跑起来，再理解，最后改造。

---

> 系列目录：[README.md](./README.md) | 全部 50 篇完成 ✅