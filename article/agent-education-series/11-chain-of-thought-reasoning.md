# 【AI Agent 系统教学 11】思维链与推理增强

> 让模型"边想边答"，是目前提升 Agent 推理能力最有效的方法。
> 但 CoT 不是万能的，什么时候用、怎么用，有讲究。

---

## 前言：Agent 为什么需要"思考"？

在 Agent 场景中，你经常遇到这样的问题：

- "帮我分析一下这个数据，然后给出建议"——需要推理
- "我该怎么做这个项目？"——需要规划
- "这个方案有什么问题？"——需要批判性思考

不加思考的 Agent 会直接输出答案——可能对，但也可能错得离谱。

**加思考的 Agent 会先"想清楚"再输出**——准确率更高，结果更可靠。

这个"想清楚"的过程，就是思维链（Chain-of-Thought）。

---

## 一、Chain-of-Thought（思维链）

### 1.1 什么是 CoT

CoT 的核心思想：**让模型先输出推理过程，再输出最终答案。**

```
问题：小明有 5 个苹果，吃了 2 个，又买了 3 个，现在有几个？

没有 CoT：6（直接输出答案）

有 CoT：
小明有 5 个苹果。
吃了 2 个，所以剩下：5 - 2 = 3 个。
又买了 3 个，所以现在有：3 + 3 = 6 个。
答案：6
```

### 1.2 CoT 为什么有效

**原因 1：分解复杂度**

把复杂问题分解成多个简单步骤。每一步的输出成为下一步的输入，模型只需要执行"简单推理"。

**原因 2：利用因果注意力**

因果注意力让前面的 token 影响后面的 token。推理链中的每一步都被"记住"，降低了"跳跃"错误。

**原因 3：自我校准**

当推理过程显式输出时，模型更容易发现自己的错误。

### 1.3 Zero-shot CoT

最简单的 CoT 实现：在 Prompt 末尾加一句"让我们一步步思考"。

```python
prompt = f"""
问题：{user_question}

让我们一步步思考。
"""
```

**效果**：在多个推理基准测试上，准确率提升 10-30%。

### 1.4 Few-shot CoT

给 2-3 个完整的推理示例：

```python
prompt = f"""
问题：小明有 10 个苹果，给了小红 3 个，又买了 5 个，现在有几个？
思考：小明有 10 个苹果。给了小红 3 个，所以剩下 10 - 3 = 7 个。又买了 5 个，所以现在有 7 + 5 = 12 个。
答案：12

问题：小明有 5 个苹果，吃了 2 个，又买了 3 个，现在有几个？
思考："""
```

**效果**：比 Zero-shot CoT 更稳定，但需要设计好的示例。

---

## 二、Self-Consistency：多路投票

### 2.1 核心思想

CoT 的一次推理结果可能因为随机性而不准确。Self-Consistency 的做法是：**多次推理，取多数结果。**

```
问题：2 + 3 × 4 = ?

推理 1：2 + 3 × 4 = 2 + 12 = 14
推理 2：2 + 3 × 4 = 2 + 12 = 14
推理 3：2 + 3 × 4 = 5 × 4 = 20
推理 4：2 + 3 × 4 = 2 + 12 = 14
推理 5：2 + 3 × 4 = 2 + 12 = 14

多数结果：14（5 次中 4 次）
```

### 2.2 实现方式

```python
def self_consistency(prompt, model, n=5):
    results = []
    for _ in range(n):
        response = model.generate(prompt, temperature=0.7)
        answer = extract_answer(response)
        results.append(answer)
    
    # 取多数结果
    most_common = max(set(results), key=results.count)
    return most_common
```

### 2.3 效果与成本

| 采样次数 | 准确率提升 | 成本增加 |
|---------|-----------|---------|
| 1 次 | 基准 | 1x |
| 3 次 | +5-10% | 3x |
| 5 次 | +8-15% | 5x |
| 10 次 | +10-20% | 10x |

