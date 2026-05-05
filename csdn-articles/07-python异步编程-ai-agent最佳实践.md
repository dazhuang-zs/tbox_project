# Python异步编程在AI Agent中的最佳实践：asyncio + 并发API调用的坑与解

> **摘要**：AI Agent的本质是"同时做多件事"——并行调用多个工具、并发请求多个LLM、一边流式输出一边处理结果。但大多数Agent代码还在用同步阻塞写法，一个LLM调用等3秒，5个串行就是15秒。本文不讲asyncio基础概念，直接聚焦AI Agent场景中的6个高频异步模式：并发LLM调用、工具并行执行、流式处理管道、信号量限流、超时熔断、混合同步异步——每个都给出可复制粘贴的生产级代码。

---

## 一、先感受一下差距：同步 vs 异步

假设你的Agent收到用户请求后需要做3件事：调用GPT-4分析意图、查询向量数据库检索文档、调用天气API获取实时数据。

**同步写法（串行，总耗时 = 3个任务之和）：**

```python
import time

def agent_run_sync(user_query: str):
    start = time.time()
    
    # 任务1：GPT-4分析意图 - 耗时2.1秒
    intent = call_gpt4(user_query)        # 2.1s
    
    # 任务2：向量检索 - 耗时0.4秒
    docs = search_vector_db(user_query)   # 0.4s
    
    # 任务3：天气API - 耗时0.8秒
    weather = get_weather("北京")         # 0.8s
    
    total = time.time() - start
    print(f"同步完成，耗时: {total:.2f}s")  # 3.3s
    return {"intent": intent, "docs": docs, "weather": weather}
```

**异步写法（并发，总耗时 = 最慢那个任务）：**

```python
import asyncio

async def agent_run_async(user_query: str):
    start = time.time()
    
    # 三个任务同时启动！
    intent_task = asyncio.create_task(call_gpt4_async(user_query))
    docs_task = asyncio.create_task(search_vector_db_async(user_query))
    weather_task = asyncio.create_task(get_weather_async("北京"))
    
    # 等待全部完成
    intent, docs, weather = await asyncio.gather(
        intent_task, docs_task, weather_task
    )
    
    total = time.time() - start
    print(f"异步完成，耗时: {total:.2f}s")  # 2.1s（最慢的GPT-4）
    return {"intent": intent, "docs": docs, "weather": weather}
```

**差距：3.3s → 2.1s，快了36%。如果你的Agent每次要做8个任务，差距会拉到5-8倍。**

---

## 二、模式1：并发LLM调用——一个请求同时问多个模型」

这是AI Agent最最常见的场景。你要么在对比不同模型的输出，要么在把一个复杂任务拆成多个子任务并行执行。

### 2.1 基础版：asyncio.gather 并发

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="your-key")

async def ask_llm(prompt: str, model: str = "gpt-4o-mini") -> str:
    """异步调用LLM"""
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content


async def multi_model_analysis(user_input: str):
    """
    同一个问题同时问三个模型，取综合结果
    """
    tasks = [
        ask_llm(f"从技术角度分析：{user_input}", "gpt-4o"),
        ask_llm(f"从商业角度分析：{user_input}", "claude-3-5-sonnet-20241022"),
        ask_llm(f"从用户体验角度分析：{user_input}", "gpt-4o-mini"),
    ]
    
    # gather 并发执行，任一失败则全部抛异常
    results = await asyncio.gather(*tasks)
    
    return {
        "tech_view": results[0],
        "business_view": results[1],
        "ux_view": results[2]
    }
```

### 2.2 进阶版：asyncio.gather 的部分失败处理

```python
async def multi_model_robust(user_input: str):
    """
    gather的return_exceptions参数：某个任务失败不影响其他
    """
    tasks = [
        ask_llm(f"分析：{user_input}", "gpt-4o"),
        ask_llm(f"分析：{user_input}", "gpt-4o-mini"),
        ask_llm(f"分析：{user_input}", "maybe-offline-model"),
    ]
    
    # return_exceptions=True → 失败的返回Exception对象，不抛异常
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    output = {}
    model_names = ["gpt-4o", "gpt-4o-mini", "offline-model"]
    
    for name, result in zip(model_names, results):
        if isinstance(result, Exception):
            output[name] = f"调用失败: {result}"
        else:
            output[name] = result
    
    return output
