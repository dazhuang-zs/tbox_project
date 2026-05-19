# MySQL 慢查询优化实战：从 3 秒到 50 毫秒的全过程

> 你是否遇到过这样的场景：用户反馈页面加载很慢，打开慢查询日志一看，一条 SQL 跑了 3 秒多。这篇文章带你从定位到根治，完整走一遍慢查询优化的实战流程。

---

## 一、现象：接口超时告警

某天下午，监控系统发出告警：`/api/orders/list` 接口 P99 响应时间飙到 5 秒以上。

排查链路：

```
用户投诉 → 接口超时 → 数据库 CPU 飙升 → 慢查询日志暴增
```

登录 MySQL，查看慢查询 TOP 10：

```sql
-- 确认慢查询是否开启
SHOW VARIABLES LIKE 'slow_query_log%';
SHOW VARIABLES LIKE 'long_query_time';

-- 如果没有开启，临时开启（重启失效）
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 0.5;  -- 超过 0.5 秒即记录
```

用 `mysqldumpslow` 分析慢查询日志：

```bash
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log
```

输出：

```
Count: 1287  Time=3.27s  Lock=0.01s  Rows=20
  SELECT o.*, u.nickname, COUNT(oi.id) AS item_count
  FROM orders o
  LEFT JOIN users u ON o.user_id = u.id
  LEFT JOIN order_items oi ON o.id = oi.order_id
  WHERE o.status = 'paid' AND o.created_at > '2025-01-01'
  GROUP BY o.id
  ORDER BY o.created_at DESC
  LIMIT 20;
```

核心信息：**3.27 秒 / 次，一天跑了 1287 次**。光这一条 SQL 每天就浪费 1 小时+ 的数据库时间。

---

## 二、诊断：EXPLAIN 分析

```sql
EXPLAIN SELECT o.*, u.nickname, COUNT(oi.id) AS item_count
FROM orders o
LEFT JOIN users u ON o.user_id = u.id
LEFT JOIN order_items oi ON o.id = oi.order_id
WHERE o.status = 'paid' AND o.created_at > '2025-01-01'
GROUP BY o.id
ORDER BY o.created_at DESC
LIMIT 20;
```

EXPLAIN 输出：

| id | select_type | table | type | key | rows | Extra |
|:--:|:-----------:|:-----:|:----:|:---:|:----:|:-----:|
| 1 | SIMPLE | o | **ALL** | NULL | **483716** | Using where; Using temporary; Using filesort |
| 1 | SIMPLE | u | eq_ref | PRIMARY | 1 | |
| 1 | SIMPLE | oi | ref | idx_order_id | 5 | |

🚨 **问题一目了然**：

| 问题 | 严重程度 | 说明 |
|------|:---:|------|
| `o` 表走了 **ALL**（全表扫描） | 🔴 致命 | 48 万行全扫 |
| `Using temporary` | 🔴 严重 | GROUP BY 创建了临时表 |
| `Using filesort` | 🟡 中等 | ORDER BY 走了文件排序 |

**根因**：`orders` 表在 `(status, created_at)` 上没有联合索引，导致 MySQL 全表扫描 48 万行数据，然后再排序、分组。

---

## 三、救治：三步优化

### 3.1 第一步：加联合索引

```sql
-- 查看现有索引
SHOW INDEX FROM orders;

-- 创建联合索引：覆盖 WHERE + ORDER BY
ALTER TABLE orders ADD INDEX idx_status_created (status, created_at);
```

> **为什么是 `(status, created_at)` 而不是反过来？**
>
> `status` 是等值查询（`=`），放在前面；`created_at` 是范围查询（`>`），放在后面。这是最左前缀原则的经典应用。

加完索引后再 EXPLAIN：

| id | table | type | key | rows | Extra |
|:--:|:-----:|:----:|:---:|:----:|:-----:|
| 1 | o | **range** | **idx_status_created** | **12450** | Using where; Using temporary; Using filesort |

扫描行数从 **48 万降到 1.2 万**，type 从 ALL 变成 range。但还有 `Using temporary` 和 `Using filesort`。

### 3.2 第二步：消除临时表和文件排序

`GROUP BY o.id` 和 `ORDER BY o.created_at` 用了不同的列，MySQL 必须建临时表。优化思路：

```sql
-- 优化后的 SQL：先过滤再关联，利用覆盖索引
SELECT o.*, u.nickname, 
       (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) AS item_count
FROM orders o FORCE INDEX (idx_status_created)
LEFT JOIN users u ON o.user_id = u.id
WHERE o.status = 'paid' AND o.created_at > '2025-01-01'
ORDER BY o.created_at DESC
LIMIT 20;
```

