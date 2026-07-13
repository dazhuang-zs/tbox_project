# 【AI Agent 系统教学 21】RAG 评估与优化

> 不做评估的 RAG 系统，就是在黑暗中奔跑。
> 你不知道它什么时候好、什么时候差、什么时候该优化。

---

## 前言：RAG 的"好"是什么？

在 Agent 中，RAG 做得好不好，直接决定了 Agent 的回答质量。

但"RAG 做得好"不是一句简单的"检索结果相关"就能概括的。它需要从多个维度来衡量：

- **检索到了吗？**（召回率）
- **检索到的相关吗？**（精确率）
- **模型用了吗？**（利用度）
- **回答对了吗？**（准确率）
- **用户满意吗？**（体验）

---

## 一、RAG 评估的三层体系

### 1.1 评估金字塔

```
           ┌──────────┐
           │ 端到端质量 │  ← 用户最关心的
           │ (准确率)   │
          ┌┴──────────┴┐
          │  生成质量   │  ← 模型 + RAG 的综合
          │ (忠实度)    │
         ┌┴───────────┴┐
         │  检索质量    │  ← RAG 的核心
         │ (召回+精确)  │
         └─────────────┘
```

### 1.2 检索质量评估

| 指标 | 含义 | 计算方法 |
|------|------|---------|
| 召回率 | 正确结果中有多少被检索到 | 检索到的正确结果 / 所有正确结果 |
| 精确率 | 检索到的结果中有多少正确 | 检索到的正确结果 / 所有检索到的结果 |
| MRR | 第一个正确结果的排名 | 1 / 第一个正确结果的排名 |
| NDCG | 排序质量 | 考虑排名位置的加权精度 |
| Hit Rate | 是否有正确结果在 top-k 中 | 1 如果有，0 如果没有 |

```python
def evaluate_retrieval(retriever, test_queries, k_values=[1, 3, 5, 10]):
    """评估检索质量"""
    results = {k: {"hit_rate": 0, "precision": 0, "recall": 0} for k in k_values}
    
    for query, expected_docs in test_queries:
        for k in k_values:
            retrieved = retriever.retrieve(query, k=k)
            retrieved_ids = set([d.id for d in retrieved])
            expected_ids = set(expected_docs)
            
            hits = retrieved_ids & expected_ids
            results[k]["hit_rate"] += 1 if len(hits) > 0 else 0
            results[k]["precision"] += len(hits) / k
            results[k]["recall"] += len(hits) / len(expected_ids)
    
    n = len(test_queries)
    for k in k_values:
        results[k]["hit_rate"] /= n
        results[k]["precision"] /= n
        results[k]["recall"] /= n
    
    return results
```

### 1.3 生成质量评估

| 指标 | 含义 | 评估方法 |
|------|------|---------|
| 忠实度 | 回答是否基于检索到的文档 | 检查是否有"幻觉" |
| 相关性 | 回答是否回答了问题 | 检查是否离题 |
| 完整性 | 回答是否覆盖了所有要点 | 对比参考答案 |
| 有用性 | 回答是否对用户有帮助 | 用户评分 |

```python
class GenerationEvaluator:
    def __init__(self, judge_llm):
        self.judge = judge_llm
    
    def evaluate_faithfulness(self, query, answer, context):
        """评估忠实度：回答是否基于上下文"""
        prompt = f"""
        问题：{query}
        上下文：{context}
        回答：{answer}
        
        评估回答是否忠实地基于上下文（是否有编造）：
        - "faithful"：完全基于上下文
        - "partial"：部分基于上下文，部分编造
        - "unfaithful"：完全编造
        """
        return self.judge.generate(prompt)
    
    def evaluate_completeness(self, query, answer, reference):
        """评估完整性：回答是否覆盖了所有要点"""
        prompt = f"""
        问题：{query}
        参考回答：{reference}
        模型回答：{answer}
        
        评估模型回答是否覆盖了参考回答中的所有要点（1-5分）：
        """
        return self.judge.generate(prompt)
```

---

## 二、端到端评估

### 2.1 构建评估数据集

