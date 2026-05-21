# Linux 进程调度演化史：从 O(n) 到 CFS 再到 EEVDF，30 年调度器的三次跃迁

> 进程调度是操作系统的脉搏。这篇文章不堆概念，带你从 Linux 0.01 走到内核 6.6，看懂调度器为什么这样设计，以及每次重构到底解决了什么问题。

---

## 一、为什么调度器是 OS 的核心

CPU 是整台计算机最宝贵的资源。一个操作系统可以没有图形界面、没有网络栈，但不能没有进程调度——因为 CPU 只有一个（或几个核），而想用它的程序可能有几百个。

**调度器的终极命题：** 在有限的 CPU 时间内，让所有进程都觉得「公平」，同时最大化系统吞吐量。

这个命题里有两个天然矛盾：

1. **公平 vs 吞吐量**：让每个进程平均分配 CPU（公平）意味着频繁切换进程（上下文切换开销大），降低吞吐量。
2. **延迟 vs 吞吐量**：交互进程（比如你打字）需要快速响应，但计算密集型进程（比如视频渲染）需要长时间占用 CPU。

一个好的调度器，就是在这些矛盾之间找到平衡点。

---

## 二、第一代：Linux 0.01 的原始调度器（1991）

Linus Torvalds 在 1991 年写的第一版 Linux 内核里，调度器的核心逻辑非常简单：

```c
// 简化版伪代码——遍历所有进程，找 counter 最大的那个
void schedule(void) {
    int c = -1;
    struct task_struct *p, *next;
    
    for_each_task(p) {
        if (p->state == TASK_RUNNING && p->counter > c) {
            c = p->counter;
            next = p;
        }
    }
    
    if (!c) {
        // 所有进程 counter 都用完了，重新分配
        for_each_task(p)
            p->counter = (p->counter >> 1) + p->priority;
    }
    
    switch_to(next);
}
```

这段代码只有几十行，逻辑是：

- 每个进程有一个 `counter`，初始值等于优先级 `priority`。
- 调度时遍历所有进程，找到 `counter` 最大的来执行。
- **时钟中断**每发生一次，当前进程的 `counter` 减 1。
- 当所有进程的 `counter` 都降到 0，系统重新计算：`counter = counter/2 + priority`。

**这个设计的巧妙之处：**

你注意那个 `counter >> 1`（除以 2）——它会「记住」之前用过 CPU 的进程。一个刚刚用光 counter 的进程，下一轮从 `priority` 开始；但一个之前没用过 CPU 的进程（counter 保持初始值），下一轮会得到 `counter + priority`，远大于别人。

这就是**最简单的交互性优化**：I/O 密集型进程（经常因为等 I/O 而主动让出 CPU，counter 没怎么消耗）会在下一轮获得更多 CPU 时间。

**缺点：** 时间复杂度 O(n)。2000 年左右的服务器可能有上百个进程，每次调度都要遍历一遍。

---

## 三、第二代：O(1) 调度器（2003，Linux 2.6）

Ingo Molnar 在 2003 年提交了 O(1) 调度器，核心思想是用两个**位图 + 优先级数组**替代遍历：

```
Active 数组（正在运行）          Expired 数组（时间片用完）
┌─────────────────────┐          ┌─────────────────────┐
│ prio 0: [进程A, B]   │          │ prio 0: [进程E]      │
│ prio 1: [进程C]      │          │ prio 1: []           │
│ prio 2: []           │          │ prio 2: [进程F, G]   │
│ ...                  │          │ ...                  │
│ prio 139: []         │          │ prio 139: []         │
└─────────────────────┘          └─────────────────────┘
         ↑                              ↑
    当前从这取                         Active 空了就交换
```

- 140 个优先级（0-99 实时，100-139 普通进程），每个优先级一个链表。
- 用一个 140-bit 的位图，bit[i]=1 表示优先级 i 有可运行的进程。
- 找最高优先级 = 找位图里第一个为 1 的位 → 一条 CPU 指令（`bsfl`）搞定。

**时间复杂度从 O(n) 变成了 O(1)，在当时是个质的飞跃。**

但它的问题也逐渐暴露：

