# 【AI Agent 系统教学 19】高级 RAG：RAPTOR、CRAG、Self-RAG

> 当简单 RAG 不够用时，需要更聪明的策略。
> 这些高级方案，让 RAG 从"检索-拼接"进化到"理解-推理-优化"。

---

## 前言：Naive RAG 的瓶颈

Naive RAG 的工作方式：**一次检索，一次生成**。

对于大多数简单问题，这已经够了。但遇到以下情况就不行了：

- 问题需要**多篇文档**的信息综合
- 检索到的信息**不相关或矛盾**
- 需要**多层次**的信息（从摘要到细节）
- 问题本身的**表述不清晰**

高级 RAG 方案就是为了解决这些问题。

---

## 一、RAPTOR：分层检索

### 1.1 核心思想

RAPTOR（Recursive Abstractive Processing for Tree-Organized Retrieval）的核心洞察：

> **文档天然有层次结构——段落、章节、整篇文档。RAPTOR 显式构建这个层次，然后从顶层（摘要）到底层（细节）逐层检索。**

### 1.2 构建层次索引

```python
class RAPTORIndex:
    def __init__(self, llm, embedder):
        self.llm = llm
        self.embedder = embedder
        self.tree = {}  # 层次结构
    
    def build_tree(self, chunks, max_leaf_size=10):
        """
        构建层次树
        叶子节点：原始文本块
        中间节点：子节点的摘要
        根节点：顶层摘要
        """
        # 1. 叶子层：原始块
        level = 0
        self.tree[level] = chunks
        
        # 2. 逐层向上构建
        while len(self.tree[level]) > 1:
            level += 1
            summaries = []
            
            # 每 max_leaf_size 个块聚合成一个摘要
            for i in range(0, len(self.tree[level-1]), max_leaf_size):
                group = self.tree[level-1][i:i+max_leaf_size]
                summary = self.summarize(group)
                summaries.append(summary)
            
            self.tree[level] = summaries
    
    def summarize(self, chunks):
        """生成一组块的摘要"""
        texts = "\n\n".join([c.text for c in chunks])
        prompt = f"请总结以下内容：\n{texts}\n\n总结（100字以内）："
        return self.llm.generate(prompt)
```

### 1.3 分层检索

```python
class RAPTORRetriever:
    def __init__(self, index, embedder):
        self.index = index
        self.embedder = embedder
    
    def retrieve(self, query, k=5):
        """
        从顶层开始检索，逐层深入
        """
        results = []
        query_embedding = self.embedder.embed(query)
        
        # 从顶层开始
        for level in sorted(self.index.tree.keys(), reverse=True):
            nodes = self.index.tree[level]
            
            # 计算与查询的相似度
            scores = []
            for node in nodes:
                node_embedding = self.embedder.embed(node.text)
                score = cosine_similarity(query_embedding, node_embedding)
                scores.append((node, score, level))
            
            # 取 top-k
            scores.sort(key=lambda x: x[1], reverse=True)
            top_nodes = scores[:k]
            
            # 如果到达叶子层，直接返回
            if level == 0:
                results.extend([n for n, _, _ in top_nodes])
            else:
                # 中间层：展开选中的节点，继续向下检索
                for node, _, _ in top_nodes:
                    expanded = self.expand_node(node, level)
                    results.extend(expanded)
        
        return results[:k]
    
    def expand_node(self, node, level):
        """展开中间节点，返回其子节点"""
        if level - 1 not in self.index.tree:
            return [node]
        
        children = self.index.tree[level - 1]
        # 找到属于这个节点的子节点
        return [c for c in children if c.parent_id == node.id]
```

### 1.4 RAPTOR 的效果

```
查询："Transformer 的注意力机制是什么？"

Naive RAG（直接检索块）：
  "Transformer 架构中，Attention 的计算公式为..."
  （只找到局部信息，缺少上下文）

RAPTOR（分层检索）：
  顶层摘要："Transformer 是一种基于注意力机制的序列处理架构..."
  中层："Transformer 包含编码器-解码器结构..."
  底层："Self-Attention 的计算公式为...，其中 Q、K、V 分别代表..."
  （从整体到局部，信息完整）
```

---

## 二、CRAG：纠正性 RAG

### 2.1 核心思想

CRAG（Corrective RAG）的核心洞察：

