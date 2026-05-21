# 高德AI应用开发面试题深度解析：从LangGraph到MCP的实战经验

> 面试不是背书，而是展示你真的做过项目。
> 这篇文章整理了高德AI应用开发一面的12道核心问题，每个答案都来自真实项目踩坑经验。
> 如果你也在准备AI应用开发的面试，希望能帮你少走弯路。

---

## 前言：为什么这些问题值得深入思考？

2026年，AI应用开发已经从"能不能做"进化到"怎么做得好"。

高德的AI应用开发岗位，面试题目不再是概念背诵，而是**你真的用过这些技术吗？遇到过什么问题？怎么解决的？**

这篇文章的12个问题，覆盖了AI应用开发的核心技术栈：
- **Agent框架**：LangGraph vs Workflow
- **记忆系统**：上下文管理、短期/长期记忆
- **工具调用**：Function Calling、MCP协议
- **工程实践**：多智能体协作、容错设计

每个答案都不是标准答案，而是**我在真实项目中踩过的坑、试过的方案、最终的选择**。

---

## 一、LangGraph 相比普通 Workflow 或链式调用，最大的价值是什么？

### 标准答案（背书版）

> LangGraph支持循环和状态管理，Workflow是线性的。

**这个回答面试官每天听10遍，直接让你回家。**

### 真实项目经验（值钱版）

**最大价值：状态可控 + 循环/回溯。**

普通链式调用（LangChain的LCEL）是线性的：A→B→C，一旦卡住只能整体重试。LangGraph把流程变成**有向图**，每个节点是一个step，边是条件跳转。

#### 真实踩坑案例

我之前做**智能行程规划助手**，一开始用LCEL链式调用：

```python
# 第一版：链式调用（失败案例）
chain = (
    PlanningPromptTemplate()
    | llm
    | ParsingOutputParser()
    | ValidationStep()
    | FinalOutput()
)
result = chain.invoke({"user_input": "上海3日游，预算5000"})
```

**问题**：用户看到初步方案后说"不喜欢这个范围，换一个"，整个链要**重头跑**，包括已经正确的部分（比如酒店推荐）。

**第二版：换成LangGraph**

```python
from langgraph.graph import StateGraph, END

class TripPlanningState(TypedDict):
    user_input: str
    draft_plan: Optional[dict]
    user_confirmed: bool
    retry_count: int

def create_trip_graph():
    workflow = StateGraph(TripPlanningState)
    
    # 添加节点
    workflow.add_node("plan", planning_node)
    workflow.add_node("validate", validation_node)
    workflow.add_node("human_review", human_review_node)
    
    # 关键：条件边
    workflow.add_conditional_edges(
        "human_review",
        should_retry,  # 判断函数
        {
            "confirm": END,  # 用户确认，结束
            "retry": "plan",  # 用户不满意，回到规划节点
        }
    )
    
    return workflow.compile()
```

**效果**：
- 用户说"换一个"，只需要重新执行`plan`节点
- 已经确认的部分（酒店、交通）**保留**，不重复生成

#### 核心差异总结

| 特性 | 普通Workflow | LangGraph |
|------|--------------|-----------|
| 执行方式 | 线性（A→B→C） | 图结构（可循环、可跳转） |
| 状态管理 | 无（每次重头） | 有（State对象跨节点共享） |
| 人工介入 | 难（要中断整个链） | 易（Human-in-the-Loop节点） |
| 适用场景 | 固定步骤任务 | 需要多轮决策/回溯的任务 |

**面试官想听的不是概念，而是：**
1. 你有没有遇到过"链式调用不够用"的场景？
2. 你是怎么解决的？
3. 换成LangGraph之后，具体带来了什么好处？

---

## 二、LangGraph 和 Agent 的关系是什么？

### 常见误解

> LangGraph就是Agent。

**错。LangGraph是框架，Agent是产品形态。**

### 正确认知

**LangGraph = 实现Agent的工程框架**

一个完整的Agent需要：
1. **LLM**：做决策（"下一步调用哪个工具"）
2. **工具调用**：执行动作（"调用高德API查天气"）
3. **循环决策**：根据工具返回结果，决定下一步（"天气不好，换室内景点"）

**LangGraph负责第3部分**——它提供了状态机、条件边、内存管理，让你不用自己手写`while True`循环。

#### 真实项目：CSDN文章批量生成Agent

我用LangGraph搭了一个多步Agent，流程是：

```
搜索热点 → 选择写作方向 → 写文章 → 自我审查 → 不通过就重写
```

**关键代码（简化版）**：

```python
from langgraph.graph import StateGraph

class ArticleState(TypedDict):
    topic: str
    draft: Optional[str]
    review_passed: bool
    retry_count: int

def create_article_agent():
    workflow = StateGraph(ArticleState)
    
    # 节点
    workflow.add_node("write", write_article_node)
    workflow.add_node("review", review_article_node)
    workflow.add_node("rewrite", rewrite_article_node)
    
    # 条件边：审查通过？
    workflow.add_conditional_edges(
        "review",
        lambda s: "pass" if s["review_passed"] else "fail",
        {
            "pass": END,
            "fail": "rewrite"
        }
    )
    
    return workflow.compile()
```

