# 数据库选择之战：PostgreSQL vs MySQL vs SQLite

> 绝大多数人在选数据库时，只看了"谁更流行"，却忽略了"谁更适合我的场景"。
> 
> 这篇文章不讲废话，只讲我踩过的坑、写过的 SQL、掉过的头发。

---

## 先说结论

| 场景 | 推荐 | 为什么 |
|------|------|--------|
| 单机小程序、工具脚本、桌面应用 | **SQLite** | 零配置、零运维、嵌入式 |
| Web 应用、创业项目、快速迭代 | **PostgreSQL** | 功能强大、生态完善、JSON 支持好 |
| 传统企业应用、高频写入、主从分离需求 | **MySQL** | 生态成熟、运维方案多、云厂商支持好 |

**但如果你选错了，后果可能是：**

- SQLite 在高并发写入时锁死整个文件，10 个人并发写入就崩
- MySQL 处理复杂查询时，执行计划像在"盲猜"
- PostgreSQL 的 JSON 查询性能在数据量百万级后断崖下跌

---

## 一、我为什么从 MySQL 跳槽到 PostgreSQL

### 一个真实的 MySQL 惨案

2022 年，我负责一个电商项目的数据分析模块。需求很简单：统计用户行为日志，按天、按商品类目做聚合。

表结构大概是这样：

```sql
-- MySQL 的表结构
CREATE TABLE user_behavior_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    category_id INT NOT NULL,
    action VARCHAR(20) NOT NULL,  -- 'view', 'click', 'purchase'
    created_at DATETIME NOT NULL,
    extra_data TEXT,  -- JSON 字符串，MySQL 5.7 没有好用的 JSON 类型
    INDEX idx_user (user_id),
    INDEX idx_product (product_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

问题来了，产品经理要查"过去 30 天，每个类目下，用户购买前平均浏览了多少次"。

```sql
-- MySQL 的查询
SELECT 
    category_id,
    COUNT(DISTINCT user_id) AS unique_users,
    AVG(view_count) AS avg_views_before_purchase
FROM (
    SELECT 
        l.user_id,
        l.category_id,
        SUM(CASE WHEN l.action = 'view' THEN 1 ELSE 0 END) AS view_count,
        SUM(CASE WHEN l.action = 'purchase' THEN 1 ELSE 0 END) AS purchase_count
    FROM user_behavior_logs l
    WHERE l.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    GROUP BY l.user_id, l.category_id
    HAVING purchase_count > 0
) AS user_stats
GROUP BY category_id
ORDER BY avg_views_before_purchase DESC;
```

**执行时间：6 分 37 秒**（数据量 8000 万行）

优化了索引、加了覆盖索引、调整了查询顺序，最好也得 4 分多。

### PostgreSQL 的降维打击

后来迁移到 PostgreSQL，表结构改成这样：

```sql
-- PostgreSQL 的表结构
CREATE TABLE user_behavior_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    category_id INT NOT NULL,
    action VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    extra_data JSONB,  -- PostgreSQL 的 JSONB，支持索引
    INDEX idx_user (user_id),
    INDEX idx_product (product_id),
    INDEX idx_created (created_at),
    INDEX idx_extra_data_gin ON user_behavior_logs USING GIN (extra_data)  -- JSONB 索引
);
```

同样的查询：

```sql
-- PostgreSQL 写法
SELECT 
    category_id,
    COUNT(DISTINCT user_id) AS unique_users,
    AVG(view_count) AS avg_views_before_purchase
FROM (
    SELECT 
        user_id,
        category_id,
        COUNT(*) FILTER (WHERE action = 'view') AS view_count,
        COUNT(*) FILTER (WHERE action = 'purchase') AS purchase_count
    FROM user_behavior_logs
    WHERE created_at >= NOW() - INTERVAL '30 days'
    GROUP BY user_id, category_id
    HAVING COUNT(*) FILTER (WHERE action = 'purchase') > 0
) AS user_stats
GROUP BY category_id
ORDER BY avg_views_before_purchase DESC;
```

**执行时间：23 秒**（同样的 8000 万行数据）

为什么差这么多？

1. **PostgreSQL 的 FILTER 语法** 比 MySQL 的 `CASE WHEN` 更高效
2. **更智能的查询优化器** - PostgreSQL 能自动选择 hash aggregate
3. **更好的并行查询支持** - PostgreSQL 13+ 自动并行化这个查询

### PostgreSQL 的杀手锏：JSONB

MySQL 5.7 开始支持 JSON 类型，但说实话，**很鸡肋**。

```sql
-- MySQL 的 JSON 查询（慢到怀疑人生）
SELECT * FROM user_behavior_logs 
WHERE JSON_EXTRACT(extra_data, '$.source') = 'mobile_app'
  AND JSON_EXTRACT(extra_data, '$.version') > '2.0.0';
