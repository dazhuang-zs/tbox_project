# RAG：给 LLM 装上知识库——从原理到完整可运行系统

> LLM 的知识截止在训练日期。RAG 让 AI 能「查资料」回答——这是 Agent 有「长期记忆」的基础。

---

## 一、为什么需要 RAG

```
用户：HarmonyOS NEXT 的 @Observed 装饰器怎么用？

没有 RAG 的 LLM：
"@Observed 是用于..."（可能对，可能编——因为它的训练数据可能没有最新文档）

有 RAG 的 Agent：
1. 把问题向量化
2. 在文档库中检索相关段落
3. 把检索到的文档 + 问题一起发给 LLM
4. LLM 基于真实文档回答 → 准确、有出处
```

---

## 二、RAG 完整流程（5 步）

```
① 文档分块（Chunking）
   大文档切成 512 Token 的小块
        ↓
② 向量化（Embedding）
   每个小块 → 1024 维向量
        ↓
③ 存入向量库
   向量 + 原文 → Milvus / Chroma
        ↓
④ 检索（Retrieval）
   用户问题向量化 → 向量库找 Top-K 相似
        ↓
⑤ 生成（Generation）
   问题 + 检索结果 → LLM → 答案
```

---

## 三、完整 RAG 系统代码

```python
# ── 1. 环境准备 ──
# pip install chromadb sentence-transformers openai

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

# ── 2. 初始化 Chroma（向量数据库） ──
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-large-zh-v1.5"
)

client = chromadb.PersistentClient(path="./rag_db")
collection = client.get_or_create_collection(
    name="harmonyos_docs",
    embedding_function=embedding_fn
)

client_llm = OpenAI(
    api_key="your-key",
    base_url="https://api.deepseek.com/v1"
)

# ── 3. 导入文档 ──
documents = [
    "@Observed 装饰器用于观察类对象的变化。当被 @Observed 装饰的类的属性发生变化时，"
    "绑定该对象的组件会自动重新渲染。用法：@Observed class MyData { ... }",
    
    "@State 装饰器用于声明组件内部的状态变量。当状态变量改变时，组件重新渲染。"
    "@Prop 装饰器用于父组件向子组件传递数据，子组件不能修改 @Prop 变量。",
    
    "HarmonyOS NEXT 基于 ArkTS 语言。ArkTS 是 TypeScript 的超集，"
    "增加了声明式 UI 语法和状态管理能力。API 12 是最新版本。",
]

collection.add(
    documents=documents,
    ids=[f"doc_{i}" for i in range(len(documents))]
)
print(f"✅ 已导入 {len(documents)} 个文档片段")

# ── 4. RAG 查询函数 ──
def rag_query(question: str, n_results: int = 3) -> str:
    # 4.1 向量检索
    results = collection.query(
        query_texts=[question],
        n_results=n_results
    )
    
    # 4.2 拼接检索结果
    retrieved_docs = results["documents"][0]
    context = "\n\n---\n\n".join(retrieved_docs)
    
    # 4.3 调用 LLM 生成答案
    system_prompt = """你是 HarmonyOS 开发助手。请根据提供的参考文档回答问题。
如果文档中没有相关信息，请明确告知。回答时引用文档来源。"""
    
    response = client_llm.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"参考文档：\n{context}\n\n用户问题：{question}"}
        ]
    )
    
    return response.choices[0].message.content

# ── 5. 测试 ──
questions = [
    "@Observed 装饰器是做什么的？",
    "@State 和 @Prop 有什么区别？",
    "HarmonyOS NEXT 用什么语言？",
]

for q in questions:
    print(f"\n{'='*50}")
    print(f"❓ {q}")
    answer = rag_query(q)
    print(f"🤖 {answer}")
```

---

## 四、Embedding 怎么选

| 模型 | 维度 | 中文效果 | 部署难度 |
|------|:--:|:--:|:--:|
| BGE-Large-ZH v1.5 | 1024 | ⭐⭐⭐⭐⭐ | pip install 即用 |
| text2vec-large-chinese | 1024 | ⭐⭐⭐⭐ | 同上 |
| M3E-large | 1024 | ⭐⭐⭐⭐ | 同上 |
| OpenAI text-embedding-3 | 1536 | ⭐⭐⭐ | API 计费 |

> **建议**：BGE-Large-ZH，免费、中文最好、本地跑、1024 维不高不低。

---

## 五、Chunking（分块）策略

| 策略 | 块大小 | 适用场景 |
|------|:--:|------|
| 固定大小 | 512 Token | 通用 |
| 按标题分割 | h2/h3 为界 | 技术文档 |
| 语义分割 | 相似度阈值 | 高级场景 |
| 递归分割 | 按段落→句子 | 混合内容 |

```python
# 按标题分割（适合技术文档）
def split_by_headers(markdown_text: str) -> list[str]:
    """按 ## 和 ### 分割文档"""
    chunks = []
    current_chunk = []
    
    for line in markdown_text.split("\n"):
        if line.startswith("## "):  # 遇到新标题
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            current_chunk = [line]
        else:
            current_chunk.append(line)
    
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    return chunks
```

---

## 六、进阶：混合检索

纯向量检索的准确率约 70-75%。加上关键词检索（BM25），可到 85%+。