**为什么不用普通Agent框架？**

因为"审查不通过→重写"这个循环，如果用`while True`手写：

```python
# 手写循环（容易出bug）
while True:
    draft = write_article(topic)
    passed = review(draft)
    if passed:
        break
    # 问题：没有状态管理，retry_count要自己维护
    # 问题：调试难，不知道为什么死循环
```

LangGraph的优势：
1. **状态自动管理**：`ArticleState`对象跨节点共享
2. **可视化**：用`langgraph-checkpointer`可以看到Agent的执行路径
3. **可中断/恢复**：保存到checkpoint，下次从断点继续

---

## 三、什么场景下普通 Workflow 就够了？

### 判断标准：画流程图的时候，有没有菱形判断框？

**如果没有菱形判断框（if/else），Workflow就够了。**

### 具体场景

#### 场景1：固定步骤的内容生成

比如：先写大纲 → 再写正文 → 再润色

```python
# 用LCEL链式调用，20行搞定
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

chain = (
    ChatPromptTemplate.from_template("写大纲：{topic}")
    | llm
    | StrOutputParser()
    | ChatPromptTemplate.from_template("根据大纲写正文：{topic}，大纲：{input}")
    | llm
    | StrOutputParser()
)
```

**用LangGraph反而复杂**：要多写状态定义、节点连接、条件边，维护成本高了一倍。

#### 场景2：一次性问答（RAG）

```python
# RAG标准流程：检索 → 拼prompt → 返回答案
chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
```

**不需要循环**，因为：
- 检索结果是确定的
- LLM生成答案是确定的
- 没有"生成错了要重来"的逻辑

#### 场景3：数据ETL

```python
# 数据抽取 → 转换 → 加载
chain = (
    extract_data
    | transform_data
    | load_data
)
```

逻辑固定，不需要Agent决策。

### 什么时候必须用LangGraph？

**只要出现以下任何一种情况，就用LangGraph：**

1. **需要循环**：比如"代码生成 → 运行 → 报错 → 改代码"，可能循环5-10次
2. **需要人工介入**：比如"生成方案 → 用户确认 → 不确认就重新生成"
3. **多Agent协作**：比如"规划Agent → 执行Agent → 审查Agent"，彼此之间有依赖

**我的经验**：
- 一开始我把所有东西都往LangGraph里塞
- 后来发现**CSDN文章保存草稿**这个任务，就是固定三步：读取md文件 → 调用API → 返回结果
- 用LCEL链式调用20行搞定，用LangGraph反而要多写状态定义和节点连接

**结论**：先用普通Workflow把功能跑通，真的遇到"需要循环/回溯"的痛点了，再迁移到LangGraph。别为了炫技提前上图编排。

---

## 四、图编排的维护成本会不会更高？

### 直接答案：会，而且高不少。但值不值要看场景。

#### 维护成本高在哪里？

**1. 调试难**

普通Workflow是线性执行，报错看堆栈就知道哪步错了。

图编排可能走了奇怪的路径（比如条件边配错了，死循环），要装LangSmith或者自己打日志。

```python
# 调试图编排，需要显式打日志
def planning_node(state):
    print(f"[DEBUG] Entering planning_node, retry_count={state['retry_count']}")
    # ...
```

**2. 新人上手慢**

普通Workflow一看就懂：A→B→C。

图编排要理解：
- 状态定义（State对象）
- 节点职责（每个node做什么）
- 边的触发条件（conditional_edges的逻辑）

**3. 过度设计风险**

很多人（包括我）一上来就用LangGraph，结果任务根本不需要循环，白复杂化。

#### 但有些场景必须承担这个成本

**场景1：多步工具调用**

比如写代码 → 运行 → 报错 → 改代码，可能循环5-10次。

用普通Workflow要手写`while True`，还要自己管理：
- 循环次数上限（防止死循环）
- 中间状态保存（代码写到哪了）
- 错误恢复（API超时了怎么办）

用LangGraph，这些都有现成的pattern：

```python
# LangGraph的自动重试 + 状态管理
workflow.add_node("write_code", write_code_node)
workflow.add_node("run_code", run_code_node)
workflow.add_node("fix_code", fix_code_node)

workflow.add_conditional_edges(
    "run_code",
    lambda s: "success" if s["exit_code"] == 0 else "fail",
    {
        "success": END,
        "fail": "fix_code"
    }
)
```

**场景2：多Agent协作**

比如规划Agent → 执行Agent → 审查Agent，彼此之间有依赖。

用普通Workflow要手动管理Agent之间的数据传递，用LangGraph直接通过State对象共享。

#### 成本 vs 收益的权衡

| 场景 | 维护成本 | 收益 | 建议 |
|------|---------|------|------|
| 固定步骤任务 | 高（过度设计） | 低 | 用普通Workflow |
| 需要循环/回溯 | 中 | 高（避免手写状态管理） | 用LangGraph |
| 多Agent协作 | 中 | 高（清晰的依赖管理） | 用LangGraph |
| 简单原型验证 | 高（杀鸡用牛刀） | 低 | 用普通Workflow |

**我的建议**：
1. 先用普通Workflow把功能跑通
2. 真的遇到"需要循环/回溯"的痛点了，再迁移到LangGraph
3. 别为了炫技提前上图编排

