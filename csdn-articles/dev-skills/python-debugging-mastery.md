# 强烈推荐收藏！Python 调试从入门到精通：pdb、VS Code、远程调试、asyncio——10年经验总结的调试方法论

> 你还用 `print()` 调试吗？每次加一行 print 等半分钟重启、print 太多眼花缭乱、上线前还要删光。本文用 pdb 交互式调试打底，配上 VS Code 可视化断点、远程容器调试、异步代码专用技巧，最后给一个「先猜后证」的调试心法——让你从「打日志找 Bug」进化到「读代码推 Bug」。

---

## 一、pdb：Python 自带的神器，90% 的人只用过 10%

### 1.1 基础命令速查

```python
# 在代码中插入断点
def buggy_function(x, y):
    import pdb; pdb.set_trace()  # 程序跑到这里会暂停
    result = x / y  # 想检查 x 和 y 的值
    return result

# 或者 Python 3.7+ 的简洁写法
def buggy_function(x, y):
    breakpoint()  # 等效于上面，但更简洁
    result = x / y
    return result
```

进入 pdb 后的常用命令：

| 命令 | 简写 | 作用 |
|------|:--:|------|
| `next` | `n` | 执行下一行（不进入函数） |
| `step` | `s` | 进入函数内部 |
| `continue` | `c` | 继续执行到下一个断点 |
| `where` | `w` | 显示当前调用栈 |
| `list` | `l` | 显示当前位置的源码 |
| `print(x)` | `p x` | 打印变量 x 的值 |
| `pp vars(obj)` | `pp` | 美观打印对象属性 |
| `quit` | `q` | 退出调试 |
| `return` | `r` | 执行到当前函数返回 |
| `until 42` | `u 42` | 执行到第 42 行 |
| `args` | `a` | 显示当前函数的参数 |

### 1.2 pdb 实战：调试一个 API 调用

```python
import httpx

async def fetch_user(user_id: int):
    """从 API 获取用户信息——这个函数偶尔返回 None，为什么？"""
    breakpoint()  # 断点 1：检查入参

    async with httpx.AsyncClient() as client:
        url = f"https://api.example.com/users/{user_id}"
        response = await client.get(url, timeout=5)
        
        breakpoint()  # 断点 2：检查响应状态
        # p response.status_code
        # p response.text[:200]
        
        if response.status_code == 200:
            data = response.json()
            breakpoint()  # 断点 3：检查解析后的数据
            # pp data
            # p data.get("name")
            return data
        elif response.status_code == 404:
            return None
        else:
            breakpoint()  # 断点 4：意外的状态码
            # p response.status_code
            # p response.text
            raise Exception(f"Unexpected status: {response.status_code}")
```

**调试流程**：

```python
# 运行时
(Pdb) n          # 先走到 url 那行
(Pdb) p user_id  # 确认 user_id 正确
(Pdb) c          # 继续到下一个断点（response 返回后）

(Pdb) p response.status_code  # 502? 看看为什么
(Pdb) p response.text[:200]   # 打印响应内容
(Pdb) w                       # 看看是谁调用了这个函数
```

### 1.3 条件断点

```python
# 只在特定条件下才暂停
for i in range(1000):
    # 只当 i == 998 时暂停
    if i == 998:
        breakpoint()
    process(i)

# 或者用 pdb 的命令行方式
# python -m pdb script.py
# (Pdb) break 15, i == 998
```

### 1.4 事后调试：post-mortem

```python
# 程序崩溃后，自动进入 pdb 查看崩溃现场
python -m pdb -c continue script.py

# 或者在代码中
import pdb
import traceback
import sys

def main():
    try:
        buggy_function()
    except Exception:
        # 崩溃时自动进入 pdb，查看所有变量的值
        pdb.post_mortem(sys.exc_info()[2])
```

---

## 二、VS Code 可视化调试

### 2.1 配置文件

`.vscode/launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "src.main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ],
            "jinja": true,
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "LOG_LEVEL": "debug"
            },
            "justMyCode": false
        },
        {
            "name": "Python: 当前文件",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

### 2.2 VS Code 断点技巧

| 技巧 | 操作 | 场景 |
|------|------|------|
| 条件断点 | 右键断点 → Edit Breakpoint → Expression | 只在 `i == 998` 时暂停 |
| 日志断点 | 右键断点 → Logpoint | 不暂停，只打印 `"i={i}"` |
| 异常断点 | Debug 面板 → Breakpoints → Raised Exceptions | 任何异常都暂停 |
| 函数断点 | Debug 面板 → + → Function Breakpoint | 断在函数入口 |
| Watch | Debug 面板 → Watch | 实时监控表达式值 |

---

## 三、远程调试：容器里的代码怎么打断点

### 3.1 Docker 内的调试

```dockerfile
# Dockerfile
FROM python:3.12-slim
RUN pip install debugpy
COPY . /app
WORKDIR /app
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "src/main.py"]
```

`.vscode/launch.json` 远程附加：

```json
{
    "name": "Python: Remote Attach",
    "type": "debugpy",
    "request": "attach",
    "connect": {
        "host": "localhost",
        "port": 5678
    },
    "pathMappings": [
        {
            "localRoot": "${workspaceFolder}",
            "remoteRoot": "/app"
        }
    ]
}
```

### 3.2 生产环境应急调试

```bash
# 1. 在正在运行的容器中安装 debugpy
docker exec -it app_container pip install debugpy

