# 数据库优化实战：MySQL 慢查询终结者 + Redis 缓存避坑指南

> **摘要**：MySQL 慢查询和 Redis 缓存雪崩是后端开发的两大噩梦。本文不讲理论，直接上实战——MySQL 的 EXPLAIN 解读、索引优化 5 大原则、分库分表决策树，以及 Redis 缓存穿透/击穿/雪崩的三件套解决方案。附完整排查 SQL 和 Redis 配置模板。

---

## 一、你遇到过这种场景吗？

凌晨 2 点，报警电话："用户登录不了！"

查监控：MySQL 慢查询堆积 2000+，CPU 100%。Redis 连接池耗尽。

你睡眼惺忪地打开终端，面对着 500 行 SQL 和一堆 EXPLAIN 输出——该从哪下手？

这篇文章就是你的排查手册。

---

## Part A：MySQL 优化

## 二、第一步永远是 EXPLAIN

```sql
EXPLAIN SELECT * FROM orders 
WHERE user_id = 12345 
AND status = 'paid' 
ORDER BY created_at DESC 
LIMIT 20;
```

### EXPLAIN 关注 4 个核心字段

| 字段 | 看什么 | 好信号 | 坏信号 |
|------|--------|--------|--------|
| type | 访问方式 | const, eq_ref, ref, range | ALL（全表扫描） |
| key | 用的哪个索引 | 有值 | NULL |
| rows | 扫描行数 | 越小越好 | 几十万+ |
| Extra | 额外信息 | Using index（覆盖索引） | Using filesort, Using temporary |

**黄金法则**：type 列是 ALL → 必须加索引。Extra 有 Using filesort → 索引没覆盖排序字段。

---

## 三、索引优化的 5 大铁律

### 铁律 1：最左前缀原则

```sql
-- 索引：(user_id, status, created_at)
-- ✅ 用到索引
WHERE user_id = 123
WHERE user_id = 123 AND status = 'paid'
WHERE user_id = 123 AND status = 'paid' AND created_at > '2026-01-01'

-- ❌ 用不到索引（跳过了最左列 user_id）
WHERE status = 'paid'
WHERE created_at > '2026-01-01'
```

**记住**：联合索引像一列火车——要从车头开始上，不能从中间跳上去。

### 铁律 2：索引列不能做函数运算

```sql
-- ❌ 索引失效
WHERE YEAR(created_at) = 2026
WHERE LEFT(phone, 3) = '138'

-- ✅ 改写
WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'
WHERE phone LIKE '138%'
```

**原理**：索引存的是原始值，函数运算后的值不在索引里。

### 铁律 3：覆盖索引是性能银弹

```sql
-- 索引：(user_id, status, amount)
-- ✅ 覆盖索引：不回表，直接从索引取数据
SELECT user_id, status, amount FROM orders WHERE user_id = 123;

-- ❌ 回表查询：索引里没有 phone，需要去聚簇索引找
SELECT user_id, status, phone FROM orders WHERE user_id = 123;
```

**Extra 显示 "Using index" → 覆盖索引，查询最快。**

### 铁律 4：避免 SELECT *

```sql
-- ❌ 慢
SELECT * FROM orders WHERE user_id = 123;

-- ✅ 快（只取需要的列，还能利用覆盖索引）
SELECT id, user_id, amount, status FROM orders WHERE user_id = 123;
```

### 铁律 5：分页深坑用"延迟关联"或"游标"

```sql
-- ❌ 翻到第 100 万页：巨慢
SELECT * FROM orders ORDER BY id LIMIT 1000000, 20;

-- ✅ 方案一：子查询先拿 ID
SELECT * FROM orders 
WHERE id >= (SELECT id FROM orders ORDER BY id LIMIT 1000000, 1)
ORDER BY id LIMIT 20;

-- ✅ 方案二：记住上一页最后一条的 ID（推荐）
SELECT * FROM orders 
WHERE id > 999999
ORDER BY id LIMIT 20;
```

---

## 四、慢查询排查三步走

### Step 1：开启慢查询日志

```sql
-- 查看是否开启
SHOW VARIABLES LIKE 'slow_query_log%';
SHOW VARIABLES LIKE 'long_query_time';

-- 临时开启（重启失效）
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;  -- 超过1秒记录
```

### Step 2：用 pt-query-digest 分析

```bash
# 安装 Percona Toolkit
pt-query-digest /var/log/mysql/slow.log > slow_report.txt
```

报告会告诉你：哪些 SQL 最慢、执行了多少次、占总时间的百分比。

### Step 3：对症下药

| 问题类型 | 解决方案 |
|---------|---------|
| 全表扫描 | 加索引 |
| 索引失效 | 改写 SQL（避免函数、隐式转换） |
| 回表太多 | 建覆盖索引 |
| 锁等待 | 拆分大事务、优化事务顺序 |
| 数据量大 | 分库分表、归档历史数据 |

---

## 五、分库分表决策树

```
你的单表数据量 > 2000万？
  ├── 否 → 不需要分表，优化索引即可
  └── 是 → QPS 撑不住了吗？
        ├── 是 → 分库（水平拆分，按 user_id 哈希）
        └── 否 → 数据量太大但 QPS 还行？
              ├── 历史数据多 → 归档（冷热分离）
              └── 活跃数据也大 → 分表（按时间/取模）
```