> **检索到的文档不总是有用的。CRAG 在生成前评估检索结果的质量，决定如何使用——增强、修正还是搜索。**

### 2.2 实现

```python
class CRAGPipeline:
    def __init__(self, retriever, llm, evaluator):
        self.retriever = retriever
        self.llm = llm
        self.evaluator = evaluator  # 评估检索质量的模型
    
    def answer(self, query):
        # 1. 检索
        docs = self.retriever.retrieve(query, k=5)
        
        # 2. 评估检索质量
        quality = self.evaluate_retrieval(query, docs)
        
        # 3. 根据质量决定策略
        if quality == "good":
            # 直接增强生成
            return self.augment_and_generate(query, docs)
        
        elif quality == "partial":
            # 部分相关：修正 + 检索更多
            relevant = self.filter_relevant(docs)
            missing = self.identify_missing(query, relevant)
            more_docs = self.retriever.retrieve(missing, k=3)
            return self.augment_and_generate(query, relevant + more_docs)
        
        elif quality == "bad":
            # 全不相关：重新搜索
            new_query = self.rewrite_query(query)
            new_docs = self.retriever.retrieve(new_query, k=5)
            return self.augment_and_generate(query, new_docs)
    
    def evaluate_retrieval(self, query, docs):
        """评估检索结果的质量"""
        prompt = f"""
        查询：{query}
        检索到的文档：{docs}
        
        评估检索质量：
        1. "good"：文档与查询高度相关，可以直接使用
        2. "partial"：部分文档相关，部分不相关
        3. "bad"：文档与查询不相关
        """
        return self.evaluator.evaluate(prompt)
```

### 2.3 CRAG 的决策逻辑

```
         ┌─ 质量好 → 直接增强生成
         │
检索结果 ── 部分好 → 过滤相关 + 补充检索
         │
         └─ 质量差 → 查询改写 + 重新检索
```

---

## 三、Self-RAG：自反思 RAG

### 3.1 核心思想

Self-RAG 让模型自己决定：

1. **是否需要检索**——有些问题不需要检索（如"你好"）
2. **检索到什么**——检索到的文档是否相关
3. **是否使用检索结果**——检索结果是否可靠
4. **是否生成引用**——是否需要在回答中引用来源

### 3.2 实现

```python
class SelfRAGPipeline:
    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever
    
    def answer(self, query):
        # 1. 决定是否需要检索
        need_retrieval = self.need_retrieval(query)
        
        if not need_retrieval:
            # 不需要检索，直接用模型回答
            return self.llm.generate(query)
        
        # 2. 检索
        docs = self.retriever.retrieve(query, k=5)
        
        # 3. 评估每个文档的相关性
        relevant_docs = []
        for doc in docs:
            if self.is_relevant(query, doc):
                relevant_docs.append(doc)
        
        # 4. 如果所有文档都不相关，告诉用户
        if not relevant_docs:
            return "我没有找到相关信息。"
        
        # 5. 基于相关文档生成回答
        response = self.generate_with_docs(query, relevant_docs)
        
        # 6. 自评估：是否需要重新检索
        if self.needs_refinement(query, response):
            refined_query = self.refine_query(query, response)
            return self.answer(refined_query)
        
        return response
    
    def need_retrieval(self, query):
        """判断是否需要检索"""
        prompt = f"""
        查询：{query}
        
        这个查询是否需要检索外部知识？
        1. 需要：查询涉及具体事实、最新信息、专业知识
        2. 不需要：查询是常识、问候、观点
        """
        return self.llm.generate(prompt) == "需要"
    
    def is_relevant(self, query, doc):
        """判断文档是否与查询相关"""
        prompt = f"""
        查询：{query}
        文档：{doc.text}
        
        这个文档是否与查询相关？回答"是"或"否"。
        """
        return self.llm.generate(prompt) == "是"
    
    def needs_refinement(self, query, response):
        """判断是否需要优化"""
        prompt = f"""
        查询：{query}
        回答：{response}
        
        这个回答是否令人满意？回答"是"或"否"。
        """
        return self.llm.generate(prompt) == "否"
```

---

## 四、高级 RAG 方案对比

