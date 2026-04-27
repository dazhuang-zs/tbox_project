# Spark vs Flink：2026 年大数据处理选型终极指南

> **摘要**：每次技术选型讨论"批处理用 Spark，流处理用 Flink"，这个说法在 2026 年还成立吗？本文从架构原理、性能实测、成本对比三个维度，深度对比 Spark 3.5+ 和 Flink 2.0+ 的差异。附带真实场景的选型决策树和代码示例——读完你就能做出正确的技术决策。

---

## 一、那个经典的问题

> "我们公司要做实时数仓，用 Spark 还是 Flink？"

如果是 2018 年，答案很明确：Flink。

如果是 2026 年——答案变复杂了。

Spark Structured Streaming 已经相当成熟，Flink 也在强化批处理能力。两者在互相侵入对方的领地。本文基于最新的版本（Spark 3.5+, Flink 2.0+），给你一份诚实的对比。

---

## 二、架构层面的根本差异

### Spark：微批处理引擎

```
数据流 → [Micro-Batch] → [Micro-Batch] → [Micro-Batch] → 结果
         ← 延迟：100ms-1s →
```

Spark Streaming（含 Structured Streaming）本质上是**微批处理**。它把一个流切成一小段一小段的批次来处理。延迟通常在 100ms 到 1s 之间。

**优点**：容错简单（基于 RDD lineage）、Exactly-Once 开箱即用、SQL 支持完善。
**缺点**：延迟下不去（不是真正的逐条处理）。

### Flink：真正的流处理引擎

```
数据流 → event → event → event → event → event → 结果
         ← 延迟：毫秒级 →
```

Flink 是真正的**逐事件处理**。每个事件到达后立即处理，延迟可以到毫秒级。

**优点**：真正的低延迟、状态管理强大（RocksDB State Backend）、事件时间处理精准。
**缺点**：学习曲线陡峭、SQL 成熟度不如 Spark。

### 一张表看懂核心差异

| 维度 | Spark 3.5+ | Flink 2.0+ |
|------|-----------|-----------|
| 处理模型 | 微批处理 | 逐事件流处理 |
| 最低延迟 | ~100ms | ~1ms |
| 状态后端 | 内存/HDFS | RocksDB（默认） |
| Exactly-Once | ✅（Checkpoint） | ✅（Checkpoint + 二阶段提交） |
| SQL 支持 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 批处理性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 流处理性能 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 学习曲线 | 中等 | 陡峭 |
| 生态集成 | Hadoop/Hive/Delta Lake | Kafka/Pulsar/Iceberg |

---

## 三、核心代码对比：同一个 WordCount

### Spark Structured Streaming

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import explode, split, window

spark = SparkSession.builder \
    .appName("WordCount") \
    .getOrCreate()

# 读取 Kafka
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "input-topic") \
    .load()

# 处理
words = df.select(
    explode(split(df.value.cast("string"), " ")).alias("word"),
    df.timestamp
)

windowed = words \
    .withWatermark("timestamp", "10 minutes") \
    .groupBy(window("timestamp", "5 minutes"), "word") \
    .count()

# 输出
query = windowed.writeStream \
    .outputMode("update") \
    .format("console") \
    .start()

query.awaitTermination()
```

### Flink DataStream

```java
StreamExecutionEnvironment env = 
    StreamExecutionEnvironment.getExecutionEnvironment();

DataStream<String> text = env
    .addSource(new FlinkKafkaConsumer<>(
        "input-topic",
        new SimpleStringSchema(),
        properties
    ));

DataStream<Tuple2<String, Integer>> counts = text
    .flatMap(new Tokenizer())
    .keyBy(value -> value.f0)
    .window(TumblingProcessingTimeWindows.of(Time.minutes(5)))
    .sum(1);

counts.print();
env.execute("WordCount");
```

### Flink SQL（2026 推荐写法）

```sql
-- Flink SQL 是趋势，大幅降低开发成本
CREATE TABLE input (
    word STRING,
    ts TIMESTAMP(3),
    WATERMARK FOR ts AS ts - INTERVAL '30' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'input-topic',
    'properties.bootstrap.servers' = 'localhost:9092',
    'format' = 'json'
);

CREATE TABLE output (
    word STRING,
    cnt BIGINT,
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3)
) WITH (
    'connector' = 'print'
);

INSERT INTO output
SELECT 
    word, 
    COUNT(*) as cnt,
    TUMBLE_START(ts, INTERVAL '5' MINUTE),
    TUMBLE_END(ts, INTERVAL '5' MINUTE)
FROM input
GROUP BY word, TUMBLE(ts, INTERVAL '5' MINUTE);
```

---

## 四、2026 年的五个关键选型场景

### 场景 1：实时数仓（秒级延迟 OK）

**推荐：Spark Structured Streaming**

理由：Spark SQL 和 DataFrame API 非常成熟，和 Hive、Delta Lake 集成天然。微批处理的延迟（秒级）对大多数数仓场景完全够用。

```python
# Spark + Delta Lake 实时写入
df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/checkpoint/orders") \
    .trigger(processingTime="10 seconds") \
    .start("/delta/orders")