```python
class RAGEvaluationDataset:
    def __init__(self):
        self.test_cases = []
    
    def add_from_logs(self, logs, n=100):
        """从生产日志中提取测试用例"""
        sampled = random.sample(logs, n)
        for log in sampled:
            self.test_cases.append({
                "query": log["user_input"],
                "expected_answer": log.get("expected_answer"),
                "relevant_docs": log.get("relevant_docs"),
                "difficulty": log.get("difficulty", "medium"),
            })
    
    def add_manual_cases(self):
        """添加人工构造的边缘案例"""
        edge_cases = [
            {"query": "", "expected_answer": "请输入问题"},
            {"query": "你好", "expected_answer": "你好"},
            {"query": "不知道", "expected_answer": "不知道"},
            # 复杂查询
            # 歧义查询
            # ......
        ]
        self.test_cases.extend(edge_cases)
```

### 2.2 自动化评估

```python
def auto_evaluate_rag(rag_system, dataset, judge_llm):
    """自动评估 RAG 系统"""
    results = []
    
    for case in dataset.test_cases:
        # 1. 执行 RAG
        response = rag_system.answer(case["query"])
        
        # 2. 自动评估
        faithfulness = judge_llm.evaluate_faithfulness(
            case["query"], response, rag_system.last_context
        )
        relevance = judge_llm.evaluate_relevance(
            case["query"], response
        )
        
        results.append({
            "query": case["query"],
            "faithfulness": faithfulness,
            "relevance": relevance,
            "latency": response.latency,
            "tokens": response.total_tokens,
        })
    
    # 3. 汇总
    summary = {
        "faithfulness_rate": sum(r["faithfulness"] == "faithful" for r in results) / len(results),
        "avg_relevance": sum(r["relevance"] for r in results) / len(results),
        "avg_latency": sum(r["latency"] for r in results) / len(results),
        "avg_tokens": sum(r["tokens"] for r in results) / len(results),
    }
    
    return summary
```

---

## 三、RAG 优化策略

### 3.1 优化路线图

```
第一阶段：基础优化
  - 选对嵌入模型
  - 优化分块策略
  - 调整检索数量

第二阶段：检索增强
  - 查询改写
  - 重排序
  - 混合检索

第三阶段：高级方案
  - CRAG 纠正
  - Self-RAG 自评估
  - 多轮检索

第四阶段：系统优化
  - 缓存
  - 异步检索
  - 索引优化
```

### 3.2 常见问题与优化

| 问题 | 诊断 | 解决方案 |
|------|------|---------|
| 检索不到 | 召回率低 | 查询改写、HyDE、增加 k |
| 检索不相关 | 精确率低 | 重排序、减少 k、换嵌入模型 |
| 回答不准确 | 忠实度低 | 优化 Prompt、增加上下文约束 |
| 回答太慢 | 延迟高 | 缓存、异步、减少检索量 |
| 成本太高 | token 消耗大 | 小模型重排序、减少检索量 |

### 3.3 分块优化

```python
def optimize_chunking(documents, retriever, eval_dataset):
    """优化分块策略"""
    strategies = [
        {"name": "fixed_256", "chunk_size": 256, "overlap": 50},
        {"name": "fixed_512", "chunk_size": 512, "overlap": 50},
        {"name": "fixed_1024", "chunk_size": 1024, "overlap": 100},
        {"name": "semantic", "method": "semantic"},
        {"name": "recursive", "method": "recursive"},
    ]
    
    results = []
    for strategy in strategies:
        # 重新分块
        chunks = chunk_documents(documents, strategy)
        
        # 重建索引
        retriever.rebuild_index(chunks)
        
        # 评估
        score = evaluate_retrieval(retriever, eval_dataset)
        results.append({**strategy, "score": score})
    
    # 选最优
    return max(results, key=lambda x: x["score"]["hit_rate"])
```

---

## 四、生产环境的 RAG 监控

### 4.1 监控指标

```python
class RAGMonitor:
    def __init__(self):
        self.metrics = {
            "retrieval": {
                "avg_latency": [],
                "avg_results": [],
                "empty_results": 0,  # 空结果率
            },
            "generation": {
                "avg_latency": [],
                "avg_tokens": [],
                "faithfulness_scores": [],
            },
            "user": {
                "thumbs_up": 0,
                "thumbs_down": 0,
                "corrections": 0,
            },
        }
    
    def log_retrieval(self, query, results, latency):
        self.metrics["retrieval"]["avg_latency"].append(latency)
        self.metrics["retrieval"]["avg_results"].append(len(results))
        if len(results) == 0:
            self.metrics["retrieval"]["empty_results"] += 1
    
    def log_user_feedback(self, feedback):
        if feedback == "up":
            self.metrics["user"]["thumbs_up"] += 1
        elif feedback == "down":
            self.metrics["user"]["thumbs_down"] += 1
    
    def get_report(self, window="24h"):
        """生成监控报告"""
        return {
            "retrieval": {
                "avg_latency": mean(self.metrics["retrieval"]["avg_latency"][-1000:]),
                "empty_result_rate": self.metrics["retrieval"]["empty_results"] / max(1, len(self.metrics["retrieval"]["avg_results"])),
            },
            "user_satisfaction": {
                "thumbs_up_rate": self.metrics["user"]["thumbs_up"] / max(1, self.metrics["user"]["thumbs_up"] + self.metrics["user"]["thumbs_down"]),
            },
        }
```

