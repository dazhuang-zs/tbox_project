# 强烈推荐收藏！RAG 深度原理：从向量数学到混合检索——Embedding是什么、索引算法怎么选、Hit Rate怎么算

> 70%的 RAG 文章只教你「pip install chromadb」。本文讲剩下的30%——Embedding 的数学直觉、IVF→HNSW→DiskANN 的算法演进、Hit Rate/MRR/NDCG 的数学定义、以及为什么加了 Reranker 后准确率能从 75% 飙升到 92%。

---

## 一、Embedding 的本质：把语义变成距离

### 1.1 从 One-Hot 到 Dense Vector

```python
# One-Hot 编码（传统做法）：10 万个词 → 10 万维稀疏向量
"猫" → [0, 0, 0, ..., 1, ..., 0]  # 只有一个 1，其余全 0
"狗" → [0, 0, 0, ..., 1, ..., 0]  # 另一个位置的 1

# 问题：
# - "猫"和"狗"的向量距离等于"猫"和"电脑"的距离（都是正交）
# - 10 万维向量，99.99%是 0，浪费空间

# Dense Embedding（现代做法）：压缩到 1024 维
"猫" → [0.12, -0.45, 0.78, ..., 0.33]    # 1024 维密集向量
"狗" → [0.11, -0.43, 0.76, ..., 0.31]    # 和"猫"很接近
"电脑" → [-0.54, 0.92, -0.15, ..., 0.67]  # 和"猫"很远
```

Embedding 模型的训练目标：**让语义相近的词在高维空间中靠在一起。** 这个空间就是「语义空间」。

### 1.2 Cosine Similarity：衡量两个向量的夹角

```python
import numpy as np

def cosine_similarity(a, b):
    """余弦相似度：-1（完全相反）到 1（完全相同）"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# 示例
cat = np.array([0.12, -0.45, 0.78])
dog = np.array([0.11, -0.43, 0.76])
computer = np.array([-0.54, 0.92, -0.15])

print(f"猫 vs 狗: {cosine_similarity(cat, dog):.3f}")      # 0.996 → 极近
print(f"猫 vs 电脑: {cosine_similarity(cat, computer):.3f}")  # -0.512 → 很远
```

### 1.3 常用 Embedding 模型

| 模型 | 维度 | 中文 | 大小 | 适合 |
|------|:--:|:--:|:--:|------|
| BGE-Large-ZH v1.5 | 1024 | ⭐⭐⭐⭐⭐ | 1.3GB | 中文通用 |
| M3E-large | 1024 | ⭐⭐⭐⭐ | 420MB | 轻量中文 |
| text-embedding-3-small | 1536 | ⭐⭐⭐ | API | 多语言 |
| GTE-Qwen2-7B | 3584 | ⭐⭐⭐⭐⭐ | 14GB | 最高精度 |

> BGE-Large-ZH 是中文 RAG 的最佳性价比选择——1024 维不大不小，中文排名常年第一。

---

## 二、向量索引：从暴力搜索到百亿级

### 2.1 暴力搜索：O(N)

```python
def brute_force_search(query_vec, all_vecs, k=5):
    scores = [cosine_similarity(query_vec, v) for v in all_vecs]
    top_k_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return top_k_indices
# 100万条数据 → 每次检索要算100万次余弦相似度 → 慢
```

### 2.2 IVF_FLAT：先聚类再搜索

```
离线阶段：
  1. 对所有向量做 K-Means 聚类 → 划分成 N 个桶
  2. 每个桶有一个「中心点」

在线检索：
  1. 先找离查询向量最近的 M 个桶（M << N）
  2. 只在选中的桶里精确搜索
```

**效果**：100 万条数据，暴力搜索 100 万次 → IVF 只搜 1-5 万次。精度损失约 2-3%。

### 2.3 HNSW：图索引

```
构建一个小世界图：
  - 每个向量是一个节点
  - 相近的向量之间连边
  - 构建多层图结构（类似跳表的思路）

检索：
  1. 从顶层的入口点开始
  2. 贪心搜索：每次跳到最近的邻居
  3. 逐层往下，直到最底层
```

| 算法 | 构建速度 | 检索速度 | 精度 | 内存 |
|------|:--:|:--:|:--:|:--:|
| 暴力 | 即时 | O(N) | 100% | 低 |
| IVF_FLAT | 慢 | 快 | 97-99% | 中 |
| HNSW | 很慢 | 很快 | 98-99.5% | 高 |
| DiskANN | 很慢 | 快 | 96-98% | 低(磁盘) |