```

### 场景 2：风控/欺诈检测（毫秒级必须）

**推荐：Flink CEP（复杂事件处理）**

理由：欺诈检测需要毫秒级响应 + 复杂事件模式匹配。Flink CEP 是唯一选择。

```java
// Flink CEP：检测 5 分钟内同一用户 3 次失败登录
Pattern<LoginEvent, ?> pattern = Pattern.<LoginEvent>begin("first")
    .where(event -> event.getStatus().equals("FAIL"))
    .next("second")
    .where(event -> event.getStatus().equals("FAIL"))
    .within(Time.minutes(5))
    .times(3);

CEP.pattern(stream, pattern)
    .select(pattern -> {
        // 触发风控报警
        return new Alert(pattern.get("first"));
    });
```

### 场景 3：离线 ETL（T+1 批处理）

**推荐：Spark Batch（不是 Structured Streaming）**

理由：Spark 的批处理性能仍然是业界标杆。Shuffle 优化、AQE（自适应查询执行）、动态分区裁剪——这些都是 Spark 的强项。

```python
# Spark AQE 自动优化
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

df = spark.sql("""
    SELECT /*+ BROADCAST(small_table) */
        large_table.*,
        small_table.desc
    FROM large_table
    JOIN small_table ON large_table.id = small_table.id
""")
```

### 场景 4：流批一体（同一套代码）

**推荐：Flink SQL**

理由：Flink 2.0 的流批一体已经相当成熟。同一段 SQL 可以跑流模式也可以跑批模式。特别适合需要频繁切换的场景。

```sql
-- 同一段 SQL，改个模式就行
SET 'execution.runtime-mode' = 'streaming';  -- 或 'batch'

SELECT 
    product_id,
    SUM(amount) as total,
    COUNT(DISTINCT user_id) as uv
FROM orders
GROUP BY product_id;
```

### 场景 5：AI/ML Pipeline

**推荐：Spark MLlib + Spark Structured Streaming**

理由：Spark 的 MLlib 生态完善，和 PyTorch/TensorFlow 的互操作性好。Flink 在 ML 领域的支持还比较基础。

```python
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.classification import RandomForestClassifier

# 在线推理
predictions = streaming_df \
    .select("features") \
    .transform(loaded_model)

predictions.writeStream \
    .format("kafka") \
    .option("topic", "predictions") \
    .start()
```

---

## 五、性能实测（来自公开 Benchmark）

| 场景 | Spark 3.5 | Flink 2.0 | 差距 |
|------|-----------|-----------|------|
| 1TB 数据聚合（批） | 62s | 78s | Spark 快 20% |
| 百万 QPS 流处理 | 延迟 800ms | 延迟 5ms | Flink 快 160x |
| SQL Join（10亿行） | 45s | 52s | Spark 快 13% |
| Checkpoint 恢复 | 12s | 8s | Flink 快 33% |
| 窗口聚合（10万QPS） | 正确 | 正确 | 持平 |

> 数据来源：2025 Q4 TPC-DS + Nexmark Benchmark 综合数据。

---

## 六、选型决策树

```
你的数据延迟要求是？
├── 毫秒级（<100ms）→ Flink
├── 秒级（1s-1min）→ 看团队
│    ├── 团队熟悉 Spark → Spark Structured Streaming
│    └── 团队有 Java/Scala 高手 → Flink
└── 分钟级以上 → Spark Batch

你的主要操作是？
├── 复杂 SQL 分析 → Spark
├── 复杂事件模式匹配 → Flink CEP  
├── 机器学习 → Spark MLlib
└── 简单 ETL → 两个都行，看团队

你的团队现状是？
├── Python 为主 → Spark（PySpark 成熟）
├── Java/Scala 为主 → 两个都可以
└── 想写 SQL 不写代码 → Flink SQL（流批一体更好）
```

---

## 七、2026 年值得关注的趋势

**1. Flink SQL 正在吞噬 Flink DataStream**

越来越多的场景可以直接用 SQL 完成，不需要写 Java/Scala。这对降低 Flink 使用门槛是革命性的。

**2. Spark + Delta Lake 成为 Lakehouse 标准组合**

Databricks 的全套方案（Spark + Delta + Unity Catalog + Photon）在 2026 年已经形成闭环。如果你在 Databricks 生态里，没理由用别的。

**3. Flink + Paimon（Apache Paimon）对打 Delta Lake**

阿里开源了 Paimon（原 Flink Table Store），试图在流式数仓领域复刻 Delta Lake 的体验。这是 Flink 生态在向 Lakehouse 靠拢。

**4. Rust 重写底层引擎**

Spark 的 Photon 引擎（C++）和 Flink 的部分算子重写（Rust）表明：JVM 不是大数据的唯一答案。原生代码的性能提升可达 3-5 倍。

---

> **总结**：2026 年，Spark 和 Flink 的边界越来越模糊。但核心差异没变——Spark 擅长吞吐量，Flink 擅长延迟。选型的本质不是技术优劣，而是你的业务到底需要什么。把"批处理用 Spark、流处理用 Flink"改为"吞吐优先 Spark、延迟优先 Flink、简单场景上 SQL"。

> 你们公司在用 Spark 还是 Flink？实际踩过什么坑？评论区聊聊。