---

## 五、上下文窗口、短期记忆、长期记忆分别是什么关系？

### 一句话总结

**上下文窗口是"工作记忆"，短期记忆是"这次会话的笔记"，长期记忆是"日记本"。**

### 具体区别

| 记忆类型 | 存活时间 | 存在哪 | 典型内容 | 实际例子 |
|---------|---------|--------|----------|---------|
| **上下文窗口** | 单次对话 | LLM的KV Cache | 当前对话的最近10-20轮 | "用户刚才说要用Python写" |
| **短期记忆** | 一次任务执行期间 | Agent的状态对象/Redis缓存 | 用户刚才说"用Python写"，后面步骤都记住 | 规划Agent把"用Python"传给代码生成Agent |
| **长期记忆** | 跨会话持久化 | 向量数据库/关系型数据库 | "这个用户喜欢简洁风格" | 下次对话，Agent自动用简洁风格回复 |

### 真实踩坑经验

我一开始把**短期记忆和长期记忆混在一起**，结果：

**问题案例**：
1. 用户在这次对话中说"不要用emoji"
2. 我把这个偏好存进了**长期记忆**（向量数据库）
3. 下次对话，Agent自动加载长期记忆，发现"不要用emoji"
4. **但用户其实只是这次不想用**，不是永久偏好

**解决方案**：分开管理

```python
class MemoryManager:
    def __init__(self):
        self.short_term = {}  # 存在Redis，TTL=30分钟
        self.long_term = VectorStore()  # 存在向量数据库，永久
    
    def update_short_term(self, key, value):
        """更新短期记忆，任务结束就清"""
        self.short_term[key] = value
        redis.setex(key, 1800, value)  # 30分钟过期
    
    def update_long_term(self, key, value):
        """更新长期记忆，只有用户明确说'记住这个偏好'才调用"""
        if self.user_confirmed("要永久记住这个偏好吗？"):
            self.long_term.add(key, value)
```

### 实际使用建议

**上下文窗口**：
- 不用你管，LLM自动管理
- 但要注意**上下文长度限制**（GPT-4o是128K tokens，Claude 3.5是200K）
- 如果对话太长，要用**摘要压缩**或者**检索式补充**

**短期记忆**：
- 适合存"这次对话的临时状态"
- 比如：用户选择了哪个方案、当前执行到哪一步了
- 用Redis存，设置TTL，会话结束自动清

**长期记忆**：
- 适合存"用户的持久偏好"
- 比如：写作风格、常用技术栈、不喜欢的内容类型
- 用向量数据库存，支持语义检索

---

## 六、记忆和 RAG 的区别是什么？

### 核心区别

**记忆是"我记得你"，RAG是"我去查资料"。**

| 特性 | 记忆系统 | RAG系统 |
|------|---------|---------|
| **数据来源** | 历史对话、用户偏好 | 外部文档、知识库 |
| **查询方式** | 精确匹配（key-value）或语义检索 | 语义相似度搜索 |
| **数据量** | 小（单用户的历史） | 大（可能几万篇文档） |
| **更新频率** | 高（每次对话都可能更新） | 低（文档更新才更新向量库） |
| **典型场景** | "这个用户喜欢简洁风格" | "公司年假政策是什么" |

### 真实项目经验

我做**智能行程规划**的时候，两种都用：

#### 记忆系统的用法

```python
# 用户说"不喜欢爬山"
memory.save(
    user_id="user_123",
    key="preferences",
    value={"dislike": ["爬山"], "budget": 5000}
)

# 下次对话，自动加载
prefs = memory.load(user_id="user_123", key="preferences")
# prefs = {"dislike": ["爬山"], "budget": 5000}
```

**特点**：
- 数据量小（一个用户的偏好就几KB）
- 需要精确匹配（不能把"不喜欢爬山"检索成"不喜欢运动"）
- 更新频繁（用户可能随时改偏好）

#### RAG系统的用法

```python
# 向量数据库里有几万条POI信息
vector_db = Chroma.from_documents(poi_documents)

# 用户问"上海适合拍照的免费景点"
query_vector = embed("上海适合拍照的免费景点")
results = vector_db.similarity_search(query_vector, k=5)

# results = [
#   "外滩：免费，适合拍照，评分4.5",
#   "田子坊：免费，适合拍照，评分4.3",
#   ...
# ]
```

**特点**：
- 数据量大（几万条POI）
- 需要语义检索（"适合拍照"要能匹配"风景好看"）
- 更新不频繁（POI信息可能几个月才更新一次）

### 组合使用：记忆 + RAG

实际项目通常是**记忆+RAG混合**：

```python
def plan_trip(user_input: str):
    # 第一步：查记忆，了解用户偏好
    user_prefs = memory.load(user_id, key="preferences")
    # user_prefs = {"dislike": ["爬山"], "budget": 5000}
    
    # 第二步：用RAG检索相关POI
    query = f"{user_input}，排除{user_prefs['dislike']}"
    poi_results = vector_db.similarity_search(query, k=10)
    
    # 第三步：把用户偏好和POI信息一起喂给LLM
    prompt = f"""
    用户需求：{user_input}
    用户偏好：{user_prefs}
    相关POI：{poi_results}
    请生成行程规划。
    """
    plan = llm.invoke(prompt)
    return plan
```