**分表策略对比**：

| 策略 | 优点 | 缺点 | 适用 |
|------|------|------|------|
| 按时间（按月） | 简单，归档方便 | 热点数据集中 | 日志、流水 |
| 按取模（user_id % 64） | 均匀分布 | 扩容麻烦 | 用户数据 |
| 按范围（user_id 0-1000万） | 扩容简单 | 可能不均匀 | 可按范围迁移 |

---

## Part B：Redis 优化

## 六、Redis 缓存的"三座大山"

```
         ┌────── 缓存穿透 ──────┐
         │  查一个不存在的数据    │
         │  → 每次穿透到 DB      │
         └──────────────────────┘

         ┌────── 缓存击穿 ──────┐
         │  热点 key 过期瞬间     │
         │  → 大量请求打到 DB    │
         └──────────────────────┘

         ┌────── 缓存雪崩 ──────┐
         │  大量 key 同时过期     │
         │  → DB 瞬间被打崩      │
         └──────────────────────┘
```

### 穿透解决方案：布隆过滤器

```python
import redis
from pybloom_live import BloomFilter

# 初始化布隆过滤器
bf = BloomFilter(capacity=10000000, error_rate=0.001)

# 预热：把所有存在的 ID 加入布隆过滤器
for product_id in get_all_product_ids():
    bf.add(product_id)

def get_product(product_id):
    # 布隆过滤器说"不存在" → 一定不存在，直接返回
    if product_id not in bf:
        return None
    
    # 布隆过滤器说"可能存在" → 查缓存 → 查 DB
    cache = r.get(f"product:{product_id}")
    if cache:
        return json.loads(cache)
    
    product = db.query(product_id)
    if product:
        r.setex(f"product:{product_id}", 3600, json.dumps(product))
    else:
        # 缓存空值，防止同一个不存在 key 反复穿透
        r.setex(f"product:{product_id}", 60, "NULL")
    return product
```

### 击穿解决方案：互斥锁

```python
def get_product_with_lock(product_id):
    # 先查缓存
    cache = r.get(f"product:{product_id}")
    if cache:
        return json.loads(cache) if cache != b"NULL" else None
    
    # 缓存没命中 → 加锁
    lock_key = f"lock:product:{product_id}"
    if r.setnx(lock_key, 1):
        r.expire(lock_key, 10)  # 防死锁
        
        try:
            # 双重检查
            cache = r.get(f"product:{product_id}")
            if cache:
                return json.loads(cache)
            
            product = db.query(product_id)
            if product:
                r.setex(f"product:{product_id}", 3600, json.dumps(product))
            else:
                r.setex(f"product:{product_id}", 60, "NULL")
            return product
        finally:
            r.delete(lock_key)
    else:
        # 没拿到锁 → 等一会儿再试
        time.sleep(0.05)
        return get_product_with_lock(product_id)  # 递归重试
```

### 雪崩解决方案：过期时间加随机

```python
import random

# ❌ 危险：所有缓存同一时间过期
r.setex(f"product:{product_id}", 3600, data)

# ✅ 安全：加随机偏移 0-600 秒
base_ttl = 3600
random_offset = random.randint(0, 600)
r.setex(f"product:{product_id}", base_ttl + random_offset, data)
```

---

## 七、Redis 性能调优速查

### 内存优化

```bash
# 查看大 key（阻塞风险！生产慎用）
redis-cli --bigkeys

# 查看内存使用
redis-cli INFO memory
```

| 优化手段 | 效果 |
|---------|------|
| 压缩 value（MessagePack/ProtoBuf 替代 JSON） | 节省 30-50% 内存 |
| 短 key 名（u:12345 替代 user:profile:12345） | 节省 10-20% 内存 |
| 设置 maxmemory + LRU 淘汰策略 | 防止 OOM |
| 用 Hash 代替 String 存对象 | 节省内存，方便部分字段更新 |

### 连接池配置

```python
# 推荐的连接池配置（Python redis-py）
pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,       # 别太大，CPU 核数 * 2 即可
    socket_timeout=5,         # 超时宁可失败，也别等
    socket_connect_timeout=2,
    health_check_interval=30  # 定期检查连接是否存活
)
```

### 危险的 Redis 命令（生产慎用）

```bash
❌ KEYS *          # 阻塞整个 Redis！用 SCAN 代替
❌ FLUSHALL        # 清库，删库跑路专用
❌ MONITOR         # 性能下降 50%
⚠️ HGETALL 大 Hash # 元素太多会阻塞
```

---

## 八、排查清单（顺着查）

```
□ 慢查询日志开了吗？
□ EXPLAIN type 列有没有 ALL？
□ 索引走了最左前缀吗？
□ 联合索引列有没有被函数包裹？
□ 能改成覆盖索引吗？
□ 分页有没有用游标代替 OFFSET？
□ Redis key 的过期时间有没有加随机偏移？
□ 热点 key 有没有互斥锁保护？
□ 有没有布隆过滤器防穿透？
□ 有没有处理缓存与 DB 双写一致性？
```

---

> **总结**：数据库优化没有银弹，但有规律。MySQL 的核心是"让索引干活"，Redis 的核心是"别让缓存变成攻击入口"。顺着排查清单走一遍，90% 的问题都能定位。

> 你遇到过最奇葩的数据库故障是什么？评论区展开讲讲。