**注意**：提升幅度随采样次数增加而递减。5 次之后边际收益很低。

### 2.4 对 Agent 的启示

在 Agent 的**关键决策点**使用 Self-Consistency：

```python
def agent_decision(self, user_input, critical=True):
    if critical:
        # 关键决策：多次推理，取多数
        candidates = []
        for _ in range(3):
            plan = self.plan(user_input)
            candidates.append(plan)
        return self.select_best(candidates)
    else:
        # 常规决策：一次推理
        return self.plan(user_input)
```

---

## 三、Tree of Thought（思维树）

### 3.1 从链到树

CoT 的局限：推理路径是线性的，一条路走到黑。如果中间错了，后面全错。

ToT 的做法：**在每一步生成多个可能的推理分支，然后评估、选择、回溯。**

```
问题：如何优化一个慢的 Python 函数？

思路 1：使用缓存
    ├─ 子思路 1.1：functools.lru_cache
    └─ 子思路 1.2：手动缓存

思路 2：使用更快的算法
    ├─ 子思路 2.1：二分查找
    └─ 子思路 2.2：哈希表

思路 3：并行计算
    ├─ 子思路 3.1：多线程
    └─ 子思路 3.2：异步

评估：思路 1 最容易实现，但效果有限。
      思路 2 效果最好，但需要重构代码。
      思路 3 对计算密集型任务有效。

选择：根据用户需求，选择思路 2。
```

### 3.2 ToT 的步骤

```
1. 生成：从当前状态，生成 K 个可能的下一步
2. 评估：评估每个下一步的"价值"
3. 选择：选择价值最高的 M 个继续
4. 重复：直到找到解决方案
5. 回溯：如果当前路径走不通，回到之前的分支点
```

### 3.3 对 Agent 的启示

ToT 特别适合需要**探索多个方案**的 Agent 场景：

```python
def agent_plan_with_tot(self, task, max_depth=3, branch_factor=3):
    def evaluate(plan):
        """评估一个方案的价值"""
        prompt = f"评估这个方案：{plan}\n维度：可行性、效果、成本"
        return self.llm(prompt)
    
    def generate_branches(state, k=3):
        """从当前状态生成 K 个分支"""
        prompt = f"当前状态：{state}\n生成 {k} 个可能的下一步方案"
        return self.llm(prompt, n=k)
    
    # ToT 主循环
    current_state = task
    for depth in range(max_depth):
        branches = generate_branches(current_state, branch_factor)
        scores = [evaluate(b) for b in branches]
        best_branch = branches[argmax(scores)]
        current_state = best_branch
    
    return current_state
```

---

## 四、Graph of Thought（思维图）

### 4.1 从树到图

ToT 的局限：分支之间不能交互信息。

GoT 的做法：**允许不同推理路径之间共享信息，形成一个图结构。**

```
问题：设计一个电商系统

思路 A：前端框架
    ↓
思路 A1：React
    └─────────────→ 结合
思路 B：后端框架                ↓
    ↓                   综合方案：React + FastAPI + PostgreSQL
思路 B1：FastAPI
    ↑
思路 C：数据库
    ↓
思路 C1：PostgreSQL
```

### 4.2 GoT 的操作

GoT 定义了四种操作：
1. **生成**：从当前节点生成新节点
2. **聚合**：合并多个节点的信息
3. **精炼**：优化单个节点的内容
4. **评估**：对节点进行评分

### 4.3 GoT vs 其他方法

| 方法 | 结构 | 信息流 | 适合场景 |
|------|------|--------|---------|
| CoT | 链 | 线性 | 简单的多步推理 |
| Self-Consistency | 多条链 | 投票 | 需要高准确率的决策 |
| ToT | 树 | 分层 | 探索多个方案 |
| GoT | 图 | 任意 | 复杂问题，需要综合 |

---

## 五、Agent 中的推理增强实践

### 5.1 推理模式选择

