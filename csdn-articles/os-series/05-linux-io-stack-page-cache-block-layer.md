# Linux I/O 全栈：从 `write()` 到磁盘磁头——一个字节的万里长征

> 你调用 `write(fd, buf, 4096)` 只花了 50 微秒。这 50 微秒里发生了什么？这篇文章追踪一个字节的完整旅程——从用户态系统调用到磁盘控制器，经过 VFS、Page Cache、Block Layer、I/O 调度器、设备驱动，共七层。

---

## 一、你写了 `write()` 之后

```c
int fd = open("/data/file.txt", O_WRONLY | O_CREAT, 0644);
char buf[4096] = "Hello, World!";
write(fd, buf, 4096);
close(fd);
```

这行 `write()` 触发了 Linux I/O 栈的全部七层：

```
用户态  ───── write(fd, buf, 4096)
                │
       ═════════╪═══════════ 系统调用边界
                │
内核态  ┌───────▼──────────┐  1. VFS 层（统一接口）
        │ vfs_write()      │
        └───────┬──────────┘
                │
        ┌───────▼──────────┐  2. 文件系统层（ext4/XFS）
        │ ext4_file_write() │
        └───────┬──────────┘
                │
        ┌───────▼──────────┐  3. Page Cache（缓存层）
        │ generic_perform_  │
        │   write()         │
        └───────┬──────────┘
                │
        ┌───────▼──────────┐  4. Block Layer（I/O 提交层）
        │ submit_bio()     │
        └───────┬──────────┘
                │
        ┌───────▼──────────┐  5. I/O 调度器（排序/合并）
        │ blk_mq (多队列)   │
        └───────┬──────────┘
                │
        ┌───────▼──────────┐  6. 设备驱动（NVMe/SATA/SCSI）
        │ nvme_queue_rq()  │
        └───────┬──────────┘
                │
        ┌───────▼──────────┐  7. 硬件（磁盘控制器 → NAND/盘片）
        │  DMA 传输         │
        └──────────────────┘
```

---

## 二、第一层：VFS——不管你用 ext4 还是 XFS，接口都一样

```c
// fs/read_write.c (简化)
ssize_t vfs_write(struct file *file, const char __user *buf,
                  size_t count, loff_t *pos)
{
    // 1. 安全检查：文件是否可写？用户传入的指针是否有效？
    if (!(file->f_mode & FMODE_WRITE))
        return -EBADF;
    
    // 2. 验证用户空间缓冲区
    if (!access_ok(buf, count))
        return -EFAULT;
    
    // 3. 调用具体文件系统的 write 实现
    // file->f_op->write 指向 ext4_file_write() 或 xfs_file_write()
    ret = file->f_op->write(file, buf, count, pos);
    
    // 4. 更新文件的修改时间（mtime）
    file_accessed(file);  // 更新 atime
    
    return ret;
}
```

**VFS 的职责：** 安全检查、用户空间内存验证、文件系统路由。性能开销极小。

---

## 三、第二层 + 第三层：文件系统 + Page Cache

### 3.1 ext4 的写入流程

```c
// fs/ext4/file.c (简化)
static ssize_t ext4_file_write(struct kiocb *iocb, struct iov_iter *from)
{
    // 如果文件以 O_DIRECT 打开，走直接 I/O（绕过 Page Cache）
    if (iocb->ki_flags & IOCB_DIRECT)
        return ext4_dio_write_iter(iocb, from);
    
    // 否则走缓冲 I/O（经过 Page Cache）——99% 的场景
    return generic_perform_write(iocb, from);
}
```

### 3.2 Page Cache——写入的秘密就在这里

**关键事实：** 默认情况下，`write()` 不会直接写到磁盘。它把数据写入 **Page Cache**（内存中的页面缓存），然后返回。实际的磁盘写入由内核在后台异步完成（称为「回写」或 writeback）。

