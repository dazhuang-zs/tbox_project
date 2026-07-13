# 【AI Agent 系统教学 17】密集检索 vs 稀疏检索

> 向量检索懂"语义"但不懂"精确匹配"，关键词检索懂"精确匹配"但不懂"语义"。
> 所以，把它们结合起来。

---

## 前言：检索的两种哲学

在 RAG 中，检索有两种完全不同的实现方式：

**密集检索（Dense Retrieval）**：用嵌入模型把文本转成向量，通过语义相似度搜索。懂"意思"，但可能忽略精确匹配。

**稀疏检索（Sparse Retrieval）**：用词频统计（如 BM25）匹配关键词。懂"词"，但不懂"意思"。

这两种方法各有优劣，对应不同的检索场景。

---

## 一、BM25：经典的稀疏检索

### 1.1 什么是 BM25

BM25 是 2026 年仍在广泛使用的关键词检索算法。它是 TF-IDF 的改进版。

**核心思想**：一个词在文档中出现得越多，这个词越重要；但一个词出现得太频繁，它的重要性会递减。

```
BM25 分数 = 词频影响 × 逆文档频率 × 文档长度归一化

词频影响：出现次数越多分数越高，但不会线性增长
逆文档频率：在越少文档中出现的词，越重要
文档长度归一化：长文档的分数会被"惩罚"
```

### 1.2 BM25 在 Python 中的实现

```python
from rank_bm25 import BM25Okapi

# 构建索引
corpus = [
    "苹果是一种水果",
    "苹果公司发布了新手机",
    "香蕉是热带水果",
    "华为发布了新手机",
]
tokenized_corpus = [doc.split(" ") for doc in corpus]
bm25 = BM25Okapi(tokenized_corpus)

# 检索
query = "水果"
tokenized_query = query.split(" ")
scores = bm25.get_scores(tokenized_query)

# 结果
results = sorted(zip(corpus, scores), key=lambda x: x[1], reverse=True)
print(results)
# [('苹果是一种水果', 0.85), ('香蕉是热带水果', 0.72), ('苹果公司发布了新手机', 0.0), ('华为发布了新手机', 0.0)]
```

### 1.3 BM25 的优缺点

| 优点 | 缺点 |
|------|------|
| 不需要训练，开箱即用 | 无法理解语义（"苹果"和"水果"的语义关系不识别） |
| 速度快，延迟低 | 对同义词不敏感（"苹果"和"iPhone"没关联） |
| 精确匹配，召回率稳定 | 对查询词变化敏感（"水果"搜不到"苹果"） |
| 可解释性强 | 需要精确分词 |

---

## 二、密集检索：基于语义的搜索

### 2.1 密集检索的工作原理

```
1. 用嵌入模型把所有文档转成向量
2. 用相同的嵌入模型把查询转成向量
3. 计算查询向量与所有文档向量的相似度
4. 返回相似度最高的 K 个文档
```

### 2.2 密集检索的优缺点

| 优点 | 缺点 |
|------|------|
| 理解语义（"水果" → "苹果"、"香蕉"） | 需要训练嵌入模型 |
| 对同义词有效 | 对精确匹配不敏感（搜"iPhone 15"可能返回"手机"） |
| 多语言统一 | 计算量大 |
| 可以处理模糊查询 | 可解释性差 |

### 2.3 密集检索的典型问题

```
查询："iPhone 15 的价格"
密集检索返回："手机价格汇总"（语义相似，但不是精确结果）
BM25 返回："iPhone 15 价格正式公布"（精确匹配，正是用户想要的）
```

---

## 三、混合检索：两全其美

### 3.1 混合检索的原理

混合检索的核心思想：**同时使用密集检索和稀疏检索，融合两者的结果。**