```

**索引？有，但要手动创建生成列 + 索引，麻烦得很。**

```sql
-- PostgreSQL 的 JSONB 查询（飞快）
SELECT * FROM user_behavior_logs 
WHERE extra_data @> '{"source": "mobile_app"}'::jsonb
  AND (extra_data->>'version')::float > 2.0;

-- 索引自动生效（因为我们创建了 GIN 索引）
```

实测：8000 万行数据，包含 JSON 字段的查询，PostgreSQL 0.8 秒，MySQL 12 秒。

**差距 15 倍。**

---

## 二、SQLite：被低估的王者

很多人瞧不起 SQLite，觉得它"玩具数据库"。

**这种想法是错的。**

### SQLite 的真实威力

我写过很多 Python 工具脚本，需要存储一些数据。之前用 MySQL，然后：

1. 要装 MySQL 服务
2. 要创建数据库
3. 要配置账号密码
4. 部署到客户机器上，可能版本不兼容
5. 客户机器没有 MySQL？崩溃

用 SQLite 后：

```python
import sqlite3
import json
from datetime import datetime

# 连接数据库（文件不存在自动创建）
conn = sqlite3.connect('my_tool.db')
conn.row_factory = sqlite3.Row  # 返回字典格式

# 创建表
conn.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        priority INTEGER DEFAULT 0,
        tags TEXT,  -- 存 JSON
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')

# 创建索引
conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority DESC)')

# 插入数据
conn.execute('''
    INSERT INTO tasks (title, status, priority, tags)
    VALUES (?, ?, ?, ?)
''', ('完成报告', 'in_progress', 5, json.dumps(['work', 'urgent'])))

conn.commit()

# 查询
cursor = conn.execute('''
    SELECT id, title, status, priority, tags, created_at
    FROM tasks
    WHERE status != 'completed'
    ORDER BY priority DESC, created_at ASC
    LIMIT 20
''')

for row in cursor.fetchall():
    print(dict(row))

conn.close()
```

**2 行代码启动，无需任何配置。**

### SQLite 的真实使用场景

| 场景 | 我用 SQLite 做过什么 |
|------|---------------------|
| 桌面应用配置存储 | Electron + SQLite 存用户偏好、历史记录 |
| 数据采集工具 | 爬虫把结果存 SQLite，然后导出 CSV |
| 本地缓存层 | 频繁 API 请求的数据缓存到 SQLite，过期删除 |
| 单元测试 | 测试数据库逻辑，每次测试创建新的 :memory: 数据库 |
| 移动 App | React Native + SQLite 存离线数据 |

```python
# 内存数据库，用于测试（超快）
import sqlite3

conn = sqlite3.connect(':memory:')

conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)')
conn.execute("INSERT INTO test (value) VALUES ('hello'), ('world')")

result = conn.execute('SELECT * FROM test').fetchall()
print(result)  # [(1, 'hello'), (2, 'world')]
```

### SQLite 的致命弱点

但 SQLite 不是万能的。**高并发写入是它的死穴。**

```python
# SQLite 写入测试（多线程）
import threading
import sqlite3
import time

def write_task(thread_id):
    conn = sqlite3.connect('test_concurrent.db', timeout=30)
    for i in range(100):
        try:
            conn.execute('INSERT INTO items (name) VALUES (?)', 
                        (f'thread_{thread_id}_item_{i}',))
            conn.commit()
        except sqlite3.OperationalError as e:
            print(f'Thread {thread_id} got error: {e}')
    conn.close()

# 创建表
conn = sqlite3.connect('test_concurrent.db')
conn.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)')
conn.close()

