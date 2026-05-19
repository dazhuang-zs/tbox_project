# FastAPI + SQLite 从零搭建记账系统（完整项目）

> 用 200 行代码搭一个能用的个人记账系统，前后端分离，API 文档自动生成。看完就能跑。

---

## 一、为什么选这个技术栈

| 技术 | 选择理由 |
|------|---------|
| **FastAPI** | Python 最快的 Web 框架之一，自动生成 Swagger 文档，类型安全 |
| **SQLite** | 零配置、单文件、无需安装服务，个人项目首选 |
| **SQLAlchemy** | Python 最强 ORM，异步支持好，防 SQL 注入 |
| **Pydantic** | FastAPI 原生支持，请求/响应自动校验 |

> 目标受众：有 Python 基础，想在 30 分钟内跑起来一个真实项目的开发者。

---

## 二、项目结构

```
accounting-app/
├── main.py          # FastAPI 入口
├── models.py        # 数据库模型
├── schemas.py       # Pydantic 请求/响应模型
├── database.py      # 数据库连接
├── crud.py          # 增删改查逻辑
└── requirements.txt
```

---

## 三、完整代码

### 3.1 依赖安装

```bash
pip install fastapi uvicorn sqlalchemy pydantic
```

`requirements.txt`：

```
fastapi==0.115.0
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
pydantic==2.9.0
```

