# 【AI Agent 系统教学 16】嵌入模型与向量数据库

> 嵌入模型负责"理解"语义，向量数据库负责"快速找到"相关内容。
> 这两者共同决定了 RAG 的检索质量。

---

## 前言：检索不是"搜索"，是"理解"

传统搜索（关键词搜索）匹配的是"词"——你搜"苹果"，它找包含"苹果"的文档。

RAG 的检索匹配的是"语义"——你搜"水果"，它也能找到"苹果"相关的文档。

这个"语义理解"的能力，来自**嵌入模型（Embedding Model）**。

---

## 一、嵌入模型

### 1.1 什么是嵌入模型

嵌入模型把文本转换为向量（数字数组），使得语义相近的文本在向量空间中距离更近。

```
"苹果很好吃" → [0.12, 0.34, -0.56, 0.78, ...]  (768维)
"香蕉很甜"   → [0.15, 0.31, -0.52, 0.81, ...]  (距离近，语义相似)
"汽车发动了" → [0.89, -0.23, 0.45, -0.67, ...] (距离远，语义不相关)
```

### 1.2 主流嵌入模型对比（2026年）

| 模型 | 维度 | 最大输入 | 语言 | 价格 | 特点 |
|------|------|---------|------|------|------|
| text-embedding-3-large | 3072 | 8191 | 多语言 | 高 | 能力最强，最贵 |
| text-embedding-3-small | 1536 | 8191 | 多语言 | 低 | 性价比高 |
| bge-large-zh-v1.5 | 1024 | 512 | 中文 | 免费 | 中文最强之一 |
| m3e-base | 768 | 512 | 中文 | 免费 | 轻量级中文 |
| GTE-Qwen2 | 4096 | 8192 | 多语言 | 免费 | 开源，能力接近商业 |
| stella-base-zh-v3 | 768 | 512 | 中文 | 免费 | 小模型，快速 |

### 1.3 嵌入模型的选型

```python
def select_embedding_model(
    language="zh",
    budget="low",
    quality="high",
    max_input_length=512,
):
    """
    嵌入模型选型建议
    """
    if language == "zh":
        if budget == "free" and quality == "high":
            return "GTE-Qwen2"  # 开源最强
        elif budget == "free" and quality == "medium":
            return "bge-large-zh-v1.5"
        elif budget == "free" and quality == "fast":
            return "stella-base-zh-v3"
        else:
            return "text-embedding-3-small"  # 付费但可靠
    else:
        if budget == "high":
            return "text-embedding-3-large"
        else:
            return "text-embedding-3-small"
```

### 1.4 嵌入模型的评估指标

```
MTEB（Massive Text Embedding Benchmark）：
  - 分类准确率
  - 聚类质量
  - 检索质量（最重要的指标）
  - 语义相似度
  - 重排序能力
  
C-MTEB（中文版）：
  - 同上，但使用中文数据集
```

---

## 二、向量数据库

### 2.1 向量数据库做什么

向量数据库的核心功能：**快速找到与查询向量最相似的 K 个向量。**

```
输入：查询向量 [0.12, 0.34, ...]
输出：最相似的 K 个文档及其相似度分数

挑战：当向量库有 1000 万条数据时，暴力搜索需要 1000 万次比较
解决方案：使用近似最近邻（ANN）算法
```

### 2.2 主流向量数据库对比

| 数据库 | 类型 | 索引算法 | 处理能力 | 运维 | 特点 |
|-------|------|---------|---------|------|------|
| Chroma | 嵌入式 | HNSW | 小规模 | 无需运维 | 原型开发首选 |
| Pinecone | 托管 | 专有 | 大规模 | 全托管 | 开箱即用 |
| Weaviate | 独立服务 | HNSW + 自定义 | 中等 | 自托管 | 支持混合检索 |
| Qdrant | 独立服务 | HNSW | 大规模 | 自托管 | Rust 实现，性能好 |
| Milvus | 分布式 | 多种 | 超大规模 | 复杂 | 企业级 |
| PGVector | PostgreSQL 插件 | IVFFlat/HNSW | 中等 | 使用 Postgres | 不需要额外数据库 |
| FAISS | 库（非数据库） | 多种 | 任意 | 无 | 底层引擎，需要自己包装 |