### 4.2 告警机制

```python
def check_rag_health(monitor):
    """检查 RAG 系统健康状态"""
    alerts = []
    report = monitor.get_report()
    
    if report["retrieval"]["empty_result_rate"] > 0.1:
        alerts.append("🔴 空结果率超过 10%，需要检查索引或检索策略")
    
    if report["retrieval"]["avg_latency"] > 500:
        alerts.append("🟡 检索延迟超过 500ms，需要优化")
    
    if report["user_satisfaction"]["thumbs_up_rate"] < 0.6:
        alerts.append("🔴 用户满意度低于 60%，需要排查问题")
    
    return alerts
```

---

## 五、RAG 优化实战案例

### 5.1 案例：检索质量优化

```
问题：用户查询"如何退款"，但知识库中用的是"退货""投递""取消订单"

分析：
- 用户用词（"退款"）与知识库用词（"退货"）不匹配
- 向量检索能处理语义相似，但效果不够好

优化方案：
1. 查询改写：把"如何退款"改写为"退货流程 退款政策"
2. 增加同义词扩展：退款 → 退货、取消订单、投诉
3. 混合检索：向量检索 + BM25

效果：
- 检索召回率：62% → 89%
- 用户满意度：4.1 → 4.5
```

### 5.2 案例：生成质量优化

```
问题：Agent 经常不基于检索结果回答，而是"自由发挥"

分析：
- Prompt 中"基于以下信息回答"的约束不够强
- 模型倾向于使用自己的知识

优化方案：
1. 强化 Prompt 约束："如果你回答的信息不在以上参考内容中，请说'未找到相关信息'"
2. 降低 temperature（0.7 → 0.3）
3. 增加"信息不足"的默认输出

效果：
- 忠实度：72% → 94%
- 幻觉率：15% → 3%
```

---

## 六、RAG 评估的陷阱

### 6.1 常见陷阱

| 陷阱 | 表现 | 解决方法 |
|------|------|---------|
| 测试集过小 | 评估结果不可靠 | 至少 100+ 测试用例 |
| 测试集与真实分布不符 | 评估结果偏差 | 从生产日志中采样 |
| 只评估检索不评估生成 | 端到端效果未知 | 评估完整链路 |
| 使用有偏的评估模型 | 评估结果失真 | 使用多个评估模型 |
| 一次评估就完事 | 无法追踪趋势 | 持续评估，追踪变化 |

### 6.2 评估成本

评估 RAG 系统本身也有成本：

```
评估 100 个测试用例：
  - 执行 RAG：100 次 LLM 调用
  - 评估检索：100 次检索
  - 评估生成：100 次 LLM-as-Judge

总成本 ≈ 200-300 次 LLM 调用

优化：先用小数据集快速评估，再扩大数据集做精确评估
```

---

## 总结

| 评估层次 | 关键指标 | 优化策略 |
|---------|---------|---------|
| 检索质量 | 召回率、精确率、MRR | 分块、嵌入、检索策略 |
| 生成质量 | 忠实度、完整性 | Prompt、温度、约束 |
| 端到端 | 准确率、满意度 | 综合优化 |
| 生产级 | 延迟、成本、稳定性 | 缓存、监控、告警 |

**评估不是一次性的工作，而是持续的过程。** 随着数据变化、模型更新、用户需求变化，RAG 系统的表现也会变化。持续评估，持续优化。

下一篇文章，我们将完成模块三，深入**RAG 在 Agent 中的角色**——RAG 作为工具、与 Memory 的关系、以及高级集成模式。

---

**思考题**：
1. 你的 RAG 系统现在有评估吗？如果还没有，最优先评估什么？
2. 检索质量和生成质量，哪个对你的场景更重要？为什么？
3. 如果资源有限（只能做 3 个优化），你会优先优化什么？

---

> 上一篇：[20] Graph RAG：知识图谱增强
> 下一篇：[22] RAG 在 Agent 中的角色
> 系列目录：[README.md](./README.md)