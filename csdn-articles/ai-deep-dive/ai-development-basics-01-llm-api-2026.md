# AI 开发基础（第1章）：LLM API - 一切的起点

> 如果你要学AI应用开发，LLM API是第一章。
> 不是因为你会一直直接调API，而是因为**所有上层封装（LangChain、LangGraph、OpenClaw）最终都落在LLM API调用上**。
> 理解了这一层，上面封装出问题时，你知道去哪里排查。

---

## 一、LLM API 是什么？

### 核心定义

**LLM API = 大语言模型的远程调用接口。**

你给模型发一段文字（prompt），模型返回一段文字（completion）。

**类比**：
- 就像调用一个函数：`response = llm(prompt)`
- 但这个"函数"不在本地，在远程服务器（OpenAI、DeepSeek、智谱...）

### 最小可运行示例

```python
from openai import OpenAI

# 创建客户端（连到OpenAI的服务器）
client = OpenAI(api_key="your-api-key")

# 调用LLM API
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "请用Python写一个快速排序"}
    ]
)

# 提取返回的文字
answer = response.choices[0].message.content
print(answer)
```

**输出**：
```python
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
```

**关键点**：
1. **`model`**：指定用哪个模型（gpt-4o、deepseek-v3、qwen-turbo...）
2. **`messages`**：对话历史（LLM是无状态的，每次都要传完整历史）
3. **`response.choices[0].message.content`**：取返回的文字

---

## 二、为什么需要LLM API？

### 问题背景

**没有LLM API之前**：
- 你要用自己的数据微调一个模型，需要几十张GPU、几个月时间、几百万人民币
- 就算微调完了，推理（生成文字）也需要昂贵的硬件

**有了LLM API之后**：
- 你只需要**调一个HTTP接口**，模型在厂商的服务器上跑
- 你按**Token**付费（比如OpenAI GPT-4o：输入$5/1M tokens，输出$15/1M tokens）
- 不需要自己维护模型、GPU、推理优化

**类比**：
- 没有LLM API = 自己买发电机（贵、麻烦、维护成本高）
- 有LLM API = 用电网的电（按需付费、不需要维护发电机）

---

## 三、LLM API 的核心参数

### 1. `model`：选模型

| 模型 | 优势 | 劣势 | 价格（输入/输出，每1M tokens） |
|------|------|------|-----------------------------|
| **GPT-4o** | 能力强、稳定 | 贵 | $5 / $15 |
| **DeepSeek-V3** | 便宜、中文好 | 偶尔不稳定 | $0.14 / $0.28 |
| **Qwen-Turbo** | 便宜、速度快 | 能力弱于GPT-4o | ¥0.3 / ¥0.9 |
| **Claude 3.5 Sonnet** | 长文档理解好 | 贵 | $3 / $15 |

**真实项目经验**：
- 我做**CSDN文章生成**的时候，用**DeepSeek-V3**（便宜，中文好）
- 需要做**复杂推理**的时候，用**GPT-4o**（能力强）
- 需要**长文档理解**（比如总结几万字的技术文档），用**Claude 3.5 Sonnet**（128K上下文）

### 2. `messages`：对话历史

**LLM是无状态的**：
- 你第一轮问："推荐几本Python书"
- 第二轮问："有没有免费的？"
- LLM不知道你在说"Python书"，因为它不记得第一轮对话

**解决方案**：每次调用API，都要传完整的对话历史

```python
# 第一轮对话
messages = [
    {"role": "user", "content": "推荐几本Python书"}
]
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)
# 假设返回："推荐《Python编程：从入门到实践》..."

# 把第一轮对话加入历史
messages.append({"role": "assistant", "content": "推荐《Python编程：从入门到实践》..."})
# 加上第二轮问题
messages.append({"role": "user", "content": "有没有免费的？"})

# 第二轮调用API（传完整历史）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages  # 现在LLM知道你在说"Python书"
)
```

**关键点**：
- `role: "user"` = 用户说的
- `role: "assistant"` = AI说的
- `role: "system"` = 系统提示词（比如"你是一个Python专家"）

### 3. `temperature`：控制随机性

**取值范围**：0.0 ~ 2.0

| temperature值 | 效果 | 适用场景 |
|--------------|------|----------|
| **0.0** | 完全确定性（每次返回一样） | 需要准确答案（比如写SQL、写代码） |
| **0.7** | 适度随机（推荐值） | 日常对话、内容生成 |
| **1.2** | 高度随机（创意性强） | 写小说、头脑风暴 |

**真实项目经验**：
- 我做**CSDN技术文章生成**的时候，用`temperature=0.7`（适度随机，每篇文章不一样）
- 我做**SQL生成**的时候，用`temperature=0.0`（需要准确，不能乱写）

```python
# 写技术文章：适度随机
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的文章"}],
    temperature=0.7  # 每篇文章会不一样
)

# 生成SQL：完全确定
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "生成查询用户表的SQL"}],
    temperature=0.0  # 每次都生成一样的SQL
)
```

