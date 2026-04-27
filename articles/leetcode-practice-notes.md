# LeetCode 刷题笔记：从 0 到 300 题，我的 12 周进化路线

> **摘要**：刷了 300 道 LeetCode 后回头看，最高效的方式不是按题号顺序刷，而是按"算法范式"分类突破。本文分享一套经过验证的 12 周刷题路线、每类题目的解题模板、面试高频 Top 50 题清单，以及最容易踩的 5 个坑。

---

## 一、我走过的弯路

刚开始刷题时，我的策略是：打开 LeetCode → 按题号顺序 → 从 Two Sum 开始。

刷到第 50 题时，我发现一个致命问题：**昨天刚做的滑动窗口，今天换个题又不会了。**

后来改变策略：不按题号刷，按**算法思想分类刷**。一个周末只做双指针，做到"看到题目就知道是不是双指针题"为止。

效率提升了至少 3 倍。

核心原因很简单：**大脑学习模式是"找规律"，不是"记题目"。** 当你连续做 10 道双指针题，你的大脑会自然提炼出"什么题用双指针"的模式识别能力。

---

## 二、12 周刷题路线

### Week 1-2：双指针 & 滑动窗口（~15 题）

**核心模板——滑动窗口**

```python
def sliding_window(s):
    window = {}  # 窗口内元素计数
    left = right = 0
    res = 0
    
    while right < len(s):
        c = s[right]
        window[c] = window.get(c, 0) + 1
        right += 1
        
        # 窗口不满足条件时收缩
        while 需要收缩:
            d = s[left]
            window[d] -= 1
            left += 1
        
        # 更新结果
        res = max(res, right - left)
    
    return res
```

**练习清单**：3, 11, 15, 16, 26, 27, 76, 209, 283, 424, 438, 567, 713, 1004, 1493

**达标标准**：15 分钟内独立写出"替换后的最长重复字符"（424）。

### Week 3-4：二分查找（~12 题）

**核心模板——统一左闭右闭写法**