### 2.3 选型建议

```
原型阶段（< 10 万条）：
  Chroma 或 PGVector
  - 无需额外部署
  - 快速验证

生产阶段（< 100 万条）：
  Qdrant 或 Weaviate
  - 自托管，成本可控
  - 支持混合检索

大规模（> 1000 万条）：
  Milvus 或 Pinecone
  - 分布式，高可用
  - 专业运维
```

### 2.4 索引算法

| 算法 | 检索速度 | 构建速度 | 内存占用 | 召回率 |
|------|---------|---------|---------|-------|
| 暴力搜索 | 最慢 | 无 | 最低 | 100% |
| IVFFlat | 快 | 快 | 低 | 90-95% |
| HNSW | 最快 | 慢 | 高 | 95-99% |
| IVF_PQ | 很快 | 中等 | 极低（压缩） | 85-95% |

**HNSW 是 2026 年最推荐的生产级索引算法**——速度快，召回率高，虽然内存占用大但值得。

---

## 三、向量检索的优化

### 3.1 检索质量优化

```python
class RAGRetriever:
    def __init__(self, embedding_model, vector_db):
        self.embedder = embedding_model
        self.db = vector_db
    
    def retrieve(self, query, k=5, rerank=True):
        # 1. 查询嵌入
        query_vec = self.embedder.embed(query)
        
        # 2. 向量检索（取更多，留给重排序筛）
        candidates = self.db.search(query_vec, k=k*3 if rerank else k)
        
        # 3. 重排序
        if rerank:
            candidates = self.rerank(query, candidates)
            candidates = candidates[:k]
        
        return candidates
    
    def rerank(self, query, candidates):
        """使用重排序模型优化结果"""
        # 重排序模型（如 BGE-reranker）对每个候选重新打分
        pairs = [(query, doc.text) for doc in candidates]
        scores = self.reranker.score(pairs)
        
        # 按新分数排序
        ranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return [doc for doc, _ in ranked]
```

### 3.2 混合检索

```python
class HybridRetriever:
    def __init__(self, vector_db, bm25_index):
        self.vector_db = vector_db
        self.bm25 = bm25_index
    
    def retrieve(self, query, k=5, alpha=0.5):
        # 向量检索
        vector_results = self.vector_db.search(query, k=k*2)
        
        # 关键词检索
        keyword_results = self.bm25.search(query, k=k*2)
        
        # 分数融合
        scores = {}
        for doc, score in vector_results:
            scores[doc.id] = scores.get(doc.id, 0) + alpha * score
        
        for doc, score in keyword_results:
            scores[doc.id] = scores.get(doc.id, 0) + (1-alpha) * score
        
        # 排序
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:k]
```

### 3.3 元数据过滤

在检索时加上元数据过滤条件：

```python
def retrieve_with_filter(query, filters, k=5):
    """
    filters: 
    {
        "date": {"gte": "2026-01-01"},
        "category": {"eq": "技术文档"},
        "author": {"eq": "张三"},
    }
    """
    results = vector_db.search(
        embedding=embed(query),
        k=k,
        filter=filters,  # 只检索符合过滤条件的文档
    )
    return results
```

---

## 四、实战：构建 RAG 索引

### 4.1 索引构建流程

```python
class RAGIndexBuilder:
    def __init__(self, embedder, vector_db, chunker):
        self.embedder = embedder
        self.db = vector_db
        self.chunker = chunker
    
    def build_index(self, documents):
        """
        构建完整的 RAG 索引
        """
        for doc_id, doc in enumerate(documents):
            # 1. 分块
            chunks = self.chunker.chunk(doc.text)
            
            for chunk_id, chunk in enumerate(chunks):
                # 2. 生成嵌入
                embedding = self.embedder.embed(chunk)
                
                # 3. 存储
                self.db.insert({
                    "id": f"{doc_id}_{chunk_id}",
                    "text": chunk,
                    "embedding": embedding,
                    "metadata": {
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                        "source": doc.source,
                        "date": doc.date,
                    }
                })
        
        # 4. 构建索引
        self.db.create_index()
```