```c
// mm/filemap.c (简化)
ssize_t generic_perform_write(struct kiocb *iocb, struct iov_iter *i)
{
    while (iov_iter_count(i)) {
        // 1. 在 Page Cache 中找到或创建一个页（4KB）
        page = grab_cache_page_write_begin(mapping, index);
        
        // 2. 把用户空间的数据复制到这个页
        copied = iov_iter_copy_from_user_atomic(page, i, offset, bytes);
        
        // 3. 标记这个页为「脏页」（dirty page）
        //    这意味着它和磁盘上的内容不一致，需要后续写回
        __set_page_dirty_nobuffers(page);
        
        // 4. 如果脏页过多，触发后台回写
        balance_dirty_pages_ratelimited(mapping);
        
        pos += copied;
    }
}
```

**Page Cache 的意义：**

1. **写缓冲**——把多次小写入合并成一次大写入（减少 I/O 次数）
2. **读缓存**——下次读同一文件时直接从内存返回，零磁盘 I/O
3. **预读**——顺序读时提前把后续的页加载到 Page Cache

### 3.3 脏页回写——谁来决定什么时候写盘

```
脏页水位线（以 /proc/sys/vm/dirty_* 控制）：

┌──────────────────────────────┐  100% dirty_ratio (默认 20%)
│  强制回写：阻塞所有写入进程    │  到达此线：write() 调用者被阻塞
├──────────────────────────────┤
│  后台回写：唤醒 flusher 线程   │  dirty_background_ratio (默认 10%)
├──────────────────────────────┤
│  正常：只标记脏页，不写盘      │
└──────────────────────────────┘  0%
```

Linux 有一组内核线程 `flusher`（以前叫 `pdflush`）专门负责脏页回写：

```bash
# 查看当前脏页配置
sysctl -a | grep dirty

# dirty_background_ratio: 脏页超过总内存的 10% 时启动后台回写
# dirty_ratio: 脏页超过 20% 时阻塞写入进程，强制回写
# dirty_expire_centisecs: 脏页超过 30 秒未回写，强制回写（3000 = 30s）
# dirty_writeback_centisecs: flusher 线程每 5 秒醒来检查一次（500 = 5s）
```

**注意：** `fsync()` 或 `O_SYNC` 可以强制立即写盘，绕过 Page Cache 的延迟。数据库（如 PostgreSQL、MySQL）大量使用 `fsync()` 来保证事务的持久性——代价是吞吐量大幅下降。

---

## 四、第四层：Block Layer——最后的合并机会

当 Page Cache 决定回写时，它构建一个 **bio**（block I/O）结构体，提交给 Block Layer。

```c
// 一个 bio 描述一次块设备 I/O 请求
struct bio {
    sector_t      bi_sector;    // 起始扇区号（LBA）
    struct bio    *bi_next;     // 下一个 bio（链表）
    unsigned short bi_vcnt;     // bio_vec 数组中的条目数
    struct bio_vec *bi_io_vec;  // 数据所在的内存页列表
    // ...
};

struct bio_vec {
    struct page *bv_page;   // 指向 Page Cache 中的页
    unsigned int bv_len;    // 这个段（segment）的长度
    unsigned int bv_offset; // 页内偏移
};
```

**Block Layer 的优化——合并相邻请求：**

```
提交前：三个独立的 bio
bio1: 扇区 100-103
bio2: 扇区 104-107   ← 和 bio1 相邻！
bio3: 扇区 200-203

合并后：
bio1: 扇区 100-107   ← 合并为一个连续的请求
bio3: 扇区 200-203
```

这种合并对机械硬盘（HDD）来说极其重要——减少磁头寻道次数。对于 SSD，合并的作用是减少 I/O 命令数（NVMe 协议的快的是并行性，但合并仍能减少命令提交开销）。

---

## 五、第五层：I/O 调度器——给请求排队的「交通警察」

Block Layer 把 bio 转换成 **request**，放入请求队列。I/O 调度器决定这些 request 的执行顺序。

### 5.1 机械硬盘时代的调度器

对于旋转磁盘（HDD），访问时间 = 寻道时间 + 旋转延迟 + 数据传输时间。寻道时间通常是 5-10ms，是绝对主导因素。