> **技巧说明**：用标量子查询代替 `JOIN + GROUP BY`，避免临时表。`FORCE INDEX` 确保 MySQL 走我们指定的索引。

### 3.3 第三步：减少回表

上面的查询还需要回 `orders` 表拿 `SELECT o.*` 的数据。如果业务不需要全部字段，用覆盖索引进一步优化：

```sql
-- 创建覆盖索引（包含 SELECT 和 WHERE 涉及的列）
ALTER TABLE orders ADD INDEX idx_status_created_cover 
  (status, created_at, id, user_id, amount);

-- 最终优化版 SQL
SELECT o.id, o.user_id, o.amount, o.created_at, o.status,
       u.nickname,
       (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) AS item_count
FROM orders o
LEFT JOIN users u ON o.user_id = u.id
WHERE o.status = 'paid' AND o.created_at > '2025-01-01'
ORDER BY o.created_at DESC
LIMIT 20;
```

---

## 四、验证：对比数据

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|:---:|
| 执行时间 | **3.27 秒** | **0.048 秒** | **98.5%** ⬇️ |
| 扫描行数 | 483,716 | 12,450 | **97.4%** ⬇️ |
| type | ALL | range | — |
| Extra | Using temporary; Using filesort | Using index condition | — |
| 索引命中 | 无 | idx_status_created_cover | — |

48 毫秒，比 50 毫秒目标还快。

---

## 五、复盘：慢查询优化方法论

```
┌──────────────────────────────────────────┐
│           慢查询优化四步法                  │
├──────────────────────────────────────────┤
│  ① 定位：慢查询日志 / Performance Schema  │
│  ② 分析：EXPLAIN → type/rows/Extra       │
│  ③ 优化：加索引 → 改写 SQL → 覆盖索引     │
│  ④ 验证：对比执行时间 + EXPLAIN           │
└──────────────────────────────────────────┘
```

### 常用诊断命令速查

```sql
-- 1. 查看当前正在执行的查询
SHOW FULL PROCESSLIST;

-- 2. 查看表索引使用情况
SELECT * FROM sys.schema_unused_indexes;

-- 3. 查看哪些查询没用索引（全表扫描）
SELECT * FROM sys.statements_with_full_table_scans 
WHERE db = 'your_database' 
ORDER BY exec_count DESC 
LIMIT 10;

-- 4. 查看表统计信息（索引基数）
SHOW INDEX FROM orders;
ANALYZE TABLE orders;  -- 更新统计信息
```

### 生产环境加索引的安全姿势

```sql
-- ❌ 错误：高峰期直接加索引，锁表 5 分钟
ALTER TABLE orders ADD INDEX idx_xxx (column1, column2);

-- ✅ 正确：使用 ALGORITHM=INPLACE（MySQL 5.6+）
ALTER TABLE orders 
  ADD INDEX idx_xxx (column1, column2) 
  ALGORITHM=INPLACE, LOCK=NONE;

-- ✅ 更安全：用 pt-online-schema-change（Percona Toolkit）
pt-online-schema-change \
  --alter "ADD INDEX idx_xxx (column1, column2)" \
  D=your_db,t=orders \
  --execute
```

---

## 六、常见误区

| 误区 | 真相 |
|------|------|
| 「加索引越多越好」 | 每个索引拖慢写入，占用空间。按查询模式精确加 |
| 「EXPLAIN rows 少就一定快」 | rows 是估算值，实际看执行时间 |
| 「MySQL 会自动选最优索引」 | 大部分时候会，但统计信息不准时会选错，需要 FORCE INDEX |
| 「JOIN 一定比子查询快」 | 不一定。本例中关联子查询反而消除了临时表 |
| 「慢查询只和 SQL 有关」 | 还和锁竞争、Buffer Pool 命中率、磁盘 I/O 有关 |

---

## 七、延伸：预防慢查询的日常习惯

1. **Code Review 必查 SQL** —— 每个涉及数据库的 PR，强制附 EXPLAIN 截图
2. **慢查询阈值设 200ms** —— 不要等到用户投诉才发现
3. **ORM 日志全开** —— Django/MyBatis/GORM 的 SQL 日志是排查利器
4. **压测时同时监控慢查询** —— 别只看 QPS，慢查询曲线同样重要

---

> 下一篇文章预告：**《数据库索引原理：B+ 树为什么是最优解》**—— 从 B 树到 B+ 树再到 LSM 树，用图说话，讲透索引的底层逻辑。

*本文所有 SQL 在 MySQL 8.0 上验证通过。*
