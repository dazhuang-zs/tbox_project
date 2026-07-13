# 【AI Agent 系统教学 20】Graph RAG：知识图谱增强

> 向量检索知道"相似"，但不知道"关系"。
> Graph RAG 补上了这块——谁和谁相关、怎么相关、为什么相关。

---

## 前言：向量检索的盲区

向量检索擅长找"相似"的内容。但很多问题需要的是"关系"：

- "张三和李四是什么关系？"（实体关系）
- "A 产品影响了哪些模块？"（因果链）
- "从巴黎到柏林经过哪些城市？"（路径）
- "这个团队有多少人？"（聚合）

这些问题，向量检索束手无策。因为向量检索只关心"语义相似度"，不关心"实体之间的关系"。

**Graph RAG 就是来解决这个问题的。**

---

## 一、知识图谱基础

### 1.1 什么是知识图谱

知识图谱用**三元组**表示知识：

```
(实体, 关系, 实体)
(北京, 是, 首都)
(北京, 位于, 中国)
(张三, 任职于, 某公司)
(某公司, 生产, 产品A)
```

### 1.2 从文档到知识图谱

```python
class KnowledgeGraphBuilder:
    def __init__(self, llm):
        self.llm = llm
        self.graph = {
            "entities": {},
            "relations": [],
        }
    
    def extract_triples(self, text):
        """从文本中提取三元组"""
        prompt = f"""
        从以下文本中提取所有(实体, 关系, 实体)三元组：
        
        {text}
        
        输出格式（每行一个三元组，用|分隔）：
        实体1|关系|实体2
        """
        response = self.llm.generate(prompt)
        triples = []
        for line in response.strip().split("\n"):
            parts = line.split("|")
            if len(parts) == 3:
                triples.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
        return triples
    
    def add_triples(self, triples):
        """添加三元组到图谱"""
        for subj, rel, obj in triples:
            # 添加实体
            if subj not in self.graph["entities"]:
                self.graph["entities"][subj] = {"id": subj, "type": "unknown"}
            if obj not in self.graph["entities"]:
                self.graph["entities"][obj] = {"id": obj, "type": "unknown"}
            
            # 添加关系
            self.graph["relations"].append({
                "subject": subj,
                "relation": rel,
                "object": obj,
            })
```

---

## 二、微软 GraphRAG 方案

### 2.1 GraphRAG 的核心思想

微软在 2024 年发布的 GraphRAG，核心创新：

1. **自动构建知识图谱**：从文档中提取实体和关系
2. **社区检测**：找出紧密相关的实体群
3. **分层摘要**：对每个社区生成摘要
4. **图谱检索**：基于图谱进行检索

### 2.2 构建流程

```python
class MicrosoftGraphRAG:
    def __init__(self, llm, embedder):
        self.llm = llm
        self.embedder = embedder
        self.graph = {}
        self.communities = []
        self.summaries = {}
    
    def build(self, documents):
        """构建完整的 GraphRAG 索引"""
        # 1. 提取实体和关系
        for doc in documents:
            triples = self.extract_triples(doc)
            self.add_to_graph(triples)
        
        # 2. 社区检测
        self.communities = self.detect_communities()
        
        # 3. 生成社区摘要
        for community in self.communities:
            self.summaries[community.id] = self.summarize_community(community)
        
        # 4. 生成社区摘要的嵌入
        self.community_embeddings = {
            cid: self.embedder.embed(summary)
            for cid, summary in self.summaries.items()
        }
    
    def detect_communities(self):
        """
        社区检测：使用 Leiden 算法
        找出紧密连接的实体群
        """
        # 构建图
        G = nx.Graph()
        for rel in self.graph["relations"]:
            G.add_edge(rel["subject"], rel["object"])
        
        # Leiden 社区检测
        communities = nx.community.leiden_communities(G)
        return [Community(id=i, members=list(c)) for i, c in enumerate(communities)]
    
    def summarize_community(self, community):
        """生成社区摘要"""
        members = community.members
        relations = [
            r for r in self.graph["relations"]
            if r["subject"] in members or r["object"] in members
        ]
        
        prompt = f"""
        以下是一个实体群，请总结它们之间的关系：
        
        实体：{members}
        关系：{relations}
        
        总结这个群的核心主题（100字以内）：
        """
        return self.llm.generate(prompt)
```