| 调度器 | 策略 | 适合 |
|--------|------|------|
| **noop** | 不排序，只合并 | SSD、虚拟机 |
| **deadline** | 保证每个请求的延迟上限，同时尽量合并 | 通用 HDD |
| **cfq**（完全公平队列） | 每个进程一个队列，轮转调度，公平分配带宽 | 多用户系统 |
| **anticipatory** | 完成一个请求后等 6ms，看有没有相邻请求（已被 deadline 取代） | — |

**deadline 调度器的工作原理：**

```
请求按 LBA 排序的红黑树（用于合并）：
扇区 50  → 100 → 150 → 200 → 300

请求按到达时间的 FIFO 队列（用于保证延迟上限）：
读请求延迟上限：500ms（默认）
写请求延迟上限：5000ms（写不重要，可以等）

调度逻辑：
1. 先检查读 FIFO 队头——超过 500ms 了？立刻处理！
2. 否则从排序树中取相邻请求（合并优化）
3. 处理一批请求后，再检查写 FIFO——超过 5 秒了？立刻处理！
```

### 5.2 SSD 时代：blk-mq 多队列

SSD 没有旋转寻道的时间，内部有多个并行通道。传统单队列调度器成了瓶颈——请求队列本身的开销限制了 SSD 的性能。

Linux 3.13 引入了 blk-mq（多队列块层）：

```
每个 CPU 核心一个软件队列（加锁开销极小）：

CPU 0 → [软队列0] ──┐
CPU 1 → [软队列1] ──┤
CPU 2 → [软队列2] ──┤→ [硬件调度队列] → 设备驱动
CPU 3 → [软队列3] ──┘

特点：
- 队列绑定到 CPU 核心 → 无锁或极少的锁
- 多个硬件队列 → 利用 NVMe 的多队列并行特性
- 不支持 I/O 排序（SSD 内部并行，LBA 排序没有意义）
```

```bash
# 查看当前的 I/O 调度器
cat /sys/block/sda/queue/scheduler
# 输出示例：[mq-deadline] none

# 对于 NVMe SSD，用 none（完全不调度，直接下发）
echo none > /sys/block/nvme0n1/queue/scheduler
```

---

## 六、第六层 + 第七层：设备驱动与硬件

### 6.1 NVMe vs SATA——协议层面的差异

| 维度 | SATA（AHCI） | NVMe |
|------|-------------|------|
| 命令队列深度 | 最多 32 | 最多 65536 |
| 队列数 | 1 | 最多 65536 |
| 中断方式 | 每完成一个命令产生一次中断 | 支持中断聚合（多个完成一次性通知） |
| 延迟 | ~100μs | ~10μs |
| 协议栈 | SCSI 翻译层 → ATA | 原生 PCIe，几乎没有翻译开销 |

NVMe 是为闪存从头设计的协议，不需要兼容几十年前的硬盘控制器。这也是为什么 NVMe SSD 的延迟比 SATA SSD 低一个数量级——不是闪存更快，是**协议层的开销更小**。

### 6.2 DMA——CPU 不搬数据

传统 I/O 方式（PIO，Programmed I/O）需要 CPU 逐字节从内存搬到磁盘控制器。对于 4KB 的一次写入，这就是几千条 `mov` 指令。

DMA（Direct Memory Access，直接内存访问）让磁盘控制器自己从内存拉数据：

```
不用 DMA：                     用 DMA：
CPU 搬数据到磁盘控制器          磁盘控制器直接从内存读
┌──────┐    ┌────────┐        ┌──────┐         ┌────────┐
│ CPU  │───→│ 控制器  │        │ CPU  │  ←设置→ │ 控制器  │
└──────┘    └───┬────┘        └──────┘         └───┬────┘
                │                                   │
            ┌───▼──┐             直接从内存读 →  ┌───▼──┐
            │ 磁盘  │                            │ 磁盘  │
            └──────┘                            └──────┘
```

DMA 传输过程中，CPU 可以去做别的事（比如调度下一个进程）。传输完成后，磁盘控制器通过中断通知 CPU。

---

## 七、直接 I/O vs 缓冲 I/O——数据库的选择