```python
def hybrid_search(query, dense_retriever, sparse_retriever, k=5, alpha=0.5):
    """
    混合检索
    alpha: 密集检索的权重（0-1）
    alpha=1: 纯密集检索
    alpha=0: 纯稀疏检索
    """
    # 密集检索
    dense_results = dense_retriever.retrieve(query, k*2)
    dense_scores = {doc_id: score for doc_id, score in dense_results}
    
    # 稀疏检索
    sparse_results = sparse_retriever.retrieve(query, k*2)
    sparse_scores = {doc_id: score for doc_id, score in sparse_results}
    
    # 分数归一化
    dense_scores = normalize(dense_scores)
    sparse_scores = normalize(sparse_scores)
    
    # 融合
    all_doc_ids = set(dense_scores.keys()) | set(sparse_scores.keys())
    combined = {}
    for doc_id in all_doc_ids:
        combined[doc_id] = (
            alpha * dense_scores.get(doc_id, 0) +
            (1-alpha) * sparse_scores.get(doc_id, 0)
        )
    
    # 排序
    ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)
    return ranked[:k]
```

### 3.2 混合检索的效果

```
查询："iPhone 15 价格"

密集检索（alpha=1.0）：
  "手机价格汇总"  (score: 0.92)  ← 语义相关，但不是精确答案
  "苹果手机报价"  (score: 0.88)
  "2026年手机推荐" (score: 0.85)

稀疏检索（alpha=0.0）：
  "iPhone 15 价格正式公布" (score: 0.95)  ← 精确匹配
  "iPhone 15 评测"         (score: 0.72)
  "iPhone 14 价格调整"     (score: 0.68)

混合检索（alpha=0.5）：
  "iPhone 15 价格正式公布" (score: 0.92)  ← 最佳结果
  "手机价格汇总"           (score: 0.72)
  "苹果手机报价"           (score: 0.65)
```

### 3.3 alpha 值的调优

```python
def tune_alpha(query_type):
    """根据查询类型调整混合权重"""
    if query_type == "exact_match":
        # 精确匹配（如产品名、型号）
        return 0.3  # 稀疏检索权重更高
    elif query_type == "semantic_search":
        # 语义搜索（如概念理解）
        return 0.7  # 密集检索权重更高
    elif query_type == "general":
        # 通用查询
        return 0.5
    else:
        return 0.5
```

---

## 四、检索方法选型指南

### 4.1 决策树

```
你的数据是什么类型？
├─ 精确匹配为主（产品名、代码、ID）
│   ├─ 数据量小 → BM25 就够了
│   └─ 数据量大 → 混合检索（BM25 为主）
│
├─ 语义理解为主（概念、描述、自然语言）
│   ├─ 数据量小 → 密集检索
│   └─ 数据量大 → 混合检索（密集为主）
│
└─ 混合类型
    └─ 混合检索（默认 alpha=0.5）
```

### 4.2 场景对比

| 场景 | 推荐方法 | 原因 |
|------|---------|------|
| 产品搜索（精确匹配） | BM25 为主 | 用户搜"iPhone 15"，要的是精确匹配 |
| 知识库问答（语义理解） | 密集检索为主 | 用户问"怎么退款"，要理解意图 |
| 代码搜索 | BM25 + 密集检索混合 | 变量名精确匹配 + 功能语义理解 |
| 多语言搜索 | 密集检索 | 统一嵌入空间，跨语言检索 |
| 法律文档 | BM25 为主 | 精确引用法律条文 |

### 4.3 2018-2026 检索技术演进

```
2018: TF-IDF → 简单词频统计
2020: BM25 → 改进的关键词检索
2021: Dense Retrieval → 基于嵌入的语义检索
2022: ColBERT → 细粒度相似度计算
2023: Hybrid Search → 密集+稀疏融合
2024: Learned Sparse → 可学习的稀疏检索
2025: Multi-vector Retrieval → 多向量检索
2026: Unified Retrieval → 统一检索框架
```

---

## 五、高级检索技术

### 5.1 ColBERT：细粒度相似度

ColBERT 不是用整个文档的向量与查询比较，而是**计算每个 token 的相似度**：

