# 基金持仓管理系统 PRD

## 1. 项目概述

### 项目名称
**基金持仓管理小助手**

### 核心一句话
> 管理个人基金持仓，记录加仓/减仓历史，实时查看盈亏和净值曲线

### 目标用户
个人投资者，用于管理自己持仓的基金资产

---

## 2. 功能清单

### 2.1 基金持仓管理
- [ ] 新增基金持仓（基金ID、成本价、持有份额）
- [ ] 编辑/删除基金持仓
- [ ] 查看持仓列表（支持搜索、排序）
- [ ] 手动刷新基金净值

### 2.2 盈亏计算
- [ ] 实时计算持仓盈亏（绝对收益 + 收益率）
- [ ] 计算持仓总盈亏
- [ ] 今日涨跌显示

### 2.3 交易记录
- [ ] 记录加仓（时间、金额、份额）
- [ ] 记录减仓（时间、金额、份额）
- [ ] 查看单只基金的交易历史

### 2.4 数据可视化
- [ ] 基金净值历史曲线（ECharts）
- [ ] 持仓占比饼图
- [ ] 盈亏走势曲线

### 2.5 数据同步
- [ ] 调用天天基金/东方财富API获取净值
- [ ] 定时更新净值（可选）

---

## 3. 数据模型设计

### 3.1 基金持仓表 (fund_positions)

```sql
CREATE TABLE fund_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code VARCHAR(20) NOT NULL COMMENT '基金代码',
    fund_name VARCHAR(100) COMMENT '基金名称',
    cost_price DECIMAL(10, 4) NOT NULL COMMENT '持仓成本价',
    shares DECIMAL(12, 4) NOT NULL COMMENT '持有份额',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code)
);
```

### 3.2 交易记录表 (fund_transactions)

```sql
CREATE TABLE fund_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code VARCHAR(20) NOT NULL COMMENT '基金代码',
    trans_type VARCHAR(10) NOT NULL COMMENT '交易类型: BUY(加仓)/SELL(减仓)',
    trans_price DECIMAL(10, 4) NOT NULL COMMENT '交易价格',
    trans_shares DECIMAL(12, 4) NOT NULL COMMENT '交易份额',
    trans_amount DECIMAL(12, 2) NOT NULL COMMENT '交易金额',
    trans_date DATETIME NOT NULL COMMENT '交易日期',
    note VARCHAR(200) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_code) REFERENCES fund_positions(fund_code)
);
```

### 3.3 净值历史表 (fund_nav_history)

```sql
CREATE TABLE fund_nav_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code VARCHAR(20) NOT NULL,
    nav_date DATE NOT NULL COMMENT '净值日期',
    nav DECIMAL(10, 4) COMMENT '单位净值',
    acc_nav DECIMAL(10, 4) COMMENT '累计净值',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, nav_date)
);
```

---

## 4. 页面设计

### 4.1 首页/仪表盘
- 持仓总资产
- 持仓总盈亏（金额 + 百分比）
- 今日涨跌
- 持仓基金列表（卡片式）
- 持仓占比饼图

### 4.2 持仓详情页
- 基金名称 + 代码
- 当前净值（实时）
- 持仓成本
- 持有份额
- 当前价值 = 净值 × 份额
- 盈亏 = (净值 - 成本) × 份额
- 净值历史曲线（可选择时间范围：1周/1月/3月/1年/全部）

### 4.3 交易记录页
- 加仓/减仓按钮
- 交易历史列表（时间、类型、金额、份额）
- 筛选功能

### 4.4 新增/编辑持仓弹窗
- 基金代码（输入框，支持模糊搜索）
- 基金名称（自动获取）
- 成本价（数字输入）
- 持有份额（数字输入）
- 确认按钮

---

## 5. API 设计

### 5.1 后端接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/positions | 获取所有持仓 |
| POST | /api/positions | 新增持仓 |
| PUT | /api/positions/:id | 编辑持仓 |
| DELETE | /api/positions/:id | 删除持仓 |
| GET | /api/positions/:code | 获取单只基金详情（含净值） |
| GET | /api/transactions/:code | 获取交易记录 |
| POST | /api/transactions | 新增交易记录 |
| GET | /api/fund/:code/nav | 获取基金净值（调用外部API） |

### 5.2 基金数据接口

**东方财富接口**（示例）：
```
https://fund.eastmoney.com/pingzhongdata/基金代码.js
```

**字段映射**：
- `fund_code` - 基金代码
- `nav` - 单位净值
- `acc_nav` - 累计净值
- `nav_date` - 净值日期

---

## 6. 技术注意事项

### 6.1 数据类型（重点！）
| 字段 | 类型 | 说明 |
|------|------|------|
| 净值/成本价 | `DECIMAL(10, 4)` | 避免浮点精度丢失 |
| 金额 | `DECIMAL(12, 2)` | 金额计算 |
| 份额 | `DECIMAL(12, 4)` | 基金份额 |

### 6.2 计算逻辑
```javascript
// 正确做法 - 使用 DECIMAL
currentValue = nav * shares
profit = (nav - costPrice) * shares
profitRate = (nav - costPrice) / costPrice * 100

// 错误做法 - 避免使用 float 直接计算
// currentValue = parseFloat(nav) * parseFloat(shares) // 有精度问题
```

### 6.3 前端展示
- 所有金额保留 2 位小数
- 净值/成本保留 4 位小数
- 百分比保留 2 位小数

---

## 7. 验收标准

- [ ] 可以新增/编辑/删除基金持仓
- [ ] 持仓列表正确显示基金名称、代码、成本、份额、当前净值、盈亏
- [ ] 点击单只基金可以看到净值历史曲线
- [ ] 可以记录加仓/减仓操作
- [ ] 交易历史清晰可查
- [ ] 页面美观，数据展示清晰
- [ ] 净值精度正确，无明显误差

---

## 8. 开发计划

### Phase 1：基础功能
- 项目初始化
- 数据库设计
- 基金持仓 CRUD

### Phase 2：核心功能
- 基金净值获取
- 盈亏计算
- 交易记录

### Phase 3：可视化
- ECharts 曲线图
- 饼图、走势图

### Phase 4：优化
- 定时任务（自动更新净值）
- 数据导出

---

*文档版本：v1.0*
*创建日期：2026-03-23*