> **选型**: <100万条用 HNSW（精度最高），>1亿条用 DiskANN（唯一能上磁盘的）

---

## 三、混合检索：向量 + BM25

### 3.1 为什么纯向量检索不够

```python
# 向量检索的盲区
query = "React 18 的新特性"
向量检索 → 返回 "React 17 升级指南"（语义近，但不相关）
BM25     → 返回 "React 18 发布博客"（关键词精确匹配）

# 结合两者
混合检索 → 两路取 Top-20 → RRF 融合 → Top-10
```

### 3.2 RRF（Reciprocal Rank Fusion）

```python
def reciprocal_rank_fusion(results_a, results_b, k=60):
    """
    融合两路结果的简单而有效的方法
    score = Σ 1/(k + rank)
    """
    scores = {}
    for rank, doc in enumerate(results_a):
        scores[doc] = scores.get(doc, 0) + 1 / (k + rank + 1)
    for rank, doc in enumerate(results_b):
        scores[doc] = scores.get(doc, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### 3.3 Cross-Encoder Reranker

```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder("BAAI/bge-reranker-large")

# Bi-Encoder (Embedding 模型): 一次看一篇文档 → 快但粗糙
# Cross-Encoder (Reranker): 同时看 query + doc → 慢但精准

# 所以：先用 Bi-Encoder 捞 Top-20，再用 Cross-Encoder 精排 Top-5
pairs = [[query, doc] for doc in top_20_docs]
scores = reranker.predict(pairs)
top_5 = sorted(zip(top_20_docs, scores), key=lambda x: x[1], reverse=True)[:5]
```

**效果链**：纯向量 75% → +BM25 85% → +Reranker 92%

---

## 四、RAG 评估：别凭感觉判断

### 4.1 Hit Rate（命中率）

```python
def hit_rate(test_cases, k=10):
    """Top-K 中包含正确答案的比例"""
    hits = 0
    for test in test_cases:
        results = retrieval.search(test["query"], top_k=k)
        if test["expected_doc_id"] in results:
            hits += 1
    return hits / len(test_cases)
# 合格: > 85%
# 优秀: > 92%
```

### 4.2 MRR（Mean Reciprocal Rank）

```python
def mrr(test_cases, k=10):
    reciprocal_ranks = []
    for test in test_cases:
        results = retrieval.search(test["query"], top_k=k)
        if test["expected_doc_id"] in results:
            rank = results.index(test["expected_doc_id"]) + 1
            reciprocal_ranks.append(1 / rank)
        else:
            reciprocal_ranks.append(0)
    return sum(reciprocal_ranks) / len(reciprocal_ranks)
# MRR = 1.0 → 每次正确答案都在第一位
# MRR = 0.5 → 平均排在第二位
```

### 4.3 NDCG（Normalized Discounted Cumulative Gain）

考虑排序质量：排第一比排第十更有价值。DCG 对靠后的结果打折（除以 log₂(rank+1)），NDCG 是归一化后的版本。

---

## 五、RAG 选型决策

```
你的场景？
│
├─ 文档 < 1 万篇，原型验证
│   └─ Chroma + BGE-Large-ZH（pip install 开箱即用）
│
├─ 文档 1-100 万篇，生产环境
│   └─ Milvus (HNSW) + BM25 + Cross-Encoder Reranker
│
├─ 文档 > 1 亿篇
│   └─ Milvus (DiskANN) + 分布式部署
│
└─ 需要多模态（文+图）
    └─ CLIP Embedding + Milvus 混合检索
```

---

## 六、总结

| 层级 | 关键技术 | 影响 |
|------|------|------|
| Embedding | BGE-Large-ZH (1024维) | 语义空间的构建质量 |
| 索引 | HNSW (<100万) / DiskANN (>1亿) | 检索速度的瓶颈 |
| 混合检索 | 向量 + BM25 + RRF | 精度 +5-10% |
| 重排序 | Cross-Encoder Reranker | 精度 +5-7% |
| 评估 | Hit Rate / MRR / NDCG | 不要凭感觉判断 |

> RAG 不是「装个 Chroma 就好了」，而是一套从 Embedding 到索引到检索到评估的完整工程体系。纯向量检索的 75% 准确率远不够 Agent 用。BM25 + Reranker 是标配。

---

> 🔖 下一篇：**《LLM 推理机制：从 Token 生成到推理优化》**

*标签：#RAG #Embedding #向量检索 #HNSW #混合检索 #程序员必读*