| 方案 | 核心能力 | 解决的问题 | 成本 | 复杂度 |
|------|---------|-----------|------|-------|
| Naive RAG | 一次检索+生成 | 基础问答 | 低 | 低 |
| RAPTOR | 分层检索 | 需要多层次信息 | 中 | 高 |
| CRAG | 纠正检索错误 | 检索质量不稳定 | 中 | 中 |
| Self-RAG | 自决定+自评估 | 灵活控制检索时机 | 高 | 高 |
| RAG Fusion | 多路融合 | 单一检索不可靠 | 中 | 中 |

### 选型建议

```
你的场景：
├─ 简单的问答 → Naive RAG (够用了)
├─ 需要多篇文档综合 → RAPTOR
├─ 检索质量不稳定 → CRAG
├─ 需要灵活控制检索 → Self-RAG
└─ 需要高可靠性 → RAG Fusion + CRAG 组合
```

---

## 五、Agent 中的高级 RAG 实践

### 5.1 自适应 RAG

让 Agent 根据场景自动选择 RAG 策略：

```python
class AdaptiveRAGAgent:
    def __init__(self):
        self.strategies = {
            "simple": NaiveRAG(),
            "hierarchical": RAPTOR(),
            "corrective": CRAG(),
            "self_reflective": SelfRAG(),
        }
    
    def answer(self, query):
        # 1. 分析查询复杂度
        complexity = self.analyze_complexity(query)
        
        # 2. 选择策略
        if complexity == "simple":
            strategy = "simple"
        elif complexity == "medium":
            strategy = "corrective"
        elif complexity == "complex":
            strategy = "hierarchical"
        else:
            strategy = "self_reflective"
        
        # 3. 执行
        return self.strategies[strategy].answer(query)
    
    def analyze_complexity(self, query):
        """分析查询复杂度"""
        prompt = f"""
        查询：{query}
        
        分析复杂度：
        - "simple"：单一步骤，单一信息源
        - "medium"：需要多步推理或比较
        - "complex"：需要多篇文档综合
        """
        return self.llm.generate(prompt)
```

### 5.2 高级 RAG 的 token 成本

| 策略 | 平均每次查询的额外 token 消耗 | 比 Naive RAG 增加 |
|------|----------------------------|------------------|
| Naive RAG | 基线 | - |
| RAPTOR | +500-2000 | 1.5-2x |
| CRAG | +300-1000 | 1.2-1.5x |
| Self-RAG | +500-2000 | 1.5-2x |
| RAG Fusion | +200-500 | 1.1-1.3x |

---

## 六、2026 年 RAG 新趋势

### 6.1 Agentic RAG

RAG 不再是"检索-生成"的流水线，而是由 Agent 自主决定的：

```
Agent 决定：
1. 需要检索吗？
2. 检索什么？
3. 从哪里检索？
4. 检索到的信息怎么用？
5. 需要再检索吗？
```

### 6.2 多模态 RAG

从纯文本检索扩展到多模态：

- 图像检索 + 文本生成
- 表格检索 + 数据分析
- 代码检索 + 代码生成

### 6.3 实时 RAG

知识库实时更新，检索结果包含最新信息：

- 增量索引更新
- 实时数据源接入
- 过期数据自动淘汰

---

## 总结

| 方案 | 一句话 | 核心洞见 |
|------|--------|---------|
| RAPTOR | 分层次检索 | 文档有层次结构，检索也该有 |
| CRAG | 纠正检索错误 | 不是所有检索结果都可靠 |
| Self-RAG | 自决定检索时机 | 模型自己知道什么时候需要检索 |
| Agentic RAG | Agent 自主管理 RAG | 让 Agent 决定怎么检索、怎么用 |

**RAG 的进化方向：从"检索工具"到"检索智能体"。**

下一篇文章，我们将进入**Graph RAG**——微软的 GraphRAG，以及如何用知识图谱增强 RAG。

---

**思考题**：
1. 你的场景中，检索质量最差的情况是什么？CRAG 能解决吗？
2. RAPTOR 的分层索引在什么场景下特别有用？什么场景下反而增加复杂度？
3. Self-RAG 的"自评估"环节会不会引入新的错误？怎么处理？

---

> 上一篇：[18] 检索增强策略：查询改写与 HyDE
> 下一篇：[20] Graph RAG：知识图谱增强
> 系列目录：[README.md](./README.md)