# 启动 10 个线程并发写入
threads = []
start = time.time()
for i in range(10):
    t = threading.Thread(target=write_task, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f'Total time: {time.time() - start:.2f}s')
```

**结果：满了 `database is locked` 错误。**

SQLite 使用文件锁，写入时会锁住整个数据库文件。虽然 WAL 模式能缓解，但依然不适合高并发写入场景。

```sql
-- 开启 WAL 模式（提升并发，但依然有限）
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;  -- 等待 5 秒而不是立即失败
```

**结论：SQLite 适合读多写少的场景，写并发超过 10 个线程就该考虑其他数据库了。**

---

## 三、MySQL：老牌选手的坚持

很多人说 MySQL 过时了，我不同意。

### MySQL 依然强大的场景

**1. 主从复制、读写分离**

MySQL 的主从复制方案非常成熟：

```
主库（写入）
   ├── 从库 1（读取）
   ├── 从库 2（读取）
   └── 从库 3（读取 + 备份）
```

```sql
-- 主库配置 (my.cnf)
[mysqld]
server-id = 1
log-bin = mysql-bin
binlog-format = ROW
gtid-mode = ON

-- 从库配置 (my.cnf)
[mysqld]
server-id = 2
relay-log = relay-bin
read-only = ON
```

PostgreSQL 也有流复制，但 MySQL 的方案更成熟、资料更多、云厂商支持更好。

**2. 云原生支持**

- AWS RDS MySQL
- 阿里云 PolarDB MySQL
- 腾讯云 TencentDB MySQL
- Google Cloud SQL MySQL

所有主流云厂商都对 MySQL 有最好的支持。

**3. 运维生态**

```bash
# MySQL 的运维工具非常丰富

# 备份
mysqldump -u root -p mydb > backup.sql
mydumper -u root -p -B mydb -o /backup/mydb

# 监控
pt-query-digest /var/log/mysql/slow.log
mysqltuner

# 主从切换
mysqlrpladmin --master=root@master:3306 --slaves=root@slave1:3306,root@slave2:3306 switchover
```

### MySQL 的真实代码示例

我维护过一个用户系统，MySQL 表设计：

```sql
CREATE TABLE users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    status TINYINT DEFAULT 1 COMMENT '1-active, 0-inactive, -1-banned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    INDEX idx_phone (phone),
    INDEX idx_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户登录日志
