# 【AI Agent 系统教学 18】检索增强策略：查询改写与 HyDE

> 不是用户不会问问题，是我们的检索系统不够聪明。
> 查询改写，就是帮用户"问对问题"。

---

## 前言：用户的查询质量参差不齐

用户不会按你的检索系统设计的格式提问。他们可能是这样问的：

- "那个、就是、上次那个事"（模糊）
- "帮我看看"（不完整）
- "苹果"（一个词，信息量太少）
- "为什么我的代码跑不起来？"（笼统）

直接把这些查询扔给检索系统，结果大概率不好。

**检索增强策略**就是解决这个问题——在检索之前、之后，对查询和结果进行优化。

---

## 一、查询改写

### 1.1 什么是查询改写

用 LLM 把用户输入的原始查询，变成"对检索系统友好"的查询。

```python
def rewrite_query(original_query, llm):
    prompt = f"""
    原始用户查询：{original_query}
    
    请改写这个查询，使其更适合在知识库中检索：
    1. 扩展缩写
    2. 补充上下文
    3. 明确核心实体
    4. 使用更精确的术语
    5. 如果有多个意图，拆分成多个子查询
    
    改写后的查询：
    """
    return llm.generate(prompt)
```

### 1.2 查询改写示例

```
原始查询："那个太慢了，怎么搞"
改写后："如何优化程序性能，解决运行慢的问题？"

原始查询："上次那个报错"
改写后："记录上次遇到的错误信息及其解决方案"

原始查询："苹果"
改写后："苹果公司 或 苹果水果"
（拆分成两个子查询）
```

### 1.3 查询分解

对于复杂查询，拆分成多个子查询分别检索：

```python
def decompose_query(query, llm):
    """把复杂查询分解成多个子查询"""
    prompt = f"""
    原始查询：{query}
    
    这个查询包含多个子问题，请拆分成独立的子查询：
    - 每个子查询独立可检索
    - 子查询之间不重叠
    - 覆盖原始查询的所有意图
    
    子查询列表（每行一个）：
    """
    sub_queries = llm.generate(prompt).split("\n")
    return [q.strip() for q in sub_queries if q.strip()]
```

**示例**：

```
原始查询："今年的销售数据怎么样？和去年比有什么变化？有什么改进建议？"

子查询 1："2026年销售数据"
子查询 2："2025年销售数据对比"
子查询 3："销售改进建议"
```

---

## 二、HyDE（假设性文档嵌入）

### 2.1 核心思想

HyDE 的思路非常巧妙：

> **不在"查询空间"中检索，而在"回答空间"中检索。**

步骤如下：
1. 让 LLM 根据查询生成一个"假设性回答"
2. 用这个假设性回答的嵌入去检索
3. 检索到与"假设性回答"相似的文档

**为什么有效？** 查询和文档的表述方式差异很大（查询是问题，文档是答案），但"假设性回答"和文档的表述方式相似。

### 2.2 HyDE 实现

```python
class HyDERetriever:
    def __init__(self, llm, embedder, vector_db):
        self.llm = llm
        self.embedder = embedder
        self.db = vector_db
    
    def retrieve(self, query, k=5):
        # 1. 生成假设性回答
        hypothetical_doc = self.generate_hypothetical_doc(query)
        
        # 2. 用假设性回答的嵌入检索
        hypothetical_embedding = self.embedder.embed(hypothetical_doc)
        
        # 3. 向量检索
        results = self.db.search(hypothetical_embedding, k=k)
        
        return results
    
    def generate_hypothetical_doc(self, query):
        prompt = f"""
        问题：{query}
        
        请基于你的知识，写一段关于这个问题的回答。
        不需要非常准确，只需要描述"这种类型的问题通常会在什么文档中找到答案"。
        用陈述句，类似知识库中的文档风格。
        """
        return self.llm.generate(prompt)
```

### 2.3 HyDE 效果

```
查询："如何优化 Python 性能"

直接检索（查询嵌入）：
  "Python 基础教程" → 0.65
  "Python 性能优化技巧" → 0.72  ← 但可能不是最佳

HyDE 检索（假设性回答嵌入）：
  假设性回答："Python 性能优化通常涉及：选择合适的数据结构、
  使用内置函数、避免循环中的重复计算、使用多线程/多进程..."
  
  检索结果：
  "Python 性能优化：10 个实用技巧" → 0.91
  "Python 数据结构选择指南" → 0.87
  "Python 多线程编程实战" → 0.85
```

**HyDE 在查询和文档表述差异大时效果最好**（如用户问口语化问题，文档是正式文档）。

---

## 三、RAG Fusion

### 3.1 核心思想

RAG Fusion 结合了**多路检索 + 结果融合**：

```
1. 用不同的方法检索同一个查询
2. 融合所有结果
3. 用重排序得到最终结果
```

### 3.2 实现

```python
class RAGFusion:
    def __init__(self, retrievers):
        """
        retrievers: 多个检索器的列表
        [
            ("query_original", DenseRetriever()),
            ("query_rewritten", DenseRetriever()),
            ("hyde", HyDERetriever()),
            ("bm25", BM25Retriever()),
        ]
        """
        self.retrievers = retrievers
    
    def search(self, query, k=5):
        all_results = []
        
        # 1. 多路检索
        for name, retriever in self.retrievers:
            results = retriever.retrieve(query, k=k*2)
            for doc, score in results:
                all_results.append({
                    "doc": doc,
                    "score": score,
                    "source": name,
                })
        
        # 2. 融合（使用 Reciprocal Rank Fusion）
        fused = self.rrf(all_results)
        
        # 3. 取 top-k
        return fused[:k]
    
    def rrf(self, results, k=60):
        """Reciprocal Rank Fusion"""
        doc_scores = {}
        for doc_info in results:
            doc_id = doc_info["doc"].id
            # RRF 分数：1 / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1 / (k + doc_info["rank"])
        
        ranked = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked
```