**关键判断**：
- 如果数据量小、结构化、需要精确匹配 → 用**记忆**
- 如果数据量大、非结构化、需要语义匹配 → 用**RAG**
- 实际项目通常是**记忆+RAG混合**：先查记忆了解用户，再用RAG检索专业知识

---

## 七、为什么说记忆不是训练模型？

### 核心原因

**训练是改权重，记忆是改上下文。**

| 特性 | 训练模型（Fine-tuning） | 记忆系统 |
|------|------------------------|---------|
| **原理** | 用梯度下降调整神经网络参数 | 把历史信息存到数据库，对话时取出来拼进prompt |
| **成本** | 高（GPT-4微调要几千美元） | 低（几乎为零，只是数据库存储成本） |
| **更新速度** | 慢（要重新训练） | 快（实时更新） |
| **可逆性** | 不可逆（训坏了要重来） | 可逆（随时可以删除或修改记忆） |
| **适用场景** | 让模型学会新能力（新语言、新领域） | 让模型了解用户信息（偏好、历史行为） |

### 真实踩坑经验

我一开始想"让模型记住用户的写作风格"，第一反应是**Fine-tune**。

**第一版方案（失败）**：
- 收集用户历史文章（100篇）
- Fine-tune GPT-4（成本：约3000美元）
- 期望：模型自动用用户的写作风格生成新文章

**问题**：
1. **成本太高**：每个用户要Fine-tune一次，100个用户就是30万美元
2. **更新慢**：用户写了新文章，要重新Fine-tune才能"记住"
3. **不可逆**：Fine-tune错了（比如混入了低质量文章），要重新训练

**第二版方案（成功）**：
改成**RAG + 记忆系统**，成本几乎为零：

```python
def generate_article(user_id, topic):
    # 第一步：从记忆系统里取用户的写作风格
    user_style = memory.load(user_id, key="writing_style")
    # user_style = "简洁、用类比、避免长段落"
    
    # 第二步：从RAG里取用户历史文章（作为风格参考）
    similar_articles = vector_db.similarity_search(
        query=f"用户{user_id}写的关于{topic}的文章",
        k=3
    )
    
    # 第三步：拼进prompt
    prompt = f"""
    写作风格：{user_style}
    参考文章：{similar_articles}
    请写一篇关于{topic}的文章。
    """
    article = llm.invoke(prompt)
    return article
```

**效果**：
- 成本：几乎为零（只是LLM API调用费）
- 更新：用户写了新文章，立刻向量化存进数据库，下次对话就能用
- 可逆：用户不喜欢这个风格，删除记忆就行

### 面试可以说的点

1. **训练是"基因改造"，记忆是"查笔记"**
   - 训练：改模型权重，成本高、周期长、不可逆
   - 记忆：改上下文，成本低、实时更新、可逆

2. **训练适合让模型学会新能力，记忆适合让模型了解用户信息**
   - 训练：比如让模型学会新语言、新领域知识
   - 记忆：比如让模型记住用户偏好、历史行为

3. **现在业界趋势是"尽量用记忆/RAG，避免频繁微调"**
   - 除非任务真的需要模型内部知识改变（比如让模型学会新语言）
   - 否则都用记忆/RAG，成本低、灵活性强

---

## 八、Redis 在记忆里适合做什么？

### 直接答案

**Redis适合做短期记忆 + 高速缓存，不适合做长期记忆。**

### 具体用法

#### 用法1：会话状态存储

Agent执行多步任务时，把中间状态存Redis，设置TTL=30分钟，会话结束自动过期。

```python
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0)

def save_session_state(session_id, state):
    """保存会话状态，30分钟后过期"""
    r.setex(
        f"session:{session_id}",
        1800,  # 30分钟
        json.dumps(state)
    )

def load_session_state(session_id):
    """加载会话状态"""
    data = r.get(f"session:{session_id}")
    if data:
        return json.loads(data)
    return None

# 使用示例
state = {
    "user_input": "上海3日游",
    "draft_plan": {...},
    "retry_count": 2
}
save_session_state("session_123", state)

# 下次对话
state = load_session_state("session_123")
```

#### 用法2：上下文缓存

把LLM的输入输出缓存起来，相同问题直接返回，省API调用费。

```python
def get_llm_response(prompt):
    # 先查缓存
    cache_key = f"cache:{hash(prompt)}"
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 缓存没有，调用LLM
    response = llm.invoke(prompt)
    
    # 存入缓存，1小时后过期
    r.setex(cache_key, 3600, json.dumps(response))
    return response
```

#### 用法3：限流计数器

防止用户刷API，用Redis的`INCR` + `EXPIRE`实现滑动窗口限流。

```python
def rate_limit(user_id, max_requests=10, window=60):
    """
    限流：每个用户在60秒内最多10次请求
    """
    key = f"ratelimit:{user_id}"
    
    # 增加计数
    count = r.incr(key)
    
    # 第一次请求，设置过期时间
    if count == 1:
        r.expire(key, window)
    
    # 超过限制
    if count > max_requests:
        return False
    
    return True

# 使用示例
if not rate_limit(user_id="user_123"):
    return "请求过于频繁，请稍后再试"
```