```python
def select_reasoning_mode(task_complexity):
    """根据任务复杂度选择推理模式"""
    if task_complexity == "simple":
        return "direct"  # 直接回答
    elif task_complexity == "medium":
        return "cot"  # 思维链
    elif task_complexity == "complex":
        return "self_consistency"  # 多路投票
    elif task_complexity == "exploratory":
        return "tot"  # 思维树
```

### 5.2 Agent 的推理循环

在实际的 Agent 中，推理和行动是交织的：

```python
def agent_loop_with_reasoning(self, user_input, max_steps=10):
    step = 0
    reasoning = []
    
    while step < max_steps:
        # 1. 推理
        thought = self.reason(f"当前状态：{self.state}\n历史推理：{reasoning}")
        
        # 2. 行动（调用工具）
        action = self.act(thought)
        
        # 3. 观察结果
        observation = self.execute(action)
        
        # 4. 更新推理记录
        reasoning.append({
            "step": step,
            "thought": thought,
            "action": action,
            "observation": observation
        })
        
        # 5. 检查是否完成
        if self.is_complete(observation):
            break
        
        step += 1
    
    return self.finalize(reasoning)
```

### 5.3 推理错误的自动修复

让 Agent 在推理过程中自我修正：

```python
def agent_with_self_correction(self, task):
    plan = self.plan(task)
    
    # 第一步：执行计划
    result = self.execute(plan)
    
    # 第二步：检查结果
    check = self.verify(result, task)
    
    if check["status"] == "error":
        # 第三步：分析错误
        analysis = self.analyze_error(plan, result, check)
        
        # 第四步：修正计划
        corrected_plan = self.correct_plan(plan, analysis)
        
        # 第五步：重新执行
        result = self.execute(corrected_plan)
    
    return result
```

---

## 六、2026 年推理增强新趋势

### 6.1 推理时计算（Test-Time Compute）

2026 年最重要的趋势：**推理时消耗更多计算 = 更好的结果**。

DeepSeek R1 和 OpenAI o1 系列模型证明：让模型在推理时"想得更久"，推理能力显著提升。

**对 Agent 的影响**：未来的 Agent 将在"推理时"分配更多计算，而不是在"训练时"。

### 6.2 推理与工具调用融合

不再把"推理"和"行动"分开，而是让推理过程也可以调用工具：

```
思考："我需要查询天气数据"
行动：调用 get_weather("北京")
观察：{"temperature": 25, "condition": "晴"}
思考："气温 25 度，适合穿短袖"
行动：生成回复
```

### 6.3 自监督推理

模型自己生成推理数据，自己训练自己。

```
1. 从训练数据中取出问题
2. 模型生成推理过程 + 答案
3. 与正确答案对比
4. 如果推理正确，用这个推理数据训练
5. 重复
```

---

## 总结

| 方法 | 核心思想 | 适用场景 | Agent 中的使用 |
|------|---------|---------|--------------|
| CoT | 一步步思考 | 多步推理 | 默认推理模式 |
| Self-Consistency | 多次推理取多数 | 高准确率决策 | 关键决策点 |
| ToT | 分支探索 + 评估 | 方案探索 | 复杂任务规划 |
| GoT | 图结构信息融合 | 综合问题 | 多源信息整合 |

**推理增强不是魔法，是工程。** 选择合适的方法，在成本和效果之间找到平衡。

下一篇文章，我们将进入**少样本学习与上下文学习**——模型如何从示例中学习，以及如何设计有效的示例。

---

**思考题**：
1. 你的 Agent 在什么场景下需要 Self-Consistency？什么场景下不需要？
2. ToT 和 GoT 在 Agent 场景中哪个更实用？为什么？
3. 如果 Agent 的推理结果经常出错，你会怎么排查？是推理方法的问题还是模型的问题？

---

> 上一篇：[10] 结构化提示词：多角色、多段落、格式约束
> 下一篇：[12] 少样本学习与上下文学习
> 系列目录：[README.md](./README.md)