### 4. `max_tokens`：控制输出长度

**作用**：限制LLM最多生成多少个token（≈0.75个汉字）

**真实踩坑**：
- 我不设置`max_tokens`，LLM生成了一篇5000字文章（消耗了约2000个tokens，输出成本$0.03）
- 如果设置`max_tokens=500`，LLM生成到500个tokens就自动停止（输出成本$0.0075）

**成本优化经验**：
```python
# 不设置max_tokens（可能生成很长，成本高）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的文章"}]
)
# 可能生成5000字，输出成本$0.03

# 设置max_tokens=1000（控制长度，降低成本）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的文章"}],
    max_tokens=1000  # 最多生成1000个tokens（≈750字）
)
# 输出成本$0.015（省一半）
```

### 5. `stream`：流式输出

**问题**：LLM生成文字是逐词生成的，但默认要等全部生成完才返回。

**体验差异**：
- 不用流式：你问一个问题，等3秒，然后一次性看到全部回答
- 用流式：你问一个问题，马上看到文字一个一个蹦出来（像ChatGPT的体验）

**代码实现**：
```python
# 不用流式（等全部生成完才返回）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的文章"}]
)
print(response.choices[0].message.content)  # 3秒后一次性打印

# 用流式（一个一个token返回）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的文章"}],
    stream=True  # 开启流式
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")  # 一个一个字打印
```

**真实项目经验**：
- 我做**Web应用**的时候，必须用流式（用户体验好）
- 我做**后台批处理**（比如生成1000篇CSDN文章），不用流式（简化代码）

---

## 四、LLM API 的错误处理

### 常见错误

| 错误类型 | 原因 | 解决方案 |
|----------|------|----------|
| **RateLimitError** | 请求太快，超过限额 | 加重试、降速 |
| **APIConnectionError** | 网络问题 | 重试 |
| **InvalidRequestError** | 参数错误（比如`model`名字写错） | 检查参数 |
| **InternalServerError** | 服务端错误 | 重试 |

### 重试策略（重要）

**真实踩坑**：
- 我一开始不加重试，生产环境跑着跑着就挂了（网络抖动、API限流）
- 后来加了重试，稳定性提升90%

**代码实现（用tenacity库）**：
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError, APIConnectionError

@retry(
    stop=stop_after_attempt(3),  # 最多重试3次
    wait=wait_exponential(multiplier=1, min=4, max=10),  # 指数退避（等4秒、8秒、16秒...）
    retry=retry_if_exception_type((RateLimitError, APIConnectionError))  # 只对这两种错误重试
)
def call_llm(messages):
    """调用LLM API，自动重试"""
    return client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

# 使用示例
try:
    response = call_llm([{"role": "user", "content": "写一篇文章"}])
    print(response.choices[0].message.content)
except Exception as e:
    print(f"重试3次都失败了：{e}")
```

**关键点**：
1. **指数退避**：第一次重试等4秒，第二次等8秒，第三次等16秒（避免重试风暴）
2. **只对特定错误重试**：`RateLimitError`和`APIConnectionError`值得重试，`InvalidRequestError`（参数错误）重试也没用
3. **设置最大重试次数**：不能无限重试（比如网络断了，重试100次也没用）

---

## 五、LLM API 的成本优化

### 成本结构

**LLM API按Token收费**：
- **输入Token**：你发给模型的文字（prompt）
- **输出Token**：模型返回的文字（completion）
- **价格**：输出Token通常比输入Token贵3倍（因为生成比理解更耗算力）

**举例（OpenAI GPT-4o）**：
- 输入：$5/1M tokens
- 输出：$15/1M tokens
- 如果你发1000字（≈750 tokens）给模型，模型返回500字（≈375 tokens）
- 成本：$(750/1M * $5) + $(375/1M * $15) = $0.00375 + $0.005625 = $0.009375

### 优化策略

**策略1：压缩prompt（减少输入Token）**

**坏例子**（冗长）：
```
你是一个Python专家，有10年开发经验，擅长FastAPI、Django、Flask。
请写一篇关于FastAPI的文章，要求：
1. 面向初学者
2. 包含代码示例
3. 字数在2000字左右
...
```

**好例子**（简洁）：
```
写FastAPI入门文章，含代码示例，2000字。
```

**效果**：输入Token从200个减少到50个，成本降低75%。

**策略2：用便宜模型做简单任务**

**坏例子**（浪费）：
```python
# 用GPT-4o做简单的文本分类（成本高）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "这段文字是正面还是负面？{text}"}]
)
```

**好例子**（省钱）：
```python
# 用DeepSeek-V3做文本分类（成本降低95%）
client = OpenAI(base_url="https://api.deepseek.com", api_key="your-deepseek-key")
response = client.chat.completions.create(
    model="deepseek-v3",
    messages=[{"role": "user", "content": "这段文字是正面还是负面？{text}"}]
)
```

**成本对比**：
- GPT-4o：输入$5/1M tokens，输出$15/1M tokens
- DeepSeek-V3：输入$0.14/1M tokens，输出$0.28/1M tokens
- **成本降低95%**

**策略3：缓存重复prompt（减少输入Token）**

**问题场景**：
- 你做RAG，每次都要把"系统提示词"+"检索到的文档"+"用户问题"拼成prompt
- 如果"系统提示词"很长（比如500字），每次都要算输入Token

**解决方案（OpenAI支持Prompt Caching）**：
```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是一个Python专家..."},  # 500字系统提示词
        {"role": "user", "content": "如何安装FastAPI？"}
    ],
    extra_body={"cache_control": {"type": "ephemeral"}}  # 缓存系统提示词
)
```

**效果**：
- 第一次调用：正常计费（500字系统提示词 + 用户问题）
- 后续调用：系统提示词部分**免费**（从缓存读取）

---

## 六、LLM API 的进阶用法

### 1. Function Calling（函数调用）

**问题**：LLM只能生成文字，不能直接调用外部工具（比如查数据库、调API）。

**解决方案**：Function Calling = 让LLM生成"调用哪个函数+参数"，然后你来执行函数。

**完整流程**：
```
1. 你定义可用函数（JSON Schema格式）
2. 你把函数和用户输入发给LLM
3. LLM决定调用哪个函数，生成调用参数
4. 你执行函数，拿到结果
5. 你把函数结果发给LLM
6. LLM根据函数结果，生成最终回答
```

**示例**：
```python
# 第一步：定义可用函数
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
    }
]