### 为什么不适合长期记忆？

**原因1：Redis是内存数据库，存大量历史对话成本高**

假设每个用户每天产生1MB的对话历史，1000个用户就是1GB/天。
Redis内存成本约为**每GB 10美元/月**，而向量数据库（Milvus）用磁盘存储，成本约为**每GB 0.1美元/月**。

**原因2：Redis不支持语义搜索**

长期记忆的核心需求是"语义检索"：
- 用户问"我上次说的那个项目"，要能匹配到"2026-05-21的对话记录"
- Redis只能做精确匹配（key-value），做不到语义相似度搜索

**原因3：长期记忆需要持久化，Redis适合临时数据**

Redis的数据存在内存里，虽然可以配置持久化（RDB/AOF），但主要设计目标是**高速缓存**，不是**长期存储**。

长期记忆应该用**向量数据库**（Milvus/Chroma），支持：
- 语义搜索
- 大容量存储（磁盘）
- 元数据过滤（按时间、用户ID过滤）

### 真实项目经验

我做**CSDN草稿保存**的时候，用Redis缓存已发布的文章ID，60秒内重复保存直接拒绝（防止限流报错）。

```python
def prevent_duplicate_publish(article_id):
    """防止60秒内重复发布同一篇文章"""
    key = f"published:{article_id}"
    
    if r.exists(key):
        return False  # 60秒内已经发布过
    
    # 标记已发布，60秒后自动过期
    r.setex(key, 60, "1")
    return True
```

**这个场景Redis完美**：
- 数据小（一个文章ID就几十字节）
- 读写频繁（每次保存草稿都要检查）
- 可以丢（大不了让用户重发一次）

---

## 九、如果上下文太长被截断了，你会选滑动窗口、摘要压缩还是检索式补充？怎么判断？

### 直接答案

**看任务类型，不是二选一，是组合使用。**

### 三种策略对比

| 策略 | 适合场景 | 缺点 |
|------|---------|------|
| **滑动窗口** | 对话式任务，最近的内容最重要 | 早期信息会丢失 |
| **摘要压缩** | 长文档写作/分析，需要全局理解 | 压缩过程可能丢细节 |
| **检索式补充** | 知识密集型任务，历史信息量大 | 检索可能不精准 |

### 真实项目经验

我做**智能行程规划**的时候，上下文经常超长（用户聊了20轮，加上POI数据）。

**策略组合**：

#### 前10轮：滑动窗口

```python
def sliding_window(messages, window_size=10):
    """
    只保留最近10轮对话
    """
    if len(messages) <= window_size:
        return messages
    
    # 丢弃最早的消息，保留最近的window_size轮
    return messages[-window_size:]
```

**为什么用滑动窗口？**
- 前10轮主要是"闲聊"和"需求确认"，最近的内容更重要
- 比如用户说"我要去上海"，然后聊了5轮别的，最后说"还是去北京吧"——应该记住"北京"，而不是"上海"

#### 10轮以后：摘要压缩

```python
def compress_history(messages):
    """
    把前10轮对话压缩成3句话
    """
    history_text = "\n".join([m["content"] for m in messages[:10]])
    
    prompt = f"请把以下对话压缩成3句话：\n{history_text}"
    summary = llm.invoke(prompt)
    
    # 返回压缩后的摘要 + 最近5轮对话
    return [
        {"role": "system", "content": f"历史摘要：{summary}"},
        *messages[-5:]
    ]
```

**为什么用摘要压缩？**
- 10轮以后，对话内容已经涉及"具体规划"了，不能简单丢弃
- 比如用户说了"预算5000""不喜欢爬山"，这些信息要保留，但不能占太多token

#### 涉及具体景点时：检索式补充

```python
def retrieve_poi_info(user_query):
    """
    从向量数据库检索相关POI信息
    """
    query_vector = embed(user_query)
    results = vector_db.similarity_search(query_vector, k=5)
    return results

# 使用示例
user_query = "上海适合拍照的免费景点"
poi_info = retrieve_poi_info(user_query)
# poi_info = [
#   "外滩：免费，适合拍照，评分4.5",
#   "田子坊：免费，适合拍照，评分4.3",
#   ...
# ]
```

**为什么用检索式补充？**
- POI数据太大（几万条），不能全放上下文
- 用户问"适合拍照的景点"，只要检索相关的几条就行

### 判断标准

**如果任务依赖最近信息 → 滑动窗口**
- 比如：对话式任务、实时交互

**如果任务需要全局理解 → 摘要压缩**
- 比如：长文档写作、代码生成（需要理解整个项目）

**如果任务需要外部知识 → 检索式补充**
- 比如：知识问答、专业领域任务

**生产环境通常是三种组合**，不是单选：