```

---

## 三、模式2：工具并行执行——Agent最核心的加速场景

一个典型的ReAct Agent每一步都可能同时调用多个工具。比如用户说"帮我查一下北京的天气和今天的科技新闻"，Agent应该同时调天气API和新闻API。

```python
import aiohttp

class AsyncToolExecutor:
    """异步工具执行器"""
    
    def __init__(self):
        self.tools = {}
        self._register_tools()
    
    def _register_tools(self):
        """注册工具"""
        self.tools = {
            "search_web": self.search_web,
            "get_weather": self.get_weather,
            "run_code": self.run_code,
            "query_database": self.query_database,
        }
    
    async def execute_parallel(self, tool_calls: list[dict]) -> list[dict]:
        """
        并行执行一组工具调用
        
        Args:
            tool_calls: [{"name": "get_weather", "args": {"city": "北京"}}, ...]
        
        Returns:
            [{"name": "get_weather", "result": "晴天, 25°C"}, ...]
        """
        tasks = []
        
        for call in tool_calls:
            tool_name = call["name"]
            tool_args = call.get("args", {})
            
            if tool_name in self.tools:
                task = asyncio.create_task(
                    self._execute_tool(tool_name, tool_args)
                )
                tasks.append(task)
        
        # 并发执行所有工具
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 组装结果
        output = []
        for i, result in enumerate(results):
            call = tool_calls[i]
            if isinstance(result, Exception):
                output.append({
                    "name": call["name"],
                    "result": f"工具执行失败: {str(result)}"
                })
            else:
                output.append({
                    "name": call["name"],
                    "result": result
                })
        
        return output
    
    async def _execute_tool(self, name: str, args: dict):
        """执行单个工具并计时"""
        func = self.tools[name]
        return await func(**args)
    
    async def search_web(self, query: str) -> str:
        await asyncio.sleep(0.5)  # 模拟网络请求
        return f"搜索结果: 关于'{query}'的3条相关信息"
    
    async def get_weather(self, city: str) -> str:
        await asyncio.sleep(0.8)  # 模拟API调用
        return f"{city}: 晴, 25°C, 湿度60%"
    
    async def run_code(self, code: str) -> str:
        await asyncio.sleep(0.3)
        return f"代码执行成功, 输出: [1, 2, 3, 4, 5]"
    
    async def query_database(self, sql: str) -> str:
        await asyncio.sleep(0.2)
        return "查询结果: 42条记录"


# === 使用示例 ===
async def agent_tool_call_demo():
    executor = AsyncToolExecutor()
    
    tool_calls = [
        {"name": "get_weather", "args": {"city": "北京"}},
        {"name": "search_web", "args": {"query": "2026年AI趋势"}},
        {"name": "query_database", "args": {"sql": "SELECT * FROM users LIMIT 10"}},
    ]
    
    start = time.time()
    results = await executor.execute_parallel(tool_calls)
    elapsed = time.time() - start
    
    print(f"并行执行{len(tool_calls)}个工具，耗时: {elapsed:.2f}s")
    # 串行: 0.8+0.5+0.2=1.5s → 并行: 0.8s（最慢的那个）
    
    for r in results:
        print(f"  {r['name']}: {r['result'][:50]}...")