---

## 四、多轮检索

### 4.1 迭代式检索

对于复杂问题，单次检索可能不够。迭代式检索逐步深入：

```python
def iterative_retrieval(query, retriever, llm, max_iterations=3):
    context = []
    current_query = query
    
    for i in range(max_iterations):
        # 检索
        docs = retriever.retrieve(current_query, k=3)
        context.extend(docs)
        
        # 判断信息是否足够
        judgment = llm.generate(f"""
        当前上下文：{context}
        原始问题：{query}
        
        基于以上信息，是否能回答原始问题？
        如果不够，还需要什么信息？
        """)
        
        if "足够" in judgment:
            return context
        
        # 提取下一轮查询
        current_query = llm.generate(f"""
        原始问题：{query}
        已有信息：{context}
        还缺什么信息？请生成一个检索查询来获取缺失的信息。
        """)
    
    return context
```

### 4.2 自适应检索深度

根据任务复杂度，自动决定检索轮次：

```python
def adaptive_retrieval(query, retriever, llm, max_depth=5):
    depth = 1
    context = []
    confidence = 0
    
    while depth <= max_depth and confidence < 0.9:
        # 检索更多
        docs = retriever.retrieve(query, k=depth)
        context.extend(docs)
        
        # 评估置信度
        confidence = llm.evaluate(f"""
        问题：{query}
        当前信息：{context}
        你对基于这些信息回答问题的信心（0-1）：""")
        
        depth += 1
    
    return context
```

---

## 五、检索优化的实战策略

### 5.1 策略组合

```python
class AdvancedRAGPipeline:
    def __init__(self, llm, dense_retriever, sparse_retriever):
        self.llm = llm
        self.dense = dense_retriever
        self.sparse = sparse_retriever
        self.hyde = HyDERetriever(llm, dense_retriever.embedder, dense_retriever.db)
    
    def retrieve(self, query, k=5):
        # 1. 查询改写
        rewritten = self.rewrite_query(query)
        
        # 2. 多路检索
        results = []
        
        # 原始查询 + 密集检索
        results.extend(self.dense.retrieve(query, k=3))
        
        # 改写查询 + 密集检索
        results.extend(self.dense.retrieve(rewritten, k=3))
        
        # HyDE 检索
        results.extend(self.hyde.retrieve(query, k=3))
        
        # BM25 检索
        results.extend(self.sparse.retrieve(rewritten, k=3))
        
        # 3. 去重
        results = self.deduplicate(results)
        
        # 4. 重排序
        results = self.rerank(query, results)
        
        return results[:k]
```

### 5.2 优化效果

| 策略 | 检索质量提升 | 延迟增加 | 成本增加 |
|------|------------|---------|---------|
| 查询改写 | +5-15% | +100ms | +1 次 LLM 调用 |
| HyDE | +10-20% | +200ms | +1 次 LLM + 1 次嵌入 |
| 多路检索 | +5-10% | +100ms | +少量检索 |
| 重排序 | +10-25% | +50ms | +1 次重排序模型调用 |
| 多轮检索 | +15-30% | +500ms | +多次 LLM + 检索 |
| RAG Fusion | +10-20% | +200ms | +多路检索 |

---

## 六、Agent 中的检索增强实践

### 6.1 让 Agent 决定检索策略

```python
@tool("search_with_strategy")
def search_with_strategy(query: str, strategy: str = "auto"):
    """
    使用高级检索策略搜索知识库
    strategy: "auto", "simple", "hyde", "fusion", "iterative"
    """
    if strategy == "auto":
        strategy = detect_best_strategy(query)
    
    if strategy == "simple":
        return basic_retrieve(query)
    elif strategy == "hyde":
        return hyde_retrieve(query)
    elif strategy == "fusion":
        return fusion_retrieve(query)
    elif strategy == "iterative":
        return iterative_retrieve(query)
```

### 6.2 检索结果的引用

让 Agent 在回答中引用检索结果的来源：

```python
def answer_with_citations(query, retrieved_docs, llm):
    prompt = f"""
    问题：{query}
    
    参考信息：
    {format_docs_with_ids(retrieved_docs)}
    
    请回答问题，并在回答中引用信息来源（如 [1]、[2]）。
    如果参考信息中没有相关内容，请说"参考信息中没有找到相关内容"。
    """
    return llm.generate(prompt)
```

---

## 总结

| 策略 | 解决问题 | 适用场景 |
|------|---------|---------|
| 查询改写 | 用户查询质量差 | 用户输入模糊、口语化 |
| HyDE | 查询与文档表述差异大 | 查询是问题，文档是答案 |
| 多路检索 | 单一检索方法不足 | 数据多样性高 |
| RAG Fusion | 不同检索方法结果不一致 | 需要稳定可靠的检索 |
| 多轮检索 | 复杂问题一次检索不够 | 需要逐步深入信息 |

**检索增强不是"要不要做"的问题，而是"做多深"的问题。**

下一篇文章，我们将进入**高级 RAG**——RAPTOR、CRAG、Self-RAG 等前沿方案。

---

**思考题**：
1. 你的场景中，查询改写会带来多大的提升？有没有查询改写反而"改坏"的情况？
2. HyDE 在什么场景下效果最好？什么场景下效果反而不如直接检索？
3. 多轮检索的"什么时候停止"是一个关键问题，你有哪些判断标准？

---

> 上一篇：[17] 密集检索 vs 稀疏检索
> 下一篇：[19] 高级 RAG：RAPTOR、CRAG、Self-RAG
> 系列目录：[README.md](./README.md)