```python
def manage_context(messages, task_type):
    if task_type == "conversation":
        # 对话任务：滑动窗口 + 偶尔摘要压缩
        if len(messages) > 10:
            messages = compress_history(messages)
        return sliding_window(messages)
    
    elif task_type == "writing":
        # 写作任务：摘要压缩 + 检索式补充
        summary = compress_history(messages[:10])
        relevant_docs = retrieve_relevant_docs(messages[-1]["content"])
        return [summary] + relevant_docs + messages[-5:]
    
    elif task_type == "knowledge_qa":
        # 知识问答：检索式补充
        relevant_docs = retrieve_relevant_docs(messages[-1]["content"])
        return relevant_docs + messages[-3:]
```

---

## 十、MCP 和 Function Calling 的关系是什么？

### 核心区别

**Function Calling是能力，MCP是协议。**

| 特性 | Function Calling | MCP（Model Context Protocol） |
|------|-----------------|-------------------------------|
| **定义** | LLM的能力，让模型决定"调用哪个工具、参数是什么" | Anthropic推出的标准协议，定义了"工具怎么暴露给LLM"、"LLM怎么调用工具" |
| **提出者** | OpenAI（2023年） | Anthropic（2024年） |
| **兼容性** | 各家大模型都有自己的实现，互不兼容 | 统一协议，Claude/OpenClaw都支持 |
| **类似物** | "你会打电话" | "电话簿标准"（规定了号码格式、拨号规则） |

### 类比理解

**Function Calling就像"你会打电话"**：
- OpenAI的GPT-4会打电话
- Anthropic的Claude也会打电话
- 但他们用的"电话簿格式"不一样，你给GPT-4的电话簿，Claude看不懂

**MCP就像"电话簿标准"**：
- 规定了"电话簿"应该是什么格式（JSON Schema）
- 规定了"拨号"的流程（如何发现工具、如何调用工具、如何返回结果）
- 这样，你写一个"电话簿"（MCP Server），所有会打电话的模型（支持MCP的）都能用

### 真实项目经验

我一开始做工具调用，每个工具都手写Function Calling的JSON Schema：

```python
# 第一版：手写Function Calling（痛苦）
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_poi",
            "description": "搜索POI信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        }
    }
]

# 每加一个工具，就要手写一堆JSON Schema
# 而且OpenAI的Format和Anthropic的Format不一样，要写两套
```

**问题**：
1. **重复劳动**：每个工具都要手写JSON Schema
2. **不兼容**：OpenAI的Format和Anthropic的Format不一样，要写两套
3. **难维护**：工具多了之后，JSON Schema管理混乱

**第二版：用MCP协议**（爽）

后来发现OpenClaw支持MCP协议，可以直接接入现成的MCP服务器：

```python
# 第二版：用MCP协议（爽）
from openclaw import MCPClient

# 连接MCP Server（现成的，别人写好的）
mcp_client = MCPClient()
mcp_client.connect("filesystem")  # 文件系统工具
mcp_client.connect("browser")     # 浏览器工具
mcp_client.connect("database")     # 数据库工具

# 这些工具自动变成Agent可以用的工具
# 不需要手写JSON Schema！
agent = Agent(
    llm=claude,
    tools=mcp_client.get_tools()  # 自动获取工具定义
)
```

**效果**：
- 我的Agent能用的工具从5个变成了50+个
- 而且不需要我维护（MCP Server的开发者会更新）
- 换模型也不用改代码（MCP是标准协议）

### 面试可以说的点

1. **Function Calling是2023年OpenAI推的，各家大模型都有自己的实现，互不兼容**
   - OpenAI的Format
   - Anthropic的Format
   - Google的Format
   - 都不一样

2. **MCP是2024年Anthropic推的，目标是统一工具调用协议**
   - 类似RESTful API对Web开发的意义
   - 现在Claude/OpenClaw都支持了
   - 未来可能会有更多模型支持

3. **未来趋势：MCP会成为AI工具调用的HTTP协议**
   - 就像现在做Web开发，不用自己设计"怎么传参数""怎么返回结果"
   - 以后做AI工具开发，直接用MCP协议，所有支持MCP的模型都能用

---

## 十一、讲下你简历上的多智能体项目，他有哪几种智能体，智能体的调用链路是哪样的？

### 项目：Smart Trip Planner（智能行程规划助手）

#### 项目背景

**问题**：用户要规划一次旅行，需要考虑：
- 景点选择（哪些景点值得去）
- 交通安排（景点之间的交通方式、时间）
- 预算控制（门票、交通、住宿的总费用）
- 用户偏好（不喜欢爬山、预算5000）

**传统方案**：用链式调用（Workflow），一次性生成完整行程。

**问题**：
- 生成错了要整体重来
- 不能根据用户反馈动态调整
- 复杂任务（比如跨城市行程）一步做不到

**我的方案**：用**多智能体协作**，把任务拆解给多个Agent，每个Agent负责一部分。

#### 智能体分类

**1. 规划Agent（Planning Agent）**

**职责**：理解用户需求，生成初步行程（哪天去哪、交通方式、景点顺序）

**输入**：
- 用户需求（"上海3日游，预算5000，不喜欢爬山"）
- 用户历史偏好（从记忆系统加载）

**输出**：
- 初步行程（JSON格式）

```json
{
  "day1": {
    "morning": {"poi": "外滩", "duration": 2, "transport": "walk"},
    "afternoon": {"poi": "田子坊", "duration": 3, "transport": "subway"},
    "evening": {"poi": "东方明珠", "duration": 2, "transport": "taxi"}
  },
  "day2": {...},
  "day3": {...}
}
```