| 模式 | 描述 | write() 返回时数据去了哪 |
|------|------|------------------------|
| 缓冲 I/O（默认） | 经过 Page Cache | 在内存中，等待后台回写 |
| 直接 I/O（`O_DIRECT`） | 绕过 Page Cache | 直接提交给磁盘 | 
| 同步 I/O（`O_SYNC`） | 缓冲 I/O + 立即回写 | 数据已写到磁盘 |

```c
// 缓冲 I/O（默认）
int fd1 = open("file.txt", O_WRONLY);

// 直接 I/O——数据库常用，自己管理缓存
int fd2 = open("file.txt", O_WRONLY | O_DIRECT);

// 同步 I/O——每一步都确认落盘后才返回
int fd3 = open("file.txt", O_WRONLY | O_SYNC);
```

**为什么数据库偏好直接 I/O？** 数据库（MySQL/PostgreSQL）有自己的缓冲池（buffer pool），Page Cache 的存在意味着数据被缓存了两遍——一次在数据库的 buffer pool，一次在 Page Cache。更糟的是，Page Cache 可能在一些情况下持有脏页，让数据库误以为数据已经安全落盘。用 O_DIRECT 避免了这层重复和不确定性。

---

## 八、动手实验：追踪一次 I/O

```bash
# 1. 用 strace 追踪 write 系统调用
strace -e trace=write,open,close cat /etc/hostname > /dev/null

# 2. 用 blktrace 追踪块设备 I/O
sudo blktrace -d /dev/sda -o - | blkparse -i -

# 3. 用 iostat 查看 I/O 统计
iostat -x 1

# 4. 查看 Page Cache 使用情况
cat /proc/meminfo | grep -E "Cached|Dirty|Writeback"

# 5. 查看块设备队列参数
cat /sys/block/sda/queue/nr_requests       # 最大请求数
cat /sys/block/sda/queue/max_sectors_kb    # 单次请求最大大小
cat /sys/block/sda/queue/scheduler         # 当前使用的调度器
cat /sys/block/nvme0n1/queue/scheduler     # NVMe 通常是 "none"

# 6. 强制回写所有脏页（小心！会短时卡 IO）
sync

# 7. 查看 I/O 栈各层延迟分布
sudo bpftrace -e 'kprobe:vfs_write { @start[tid] = nsecs; }
                  kretprobe:vfs_write /@start[tid]/ {
                      @lat = hist((nsecs - @start[tid]) / 1000);
                      delete(@start[tid]); }'
# Ctrl+C 后输出延迟分布直方图
```

---

## 九、总结：七层 I/O 栈全景图

```
write(fd, buf, 4096)
    │
    ▼
┌──────────────────────────────────────────────────┐
│ VFS      │ 安全检查、用户空间验证、文件系统路由     │
├──────────┼──────────────────────────────────────┤
│ FS (ext4)│ extent 映射、块分配、日志               │
├──────────┼──────────────────────────────────────┤
│ Page Cache│ 脏页标记、合并写入、延迟分配            │
├──────────┼──────────────────────────────────────┤
│ Block Layer│ bio 构建、请求合并、blk-mq 分配       │
├──────────┼──────────────────────────────────────┤
│ I/O Scheduler│ 排序（HDD）或无排序直接下发（NVMe）  │
├──────────┼──────────────────────────────────────┤
│ Driver   │ NVMe/SATA 命令构建、DMA 设置            │
├──────────┼──────────────────────────────────────┤
│ Hardware │ 磁盘控制器接收命令、NAND 写入/磁头寻道   │
└──────────┴──────────────────────────────────────┘
```

**记住这三句话就够了：**

1. **Page Cache 是 I/O 性能的根基**——99% 的写入优化发生在这一层。
2. **合并比调度更重要**——减少 I/O 次数比排序 I/O 顺序收益大。
3. **SSD 改变了 I/O 调度的设计哲学**——从「减少寻道」变成「降低命令开销 + 利用并行」。

---

**参考来源：**

- Linux Kernel Documentation: [block](https://docs.kernel.org/block/)
- Linux Kernel Documentation: [NVMe](https://docs.kernel.org/driver-api/nvme/)
- Love, R. (2010): *Linux Kernel Development* (3rd ed.), Addison-Wesley