```
用户问题
    ↓
   ┌─────────────┐
   ▼             ▼
向量检索      关键词检索(BM25)
 Top-10        Top-10
   └──────┬──────┘
          ▼
    融合排序(RRF)
          │
          ▼
     Top-5 结果 → LLM
```

```python
# 简单实现：向量 + 关键词双路检索
def hybrid_search(query: str, top_k: int = 5):
    # 向量检索
    vec_results = collection.query(query_texts=[query], n_results=top_k)
    
    # 关键词匹配（简单版）
    keywords = set(query)
    keyword_scores = []
    for doc in documents:
        score = sum(1 for kw in keywords if kw in doc)
        keyword_scores.append(score)
    
    # 合并排序（简化的 RRF）
    # 生产环境建议用专门的 RRF 实现
    return vec_results["documents"][0]  # 这里简化了
```

---

## 七、RAG 在 Agent 中的角色

```
                     Agent
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    Function        RAG            对话
    Calling        系统            管理
   （做事）      （查知识）       （记上下文）
        │              │              │
        ▼              ▼              ▼
     天气 API     向量数据库      会话历史
     数据库        文档库          摘要
```

RAG 不是 Agent 的全部，但它是 Agent 的「知识层」。一个没有 RAG 的 Agent 只能说它训练数据里有的东西，有 RAG 的 Agent 能回答任何存入知识库的问题。

---

## 八、生产实战：RAG 系统上线前的检查清单

### 8.1 混合检索 + 重排序（完整代码）

纯向量检索准确率 70-75%。加上 BM25 关键词检索可到 85%+，再加 Cross-Encoder Reranker 可到 90%+：

```python
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
import jieba

def hybrid_search_with_rerank(query: str, all_docs: list[str], top_k: int = 5):
    # 1. 向量检索
    vec_results = collection.query(query_texts=[query], n_results=20)
    
    # 2. BM25 关键词检索
    tokenized_corpus = [list(jieba.cut(doc)) for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(list(jieba.cut(query)))
    bm25_top = sorted(range(len(bm25_scores)), 
                      key=lambda i: bm25_scores[i], reverse=True)[:20]
    
    # 3. RRF 融合 (k=60)
    rrf = {}
    for rank, doc in enumerate(vec_results['documents'][0]):
        rrf[doc] = rrf.get(doc, 0) + 1/(61 + rank)
    for rank, idx in enumerate(bm25_top):
        doc = all_docs[idx]
        rrf[doc] = rrf.get(doc, 0) + 1/(61 + rank)
    
    candidates = sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # 4. Cross-Encoder 重排序
    reranker = CrossEncoder('BAAI/bge-reranker-large')
    pairs = [[query, doc] for doc, _ in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip([d for d,_ in candidates], scores), 
                    key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:top_k]]
```

### 8.2 RAG 评估指标

做 RAG 最怕「感觉变好了」——必须有量化指标：

| 指标 | 含义 | 合格线 |
|------|------|:--:|
| Hit Rate@10 | Top-10 包含正确答案的比例 | > 85% |
| MRR | 第一个正确答案的平均排名倒数 | > 0.6 |
| NDCG@10 | 考虑排序位置的精度 | > 0.7 |

```python
def evaluate_rag(test_queries: list[dict]):
    """test_queries = [{"query": "...", "expected_doc_id": "doc_3"}]"""
    hits, rr = 0, []
    for t in test_queries:
        results = collection.query(query_texts=[t["query"]], n_results=10)
        if t["expected_doc_id"] in results["ids"][0]:
            hits += 1
            rank = results["ids"][0].index(t["expected_doc_id"]) + 1
            rr.append(1/rank)
        else:
            rr.append(0)
    print(f"Hit Rate@10: {hits/len(test_queries):.1%}  MRR: {sum(rr)/len(rr):.4f}")
```

### 8.3 Query 改写：模糊问题搜不到的原因

用户问「上次那个方法怎么用」——直接向量化什么都搜不到。必须先用 LLM 改写：

```python
REWRITE_PROMPT = "将模糊问题改写为适合检索的查询。补充指代，拆解复合问题。输出 {\"queries\": [\"查询1\"]}"

async def rewrite_query(user_input: str, history: list) -> list[str]:
    response = await llm.chat([
        {"role": "system", "content": REWRITE_PROMPT},
        {"role": "user", "content": f"历史：{history}\n问题：{user_input}"}
    ])
    return json.loads(response)["queries"]
```

### 8.4 RAG vs 长 Context：什么时候不需要 RAG

Claude 200K Context Window 能装下一整本书。那还要 RAG 吗？

| 场景 | 方案 | 理由 |
|------|------|------|
| 固定文档（如产品手册） | RAG | 只需检索相关部分 |
| 一次性长文档分析 | 直接塞 Context | RAG 检索有损耗 |
| 多轮对话引用文档 | RAG | 不可能每轮都塞全文 |
| 文档频繁更新 | RAG | 只需更新向量库 |

> **经验**：大多数场景下 RAG 更优。长 Context 是备选方案——Token 成本高且推理速度随 Context 增长线性下降

---

> 下一篇：**《Agent 设计模式：ReAct 与 Plan-Execute》**——两种最经典的 Agent 模式，让你的 Agent 学会「思考」。

*系列文章：00-总纲 → ①-LLM 原理 → ②-Prompt 工程 → ③-Function Calling → ④-RAG → ⑤-Agent 模式 → ⑥-LangGraph → ⑦-MCP → ⑧-Multi-Agent*