1. **启发式规则太多**：为了判断一个进程是「交互式」还是「计算密集型」，代码里塞了大量启发式判断（平均睡眠时间、交互性评分……），越来越难维护。
2. **公平性不够精细**：时间片的粒度太粗，对桌面互动场景不够友好。
3. **维护困难**：到了 O(1) 调度器生命周期末期，调度相关的代码已经膨胀到数千行，布满 case-by-case 的特殊处理。

---

## 四、第三代：CFS 完全公平调度器（2007，Linux 2.6.23）

### 4.1 CFS 的核心思想

Ingo Molnar 再次出手，彻底推翻了 O(1) 的设计，引入了一个全新的范式。

CFS 的核心理念可以用一句话概括——来自官方内核文档：

> **CFS 在一台真实的硬件上模拟一台「理想的、精确的多任务 CPU」。**

什么是「理想的多任务 CPU」？假设有一台 CPU，它有 100% 的算力，同时跑 N 个进程，每个进程精确地各得 1/N 的算力。如果有 2 个进程，每个得 50%；3 个进程，每个得 33.3%——绝对公平。

真实硬件不行——一次只能跑一个进程。所以 CFS 引入了**虚拟运行时间（vruntime）**的概念：

```
vruntime = 实际运行时间 × (1024 / 进程权重)
```

- 权重高的进程（nice 值低），vruntime 增长慢——能多跑。
- 权重低的进程（nice 值高），vruntime 增长快——少跑。
- CFS 始终选择 **vruntime 最小的进程**来执行。

### 4.2 红黑树——O(log n) 的任务选择

CFS 不用数组，用**红黑树**（rbtree），按 vruntime 排序：

```
         task D (vruntime=50ms)
        /                        \
  task B (30ms)              task F (80ms)
     /        \                     \
task A (10ms) task C (40ms)    task G (100ms)
```

CFS 永远选树的最左节点（vruntime 最小的进程）。红黑树保证最左节点可以在 O(log n) 内找到。

### 4.3 CFS 的几个关键参数

| 参数 | 含义 | 默认值 |
|------|------|--------|
| `sched_min_granularity_ns` | 一个进程最少连续运行多久才被抢占 | 0.75ms |
| `sched_latency_ns` | 一个调度周期内，所有可运行进程至少被调度一次 | 6ms（`nr_running < 8` 时） |
| `sched_wakeup_granularity_ns` | 唤醒进程的 vruntime 比当前进程小多少才能抢占 | 1ms |

这些参数的设计非常克制——CFS 的目标不是「切换越快越好」，而是**在公平的前提下，尽量减少上下文切换**（因为 cache 会失效）。

### 4.4 CFS 的成就与局限

CFS 从 2007 年运行到 2024 年，活了 17 年，是 Linux 历史上寿命最长的通用调度器。它足够好——公平、简洁、性能稳定。

但它有一个结构性问题：**无法区分「需要更多 CPU 时间」和「需要更快响应」**。nice 值只能调整 CPU 时间的分配比例，不能表达「我运行时间不长，但我需要马上响应」。

2018 年开始，社区尝试了 `latency-nice` 补丁来解决这个问题，但直到 2023 年，Peter Zijlstra 提出了一个更根本的方案。

---

## 五、第四代：EEVDF 调度器（2024，Linux 6.6）

### 5.1 EEVDF 是什么

EEVDF 的全称是 **Earliest Eligible Virtual Deadline First**（最早合格虚拟截止时间优先），由 Ion Stoica 和 Hussein Abdel-Wahab 在 1995 年的论文中提出。

Peter Zijlstra 在 2023 年提交了 Linux 版的 EEVDF 补丁[2]，并在 Linux 6.6（2024 年）中合并。

### 5.2 它的工作原理

EEVDF 给每个进程引入了三个新概念：

| 概念 | 含义 |
|------|------|
| **虚拟运行时间（vruntime）** | 和 CFS 一样，进程已获得的 CPU 时间 |
| **滞后值（lag）** | 进程实际获得的 CPU 时间 - 应该获得的 CPU 时间 |
| **虚拟截止时间（virtual deadline, VD）** | 进程下次必须被调度的时间点 |

**调度逻辑：**

1. 只考虑 `lag >= 0` 的进程（即它还没有超过应得的 CPU 时间份额）
2. 在这些「合格」进程中，选择 **VD 最早**的那个