# 2. 注入调试器（不重启进程）
docker exec -it app_container python -c "
import debugpy
debugpy.listen(('0.0.0.0', 5678))
print('调试器已激活，请在 VS Code 中附加')
debugpy.wait_for_client()
"

# 3. VS Code 远程附加 → 现在可以打断点了
```

> ⚠️ 紧急情况使用。调试完立刻关闭 `debugpy` 监听端口。

---

## 四、asyncio 异步代码调试

### 4.1 为什么不加断点就跳过

```python
async def fetch_data():
    data = await api_call()  # 加了断点，程序不暂停？
    return data

# 原因：await 被事件循环接管了，pdb 在异步上下文中有盲区
```

### 4.2 asyncio 调试模式

```python
import asyncio

# 开启 asyncio 调试模式
asyncio.run(main(), debug=True)

# 或环境变量
# PYTHONASYNCIODEBUG=1 python main.py
```

开启后能检测到：
- 协程未被 `await`（常见 Bug）
- 事件循环运行时间过长
- 回调执行耗时异常

### 4.3 异步代码的 pdb 实用技巧

```python
async def buggy_async_func():
    breakpoint()
    
    # (Pdb) 模式下查看异步状态
    # p asyncio.all_tasks()      → 查看所有未完成任务
    # p asyncio.current_task()   → 当前任务
    # p task.done()              → 任务是否完成
    # p task.exception()         → 任务是否有异常
```
- 用 `asyncio.all_tasks()` 查看事件循环中所有未完成的任务——排查死锁和未 await 的协程
- 用 `asyncio.get_running_loop().time()` 查看事件循环运行时长
- 用 `task.exception()` 检查异步任务是否有未处理的异常

---

## 五、调试心法：从「试错」到「推理」

### 5.1 调试三步法

```
① 复现 → 找到最小可复现案例
② 二分 → 逐步缩小问题范围（不是逐行读，是二分划分）
③ 假设 → 先猜最可能的原因，再验证（不要无目的地加 print）
```

### 5.2 先猜后证练习

```python
# 这个函数有什么 Bug？先猜，再看答案

def process_orders(orders: list[dict]) -> dict:
    result = {}
    for order in orders:
        result.setdefault(order["status"], 0)
        result[order["status"]] += order["amount"]
    return result

# 输入：[{"status": "paid", "amount": 100}, {"status": "paid", "amount": 50}]
# 期望输出：{"paid": 150}
# 实际输出：{"paid": 100}

# 答案：
# setdefault 只在 key 不存在时设置默认值
# 第二个 order 时 "paid" 已存在，setdefault 不执行 → 累加正确但初始值没重置
# 修复：result[order["status"]] = result.get(order["status"], 0) + order["amount"]
```

### 5.3 二分定位法

```python
# 问题：process_pipeline 返回的结果不对，但 200 行代码不知道哪里出了问题

def process_pipeline(data):
    # 二分法：先注释掉后半段
    data = step1(data)
    data = step2(data)
    # data = step3(data)    # 先注释掉
    # data = step4(data)    # 先注释掉
    return data

# → step2 后返回正确 → 问题在 step3 或 step4
# → 恢复 step3，继续测试
# → step3 后返回错误 → 问题在 step3
# → 在 step3 中再二分
```

---

## 六、调试工具扩展

| 工具 | 用途 | 安装 |
|------|------|------|
| **ipdb** | pdb 增强版，语法高亮+Tab补全 | `pip install ipdb` |
| **pudb** | 终端可视调试器，比 pdb 直观 | `pip install pudb` |
| **icecream** | 替代 print，自动打印变量名和值 | `pip install icecream` |
| **loguru** | 生产级日志，一行配置 | `pip install loguru` |
| **snoop** | 追踪每行代码的执行 | `pip install snoop` |
| **birdseye** | 图形化追踪函数执行 | `pip install birdseye` |

---

## 七、总结

| 场景 | 最佳工具 | 一句话 |
|------|------|------|
| 本地单文件 | pdb + breakpoint() | 原生，最快 |
| 日常项目开发 | VS Code 断点 | 可视化，条件断点 |
| 容器/远程 | debugpy 附加 | 不改代码，运行时注入 |
| 异步代码 | asyncio debug 模式 | 检测未 await |
| 生产排查 | loguru 结构化日志 | 不是调试，是事后分析 |
| 快速查看变量 | icecream | `ic(x)` 比 `print(f"x={x}")` 好用 10 倍 |
| 先猜后证 | 二分定位 | 不是逐行读，是推测→验证→缩小 |

> print 不是不能用，而是不应该是你唯一的调试工具。掌握 pdb 交互式调试 + VS Code 条件断点 + 远程 debugpy 附加，你的调试效率能从「猜谜」进化到「推理」。

---

*标签：#Python #调试 #pdb #VSCode #asyncio #程序员必读*