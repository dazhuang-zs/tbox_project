# 数据结构与算法详解：面试不再怕，这篇文章给你完整的知识地图

> **摘要**：数据结构与算法是程序员的基本功，也是大厂面试的硬通货。本文不是罗列知识点，而是帮你建立"看到问题就知道该用什么结构"的直觉。覆盖十大核心数据结构、八大算法范式、大O复杂度速查表，以及面试中最容易被问倒的高阶话题。

---

## 一、为什么你刷了 300 题还是怕面试？

我见过太多人把 LeetCode 当题库背。刷一道会一道，换道新的就不会。

根本原因：**没有建立"问题 → 数据结构 → 算法"的映射直觉。**

这篇文章的目标不是讲完所有算法（那需要一本书），而是帮你建立这个映射。读完你应该做到：看到一个题目描述，3 秒内判断该用什么数据结构，30 秒内确定算法方向。

---

## 二、一张图看懂所有数据结构

```
                     ┌── 线性结构 ──┬── 数组 (Array)
                     │              ├── 链表 (Linked List)
                     │              ├── 栈 (Stack)
                     │              ├── 队列 (Queue)
                     │              └── 哈希表 (Hash Table)
                     │
数据结构 ────────────┼── 树形结构 ──┬── 二叉树 (Binary Tree)
                     │              ├── 二叉搜索树 (BST)
                     │              ├── 平衡树 (AVL/红黑树)
                     │              ├── 堆 (Heap)
                     │              ├── 字典树 (Trie)
                     │              └── 并查集 (Union-Find)
                     │
                     └── 图形结构 ──┬── 有向图/无向图
                                    ├── 加权图
                                    └── DAG (有向无环图)
```

### 每种结构的"一句话本质" + 适用场景

| 数据结构 | 一句话 | 什么时候用 | 时间复杂度 |
|---------|--------|-----------|-----------|
| 数组 | 连续内存，下标O(1)访问 | 需要频繁按索引访问 | 查O(1), 增删O(n) |
| 链表 | 散落内存，指针串联 | 需要频繁增删，不关心索引 | 查O(n), 增删O(1) |
| 栈 | 后进先出 | 括号匹配、DFS、撤销操作 | 入出O(1) |
| 队列 | 先进先出 | BFS、消息队列、滑动窗口 | 入出O(1) |
| 哈希表 | key → value 的魔法 | 去重、计数、缓存 | 均摊O(1) |
| 二叉树 | 每个节点最多两个子节点 | 层级关系、表达式树 | 查O(log n)~O(n) |
| 堆 | 快速拿到最大/最小值 | TopK、优先队列 | 取最值O(1), 插入O(log n) |
| 字典树 | 前缀匹配 | 搜索提示、IP路由 | 查O(k), k=key长度 |
| 并查集 | "这两个元素是一伙的吗" | 连通性判断、朋友圈问题 | 接近O(1) |
| 图 | 节点 + 边 | 网络、地图、依赖关系 | 视算法而定 |

### 核心心法：从场景反推数据结构

```
需要"快速查找"         → 哈希表
需要"最大/最小值"       → 堆
需要"最近相关性"        → 栈
需要"层级/父子关系"     → 树
需要"连通性/分组"       → 并查集
需要"最短路径/拓扑"     → 图
需要"前缀匹配"          → 字典树
需要"滑动窗口/先进先出" → 队列
```

---

## 三、八大算法范式：一张地图走天下

### 1. 双指针 (Two Pointers)
**本质**：用两个指针在数组/链表上移动，将 O(n²) 降到 O(n)。

```python
# 经典：有序数组的两数之和
def twoSum(nums, target):
    left, right = 0, len(nums) - 1
    while left < right:
        s = nums[left] + nums[right]
        if s == target:
            return [left, right]
        elif s < target:
            left += 1
        else:
            right -= 1
```

**适用信号**：有序数组、链表环检测、滑动窗口、原地修改数组

### 2. 二分查找 (Binary Search)
**本质**：每次砍掉一半搜索空间。

```python
# 不只是"在有序数组找值"——二分是一种思想
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = left + (right - left) // 2  # 防溢出
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**进阶**：二分答案（在答案空间上二分，如"最小化最大值"问题）

### 3. 动态规划 (Dynamic Programming)
**本质**：大问题拆成重叠子问题，用记忆化避免重复计算。

**四步法**：
1. 定义 dp[i] 的含义
2. 找状态转移方程
3. 确定初始条件
4. 确定遍历顺序

```python
# 经典：爬楼梯
# dp[i] = dp[i-1] + dp[i-2]
def climbStairs(n):
    if n <= 2: return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b
```

**适用信号**：求"最值""方案数""是否存在"、有明显递推关系

### 4. DFS / BFS（深度/广度优先搜索）
**本质**：DFS 一条路走到黑（栈），BFS 层层扩散（队列）。

```
DFS 适用：找所有路径、排列组合、连通分量
BFS 适用：最短路径（无权图）、层序遍历、扩散问题
```

```python
# BFS 经典模板
from collections import deque
def bfs(start, target):
    queue = deque([start])
    visited = {start}
    step = 0
    while queue:
        size = len(queue)
        for _ in range(size):
            node = queue.popleft()
            if node == target:
                return step
            for neighbor in get_neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        step += 1
    return -1