### 4.2 增量更新

```python
def incremental_update(self, new_documents):
    """增量更新索引"""
    for doc in new_documents:
        chunks = self.chunker.chunk(doc.text)
        for chunk_id, chunk in enumerate(chunks):
            embedding = self.embedder.embed(chunk)
            self.db.insert({
                "id": f"new_{doc.id}_{chunk_id}",
                "text": chunk,
                "embedding": embedding,
                "metadata": doc.metadata,
            })
    
    # 只需要更新新增数据的索引
    self.db.update_index(incremental=True)
```

---

## 五、常见问题与优化

### 5.1 检索质量诊断

```python
def diagnose_retrieval(query, expected_docs, retrieved_docs):
    """诊断检索质量问题"""
    issues = []
    
    # 1. 检查召回率
    recall = len(set(expected_docs) & set(retrieved_docs)) / len(expected_docs)
    if recall < 0.8:
        issues.append(f"召回率低 ({recall:.2f})：检索到的文档中缺少关键信息")
    
    # 2. 检查精度
    precision = len(set(expected_docs) & set(retrieved_docs)) / len(retrieved_docs)
    if precision < 0.6:
        issues.append(f"精度低 ({precision:.2f})：检索到太多不相关文档")
    
    # 3. 检查结果稳定性
    results_v1 = retrieved_docs
    results_v2 = retrieve(query)
    stability = jaccard_similarity(results_v1, results_v2)
    if stability < 0.7:
        issues.append("检索结果不稳定：多次检索结果差异大")
    
    return issues
```

### 5.2 常见问题

| 问题 | 表现 | 原因 | 解决方案 |
|------|------|------|---------|
| 检索不到 | 返回空结果 | 查询词与文档不匹配 | 查询扩写、混合检索 |
| 检索不相关 | 返回无关内容 | 嵌入模型理解偏差 | 换更好的嵌入模型 |
| 检索太慢 | 响应时间长 | 索引不当或数据量大 | 优化索引、增加硬件 |
| 结果不稳定 | 同查询不同结果 | 索引未固化或数据在变 | 固化索引、减少实时更新 |

---

## 六、2026 年向量技术趋势

### 6.1 嵌入模型的新方向

- **多模态嵌入**：文本、图像、音频统一嵌入
- **稀疏嵌入**：结合稠密和稀疏的优点
- **领域微调**：在特定领域的嵌入模型

### 6.2 向量数据库的演进

- **DiskANN**：基于磁盘的 ANN，支持超大规模
- **GPU 加速**：利用 GPU 加速向量检索
- **Serverless**：无服务器向量数据库
- **SQL 融合**：向量检索与 SQL 查询的深度融合

---

## 总结

| 组件 | 核心功能 | 选型关键 |
|------|---------|---------|
| 嵌入模型 | 把文本变成向量 | 语言、维度、成本 |
| 向量数据库 | 快速近似最近邻搜索 | 规模、运维、延迟 |
| 索引算法 | 加速检索 | HNSW 是首选 |
| 重排序 | 优化检索结果 | 用小模型提高精度 |

**RAG 的检索质量 = 嵌入模型质量 × 向量数据库性能 × 检索策略。**

下一篇文章，我们将深入**密集检索 vs 稀疏检索**——BM25、Dense Retrieval、混合检索，以及如何选择。

---

**思考题**：
1. 你的场景适合用哪个嵌入模型？为什么？
2. 向量数据库和普通数据库（PostgreSQL + PGVector）有什么区别？什么时候用哪个？
3. 如果检索结果质量不好，你会从哪个环节开始排查？

---

> 上一篇：[15] RAG 基础架构：检索-阅读-生成
> 下一篇：[17] 密集检索 vs 稀疏检索
> 系列目录：[README.md](./README.md)