**关键创新：** EEVDF 允许延迟敏感型进程设置更短的时间片（time slice），从而获得更早的 VD，被更快调度——而不会占用超过它应得的 CPU 份额。这就是「响应快但不占便宜」。

### 5.3 EEVDF 为什么比 CFS 好

| 维度 | CFS | EEVDF |
|------|-----|-------|
| 公平性 | 好 | 更好（显式跟踪 lag） |
| 延迟控制 | 依赖启发式（wakeup preemption） | 精确（VD 机制） |
| 启发式规则 | 不少 | 大幅减少 |
| 延迟敏感型任务 | 需要猜测 | 明确支持（短 time slice → 早 VD） |
| 睡眠进程处理 | vruntime 最小值修正 | lag 衰减机制——防止睡眠作弊 |

一个具体场景：音频处理应用需要每 5ms 获得一次 CPU。EEVDF 可以给它一个 5ms 的 request time slice，保证它在 VD 之前被调度——不需要任何猜测或启发式规则。

### 5.4 lag 的衰减机制：防止「睡眠作弊」

这是个很精妙的设计。假设一个进程跑了很多 CPU 时间后（lag 变成负数），它主动睡眠一小段时间。如果没有衰减机制，它醒来后还是负数 lag，就能继续抢占别人——相当于「偷了 CPU 时间后睡一觉就洗白了」。

EEVDF 的做法：睡眠期间 lag 不会立即清零，而是按照虚拟运行时间（VRT）衰减。只有睡了足够长的时间，lag 才会归零。这就是「deferred dequeue」机制——进程休眠时仍保留在运行队列中，标记为待出队。

---

## 六、调度器演化全景图

```
1991 ─── Linux 0.01 原始调度器 (O(n))
          │ 问题：进程多时太慢
          ▼
2003 ─── O(1) 调度器
          │ 问题：启发式太多，公平性不够细
          ▼
2007 ─── CFS 完全公平调度器
          │ 问题：不能区分「多要时间」和「快响应」
          ▼
2024 ─── EEVDF 调度器
          │ 当前最新
```

每次换代解决的核心问题：

1. **O(n) → O(1)**：解决了性能（时间复杂度）
2. **O(1) → CFS**：解决了公平性和维护性
3. **CFS → EEVDF**：解决了延迟精度和启发式泛滥

---

## 七、动手验证：看看你的系统在用哪个

```bash
# 查看内核版本（6.6+ 才有 EEVDF）
uname -r

# 查看 CPU 调度器当前策略
cat /sys/kernel/debug/sched/features | head -20

# 查看某个进程的调度策略
chrt -p $(pgrep -f "your-app")
# 输出示例：pid xxx's current scheduling policy: SCHED_OTHER
```

如果你在内核 6.6+ 的系统上，EEVDF 已经是 `SCHED_OTHER`（普通进程）的默认调度策略。你也可以通过内核引导参数 `sched_policy=eevdf|cfs` 在两个调度器之间切换（取决于你的内核编译配置）。

---

## 八、总结

Linux 调度器的 30 年演化，本质上是三条设计原则在互相博弈：

1. **公平**——每个进程都应得到它应得的 CPU 时间
2. **效率**——不能为了公平把 CPU 浪费在调度本身
3. **响应**——交互式任务不能因为公平而卡顿

原始调度器的巧妙（counter 衰减）、O(1) 的工程智慧（位图优先级数组）、CFS 的理论优雅（理想多任务 CPU 的模拟）、EEVDF 的精确建模（lag + VD）——每一代都在三条原则之间找到了一个新的平衡点。

理解了这个演化脉络，你就理解了操作系统调度器设计语言的完整语法。

---

**参考来源：**

- Linux Kernel Documentation: [CFS Scheduler](https://docs.kernel.org/scheduler/sched-design-CFS.html)
- Linux Kernel Documentation: [EEVDF Scheduler](https://docs.kernel.org/scheduler/sched-eevdf.html)
- [LWN.net: An EEVDF CPU scheduler for Linux](https://lwn.net/Articles/925371/)
- Ion Stoica, Hussein Abdel-Wahab (1995): "Earliest Eligible Virtual Deadline First"