# 并发与同步：锁、信号量、死锁——每个 C/C++ 程序员都必须跨过的操作系统门槛

> 并发编程是操作系统课里最考验「硬实力」的部分。这篇文章不给你看教科书上的伪代码，而是带你从硬件原子指令出发，一路推到实际工程中怎么用锁、怎么避免死锁。

---

## 一、并发问题的根源：竞态条件

### 1.1 两行代码引发的血案

```c
// 全局计数器
int counter = 0;

// 线程 A                    线程 B
void thread_A() {           void thread_B() {
    counter++;                  counter++;
}                           }
```

`counter++` 在 C 语言里是一行代码，但在 CPU 眼里是三条指令：

```asm
# counter++ 的汇编（x86）
mov eax, [counter]   # 1. 从内存加载 counter 到寄存器 eax
inc eax              # 2. 寄存器里的值 +1
mov [counter], eax   # 3. 写回内存
```

**问题：** 如果线程 A 执行到第 2 步（`eax=1`），还没来得及写回内存，线程 B 开始执行第 1 步——线程 B 读到的 `counter` 还是 0。最终两个线程都把自己当成「把 0 变成 1」，counter 的结果是 1，而不是正确的 2。

这就是**竞态条件（race condition）**：多个线程同时访问共享数据，最终结果取决于线程执行的精确时序——而这个时序是不可预测和不可控的。

### 1.2 临界区

解决竞态条件的关键是识别**临界区（critical section）**——访问共享资源的那段代码，必须保证同一时刻只有一个线程在执行。

```
临界区的三个要求（必须同时满足）：
1. 互斥（Mutual Exclusion）——同一时刻最多一个线程在临界区
2. 前进（Progress）——如果没有线程在临界区，想进去的线程能进去
3. 有限等待（Bounded Waiting）——一个线程不会无限期等不到进入的机会
```

---

## 二、互斥的实现：从关中断到原子指令

### 2.1 最原始的方法：关中断

在单核 CPU 时代，最简单的互斥是关闭中断：

```c
cli();        // 关闭中断（Clear Interrupt flag）
// 临界区代码
sti();        // 打开中断（Set Interrupt flag）
```

但这是内核特权指令（ring 0），用户态程序不能用。而且多核时代这招无效——关了一个核的中断，另一个核照样能访问共享数据。

### 2.2 基于硬件的原子操作：Compare-and-Swap (CAS)

现代 CPU 提供了**原子指令**——不可被中断的「读-改-写」操作。最经典的是 CAS：

```asm
# x86: CMPXCHG
# 伪代码：if (*addr == expected) { *addr = new; return true; } else { return false; }

lock cmpxchg [addr], new_value
```

`lock` 前缀是关键的——它锁住内存总线（或缓存行），确保这个读-改-写操作在多核之间是原子的。

### 2.3 用 CAS 实现自旋锁

```c
typedef struct {
    int locked;  // 0 = 未锁, 1 = 已锁
} spinlock_t;

void spin_lock(spinlock_t *lock) {
    while (1) {
        // 原子：如果 lock->locked == 0，设为 1 并返回 0（获取成功）
        //       如果 lock->locked == 1，返回 1（被占用了）
        if (__sync_bool_compare_and_swap(&lock->locked, 0, 1)) {
            break;  // 获取锁成功
        }
        // 获取失败：自旋等待（CPU 空转）
        while (lock->locked) {
            __builtin_ia32_pause();  // 提示 CPU 这是在自旋等待，降低功耗
        }
    }
}

void spin_unlock(spinlock_t *lock) {
    lock->locked = 0;  // 简单写入即可（但不保证在其他核上的可见性，需要屏障）
    __sync_synchronize();  // 内存屏障：确保 unlock 在其他核上可见
}
```

**自旋锁的适用场景：**
- **适合：** 临界区非常短（几到几十个 CPU 周期）、锁竞争不激烈
- **不适合：** 临界区长（毫秒级）——CPU 空转浪费太严重
- Linux 内核大量使用自旋锁，因为内核临界区通常极短

### 2.4 互斥锁（mutex）——当自旋太长时

如果临界区可能较长（比如涉及磁盘 I/O），自旋锁就太浪费 CPU 了。mutex 的做法是：拿不到锁就去睡觉，等锁释放了再被唤醒。