# 第二步：把函数和用户输入发给LLM
messages = [{"role": "user", "content": "上海天气怎么样？"}]
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools  # 告诉LLM有哪些函数可用
)

# 第三步：LLM决定调用get_weather函数，生成参数
tool_call = response.choices[0].message.tool_calls[0]
function_name = tool_call.function.name  # "get_weather"
function_args = json.loads(tool_call.function.arguments)  # {"city": "上海"}

# 第四步：你执行函数
weather = get_weather(function_args["city"])  # 调用真实函数

# 第五步：把函数结果发给LLM
messages.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": weather})

# 第六步：LLM根据函数结果，生成最终回答
final_response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)
print(final_response.choices[0].message.content)
# 输出："上海今天天气晴，温度25°C，适合外出。"
```

**真实项目经验**：
- 我做**智能行程规划**的时候，用了5个函数（查天气、查POI、查门票、查路线、查评价）
- Function Calling让LLM能"操作真实世界"，而不只是"说说而已"

### 2. Batch API（批量调用）

**问题**：你要生成1000篇CSDN文章，每篇都要调一次LLM API，串行调用要跑好几个小时。

**解决方案**：Batch API = 一次性发100个请求，API异步处理，成本低50%。

**代码实现**：
```python
# 准备100个请求
requests = []
for topic in ["FastAPI", "Django", "Flask", ...]:  # 100个主题
    requests.append({
        "custom_id": f"request-{topic}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": f"写一篇关于{topic}的文章"}]
        }
    })

# 发送到Batch API
batch = client.batches.create(
    input_file_id=upload_file(requests),  # 上传请求文件
    endpoint="/v1/chat/completions",
    completion_window="24h"  # 24小时内完成
)

# 等待完成（轮询）
while True:
    batch_status = client.batches.retrieve(batch.id)
    if batch_status.status == "completed":
        break
    time.sleep(60)

# 下载结果
results = download_file(batch_status.output_file_id)
for result in results:
    print(result["response"]["body"]["choices"][0]["message"]["content"])
```

**成本优势**：
- 普通API：$5/1M input tokens
- Batch API：$2.5/1M input tokens（便宜50%）

---

## 七、本章总结

**你学到了什么**：

1. **LLM API是什么**：远程调用大语言模型的接口，按Token付费
2. **核心参数**：`model`（选模型）、`messages`（对话历史）、`temperature`（随机性）、`max_tokens`（输出长度）、`stream`（流式输出）
3. **错误处理**：加重试（tenacity库），只对网络错误和限流错误重试
4. **成本优化**：压缩prompt、用便宜模型做简单任务、缓存重复prompt
5. **进阶用法**：Function Calling（让LLM调用外部工具）、Batch API（批量调用，成本低50%）

**下一步**：
- 第2章：KV Cache - 理解推理性能的关键
- 你会学到：为什么第二次问同样的问题，LLM推理速度快很多？

---

## 参考资料

1. OpenAI API文档：https://platform.openai.com/docs/api-reference
2. DeepSeek API文档：https://platform.deepseek.com/docs
3. Tenacity重试库：https://github.com/jd/tenacity
4. OpenAI Batch API：https://platform.openai.com/docs/guides/batch

---

**作者注**：这一章是所有AI应用开发的基础。理解LLM API，后面的LangChain、LangGraph、Agent，都是在这一层上面封装的。如果你在调试Agent问题，经常要回到这一层看原始API调用。

**下一篇**：KV Cache - 理解推理性能的关键（为什么LLM推理这么慢？怎么优化？）