CREATE TABLE user_login_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    ip VARCHAR(45) NOT NULL,
    user_agent VARCHAR(500),
    login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TINYINT DEFAULT 1 COMMENT '1-success, 0-failed',
    INDEX idx_user_time (user_id, login_at),
    INDEX idx_ip (ip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**查询示例：**

```sql
-- 查询活跃用户（过去 30 天登录过）
SELECT u.id, u.username, u.email, COUNT(l.id) AS login_count
FROM users u
INNER JOIN user_login_logs l ON u.id = l.user_id
WHERE l.login_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
  AND l.status = 1
GROUP BY u.id, u.username, u.email
HAVING login_count >= 5
ORDER BY login_count DESC
LIMIT 100;

-- 查询异常登录（同一用户不同 IP 登录）
SELECT 
    user_id,
    GROUP_CONCAT(DISTINCT ip) AS login_ips,
    COUNT(*) AS total_logins,
    MIN(login_at) AS first_login,
    MAX(login_at) AS last_login
FROM user_login_logs
WHERE login_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY user_id
HAVING COUNT(DISTINCT ip) >= 3
ORDER BY total_logins DESC;
```

### MySQL 的坑

**1. 字符集问题**

```sql
-- 错误的配置（会导致 emoji 存储失败）
CREATE TABLE users (
    name VARCHAR(100)
) CHARSET=utf8;  -- utf8 是 utf8mb3，不支持 4 字节字符

-- 正确的配置
CREATE TABLE users (
    name VARCHAR(100)
) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;  -- 支持 emoji
```

**2. 大表 DDL 卡死**

```sql
-- 直接加字段，线上百万级表会锁表几分钟
ALTER TABLE users ADD COLUMN nickname VARCHAR(100);

-- 解决方案：使用 pt-online-schema-change
-- pt-online-schema-change --alter "ADD COLUMN nickname VARCHAR(100)" D=mydb,t=users
```

---

## 四、PostgreSQL vs MySQL：关键差异对比

### 1. 数据类型

| 功能 | PostgreSQL | MySQL |
|------|------------|-------|
| JSON | **JSONB**（二进制，支持索引，快） | JSON（文本，索引支持差，慢） |
| 数组 | **原生支持** `INTEGER[]`, `TEXT[]` | 不支持（用 JSON 或逗号分隔字符串模拟） |
| 全文搜索 | **内置 tsvector**，支持中文分词 | 需要第三方插件或 Elasticsearch |
| 地理空间 | **PostGIS** 扩展，功能强大 | 简单 GEOMETRY 类型，功能有限 |
| 自定义类型 | **支持** CREATE TYPE | 不支持 |

```sql
-- PostgreSQL 数组查询
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    tags TEXT[]  -- 数组类型
);

INSERT INTO posts (title, tags) VALUES 
('PostgreSQL 教程', ARRAY['数据库', 'PostgreSQL', '教程']),
('Python 入门', ARRAY['编程', 'Python', '入门']);

-- 查询包含某个标签的文章
SELECT * FROM posts WHERE 'PostgreSQL' = ANY(tags);

-- 查询同时包含多个标签的文章
SELECT * FROM posts WHERE tags @> ARRAY['数据库', '教程']::TEXT[];
```

### 2. 性能对比实例

我做过一个基准测试，同样 100 万行订单数据：

```sql
-- 复杂聚合查询
SELECT 
    user_id,
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*) AS order_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount
FROM orders
WHERE created_at >= '2023-01-01'
GROUP BY user_id, DATE_TRUNC('month', created_at)
HAVING COUNT(*) >= 3
ORDER BY total_amount DESC
LIMIT 100;
```

| 数据库 | 执行时间 | 索引使用 |
|--------|----------|----------|
| MySQL 8.0 | 8.2 秒 | 用了索引扫描 |
| PostgreSQL 15 | 1.9 秒 | 用了并行扫描 + HashAggregate |

**PostgreSQL 快 4 倍。**

---

## 五、选型决策框架

### 场景 1：个人项目 / 小团队（< 10 人）

**推荐：PostgreSQL 或 SQLite**

```python
# 如果是单机 Web 服务，用 PostgreSQL
# docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

```python
# 如果是脚本/工具，用 SQLite
import sqlite3
import os

DB_PATH = os.path.expanduser('~/.myapp/data.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn
```

### 场景 2：创业项目 / 中型团队（10-100 人）

**推荐：PostgreSQL**

理由：
1. 功能强大，扩展性好
2. 开源，无需授权费
3. JSONB 支持好，减少数据库迁移
4. 良好的 Python/Node.js 生态

```python
# Python + SQLAlchemy + PostgreSQL
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

engine = create_engine(
    'postgresql://user:pass@localhost/mydb',
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True  # 自动检测断开的连接
)

Session = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    profile = Column(JSON)  # PostgreSQL JSONB
    created_at = Column(DateTime, default=datetime.utcnow)

# 创建表
Base.metadata.create_all(engine)

# 使用
session = Session()
user = User(
    email='test@example.com',
    username='testuser',
    profile={'age': 25, 'city': 'Beijing'}
)
session.add(user)
session.commit()
```

### 场景 3：企业应用 / 高并发系统（> 100 人团队）

**推荐：MySQL（如果需要成熟运维方案）或 PostgreSQL（如果技术团队强）**

评估维度：

| 维度 | MySQL | PostgreSQL |
|------|-------|------------|
| 云厂商支持 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 主从复制 | 非常成熟 | 成熟 |
| 运维工具 | 丰富 | 较少 |
| 查询优化器 | 一般 | 优秀 |
| JSON 支持 | 一般 | 优秀 |
| 全文搜索 | 弱 | 内置 |
| 学习曲线 | 平缓 | 稍陡 |

---

## 六、我的真实项目决策案例

### 案例 1：基金持仓管理系统

**需求：**
- 管理多个基金的持仓数据
- 每日更新净值
- 支持复杂查询（按收益排名、按行业分布等）
- 用户 < 100 人
- 部署在单台服务器

**我的选择：PostgreSQL**

```sql
-- 基金表
CREATE TABLE funds (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,  -- 基金代码
    name VARCHAR(100) NOT NULL,
    fund_type VARCHAR(50),  -- 股票型、混合型、债券型等
    manager VARCHAR(50),
    company VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 持仓表（使用 JSONB 存储持仓明细）
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    fund_id INTEGER REFERENCES funds(id),
    report_date DATE NOT NULL,
    stocks JSONB,  -- 持仓股票明细
    bonds JSONB,   -- 持仓债券明细
    cash_ratio DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_id, report_date)
);

-- 净值表（使用分区表）
CREATE TABLE nav_history (
    fund_id INTEGER REFERENCES funds(id),
    nav_date DATE NOT NULL,
    nav DECIMAL(10,4) NOT NULL,
    daily_return DECIMAL(8,6),
    PRIMARY KEY (fund_id, nav_date)
) PARTITION BY RANGE (nav_date);

-- 索引
CREATE INDEX idx_holdings_stocks ON holdings USING GIN (stocks);

-- 查询：某基金的股票持仓前 10
SELECT 
    stock->>'code' AS stock_code,
    stock->>'name' AS stock_name,
    (stock->>'ratio')::DECIMAL AS holding_ratio
FROM holdings,
     LATERAL jsonb_array_elements(stocks) AS stock
WHERE fund_id = (SELECT id FROM funds WHERE code = '161725')
  AND report_date = '2023-12-31'
ORDER BY (stock->>'ratio')::DECIMAL DESC
LIMIT 10;
```

**为什么选 PostgreSQL？**
1. JSONB 存储持仓数据，灵活且高效
2. 分区表处理历史净值数据
3. 复杂查询性能好

### 案例 2：爬虫数据采集工具

**需求：**
- 每天采集几万条数据
- 单机运行
- 无需网络服务
- 数据导出为 CSV/Excel

**我的选择：SQLite**

```python
import sqlite3
from contextlib import contextmanager

DB_PATH = 'crawler_data.db'

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS crawler_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# 使用
init_db()
with get_db() as conn:
    conn.execute('INSERT INTO crawler_tasks (url) VALUES (?)', ('https://example.com',))
    conn.commit()
```

**为什么选 SQLite？**
1. 零配置，直接运行
2. 文件即数据库，备份、迁移方便
3. Python 内置支持

---

## 七、总结：选型心法

### 先问自己三个问题

1. **数据量多大？**
   - < 1GB：SQLite 足够
   - 1GB - 1TB：PostgreSQL 或 MySQL
   - > 1TB：考虑分库分表或专用数据库（ClickHouse、MongoDB）

2. **并发多高？**
   - < 10 QPS：任何数据库
   - 10-1000 QPS：PostgreSQL 或 MySQL
   - > 1000 QPS：MySQL 主从、PostgreSQL 连接池

3. **查询多复杂？**
   - 简单 CRUD：任何数据库
   - 复杂聚合、分析：PostgreSQL
   - 全文搜索：PostgreSQL tsvector 或 Elasticsearch

### 我的个人偏好

- **新项目默认 PostgreSQL**：功能强大，很少后悔
- **个人工具默认 SQLite**：零配置，够用就行
- **企业项目按需选择**：看团队技术栈和运维能力

### 记住一句话

> 数据库没有银弹，只有最适合场景的选择。
> 
> 性能不是第一位的，**够用才是**。

---

**最后，这里有我常用的连接字符串模板：**

```python
# PostgreSQL
DATABASE_URL = "postgresql://user:password@localhost:5432/mydb"

# MySQL
DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/mydb?charset=utf8mb4"

# SQLite
DATABASE_URL = "sqlite:///./mydb.db"  # 文件数据库
DATABASE_URL = "sqlite:///:memory:"   # 内存数据库

# 异步支持（FastAPI / Sanic）
# PostgreSQL
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/mydb"

# MySQL
DATABASE_URL = "mysql+aiomysql://user:password@localhost:3306/mydb?charset=utf8mb4"
```

**愿你在数据库选型之路上，少踩坑，多产出！**