```
查询："iPhone 价格"
         ↓
"iPhone" → 与文档中每个 token 比较
"价格"   → 与文档中每个 token 比较
         ↓
取最大相似度，然后求和 → 最终分数
```

**效果**：比传统密集检索更精确，但计算量更大。

### 5.2 Learned Sparse：可学习的稀疏检索

传统 BM25 的词权重是手工设计的（IDF 公式），而 Learned Sparse 用模型**学习词的重要性**：

```
训练一个模型，输入一个词，输出这个词的"重要性权重"
这个权重替代 BM25 的 IDF
权重是学习出来的，不是公式算出来的
```

**效果**：结合了稀疏检索的精确性和密集检索的学习能力。

### 5.3 SPLADE：一个具体实现

SPLADE 是 Learned Sparse 的代表方法：

```python
# SPLADE 的伪代码
def splade_encode(text):
    # 1. 用 BERT 编码文本
    outputs = bert(text)
    
    # 2. 通过 MLP 预测每个词的权重
    logits = mlp(outputs.last_hidden_state)
    
    # 3. 用 ReLU 过滤掉负权重
    weights = relu(logits)
    
    # 4. 得到一个稀疏向量（大部分维度是 0）
    return weights
```

---

## 六、在 Agent 中集成检索

### 6.1 Agent 的检索工具设计

```python
class AgentRetriever:
    def __init__(self):
        self.dense_retriever = DenseRetriever()
        self.sparse_retriever = BM25Retriever()
    
    @tool("search_knowledge")
    def search(self, query: str, search_type: str = "auto"):
        """
        搜索知识库
        query: 搜索关键词
        search_type: "exact"(精确), "semantic"(语义), "hybrid"(混合), "auto"(自动)
        """
        if search_type == "auto":
            search_type = self.detect_search_type(query)
        
        if search_type == "exact":
            return self.sparse_retriever.search(query)
        elif search_type == "semantic":
            return self.dense_retriever.search(query)
        else:
            return self.hybrid_search(query)
    
    def detect_search_type(self, query):
        """自动检测搜索类型"""
        # 如果查询包含特殊字符、数字、产品名，可能是精确搜索
        if re.search(r'[A-Z0-9\-]', query):
            return "exact"
        # 如果查询较长，可能包含语义信息
        if len(query) > 20:
            return "semantic"
        # 默认混合
        return "hybrid"
```

### 6.2 检索结果的后处理

```python
def post_process_retrieval(results, query, max_tokens=2000):
    """检索结果后处理"""
    # 1. 去重
    results = deduplicate(results)
    
    # 2. 按相关性截断
    results = results[:max_results]
    
    # 3. 按 token 限制截断
    total_tokens = 0
    truncated = []
    for doc in results:
        doc_tokens = count_tokens(doc)
        if total_tokens + doc_tokens > max_tokens:
            break
        truncated.append(doc)
        total_tokens += doc_tokens
    
    return truncated
```

---

## 总结

| 方法 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| BM25（稀疏检索） | 词频统计 | 精确匹配、可解释、快 | 不理解语义 |
| 密集检索 | 向量相似度 | 理解语义、跨语言 | 不精确、可解释差 |
| 混合检索 | 两者融合 | 两全其美 | 复杂度高 |
| Learned Sparse | 学习词权重 | 结合两者优点 | 需要训练数据 |

**没有绝对最好的检索方法，只有最适合你场景的方法。**

下一篇文章，我们将深入**检索增强策略**——查询改写、HyDE、RAG Fusion，以及如何让检索结果更精准。

---

**思考题**：
1. 你的场景中，精确匹配和语义理解哪个更重要？为什么？
2. 混合检索的 alpha 值怎么调？你会在什么场景下调高或调低？
3. Learned Sparse 和传统 BM25 最大的区别是什么？什么时候用 Learned Sparse 值得？

---

> 上一篇：[16] 嵌入模型与向量数据库
> 下一篇：[18] 检索增强策略：查询改写与 HyDE
> 系列目录：[README.md](./README.md)