```python
def binary_search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**二分进阶——搜索左边界**

```python
def search_left(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return left if left < len(nums) and nums[left] == target else -1
```

**练习清单**：33, 34, 35, 69, 74, 153, 162, 240, 287, 410, 875, 1011

**达标标准**：闭眼写出搜索旋转排序数组（33）。

### Week 5-6：DFS & BFS（~15 题）

**BFS 万能模板**

```python
from collections import deque
def bfs_level_order(root):
    if not root: return []
    res, queue = [], deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        res.append(level)
    return res
```

**DFS 回溯模板**

```python
def dfs_backtrack(选择列表, 路径):
    if 满足结束条件:
        result.add(路径)
        return
    for 选择 in 选择列表:
        做选择
        dfs_backtrack(选择列表, 路径)
        撤销选择
```

**练习清单**：17, 22, 39, 46, 78, 79, 90, 102, 127, 200, 207, 417, 547, 695, 994

**达标标准**：手撕岛屿数量（200）和全排列（46）。

### Week 7-8：动态规划（~20 题）

**DP 五步法**：
1. 确定 dp 数组和下标的含义
2. 确定递推公式
3. dp 数组如何初始化
4. 确定遍历顺序
5. 举例推导 dp 数组

```python
# 背包问题模板——0/1 背包
def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [0] * (capacity + 1)
    for i in range(n):
        for j in range(capacity, weights[i] - 1, -1):  # 倒序！
            dp[j] = max(dp[j], dp[j - weights[i]] + values[i])
    return dp[capacity]

# 最长递增子序列 (LIS)
def lengthOfLIS(nums):
    dp = [1] * len(nums)
    for i in range(len(nums)):
        for j in range(i):
            if nums[i] > nums[j]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
```

**练习清单**：5, 53, 62, 64, 70, 72, 121, 139, 152, 198, 213, 221, 279, 300, 322, 416, 474, 518, 1143, 1277

**达标标准**：独立写出最长回文子串（5）和零钱兑换（322）。

### Week 9：回溯（~10 题）

**练习清单**：17, 22, 37, 39, 40, 46, 47, 51, 77, 78, 90

**达标标准**：写出 N 皇后（51）。

### Week 10：哈希 & 堆 & 栈（~10 题）

**哈希表高频模式**：
```
两数之和 → HashMap 存"值→索引"
字母异位词分组 → 排序后的字符串做 key
最长连续序列 → HashSet + 只从序列起点开始数
```

**练习清单**：1, 20, 49, 84, 128, 146, 155, 215, 295, 347, 739

### Week 11：图算法（~10 题）

**练习清单**：133, 207, 210, 261, 269, 310, 323, 743, 787, 1514

**达标标准**：写出课程表（207）的拓扑排序。

### Week 12：综合练习 & 模拟面试（随机 10 题）

每天随机抽 2 题，限时 45 分钟。不会就看题解，但一定要**看懂后关掉题解自己写一遍**。

---

## 三、面试 Top 50 高频题

以下按出现频率排序（基于 2024-2025 大厂面经统计）：

| 题号 | 题目 | 考点 | 难度 |
|------|------|------|------|
| 1 | Two Sum | 哈希表 | Easy |
| 3 | 无重复字符的最长子串 | 滑动窗口 | Medium |
| 5 | 最长回文子串 | DP/中心扩散 | Medium |
| 15 | 三数之和 | 双指针 | Medium |
| 20 | 有效括号 | 栈 | Easy |
| 21 | 合并两个有序链表 | 链表/递归 | Easy |
| 33 | 搜索旋转排序数组 | 二分 | Medium |
| 46 | 全排列 | 回溯 | Medium |
| 53 | 最大子数组和 | DP/分治 | Medium |
| 56 | 合并区间 | 排序/数组 | Medium |
| 70 | 爬楼梯 | DP | Easy |
| 76 | 最小覆盖子串 | 滑动窗口 | Hard |
| 102 | 二叉树的层序遍历 | BFS | Medium |
| 121 | 买卖股票的最佳时机 | DP/贪心 | Easy |
| 146 | LRU 缓存 | 哈希+链表 | Medium |
| 200 | 岛屿数量 | DFS/BFS | Medium |
| 206 | 反转链表 | 链表 | Easy |
| 215 | 数组中的第K个最大元素 | 堆/快排 | Medium |
| 236 | 二叉树的最近公共祖先 | 递归 | Medium |
| 300 | 最长递增子序列 | DP+二分 | Medium |

> 完整 50 题清单见文末附录。

---

## 四、五个最致命的坑

### 坑 1：只看不写
> "这题我看题解看懂了，不用写了。"

**真相**：看懂 ≠ 能写出来。尤其在面试压力下。

**解法**：每道题至少**关掉题解独立写一遍**。一周后回来再做一遍。

### 坑 2：过早看答案
> 想了 5 分钟没思路 → 直接看答案

**真相**：思考的过程比答案更重要。

**解法**：至少思考 20-30 分钟。实在没思路，看答案的"思路描述"部分，不要看代码。然后自己实现。

### 坑 3：只刷 Easy
> "Medium 太难了，先把 Easy 刷完"

**真相**：面试 80% 是 Medium。

**解法**：Easy 刷 30 道建立信心后，直接上 Medium。Hard 遇到就做，不强求。

### 坑 4：不分析复杂度
> "代码跑过了就行"

**真相**：面试官 100% 会问时间复杂度。

**解法**：每道题做完后，标注时间和空间复杂度。养成习惯。

### 坑 5：不做总结
> 刷完就不管了

**真相**：不总结的刷题 = 没刷。

**解法**：每周日花 30 分钟，回顾本周做错的题。用一句话总结每道题的"卡点"。

---

## 五、刷题效率工具

- **LeetCode 官方题解**：质量最高，优先看
- **代码随想录**：分类清晰，适合按算法范式学习
- **labuladong 的算法小抄**：框架思维 + 模板化
- **Visualgo.net**：算法可视化，建立直觉
- **LeetCode VS Code 插件**：本地刷题，不用切浏览器

---

## 附录：面试 Top 50 完整清单

```
Easy (12道):
1, 20, 21, 70, 121, 141, 155, 160, 169, 206, 226, 283

Medium (30道):
2, 3, 5, 11, 15, 17, 19, 22, 33, 46, 48, 49, 53, 
55, 56, 62, 64, 75, 78, 79, 94, 98, 102, 105, 
139, 146, 152, 200, 215, 236, 238, 287, 300, 347, 560

Hard (8道):
4, 23, 25, 32, 42, 76, 124, 239
```

---

> **总结**：刷题的目的不是记住答案，是在大脑里建立"看到问题 → 识别模式 → 套用模板 → 调整细节"的神经通路。按算法范式分类刷，每类做到直觉级别，12 周足够拿下大厂面试。

> 你刷了多少题？卡在哪类题目最久？评论区聊聊，也许我能帮你。
