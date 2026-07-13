# 【AI Agent 系统教学 15】RAG 基础架构：检索-阅读-生成

> 模型的"知识"是训练时定格的，但世界在变。
> RAG 就是给模型装上一根"网线"——实时、可验证、可更新。

---

## 前言：为什么 Agent 需要 RAG

Agent 的核心能力之一是"获取信息"。但模型内部的知识有几个硬伤：

1. **知识截止**：模型不知道训练之后的任何事情
2. **幻觉**：模型会编造不确定的信息
3. **不精确**：模型的知识是"模糊"的，不是"精确"的
4. **不可更新**：想更新知识，得重新训练

RAG（Retrieval-Augmented Generation）解决这些问题：**不是让模型"记住"知识，而是让模型"检索"知识。**

```
模型：我"知道"的知识 → 训练时定格的，不可靠
RAG：我"检索"的知识 → 实时获取的，可验证
```

---

## 一、RAG 的核心流程

### 1.1 三段式架构

```
用户输入
    ↓
① 检索（Retrieve）
   从知识库中找到相关文档
    ↓
② 增强（Augment）
   把检索到的文档加入上下文
    ↓
③ 生成（Generate）
   模型基于上下文 + 用户输入生成回答
    ↓
输出
```

### 1.2 最小可运行示例

```python
def rag_pipeline(query, docs, llm, retriever):
    # 1. 检索
    relevant_docs = retriever.retrieve(query, k=3)
    
    # 2. 增强
    context = "\n\n".join([
        f"文档 {i+1}：{doc}"
        for i, doc in enumerate(relevant_docs)
    ])
    
    # 3. 生成
    prompt = f"""
    基于以下信息回答问题：
    
    {context}
    
    问题：{query}
    
    请基于以上信息回答，不要添加外部知识。
    如果信息不足以回答问题，请说"信息不足"。
    """
    
    return llm.generate(prompt)
```

### 1.3 Naive RAG vs 高级 RAG

| 阶段 | Naive RAG | 高级 RAG |
|------|----------|---------|
| 检索前 | 直接检索 | 查询改写、HyDE、查询分解 |
| 检索 | 简单向量检索 | 多路检索、混合检索 |
| 检索后 | 直接拼接 | 重排序、过滤、去重 |
| 生成 | 单次生成 | 多轮生成、验证、迭代 |

---

## 二、Chunk（分块）策略

### 2.1 为什么需要分块

文档通常很长（整本书、整篇论文），不能直接当作检索单元。需要把文档切成小块。

### 2.2 分块方法

```python
# 方法 1：固定长度分块（最简单）
def fixed_chunk(text, chunk_size=512, overlap=50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

# 方法 2：语义分块（推荐）
def semantic_chunk(text, model):
    """在语义边界处切分（段落、章节、句子）"""
    # 先按段落切分
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) > MAX_CHUNK_SIZE:
            chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk += "\n\n" + para
    
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

# 方法 3：递归分块（LangChain 方法）
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "，", " ", ""],
)
chunks = splitter.split_text(text)
```

### 2.3 分块参数

| 参数 | 推荐值 | 说明 |
|------|-------|------|
| chunk_size | 256-1024 | 太小信息不完整，太大检索精度下降 |
| chunk_overlap | 10-20% | 避免边界处信息丢失 |
| separators | 按语义层级 | 从粗到细，避免在句子中间切分 |

---

## 三、检索策略

### 3.1 检索方法对比

| 方法 | 原理 | 适合场景 | 局限性 |
|------|------|---------|--------|
| 向量检索 | 语义相似度搜索 | 语义匹配 | 对精确匹配不敏感 |
| 关键词检索 | BM25 词频匹配 | 精确匹配 | 对语义理解差 |
| 混合检索 | 两者结合 | 通用 | 需要调权重 |
| SQL 检索 | 结构化查询 | 有结构的数据 | 需要精确查询条件 |

### 3.2 向量检索

```python
def vector_retrieve(query, embeddings, vector_db, k=5):
    # 1. 把查询转为向量
    query_embedding = embeddings.embed(query)
    
    # 2. 在向量数据库中搜索
    results = vector_db.search(
        query_embedding,
        k=k,
        metric="cosine",  # 或 "dot_product", "euclidean"
    )
    
    return results
```

### 3.3 混合检索

```python
def hybrid_retrieve(query, chunks, k=5, alpha=0.5):
    """
    混合检索：向量检索 + BM25 关键词检索
    alpha: 向量检索的权重（0-1）
    """
    # 1. 向量检索
    vector_scores = vector_retrieve(query, chunks, k*2)
    
    # 2. BM25 关键词检索
    keyword_scores = bm25_retrieve(query, chunks, k*2)
    
    # 3. 融合分数
    combined_scores = {}
    for doc, score in vector_scores:
        combined_scores[doc] = alpha * score
    for doc, score in keyword_scores:
        combined_scores[doc] = combined_scores.get(doc, 0) + (1-alpha) * score
    
    # 4. 排序取 top-k
    ranked = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:k]]
```