**2. 检索Agent（Retrieval Agent）**

**职责**：调用高德API/POI数据库，补充景点信息、交通时间、门票价格

**输入**：
- 规划Agent生成的初步行程

**输出**：
- 补充了详细信息的行程（每个景点的门票价格、交通时间、用户评分）

```json
{
  "day1": {
    "morning": {
      "poi": "外滩",
      "duration": 2,
      "transport": "walk",
      "ticket_price": 0,
      "rating": 4.5,
      "travel_time_to_next": 15  // 到田子坊15分钟
    },
    ...
  }
}
```

**3. 审查Agent（Review Agent）**

**职责**：检查行程合理性（景点距离太远、交通时间不够、预算超了）

**输入**：
- 检索Agent补充了详细信息的行程

**输出**：
- 审查结果（通过/不通过）
- 如果不通过，给出修改建议

```json
{
  "passed": false,
  "issues": [
    "day1的上午和下午景点距离太远（50公里），交通时间不够",
    "day3的预算超了（预计6000，用户预算5000）"
  ],
  "suggestions": [
    "建议把day1的下午景点换成附近的XXX",
    "建议把day3的XXX景点换成免费的XXX"
  ]
}
```

**4. 输出Agent（Output Agent）**

**职责**：把行程格式化成用户友好的格式（Markdown/思维导图/PDF）

**输入**：
- 审查Agent通过的行程

**输出**：
- Markdown格式的行程（适合CSDN文章）
- 或者思维导图（适合可视化）
- 或者PDF（适合打印）

#### 调用链路

```
用户输入
  ↓
规划Agent（生成初步方案）
  ↓
检索Agent（补充实时数据：天气、交通、门票）→ 并行执行（asyncio.gather）
  ↓
审查Agent（检查合理性，不合理就打回给规划Agent重新规划）
  ↓
输出Agent（生成最终行程，支持导出为PDF/腾讯文档）
```

**关键设计**：

**1. 规划Agent和审查Agent之间有循环**

```python
# 伪代码
max_retries = 3
for i in range(max_retries):
    plan = planning_agent.run(user_input)
    plan = retrieval_agent.run(plan)
    review_result = review_agent.run(plan)
    
    if review_result["passed"]:
        break  # 通过审查，跳出循环
    else:
        # 不通过，把修改建议传给规划Agent，重新规划
        user_input += f"\n修改建议：{review_result['suggestions']}"
        
if i == max_retries - 1:
    # 3次还通不过，降级给用户看"部分不合理"的版本
    return plan_with_warnings(plan, review_result["issues"])
```

**2. 检索Agent是并行执行的**

```python
import asyncio

async def retrieve_weather(city):
    # 调用天气API
    ...

async def retrieve_traffic(route):
    # 调用高德API查交通
    ...

async def retrieve_ticket_prices(poi_list):
    # 查门票价格
    ...

# 并行执行，提速
weather, traffic, tickets = await asyncio.gather(
    retrieve_weather(city),
    retrieve_traffic(route),
    retrieve_ticket_prices(poi_list)
)
```

#### 踩坑经验

**踩坑1：审查Agent太严格**

**问题**：用户说"随便逛逛"，审查Agent打回了（因为"随便"不符合任何合理性规则）。

**解决**：加了**宽松模式**：

```python
def review_plan(plan, strict_mode=True):
    if not strict_mode:
        # 宽松模式：只检查硬性约束（预算超了、交通时间不够）
        # 不检查软性约束（"随便逛逛"也放行）
        ...
    
    # 用户明确说"不介意走得累"，审查Agent就放行
    if user_input.contains("不介意走得累"):
        return {"passed": True}
```

**踩坑2：检索Agent调用高德API超时**

**问题**：高德API偶尔超时（特别是节假日高峰期），整个行程规划就中断了。

**解决**：见下一节（技术难点）。

---

## 十二、讲讲你项目中最大的技术难点，以及你是怎么解决的？

### 最大难点：如何让Agent在工具调用失败时自动恢复，而不是整个任务崩溃？

#### 问题描述

规划Agent调用**高德API**获取交通时间，但高德API偶尔超时（特别是节假日高峰期）。

**第一版解决方案（失败）**：

```python
# 第一版：加try-except，捕获异常后返回"暂无数据"
try:
    traffic_time = call_gaode_api(origin, destination)
except TimeoutError:
    traffic_time = None  # 返回"暂无数据"
```

**问题**：
- 这样行程里就缺了关键信息（交通时间），用户不满意
- 比如：用户看到行程里写"上午外滩，下午田子坊"，但不知道这两个景点之间要多久

**第二版解决方案（可行但不够好）**：

```python
# 第二版：加重试机制
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
def call_gaode_api_with_retry(origin, destination):
    return call_gaode_api(origin, destination)
```

**问题**：
- 高德API如果真的挂了，重试也没用
- 而且用户要等9秒（3次 × 3秒超时）才看到结果
- 体验很差

**最终方案（生产环境在用）**：

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed

async def get_traffic_time(origin, destination):
    """
    获取交通时间，带降级策略和后台更新
    """
    try:
        # 第一优先：调用高德API（0.5秒快速失败）
        traffic_time = await asyncio.wait_for(
            call_gaode_api(origin, destination),
            timeout=0.5
        )
        return traffic_time
    
    except asyncio.TimeoutError:
        # 高德API超时，降级到百度地图API
        try:
            traffic_time = await asyncio.wait_for(
                call_baidu_api(origin, destination),
                timeout=0.5
            )
            return traffic_time
        except asyncio.TimeoutError:
            # 两个API都超时，返回估算值（后台继续跑真实数据）
            asyncio.create_task(
                update_traffic_time_later(origin, destination)
            )
            return estimate_traffic_time(origin, destination)

async def update_traffic_time_later(origin, destination):
    """
    后台继续跑真实数据，跑到了再更新
    """
    try:
        traffic_time = await call_gaode_api(origin, destination)
        # 更新到数据库
        await update_database(origin, destination, traffic_time)
    except:
        pass  # 后台更新失败，不影响用户体验
```

**技术细节**：

**1. 用`tenacity`做重试 + 降级**

```python
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_exception_type((TimeoutError, ConnectionError))
)
async def call_gaode_api_with_retry(origin, destination):
    return await call_gaode_api(origin, destination)
```

**2. 用`asyncio.wait_for`实现"快速失败 + 后台更新"**

```python
# 主流程：0.5秒快速失败
try:
    traffic_time = await asyncio.wait_for(
        call_gaode_api(origin, destination),
        timeout=0.5
    )
except asyncio.TimeoutError:
    # 快速失败，不让用户等
    traffic_time = estimate_traffic_time(origin, destination)
    
    # 后台继续跑真实数据
    asyncio.create_task(
        update_traffic_time_in_background(origin, destination)
    )
```

**3. 用LangGraph的状态管理，把"交通时间"存成`Optional[float]`，允许部分字段缺失**

```python
class TripPlanningState(TypedDict):
    user_input: str
    draft_plan: Optional[dict]
    traffic_times: Optional[dict]  # 允许为None（部分字段缺失）
    retry_count: int

def planning_node(state):
    # 即使traffic_times缺失，也继续生成行程（用估算值）
    if state["traffic_times"] is None:
        state["traffic_times"] = estimate_all_traffic_times(state["draft_plan"])
    
    # 继续生成行程
    ...
```

#### 收获

**技术上的收获**：
1. **Agent系统的核心是容错，不是完美**
   - 让用户完成任务，比让系统不报错更重要
   - 宁可返回"部分数据"，也不要让用户看到"系统错误"

2. **降级策略比重试机制更重要**
   - 重试只能解决"临时网络抖动"
   - 降级能解决"API真的挂了"的情况

3. **后台更新是提升用户体验的关键**
   - 用户不需要等真实数据（用估算值先展示）
   - 后台跑到真实数据了，再悄悄更新

**认知上的收获**：
1. **不要追求100%的完美**
   - 95%的准确率 + 实时响应 > 99%的准确率 + 让用户等10秒

2. **用户体验 > 技术完美**
   - 用户要的是"能看到行程"，而不是"行程的每一个数据都是实时精准的"

---

## 总结：AI应用开发的核心能力模型

这12个问题，覆盖了AI应用开发的核心能力：

| 能力维度 | 涵盖问题 | 核心要求 |
|---------|---------|---------|
| **Agent框架掌握** | 1, 2, 3, 4 | 不是背书，而是真的用过LangGraph，知道什么时候用、什么时候不用 |
| **记忆系统设计** | 5, 6, 7, 8, 9 | 理解上下文窗口/短期记忆/长期记忆的区别，知道用什么技术实现（Redis/向量数据库） |
| **工具调用能力** | 10 | 理解Function Calling和MCP的关系，能接入现成的MCP Server |
| **工程实践能力** | 11, 12 | 真的做过项目，遇到过问题，有解决方案 |

**面试准备建议**：

1. **不要背概念**
   - 面试官听得出你是不是背的
   - 用"我之前做XX项目的时候，遇到过XX问题，我是这么解决的"来回答

2. **准备2-3个深度项目**
   - 不要列10个项目（面试官问哪个你都说不清楚）
   - 列2-3个，每个都能讲30分钟（背景、技术选型、踩坑、解决方案、收获）

3. **关注技术趋势**
   - 比如MCP协议（2024年底才出），如果你知道并且用过，加分很多
   - 比如LangGraph vs Workflow的取舍，如果你有真实项目经验，加分很多

---

## 参考资料

1. LangGraph官方文档：https://langchain-ai.github.io/langgraph/
2. MCP协议介绍：https://www.anthropic.com/news/model-context-protocol
3. Agent记忆系统设计：https://blog.langchain.dev/memory-in-agents/
4. RAG vs Fine-tuning：https://www.anthropic.com/research/retrieval-augmented-generation

---

**作者注**：这篇文章的每一个答案，都来自真实的项目踩坑经验。如果你也在准备AI应用开发的面试，希望能帮你少走弯路。如果有问题，欢迎在评论区讨论。

**标签**：#高德面试 #AI应用开发 #LangGraph #MCP #Agent开发 #记忆系统 #RAG