### 2.3 GraphRAG 的检索

```python
class GraphRAGRetriever:
    def __init__(self, graph_rag, embedder):
        self.graph_rag = graph_rag
        self.embedder = embedder
    
    def retrieve(self, query, k=5):
        # 1. 在社区摘要中检索（快速定位相关社区）
        query_embedding = self.embedder.embed(query)
        community_scores = {
            cid: cosine_similarity(query_embedding, emb)
            for cid, emb in self.graph_rag.community_embeddings.items()
        }
        top_communities = sorted(
            community_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:k]
        
        # 2. 在相关社区中检索具体实体
        results = []
        for cid, score in top_communities:
            community = self.graph_rag.communities[cid]
            entities = community.members
            
            # 从实体中检索相关内容
            for entity in entities:
                entity_info = self.graph_rag.graph["entities"].get(entity, {})
                results.append({
                    "entity": entity,
                    "community_summary": self.graph_rag.summaries[cid],
                    "entity_info": entity_info,
                })
        
        return results
```

---

## 三、Graph RAG vs 向量 RAG

### 3.1 对比

| 维度 | 向量 RAG | Graph RAG |
|------|---------|-----------|
| 检索方式 | 语义相似度 | 关系 + 语义 |
| 理解关系 | 不能 | 能 |
| 聚合查询 | 不能 | 能 |
| 路径查询 | 不能 | 能 |
| 多跳推理 | 弱 | 强 |
| 构建成本 | 低 | 高 |
| 更新成本 | 低 | 高 |
| 存储空间 | 小 | 大 |

### 3.2 互补

**向量 RAG 和 Graph RAG 不是二选一，而是互补的：**

```
向量 RAG 擅长：语义匹配、相似文档
Graph RAG 擅长：关系推理、多跳查询

最佳实践：同时使用两者
```

### 3.3 混合方案

```python
class HybridGraphVectorRAG:
    def __init__(self, vector_rag, graph_rag):
        self.vector = vector_rag
        self.graph = graph_rag
    
    def retrieve(self, query, k=5):
        # 1. 判断查询类型
        query_type = self.classify_query(query)
        
        if query_type == "semantic":
            # 语义查询 → 向量 RAG
            return self.vector.retrieve(query, k)
        
        elif query_type == "relational":
            # 关系查询 → Graph RAG
            return self.graph.retrieve(query, k)
        
        else:
            # 混合查询 → 两者结合
            vector_results = self.vector.retrieve(query, k//2)
            graph_results = self.graph.retrieve(query, k//2)
            return self.merge(vector_results, graph_results)
    
    def classify_query(self, query):
        """判断查询类型"""
        # 包含关系词 → 关系查询
        relation_keywords = ["关系", "影响", "关联", "联系", "依赖"]
        if any(kw in query for kw in relation_keywords):
            return "relational"
        
        # 包含聚合词 → 关系查询
        aggregation_keywords = ["多少", "统计", "数量", "列表"]
        if any(kw in query for kw in aggregation_keywords):
            return "relational"
        
        return "hybrid"
```

---

## 四、Graph RAG 在 Agent 中的实践

### 4.1 作为 Agent 的知识图谱工具

```python
@tool("query_knowledge_graph")
def query_knowledge_graph(query: str):
    """
    查询知识图谱
    适合：实体关系查询、多跳推理、聚合统计
    """
    results = graph_rag.retrieve(query)
    return format_graph_results(results)


@tool("search_vector_knowledge")
def search_vector_knowledge(query: str):
    """
    语义搜索知识库
    适合：文档相似度搜索、语义匹配
    """
    results = vector_rag.retrieve(query)
    return format_vector_results(results)
```