---

## 四、增强（Augment）策略

### 4.1 上下文注入

把检索到的文档注入到 Prompt 中：

```python
def augment_prompt(query, retrieved_docs, template="default"):
    if template == "default":
        return f"""
        基于以下信息回答问题：
        
        {format_docs(retrieved_docs)}
        
        问题：{query}
        
        要求：
        - 只基于提供的信息回答
        - 如果信息不足，说"信息不足"
        - 引用信息来源
        """
    
    elif template == "agent":
        return f"""
        你是一个 AI Agent。以下是检索到的参考信息：
        
        {format_docs(retrieved_docs)}
        
        用户问题：{query}
        
        请根据参考信息回答用户的问题。
        如果信息不足以回答，请使用搜索工具获取更多信息。
        """
    
    return template
```

### 4.2 多轮增强

对于复杂问题，可能需要多轮检索：

```python
def multi_step_rag(query, llm, retriever, max_steps=3):
    context = []
    current_query = query
    
    for step in range(max_steps):
        # 检索
        docs = retriever.retrieve(current_query, k=3)
        context.extend(docs)
        
        # 判断信息是否足够
        prompt = f"""
        基于以下信息，你能回答这个问题吗？
        
        信息：{context}
        问题：{query}
        
        如果足够回答，请给出答案。
        如果不够，请说明还需要什么信息。
        """
        
        response = llm.generate(prompt)
        
        # 检查是否足够
        if "信息不足" not in response:
            return response
        
        # 提取需要的信息，作为下一轮检索的查询
        current_query = extract_missing_info(response)
    
    return "经过多轮检索，仍无法回答这个问题。"
```

---

## 五、RAG 的常见问题

### 5.1 检索不到关键信息

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 查询词不匹配 | 用户用词和文档用词不同 | 查询扩写、同义词替换 |
| 分块不合理 | 信息被切分到不同块中 | 改进分块策略、增加 overlap |
| 检索数量不足 | top-3 不够 | 增加检索数量、重排序 |
| 索引不完整 | 文档没有正确索引 | 检查索引流程 |

### 5.2 检索到的信息不相关

```
问题：番茄炒蛋怎么做？
检索到：番茄的种植技术

解决方案：提高检索质量
- 使用更好的嵌入模型
- 增加重排序步骤
- 降低检索数量，提高精度
```

### 5.3 模型忽略检索结果

```
问题：模型基于自己的知识回答，而不是检索到的信息

解决方案：
- 在 Prompt 中明确强调"只基于以下信息"
- 使用"信息不足"作为默认输出
- 降低模型的 temperature（减少创造性）
```

---

## 六、RAG 在 Agent 中的角色

### 6.1 作为工具

在 Agent 中，RAG 通常作为**工具**被调用：

```python
@tool
def search_knowledge_base(query: str) -> str:
    """
    搜索公司内部知识库
    适合：查询公司政策、产品信息、技术文档
    """
    docs = retriever.retrieve(query, k=3)
    return format_docs(docs)
```

### 6.2 与 Agent Memory 的关系

```
Agent Memory：存储"对话历史"和"用户偏好"
RAG：存储"外部知识"和"文档信息"

Memory 是"这个人说过什么"
RAG 是"这个知识库有什么"
```

### 6.3 RAG 的局限性

RAG 不是万能的。它解决的是"获取信息"的问题，不是"推理"的问题。

```
RAG 擅长：需要精确信息的场景
RAG 不擅长：需要推理、分析、综合的场景

一个 Agent 的正确用法：
RAG 负责提供事实基础
模型负责推理和决策
```

---

## 总结

| 阶段 | 核心组件 | 关键决策 |
|------|---------|---------|
| 检索 | 索引、分块、嵌入模型 | 分块策略、检索方法 |
| 增强 | Prompt 模板、上下文注入 | 注入方式、引用格式 |
| 生成 | LLM | 温度控制、约束条件 |

**RAG 给 Agent 装上了"知识库"——模型不再需要记住所有知识，只需要知道怎么检索。**

下一篇文章，我们将深入**嵌入模型与向量数据库**——如何选择 Embedding 模型、向量库的选型对比，以及如何优化检索质量。

---

**思考题**：
1. 你的 Agent 场景中，哪些信息需要通过 RAG 获取？哪些靠模型内部知识就够了？
2. 分块大小对检索质量有什么影响？你会在什么场景选择 256、512、1024 的分块大小？
3. RAG 作为 Agent 的工具，和直接调用搜索 API 有什么区别？什么时候用哪个？

---

> 上一篇：[14] 从 Prompt 到 Context Engineering
> 下一篇：[16] 嵌入模型与向量数据库
> 系列目录：[README.md](./README.md)