```c
// Linux 的 futex（Fast Userspace Mutex）机制

void mutex_lock(mutex_t *m) {
    // 快速路径：用原子操作尝试获取
    if (atomic_cmpxchg(&m->state, UNLOCKED, LOCKED) == UNLOCKED) {
        return;  // 成功！不需要系统调用
    }
    
    // 慢速路径：真的需要等待
    while (1) {
        // 如果已经有人等了，确保我们也在等
        if (atomic_cmpxchg(&m->state, LOCKED, LOCKED_WITH_WAITERS) != UNLOCKED) {
            // 系统调用：把自己加入等待队列，然后休眠
            futex_wait(&m->state, LOCKED_WITH_WAITERS);
        }
        // 被唤醒后，再次尝试
        if (atomic_cmpxchg(&m->state, UNLOCKED, LOCKED_WITH_WAITERS) == UNLOCKED) {
            return;
        }
    }
}
```

`futex` 是 Linux 的一个系统调用，它巧妙地把「快速路径」放在用户态（原子操作，不需要系统调用开销），只在真正需要等待时才陷入内核。

---

## 三、信号量（Semaphore）——不止是锁

### 3.1 信号量 vs 互斥锁

| 维度 | 互斥锁（Mutex） | 信号量（Semaphore） |
|------|----------------|---------------------|
| 谁释放 | 谁加锁谁释放（所有权） | 任何线程都能释放 |
| 计数器 | 只有 0/1（二进制） | 可以是任意非负整数 |
| 典型用途 | 保护临界区 | 资源计数、生产者-消费者 |

### 3.2 信号量的经典场景：有界缓冲

生产者-消费者问题是信号量的经典应用：

```c
sem_t empty;  // 缓冲区中的空槽位数量，初始 = BUFFER_SIZE
sem_t full;   // 缓冲区中已填充的槽位数量，初始 = 0
mutex_t m;    // 保护缓冲区本身的互斥锁

// 生产者
void producer() {
    while (1) {
        item = produce_item();
        sem_wait(&empty);   // 等一个空槽位（如果有空位，减 1；没有就阻塞）
        mutex_lock(&m);     // 进入临界区
        insert_item(item);  // 放入缓冲区
        mutex_unlock(&m);   // 离开临界区
        sem_post(&full);    // 通知：多了一个满槽位（full + 1）
    }
}

// 消费者
void consumer() {
    while (1) {
        sem_wait(&full);    // 等一个满槽位
        mutex_lock(&m);
        item = remove_item();
        mutex_unlock(&m);
        sem_post(&empty);   // 通知：多了一个空槽位
        consume_item(item);
    }
}
```

**关键洞察：** `sem_wait` 在计数为 0 时会阻塞当前线程，`sem_post` 会唤醒一个等待者。信号量既充当了同步机制，也充当了计数器——这就是它和互斥锁的本质区别。

---

## 四、死锁——四个条件缺一不可

### 4.1 产生死锁的四个必要条件

| 条件 | 含义 | 例子 |
|------|------|------|
| 互斥（Mutual Exclusion） | 资源不能被共享，一次只能被一个线程持有 | 打印机 |
| 持有并等待（Hold and Wait） | 已经持有一个资源，还在等待另一个 | 线程 A 持有锁 1，等待锁 2 |
| 不可抢占（No Preemption） | 资源只能由持有者主动释放 | 你不能强行抢走别人的锁 |
| 循环等待（Circular Wait） | 存在一个等待环 | A 等 B，B 等 C，C 等 A |

**四个条件全部满足 = 必然可能死锁。打破任何一个条件 = 不会死锁。**

### 4.2 经典的死锁场景

```c
// 线程 A                    线程 B
lock(mutex_1);              lock(mutex_2);
lock(mutex_2);  ← 等 B      lock(mutex_1);  ← 等 A
// ...                      // ...
```

时间线：
```
T1: A 获取 mutex_1
T2: B 获取 mutex_2
T3: A 尝试获取 mutex_2 → 阻塞（被 B 持有）
T4: B 尝试获取 mutex_1 → 阻塞（被 A 持有）
→ 死锁。A 和 B 都永远不会醒来。
```

### 4.3 如何预防——锁定顺序（Lock Ordering）

最简单的预防：所有线程以**相同的顺序**获取锁。

```c
// 定义全局锁顺序：总是先锁 mutex_1，再锁 mutex_2

// 线程 A                    线程 B
lock(mutex_1);              lock(mutex_1);   // B 也先锁 1
lock(mutex_2);              lock(mutex_2);   // 等 A 释放 1 后才拿到
// ...                      // ...
```