```

---

## 四、模式3：流式处理管道——边生成边处理

Agent输出可以很长。与其等全部生成完再处理，不如用流式管道：LLM一边输出 → 一边解析 → 一边执行。

```python
async def streaming_agent_pipeline(user_prompt: str):
    """
    流式管道：LLM流式输出 → 实时解析工具调用 → 异步执行工具
    """
    # 用 AsyncOpenAI 的流式API
    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": user_prompt}],
        stream=True,
        tool_choice="auto",
        tools=[...]  # 你的工具定义
    )
    
    tool_calls_buffer = {}
    text_buffer = ""
    
    async for chunk in stream:
        delta = chunk.choices[0].delta
        
        # 处理文本输出（流式显示给用户）
        if delta.content:
            text_buffer += delta.content
            print(delta.content, end="", flush=True)
        
        # 处理工具调用（边收边攒）
        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_buffer:
                    tool_calls_buffer[idx] = {
                        "id": tc.id or "",
                        "function": {"name": "", "arguments": ""}
                    }
                
                if tc.id:
                    tool_calls_buffer[idx]["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tool_calls_buffer[idx]["function"]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments
    
    print()  # 换行
    
    # 流式输出结束，检查是否有工具需要执行
    if tool_calls_buffer:
        print(f"\n🔧 检测到{len(tool_calls_buffer)}个工具调用，开始并行执行...")
        
        executor = AsyncToolExecutor()
        
        # 转为标准格式
        tool_calls = []
        for tc in tool_calls_buffer.values():
            import json
            tool_calls.append({
                "name": tc["function"]["name"],
                "args": json.loads(tc["function"]["arguments"])
            })
        
        results = await executor.execute_parallel(tool_calls)
        return {"text": text_buffer, "tool_results": results}
    
    return {"text": text_buffer, "tool_results": []}
```

---

## 五、模式4 & 5：信号量限流 + 超时熔断（生产必装）

生产环境的两个保命技能：

### 5.1 信号量并发控制——别把API打爆

```python
class RateLimitedLLM:
    """
    带并发限制的LLM调用器
    
    两个维度的限流：
    1. 并发数限制（Semaphore）：同时最多N个请求
    2. 速率限制（Token Bucket）：每秒最多M个请求
    """
    
    def __init__(self, 
                 max_concurrent: int = 5,
                 max_per_second: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = asyncio.Semaphore(max_per_second)
        self._refill_task = None
    
    async def call(self, prompt: str, model: str = "gpt-4o-mini") -> str:
        """带限流的LLM调用"""
        # 第一道闸：并发控制
        async with self.semaphore:
            # 第二道闸：速率控制
            async with self.rate_limiter:
                result = await ask_llm(prompt, model)
            
            # 速率限制：1秒后释放一个槽位
            asyncio.create_task(self._release_rate_limit())
        
        return result
    
    async def _release_rate_limit(self):
        """延迟释放速率限制槽位"""
        await asyncio.sleep(1.0)
        self.rate_limiter.release()
    
    async def batch_call(self, prompts: list[str], model: str = "gpt-4o-mini") -> list[str]:
        """
        批量调用，自动控制并发
        
        即使有100个prompt，同时最多只有max_concurrent个在跑
        """
        tasks = [self.call(p, model) for p in prompts]
        return await asyncio.gather(*tasks, return_exceptions=True)


# === 使用示例：100个请求，最多5个并发 ===
async def batch_demo():
    limiter = RateLimitedLLM(max_concurrent=5, max_per_second=10)
    
    prompts = [f"用一句话总结第{i}个话题" for i in range(20)]
    
    start = time.time()
    results = await limiter.batch_call(prompts)
    elapsed = time.time() - start
    
    success = sum(1 for r in results if not isinstance(r, Exception))
    print(f"20个请求完成: {success}成功, 耗时{elapsed:.2f}s")
```

### 5.2 超时熔断——别让一个慢任务拖垮整个Agent

```python
class ResilientAgent:
    """带超时和重试的Agent执行器"""
    
    @staticmethod
    async def call_with_timeout(coro, timeout: float = 10.0, 
                                 task_name: str = "unknown"):
        """
        带超时的异步调用
        
        超时 ≠ 失败。超时返回降级结果，不抛异常。
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            print(f"⚠️ [{task_name}] 超时({timeout}s)，返回降级结果")
            return f"[{task_name} 超时，使用默认结果]"
    
    @staticmethod
    async def call_with_retry(coro_factory, max_retries: int = 3,
                               base_delay: float = 1.0,
                               task_name: str = "unknown"):
        """
        带指数退避重试的调用
        
        coro_factory: 一个返回coroutine的可调用对象（每次重试创建新的coroutine）
        """
        for attempt in range(max_retries):
            try:
                return await coro_factory()
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ [{task_name}] 重试{max_retries}次后仍失败: {e}")
                    raise
                
                delay = base_delay * (2 ** attempt)  # 指数退避: 1s, 2s, 4s
                print(f"🔄 [{task_name}] 第{attempt+1}次失败，{delay}s后重试: {e}")
                await asyncio.sleep(delay)
    
    async def execute_agent_step(self, tool_calls: list[dict], 
                                  timeout: float = 15.0) -> list[dict]:
        """
        执行Agent的一步：并行调工具 + 超时保护 + 熔断降级
        """
        executor = AsyncToolExecutor()
        
        async def execute_with_protection(tool_call):
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            
            # 超时 + 重试 组合
            try:
                result = await self.call_with_timeout(
                    self.call_with_retry(
                        lambda: executor._execute_tool(tool_name, tool_args),
                        max_retries=2,
                        task_name=tool_name
                    ),
                    timeout=timeout,
                    task_name=tool_name
                )
                return {"name": tool_name, "result": result, "status": "ok"}
            except Exception as e:
                return {"name": tool_name, "result": f"熔断: {e}", "status": "error"}
        
        tasks = [execute_with_protection(tc) for tc in tool_calls]
        return await asyncio.gather(*tasks)


# === 使用示例 ===
async def resilient_demo():
    agent = ResilientAgent()
    
    tool_calls = [
        {"name": "get_weather", "args": {"city": "北京"}},
        {"name": "search_web", "args": {"query": "最新AI新闻"}},
    ]
    
    results = await agent.execute_agent_step(tool_calls, timeout=5.0)
    for r in results:
        print(f"  [{r['status']}] {r['name']}: {r['result'][:60]}")
```

---

## 六、模式6：混合同步异步——处理无法异步化的代码

不是所有代码都能async。比如某些数据库驱动、文件操作、CPU密集型计算。

```python
import concurrent.futures

class HybridAgent:
    """
    混合同步/异步Agent执行器
    
    场景：
    - LLM调用 → 异步（网络IO）
    - 向量DB → 可能只有同步客户端
    - 文件解析 → CPU密集型（同步）
    - 代码执行 → 必须在子进程中（安全隔离）
    """
    
    def __init__(self):
        # 线程池：处理阻塞IO（数据库、文件）
        self.io_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        # 进程池：处理CPU密集型（代码执行、大文件解析）
        self.cpu_pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)
    
    async def execute_step(self, tasks: list[dict]) -> list:
        """执行一个混合步骤"""
        async_tasks = []
        
        for task in tasks:
            task_type = task.get("type", "io")
            
            if task_type == "async":
                # 原生异步任务，直接create_task
                async_tasks.append(asyncio.create_task(
                    ask_llm(task["prompt"])
                ))
            
            elif task_type == "blocking_io":
                # 阻塞IO → 扔到线程池
                async_tasks.append(asyncio.get_event_loop().run_in_executor(
                    self.io_pool,
                    task["func"],
                    *task.get("args", [])
                ))
            
            elif task_type == "cpu_intensive":
                # CPU密集型 → 扔到进程池
                async_tasks.append(asyncio.get_event_loop().run_in_executor(
                    self.cpu_pool,
                    task["func"],
                    *task.get("args", [])
                ))
        
        return await asyncio.gather(*async_tasks, return_exceptions=True)
    
    def shutdown(self):
        """清理资源（重要！）"""
        self.io_pool.shutdown(wait=True)
        self.cpu_pool.shutdown(wait=True)


# === 使用示例 ===
def heavy_computation(n: int) -> int:
    """CPU密集型计算（不能在async中直接调用）"""
    total = 0
    for i in range(n * 1000000):
        total += i
    return total % 1000000

async def hybrid_demo():
    agent = HybridAgent()
    
    tasks = [
        {"type": "async", "prompt": "总结今天的新闻"},
        {"type": "blocking_io", "func": time.sleep, "args": [1.0]},
        {"type": "cpu_intensive", "func": heavy_computation, "args": [10]},
    ]
    
    start = time.time()
    results = await agent.execute_step(tasks)
    elapsed = time.time() - start
    
    print(f"混合任务完成，耗时: {elapsed:.2f}s")
    # 三者并发，总耗时 ≈ max(LLM延迟, sleep时间, CPU计算时间)
    
    agent.shutdown()
```

---

## 七、7个常见坑及解决方案（每个都踩过）

### 坑1：在async函数里调同步HTTP库

```python
# ❌ 错误：在async中调用requests（阻塞事件循环！）
async def bad_agent():
    import requests
    resp = requests.get("https://api.example.com")  # 阻塞整个事件循环！
    return resp.json()

# ✅ 正确：用aiohttp或httpx的async客户端
async def good_agent():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com") as resp:
            return await resp.json()
```

### 坑2：忘了await，协程没有执行

```python
# ❌ 错误：task是coroutine对象，没有执行！
task = ask_llm("hello")  # <coroutine object> — 没有await！
print(task)  # 打印的是coroutine对象，不是结果

# ✅ 正确方式：
task = asyncio.create_task(ask_llm("hello"))  # 后台执行
result = await task  # 等待结果

# 或者直接await
result = await ask_llm("hello")
```

### 坑3：gather中一个失败全失败

```python
# ❌ 一个任务抛异常，整个gather中断，其他任务结果全丢
results = await asyncio.gather(task1, task2, task3)

# ✅ 设置return_exceptions=True
results = await asyncio.gather(task1, task2, task3, return_exceptions=True)
# 成功的是正常返回值，失败的是Exception对象
```

### 坑4：在Jupyter/已有事件循环的环境中用asyncio.run()

```python
# ❌ Jupyter中asyncio.run()报错：Event loop is already running
asyncio.run(my_async_func())

# ✅ Jupyter或FastAPI等环境中直接用await
await my_async_func()  # 在已有的事件循环中
```

### 坑5：创建了Task但没有保持引用

```python
# ❌ task被垃圾回收，可能不会执行完
asyncio.create_task(background_cleanup())  # 没有保存引用！

# ✅ 保存引用
background_tasks = set()
task = asyncio.create_task(background_cleanup())
background_tasks.add(task)
task.add_done_callback(background_tasks.discard)  # 完成后自动移除
```

### 坑6：大量并发请求没有限流，被API限频

```python
# ❌ 1000个请求同时发出 → API直接返回429 Too Many Requests
tasks = [ask_llm(p) for p in prompts]
results = await asyncio.gather(*tasks)

# ✅ 用Semaphore分批
sem = asyncio.Semaphore(10)  # 最多10个并发
async def limited_call(prompt):
    async with sem:
        return await ask_llm(prompt)

results = await asyncio.gather(*[limited_call(p) for p in prompts])
```

### 坑7：进程池忘记shutdown

```python
# ❌ 进程池没关，子进程泄漏
pool = concurrent.futures.ProcessPoolExecutor()

# ✅ 用async with自动清理（Python 3.9+不支持，手动管理）
try:
    pool = concurrent.futures.ProcessPoolExecutor()
    # ... 使用
finally:
    pool.shutdown(wait=True)  # 必须调用！
```

---

## 八、最佳实践速查表

| 场景 | 推荐方案 | 关键参数 |
|------|---------|---------|
| 多个LLM并行调用 | `asyncio.gather` + `return_exceptions=True` | - |
| 工具并行执行 | `AsyncToolExecutor` | - |
| 控制API并发数 | `asyncio.Semaphore` | 设置为API限制的80% |
| 避免慢任务拖垮 | `asyncio.wait_for` | timeout=最慢可接受时长 |
| 临时故障重试 | 指数退避 | base_delay=1s, max_retries=3 |
| 流式输出+处理 | `AsyncOpenAI` stream | - |
| 阻塞IO操作 | `run_in_executor` + ThreadPool | max_workers=4-8 |
| CPU密集型操作 | `run_in_executor` + ProcessPool | max_workers=CPU核心数 |
| 后台任务 | `create_task` + 保存引用 | - |
| 批量API调用 | Semaphore + gather | max_concurrent=5-10 |

---

## 九、一个开箱即用的生产级Agent异步框架

把所有模式粘成一套：

```python
class AsyncAgent:
    """
    生产级异步Agent框架
    
    特性：
    - 并发工具执行
    - 并发LLM调用
    - 速率限制
    - 超时熔断
    - 流式输出
    - 混合同步/异步
    """
    
    def __init__(self, 
                 max_concurrent_llm: int = 5,
                 max_concurrent_tools: int = 10,
                 tool_timeout: float = 15.0,
                 llm_timeout: float = 30.0):
        
        self.llm_semaphore = asyncio.Semaphore(max_concurrent_llm)
        self.tool_semaphore = asyncio.Semaphore(max_concurrent_tools)
        self.tool_timeout = tool_timeout
        self.llm_timeout = llm_timeout
        self.tool_executor = AsyncToolExecutor()
        self._bg_tasks = set()
    
    async def run(self, user_input: str) -> dict:
        """Agent主入口"""
        # Step 1: 并发分析意图 + 检索上下文
        intent, context = await asyncio.gather(
            self._analyze_intent(user_input),
            self._retrieve_context(user_input),
            return_exceptions=True
        )
        
        # Step 2: 组装prompt并流式生成
        prompt = self._build_prompt(user_input, intent, context)
        response = await self._generate_response(prompt)
        
        # Step 3: 如果需要工具调用，并行执行
        if response.get("tool_calls"):
            tool_results = await self._execute_tools(response["tool_calls"])
            response["tool_results"] = tool_results
        
        return response
    
    async def _analyze_intent(self, user_input: str):
        async with self.llm_semaphore:
            return await asyncio.wait_for(
                ask_llm(f"分析意图：{user_input}", "gpt-4o-mini"),
                timeout=self.llm_timeout
            )
    
    async def _retrieve_context(self, user_input: str):
        # 模拟向量检索（阻塞IO → run_in_executor）
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,  # 默认线程池
            lambda: f"检索到的相关文档: 关于'{user_input}'的3条记录"
        )
    
    def _build_prompt(self, user_input, intent, context) -> str:
        return f"""用户输入: {user_input}
意图分析: {intent if not isinstance(intent, Exception) else '未知'}
相关上下文: {context if not isinstance(context, Exception) else '无'}
请回答用户的问题。"""
    
    async def _generate_response(self, prompt: str) -> dict:
        async with self.llm_semaphore:
            return {
                "content": await asyncio.wait_for(
                    ask_llm(prompt, "gpt-4o"),
                    timeout=self.llm_timeout
                ),
                "tool_calls": []  # 简化，实际需解析function calling
            }
    
    async def _execute_tools(self, tool_calls: list) -> list:
        async with self.tool_semaphore:
            return await asyncio.wait_for(
                self.tool_executor.execute_parallel(tool_calls),
                timeout=self.tool_timeout
            )
    
    def _add_bg_task(self, coro):
        """安全添加后台任务"""
        task = asyncio.create_task(coro)
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)


# === 一行启动 ===
async def main():
    agent = AsyncAgent(
        max_concurrent_llm=5,
        max_concurrent_tools=10,
        tool_timeout=15.0,
        llm_timeout=30.0
    )
    
    result = await agent.run("帮我分析一下今天的科技新闻")
    print(result["content"])
```

---

> 💡 **三个核心原则**：
> 1. **能并发的绝不串行**——Agent的每一步都可能有多个独立任务，用`gather`把耗时从累加变成取最大值
> 2. **每个await都要想超时**——Agent在生产环境中遇到的最大问题不是代码bug，是外部API超时把整个链路拖死
> 3. **Semaphore是你的好朋友**——不受控的并发 = 给自己和API提供商同时埋雷

**你的Agent代码是同步还是异步的？踩过哪些异步的坑？评论区交流。**