### 3.2 database.py —— 数据库连接

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./accounting.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 需要
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """每个请求获取独立的数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 3.3 models.py —— 数据表定义

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SAEnum
from datetime import datetime
import enum

from database import Base


class CategoryEnum(str, enum.Enum):
    """交易分类"""
    FOOD = "餐饮"
    TRANSPORT = "交通"
    SHOPPING = "购物"
    ENTERTAINMENT = "娱乐"
    SALARY = "工资"
    INVESTMENT = "投资"
    RENT = "房租"
    OTHER = "其他"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False, comment="金额，支出为负数")
    category = Column(
        SAEnum(CategoryEnum, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="交易分类"
    )
    note = Column(String(200), default="", comment="备注")
    trans_date = Column(
        DateTime,
        default=datetime.utcnow,  # Python 3.12+ 改为 datetime.now(timezone.utc)
        index=True,
        comment="交易日期"
    )
    created_at = Column(DateTime, default=datetime.utcnow)  # Python 3.12+ 改为 datetime.now(timezone.utc)
```

> 💡 **设计要点**：支出用负数，收入用正数。这样查月度结余时直接 `SUM(amount)` 即可，不需要额外字段。

### 3.4 schemas.py —— 请求/响应模型

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TransactionCreate(BaseModel):
    """创建交易"""
    amount: float = Field(..., description="金额，支出为负数")
    category: str = Field(..., description="交易分类")
    note: str = Field(default="", max_length=200)
    trans_date: Optional[datetime] = None


class TransactionOut(BaseModel):
    """交易响应"""
    id: int
    amount: float
    category: str
    note: str
    trans_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 替代 orm_mode


class MonthlySummary(BaseModel):
    """月度汇总"""
    month: str
    total_income: float
    total_expense: float
    balance: float
    transaction_count: int
    top_categories: list[dict]
```

### 3.5 crud.py —— 业务逻辑

```python
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime

from models import Transaction


def create_transaction(db: Session, data: dict) -> Transaction:
    """新增一笔交易"""
    if not data.get("trans_date"):
        data["trans_date"] = datetime.utcnow()  # Python 3.12+ 改为 datetime.now(timezone.utc)
    txn = Transaction(**data)
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def get_transactions(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    category: str | None = None,
    month: str | None = None  # 格式: "2025-06"
) -> list[Transaction]:
    """分页查询交易记录，支持按分类和月份筛选"""
    query = db.query(Transaction)
    
    if category:
        query = query.filter(Transaction.category == category)
    if month:
        year, mon = map(int, month.split("-"))
        query = query.filter(
            extract("year", Transaction.trans_date) == year,
            extract("month", Transaction.trans_date) == mon
        )
    
    return query.order_by(Transaction.trans_date.desc()).offset(skip).limit(limit).all()


def get_monthly_summary(db: Session, month: str) -> dict:
    """月度收支汇总"""
    year, mon = map(int, month.split("-"))
    
    records = db.query(Transaction).filter(
        extract("year", Transaction.trans_date) == year,
        extract("month", Transaction.trans_date) == mon
    ).all()
    
    total_income = sum(r.amount for r in records if r.amount > 0)
    total_expense = sum(abs(r.amount) for r in records if r.amount < 0)
    
    # 分类统计
    from collections import Counter
    category_totals = Counter()
    for r in records:
        if r.amount < 0:
            category_totals[r.category] += abs(r.amount)
    
    top_categories = [
        {"category": cat, "amount": round(amt, 2)}
        for cat, amt in category_totals.most_common(5)
    ]
    
    return {
        "month": month,
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "balance": round(total_income - total_expense, 2),
        "transaction_count": len(records),
        "top_categories": top_categories
    }


def update_transaction(db: Session, txn_id: int, data: dict) -> Transaction | None:
    """更新交易"""
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        return None
    for key, value in data.items():
        setattr(txn, key, value)
    db.commit()
    db.refresh(txn)
    return txn


def delete_transaction(db: Session, txn_id: int) -> bool:
    """删除交易"""
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        return False
    db.delete(txn)
    db.commit()
    return True
```

### 3.6 main.py —— API 入口

```python
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import engine, get_db, Base
from models import CategoryEnum
from schemas import TransactionCreate, TransactionOut, MonthlySummary
import crud

# 自动建表（生产环境请用 Alembic）
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="个人记账系统",
    description="FastAPI + SQLite 实战项目",
    version="1.0.0"
)


@app.post("/transactions", response_model=TransactionOut)
def add_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    """新增一笔交易"""
    return crud.create_transaction(db, data.model_dump())


@app.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    month: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """分页查询交易记录"""
    return crud.get_transactions(db, skip=skip, limit=limit, category=category, month=month)


@app.get("/summary/{month}", response_model=MonthlySummary)
def monthly_summary(month: str, db: Session = Depends(get_db)):
    """月度收支汇总（month 格式：2025-06）"""
    return crud.get_monthly_summary(db, month)


@app.put("/transactions/{txn_id}", response_model=TransactionOut)
def edit_transaction(txn_id: int, data: TransactionCreate, db: Session = Depends(get_db)):
    """更新一条交易"""
    txn = crud.update_transaction(db, txn_id, data.model_dump())
    if not txn:
        raise HTTPException(status_code=404, detail="交易不存在")
    return txn


@app.delete("/transactions/{txn_id}")
def remove_transaction(txn_id: int, db: Session = Depends(get_db)):
    """删除一条交易"""
    ok = crud.delete_transaction(db, txn_id)
    if not ok:
        raise HTTPException(status_code=404, detail="交易不存在")
    return {"message": "删除成功"}


@app.get("/categories")
def list_categories():
    """获取所有交易分类"""
    return [{"key": c.name, "label": c.value} for c in CategoryEnum]
```

---

## 四、启动与测试

```bash
# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

浏览器打开 **http://localhost:8000/docs**，你会看到自动生成的 Swagger 文档：

- `POST /transactions` —— 记一笔
- `GET /transactions?month=2025-06` —— 查账
- `GET /summary/2025-06` —— 月度汇总
- `PUT /transactions/{id}` —— 修改
- `DELETE /transactions/{id}` —— 删除

全程不需要 Postman，直接在 Swagger 页面上点 "Try it out" 就能测。

---

## 五、测试数据

用 Swagger 或 curl 灌一些数据：

```bash
# 记一笔工资
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": 15000, "category": "工资", "note": "6月工资"}'

# 记一笔午餐
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": -35, "category": "餐饮", "note": "公司楼下黄焖鸡"}'

# 记一笔地铁
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": -6, "category": "交通", "note": "上班地铁"}'

# 查月度汇总
curl http://localhost:8000/summary/2025-06
```

返回示例：

```json
{
  "month": "2025-06",
  "total_income": 15000.0,
  "total_expense": 41.0,
  "balance": 14959.0,
  "transaction_count": 3,
  "top_categories": [
    {"category": "餐饮", "amount": 35.0},
    {"category": "交通", "amount": 6.0}
  ]
}
```

---

## 六、进阶优化建议

| 优化项 | 方案 |
|--------|------|
| 数据迁移 | 改用 Alembic 管理 schema 版本 |
| 认证 | 加 JWT 登录，用 FastAPI 的 `Depends` 做鉴权 |
| 并发 | SQLite 不适合高并发写入，>100 用户考虑换 PostgreSQL |
| 预算预警 | 加一张 `budgets` 表，月度汇总时对比预算触发提醒 |
| 前端 | 用 React/Vue 或直接用 [Streamlit](https://streamlit.io) 快速搭 UI |
| 导出 | 加 `GET /transactions/export?month=xxx` 导出 CSV/Excel |

---

## 七、完整代码

> 📦 完整项目代码见 GitHub：`your-repo/fastapi-accounting`

也可以直接复制上面 6 个文件到同一个目录，`pip install` 后一键启动。

---

> 下一篇预告：**《向量数据库入门：Milvus / Chroma / Pinecone 怎么选》**——从零理解什么是向量、为什么传统数据库做不了语义搜索、三个主流向量数据库的对比与选型。

*文中所有代码在 Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 上测试通过。*