如果无法定义全局顺序，使用 `try_lock` + 回退：

```c
while (1) {
    lock(mutex_1);
    if (try_lock(mutex_2)) {
        break;  // 两个都拿到了
    }
    unlock(mutex_1);  // 拿不到就释放已持有的，然后重试
    usleep(random());  // 随机延迟避免活锁（两个线程同时重试同时失败）
}
```

### 4.4 如何检测——线程转储

```bash
# 查看进程的所有线程和它们的调用栈
gdb -p <pid> -ex "thread apply all bt" -ex "detach" -ex "quit"

# 或者用 pstack（Linux）
pstack <pid>

# 看锁等待（需要 debug 符号）
cat /proc/<pid>/stack
```

在生产环境中，如果发现大量线程在 `pthread_mutex_lock` 或 `futex_wait` 上阻塞，检查它们各自持有哪些锁、在等哪些锁——如果形成了环，就是死锁。

---

## 五、读写锁与 RCU——读多写少的场景

### 5.1 读写锁（RWLock）

如果 90% 的操作是读，10% 是写，互斥锁太浪费了——读操作之间完全不需要互斥。

```c
pthread_rwlock_t rwlock;

// 读线程（多个可以同时持有）
pthread_rwlock_rdlock(&rwlock);
// 读取共享数据
pthread_rwlock_unlock(&rwlock);

// 写线程（独占，等所有读线程释放后才获得）
pthread_rwlock_wrlock(&rwlock);
// 修改共享数据
pthread_rwlock_unlock(&rwlock);
```

**注意：** 如果读操作非常频繁且没有间隙，写线程可能饿死（永远等不到锁）。`pthread_rwlockattr_setkind_np` 可以设置读写锁策略来避免这个问题。

### 5.2 RCU（Read-Copy-Update）——Linux 内核的王牌

RCU 是 Linux 内核中最极致的读优化。它的核心思想：**读者完全不需要锁。**

```c
// 读者（无锁！）
rcu_read_lock();
data = rcu_dereference(shared_ptr);  // 读取共享指针（有内存屏障保证）
// ... 使用 data ...
rcu_read_unlock();

// 写者
new_data = copy_data(old_data);      // 1. 复制一份
modify(new_data);                     // 2. 修改副本
rcu_assign_pointer(shared_ptr, new_data);  // 3. 原子替换指针
synchronize_rcu();                    // 4. 等所有读者退出后，释放旧数据
```

**原理：** 写者不修改原数据，而是复制一份、改副本、然后原子地替换指针。旧数据在所有正在读的线程退出后才释放。读者从头到尾不需要任何锁——只要持有一个引用就可以安全访问。

RCU 是 Linux 内核中最广泛使用的同步机制之一，尤其适合网络协议栈、文件系统缓存等读极多写极少的场景。

---

## 六、动手实验：检测你程序中的并发问题

```bash
# 用 ThreadSanitizer 检测数据竞争（编译时加 -fsanitize=thread）
gcc -fsanitize=thread -g -o myapp myapp.c
./myapp
# TSan 会在检测到竞态时打印详细的冲突位置

# 用 Helgrind 检测锁问题
valgrind --tool=helgrind ./myapp

# 用 perf 查看锁竞争情况
perf record -e 'syscalls:sys_enter_futex' -ag -- sleep 10
perf report

# 查看内核锁统计
cat /proc/lock_stat  # 需要 CONFIG_LOCK_STAT=y
```

---

## 七、总结：选锁决策树

```
你需要保护共享数据吗？
├── 临界区极短（<1μs）+ 竞争不激烈 → 自旋锁（spinlock）
├── 临界区可能较长 → 互斥锁（mutex / futex）
│   ├── 读多写少 → 读写锁（RWLock）
│   └── 读极多写极少 + 数据量小 → RCU
├── 控制资源数量（如线程池）→ 信号量（semaphore）
└── 需要跨进程同步 → 文件锁（flock）或共享内存 + 信号量
```

核心原则就两条：

1. **尽量减少锁的范围**——锁住的代码越短，竞争越少。
2. **始终保持锁的获取顺序一致**——消除循环等待，死锁永远不会发生。

---

**参考来源：**

- Linux Kernel Documentation: [locking](https://docs.kernel.org/locking/)
- Linux Kernel Documentation: [RCU](https://docs.kernel.org/RCU/)
- `man 7 futex`, `man 7 pthreads`