### 4.2 多跳推理

Graph RAG 特别适合多跳推理任务：

```
用户问题："张三的团队开发了哪些产品？"

图查询路径：
张三 → 管理 → 团队A
团队A → 开发 → 产品X
团队A → 开发 → 产品Y
产品X → 属于 → 产品线1

答案：张三的团队（团队A）开发了产品X和产品Y。
```

```python
def multi_hop_query(start_entity, graph, max_hops=3):
    """多跳查询"""
    visited = set()
    results = []
    
    def dfs(entity, depth):
        if depth > max_hops or entity in visited:
            return
        visited.add(entity)
        
        # 查找以该实体为起点的关系
        for rel in graph["relations"]:
            if rel["subject"] == entity:
                results.append((entity, rel["relation"], rel["object"]))
                dfs(rel["object"], depth + 1)
    
    dfs(start_entity, 0)
    return results
```

---

## 五、构建 Graph RAG 的注意事项

### 5.1 实体抽取质量

```
实体抽取是 Graph RAG 的瓶颈。
抽取质量差 → 图谱质量差 → 检索质量差

优化方法：
1. 使用更大的模型抽取实体
2. 人工校验核心实体
3. 实体消歧（区分"苹果公司"和"苹果水果"）
4. 实体链接（关联到标准知识库）
```

### 5.2 图谱规模控制

```
一个中型知识库（1000 篇文档）可能产生：
- 10,000+ 实体
- 50,000+ 关系
- 100+ 社区

规模控制：
1. 只保留重要实体（频率阈值）
2. 合并相似实体
3. 定期清理过期实体
```

### 5.3 更新策略

```
知识图谱的更新比向量索引更复杂：
- 新增实体：需要检测社区变化
- 删除实体：需要清理相关关系
- 修改关系：需要重新计算社区

推荐策略：全量重建（每周/每月）
```

---

## 六、2026 年 Graph RAG 趋势

### 6.1 动态知识图谱

知识图谱不再是静态的，而是**随对话动态更新**：

```
用户："张三离职了"
Agent 操作：
1. 从图谱中删除张三的"任职于"关系
2. 标记张三状态为"已离职"
3. 更新受影响的关系
```

### 6.2 个人知识图谱

从"公司知识图谱"到"个人知识图谱"：

- 用户的关注领域
- 用户的专业背景
- 用户的历史交互
- 用户的知识偏好

### 6.3 多模态知识图谱

从纯文本扩展到多模态：
- 图像中的实体关系
- 视频中的事件图谱
- 代码中的依赖关系

---

## 总结

| 概念 | 向量 RAG | Graph RAG |
|------|---------|-----------|
| 核心 | 语义相似度 | 实体关系 |
| 适合 | "找相似" | "找关系" |
| 查询 | "类似的文档" | "相关的实体" |
| 推理 | 单步 | 多跳 |
| 构建 | 简单 | 复杂 |
| 互补 | 语义理解 | 关系推理 |

**Graph RAG 不是替代向量 RAG，而是补上向量 RAG 缺少的"关系理解"能力。**

下一篇文章，我们将进入**RAG 评估与优化**——如何衡量 RAG 系统的质量，以及如何系统性地优化。

---

**思考题**：
1. 你的场景中，有哪些查询是向量 RAG 搞不定的，需要 Graph RAG？
2. 构建知识图谱的成本很高，10 个问题的场景值得做 Graph RAG 吗？
3. 如果同时使用向量 RAG 和 Graph RAG，怎么融合两者的结果？

---

> 上一篇：[19] 高级 RAG：RAPTOR、CRAG、Self-RAG
> 下一篇：[21] RAG 评估与优化
> 系列目录：[README.md](./README.md)