```

### 5. 回溯 (Backtracking)
**本质**：穷举所有可能性，发现走不通就"回溯"。

```python
# 经典：全排列
def permute(nums):
    res = []
    def backtrack(path, used):
        if len(path) == len(nums):
            res.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]: continue
            used[i] = True
            path.append(nums[i])
            backtrack(path, used)
            path.pop()
            used[i] = False
    backtrack([], [False] * len(nums))
    return res
```

**适用信号**：求"所有组合/排列/子集"、N皇后、数独

### 6. 贪心 (Greedy)
**本质**：每步做局部最优选择，期望得到全局最优。

**⚠️ 最大陷阱**：贪心不一定正确！使用前必须证明"局部最优 = 全局最优"（或用反例证伪）。

```python
# 经典：跳跃游戏
def canJump(nums):
    max_reach = 0
    for i, num in enumerate(nums):
        if i > max_reach:
            return False
        max_reach = max(max_reach, i + num)
    return True
```

### 7. 滑动窗口 (Sliding Window)
**本质**：双指针维护一个区间，O(n) 解决子串/子数组问题。

```python
# 经典：无重复字符的最长子串
def lengthOfLongestSubstring(s):
    window = {}
    left = res = 0
    for right, ch in enumerate(s):
        if ch in window and window[ch] >= left:
            left = window[ch] + 1
        window[ch] = right
        res = max(res, right - left + 1)
    return res
```

**适用信号**：子串、子数组、连续区间

### 8. 前缀和 / 差分
**本质**：用空间换时间，O(1) 查询区间和。

```python
# 前缀和：pre[i] = sum(nums[0..i-1])
# 区间和 [i, j] = pre[j+1] - pre[i]
def subarraySum(nums, k):
    pre_sum = {0: 1}
    cur_sum = count = 0
    for num in nums:
        cur_sum += num
        if cur_sum - k in pre_sum:
            count += pre_sum[cur_sum - k]
        pre_sum[cur_sum] = pre_sum.get(cur_sum, 0) + 1
    return count
```

---

## 四、大 O 复杂度速查表

### 排序算法

| 算法 | 最好 | 平均 | 最坏 | 空间 | 稳定 |
|------|------|------|------|------|------|
| 快排 | O(n log n) | O(n log n) | O(n²) | O(log n) | ❌ |
| 归并 | O(n log n) | O(n log n) | O(n log n) | O(n) | ✅ |
| 堆排 | O(n log n) | O(n log n) | O(n log n) | O(1) | ❌ |
| 冒泡 | O(n) | O(n²) | O(n²) | O(1) | ✅ |
| 计数 | O(n+k) | O(n+k) | O(n+k) | O(k) | ✅ |

### 数据结构操作

| 操作 | 数组 | 链表 | 哈希表 | BST(均) | 堆 |
|------|------|------|--------|---------|-----|
| 查找 | O(1) | O(n) | O(1) | O(log n) | O(n) |
| 插入 | O(n) | O(1) | O(1) | O(log n) | O(log n) |
| 删除 | O(n) | O(1) | O(1) | O(log n) | O(log n) |

---

## 五、面试中最容易被问倒的三个高阶话题

### 1. LRU Cache（哈希表 + 双向链表）

**考点**：结合两种数据结构，O(1) 实现 get 和 put。

```python
class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.cache = {}  # key -> node
        # 哨兵头尾节点
        self.head = Node(0, 0)
        self.tail = Node(0, 0)
        self.head.next = self.tail
        self.tail.prev = self.head
    
    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        node = self.cache[key]
        self._remove(node)
        self._add(node)
        return node.val
```

**原理**：HashMap 负责 O(1) 查找，双向链表负责 O(1) 维护访问顺序。

### 2. 拓扑排序（Kahn 算法）

**考点**：BFS + 入度数组，判断有向图是否有环。

```python
from collections import deque
def topological_sort(n, edges):
    indegree = [0] * n
    graph = [[] for _ in range(n)]
    for u, v in edges:
        graph[u].append(v)
        indegree[v] += 1
    
    queue = deque([i for i in range(n) if indegree[i] == 0])
    result = []
    while queue:
        u = queue.popleft()
        result.append(u)
        for v in graph[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    return result if len(result) == n else []  # 有环返空
```

### 3. 单调栈 (Monotonic Stack)

**考点**：O(n) 解决"下一个更大元素"类问题。

```python
# 下一个更大元素
def nextGreaterElement(nums):
    res = [-1] * len(nums)
    stack = []  # 存下标，栈内单调递减
    for i in range(len(nums)):
        while stack and nums[stack[-1]] < nums[i]:
            res[stack.pop()] = nums[i]
        stack.append(i)
    return res
```

---

## 六、刷题路线建议

不要从 1 刷到 300。按**算法范式**分类刷，每次集中突破一种思想：

```
Week 1-2: 双指针 + 滑动窗口 (15题)
Week 3-4: 二分查找 + 排序 (12题)
Week 5-6: DFS + BFS (15题)
Week 7-8: 动态规划 (20题，先做简单的)
Week 9:   回溯 (10题)
Week 10:  贪心 + 哈希表 (10题)
Week 11:  栈/队列/单调栈 (10题)
Week 12:  图算法 (10题)
```

每类刷完后，随机混刷 5 题检验。

---

> **总结**：数据结构是容器，算法是操作容器的方法。建立"问题→结构→算法"的映射直觉，比刷 500 题更重要。记住：面试官不关心你背了多少题，他关心你拿到一道没见过的题，能不能在 5 分钟内找到正确的方向。

> 你在面试中被问过最难的算法题是什么？评论区见。
