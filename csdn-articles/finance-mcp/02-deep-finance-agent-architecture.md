# 市面上的 AI 理财助手都是花架子——真正有深度的理财 Agent 应该长这样

"帮我分析一下我的基金组合"——现在市面上任何一个接了 LLM 的理财工具都能给你回复。但回复的内容大概率是：「建议您分散投资、长期持有、根据风险偏好调整配置」。

这不是废话吗。

用户问的是「我该买什么基金」，不需要你再重复一遍理财入门课的第一章。他要的是：**我买的这三只基金底层到底投了哪些股票、有没有重叠、估值贵不贵、如果再来一次 2018 年会亏多少。**

这篇文章不讲入门。讲的是一个真正有深度的理财 Agent 应该具备哪些分析能力，以及每一层怎么实现。

---

## 一层一层拆：真正的理财 Agent 需要五件事

### 第一层：持仓穿透——「你买的基金到底是什么」

用户买了三只基金：易方达蓝筹精选、中欧医疗健康、招商中证白酒。

表面上看，分散了——消费、医疗、白酒，三个赛道。

穿透到底层持仓之后，你发现：三只基金同时重仓了茅台和五粮液。你以为你在分散投资，实际上你有一半的钱都在白酒上。

**数据从哪来**：基金季报是公开信息——天天基金、好买基金、蛋卷基金都提供持仓查询。AKShare（开源 Python 库）提供 `ak.fund_portfolio_hold_detail_em(code, year)` 接口，直接拉取基金前十大重仓股。ETF 更简单——直接查指数成分股即可，不需要等季报。

这个分析不需要 AI。需要的是一个能自动拉取基金季报数据、把每只基金的十大重仓股展开、然后按股票维度聚合的计算引擎。

**代码实现**：

```python
import akshare as ak

def fetch_top_holdings(fund_code: str) -> list[dict]:
    """拉取基金前十大重仓股（数据来源：天天基金）"""
    df = ak.fund_portfolio_hold_detail_em(symbol=fund_code, date="2025")
    return [
        {"name": row["股票名称"], "weight": float(row["占净值比例"])}
        for _, row in df.head(10).iterrows()
    ]

def penetrate_portfolio(fund_codes: list[str]) -> dict:
    """穿透基金持仓，按股票维度聚合"""
    stock_exposure = {}

    for code in fund_codes:
        holdings = fetch_top_holdings(code)
        for stock in holdings:
            name = stock['name']
            weight = stock['weight']
            stock_exposure[name] = stock_exposure.get(name, 0) + weight

    # 找出重复持仓（聚合后占比 > 5% 的股票）
    overlaps = {k: round(v, 1) for k, v in stock_exposure.items() if v > 5}
    return {
        "total_holdings": len(stock_exposure),
        "overlapping_stocks": overlaps,
        "concentration_top3": round(
            sum(sorted(stock_exposure.values(), reverse=True)[:3]), 1
        )
    }
```

运行结果可能是：「你表面投了三个赛道，实际上三只基金的十大重仓里茅台占了 18%、五粮液 9%、迈瑞医疗 7%——光前三只股票就占了你总仓位的 34%。」

这个结论不需要 AI 生成。它是一次计算的结果。但它是所有后续分析的基础。

---

### 第二层：估值分位数——「贵不贵用数据说话」

AI 跟你说「当前估值合理」——它怎么判断的？大概率是 LLM 从训练数据的模糊记忆里猜的。

真正的估值判断需要硬数据：把一只股票或一只基金当前 PE/PB 和它自己过去 5 年的历史数据对比。

```python
def valuation_percentile(stock_code: str) -> dict:
    """当前 PE 在历史 5 年中的分位数"""
    hist_pe = fetch_historical_pe(stock_code, years=5)
    current_pe = hist_pe[-1]

    below_count = sum(1 for pe in hist_pe if pe <= current_pe)
    percentile = below_count / len(hist_pe)

    return {
        "current_pe": current_pe,
        "percentile": percentile,
        "judgment": "偏低" if percentile < 0.3 else "偏高" if percentile > 0.7 else "适中"
    }
```

然后你告诉用户：「当前贵州茅台 PE 为 28.5，处于过去 5 年的 72% 分位数，意味着当前估值比过去 5 年中 72% 的时间都贵。」

这个结论有数学依据，不是 AI 猜出来的。LLM 在这个流程里的角色不是做判断，而是把数据结果翻译成人话。

---

### 第三层：风险归因——「涨跌是运气还是实力」

你说「这只基金今年涨了 20%，挺厉害」。20% 里多少是市场整体涨的（Beta）、多少是行业涨的（行业因子）、多少是基金经理真本事（Alpha）？

这个分析在金融学里有成熟的方法论，叫 Fama-French 三因子模型。

```python
import numpy as np
from sklearn.linear_model import LinearRegression

def factor_attribution(fund_returns: list, market_returns: list,
                       smb: list, hml: list):
    """
    用 Fama-French 做收益归因
    返回：市场因子、规模因子、价值因子各自的贡献
    """
    X = np.column_stack([market_returns, smb, hml])
    y = np.array(fund_returns)

    model = LinearRegression().fit(X, y)

    # R² 表示「多大程度能被这三因子解释」
    return {
        "r_squared": model.score(X, y),
        "alpha": model.intercept_,          # 基金经理的真本事
        "market_beta": model.coef_[0],      # 市场敏感度
        "size_loading": model.coef_[1],     # 大小盘偏好
        "value_loading": model.coef_[2],    # 价值/成长偏好
    }
```

输出可能是：「这只基金今年 20% 的收益里，市场整体上涨贡献了 14 个百分点，行业因子贡献了 5 个百分点，剩余约 1% 是无法用这三维解释的超额收益。」

这个信息量比「涨了 20% 好厉害」大了一百倍。它告诉你：如果市场不涨了，这只基金大概率也不会有超额收益。

**数据来源**：三因子数据可以从 Fama-French 官网免费下载（`mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html`），覆盖美股。A 股版本可以从清华大学金融科技研究院的因子库获取。

---

### 第四层：重叠度分析——「你的分散是真的还是假的」

这是最容易被忽略但最直观的一层。

用户买了五只基金，自以为分散得很好。但你把他所有基金的持仓股票拉出来，会发现一个尴尬的事实：五只基金有三只重仓了同一批股票。

```python
def overlap_analysis(fund_codes: list[str]) -> dict:
    """分析基金组合的持仓重叠度"""
    all_holdings = {}

    for code in fund_codes:
        holdings = fetch_top_holdings(code)
        all_holdings[code] = set(h['name'] for h in holdings)

    # 两两计算重叠度
    overlaps = {}
    for i, f1 in enumerate(fund_codes):
        for f2 in fund_codes[i+1:]:
            common = all_holdings[f1] & all_holdings[f2]
            all = all_holdings[f1] | all_holdings[f2]
            if all:
                overlaps[f"{f1} vs {f2}"] = len(common) / len(all)

    return overlaps
```

结果：「基金 A 和基金 B 的重叠度为 0.4——你买这两只，基本等于买了同一批股票的两倍。」

用热力图呈现这个结论比任何文字描述都有冲击力。用户一眼就能看到自己组合里哪些是真正的分散，哪些是重复下注。

---

### 第五层：历史情景测试——「再来一次 2015 年会亏多少」

AI 分析的另一个通病是只看当期数据，不看极端情景。

2015 年股灾、2018 年去杠杆、2020 年疫情崩盘——你的组合在这些极端事件下会表现如何？

```python
def scenario_test(fund_codes: list[str], scenarios: dict[str, tuple]) -> dict:
    """
    基于历史极端事件做压力测试
    scenarios = {"2015股灾": ("2015-06-12", "2015-08-26"), ...}
    """
    results = {}

    for name, (start, end) in scenarios.items():
        total_loss = 0
        valid_funds = 0
        for code in fund_codes:
            try:
                returns = fetch_returns_range(code, start, end)
                total_loss += returns
                valid_funds += 1
            except Exception as e:
                print(f"{code} 数据缺失: {e}")

        avg_loss = total_loss / valid_funds if valid_funds else 0
        results[name] = {
            "avg_drawdown": round(avg_loss, 2),
            "duration_days": (parse_date(end) - parse_date(start)).days
        }

    return results
```

然后你告诉用户：「假设 2018 年重演，你当前的组合在最坏情况下会回撤约 32%，需要大约 9 个月回到原点。」

这个数据不是预测未来，但比「投资者需注意风险」有价值得多。它让抽象的风险变成了具体的数字和情景。

---

## 真正好的理财工具长什么样——不是 Agent，是逻辑

这里不说 Agent，说几个全球做个人理财做得最好的工具。它们的共同点是：**不需要 AI，但分析深度远超任何接 LLM 的 Chatbot。**

| 工具 | 核心能力 | 值得借鉴的 |
|------|------|------|
| **Betterment** | 税务损失收割 + 自动再平衡 | 不是选基金，是算法调仓 |
| **Wealthfront** | 风险平价 + 直接指数化 | 不用 ETF，直接买底层股票 |
| **Portfolio Visualizer** | Fama-French 归因 + 蒙特卡洛模拟 | 业界标准的分析引擎 |
| **Morningstar X-Ray** | 持仓穿透 + 重叠度分析 | 告诉你「你买的到底是谁」 |

它们的共同思路是：**算出来的结论，不用 AI 生成**。AI 在这些工具里的唯一价值是把分析结果解释给用户听——不是替代计算，是翻译计算结果。

---

## 五层能力一句话总结

| 层级 | 解决的问题 | 输出示例 |
|------|------|------|
| 持仓穿透 | 你到底买了什么 | 茅台在三只基金里一共占了 18% |
| 估值分位数 | 现在贵不贵 | PE 处于 5 年 72% 分位，偏贵 |
| 风险归因 | 涨跌是什么原因 | 市场贡献 14%，Alpha 约 1% |
| 重叠度 | 分散是真的吗 | 两只基金重叠度 40%，重复下注 |
| 历史情景 | 极端情况亏多少 | 2018 年重演会回撤 32% |

---

## 从零到深：阶段推进清单

一口气做完全部不现实，按阶段来：

### 第一阶（先做，已有深度）
- [ ] 持仓穿透：接入 AKShare 拉基金季报 → 展开十大重仓 → 按股票聚合
- [ ] 重叠度：两两计算持仓重合率 → 用 Matplotlib 生成热力图

做完这两样，你的 Agent 已经比市面上所有「问问 AI 该买什么」的理财工具都有深度了。时间投入：一个周末。

### 第二阶（加专业权重）  
- [ ] PE 分位数：当前估值 vs 历史 5 年 → 贵还是便宜用数学说话
- [ ] 历史情景模拟：选 3-5 个极端事件 → 跑一遍压力测试 → 告诉用户最坏会亏多少
- [ ] 相关性矩阵：组合内每对资产的相关系数 → 真正的分散度

做完这层，你的 Agent 能输出的已经不是「建议」了，是有数据支撑的量化分析。时间投入：2-3 个周末。

### 第三阶（冲顶用）
- [ ] Fama-French 归因：拆解收益来源 → 市场涨了多少、行业涨了多少、基金经理真本事多少
- [ ] 费率侵蚀计算：1.5% vs 0.5% 管理费 → 30 年后差了多少钱，这个数字比任何投资建议都有冲击力
- [ ] 蒙特卡洛模拟：基于历史参数随机生成 10000 条未来收益路径 → 预测 5 年后资产分布范围

做完这三阶，你不是在做理财 Agent 了，你是在做个人版的 Wealthfront。

**数据源清单**：

| 数据类型 | 免费方案 | 付费方案 |
|------|------|------|
| A股行情 | AKShare（开源免费） | Wind / 同花顺 iFinD |
| 基金持仓 | 天天基金 API | Wind |
| 美股行情 | Yahoo Finance（yfinance） | Polygon.io |
| 因子数据 | Fama-French 官网 | Barra / Axioma |
| 估值分位数 | 自己算（历史 PE 数据 + 分位数） | 无需外购 |

---

市面上没有好用的理财 Agent，不是因为 LLM 不够强，是因为没人把「金融分析」的逻辑沉淀成 Agent 的工具链。你能查行情、能读财报都不算本事——能穿透持仓做重叠度分析、能归因收益做风险分解、能用历史数据模拟极端情景，才算真正有用的 Agent。

这五层不需要同时做。从持仓穿透和重叠度开始，两样加起来不超过 200 行 Python。但做完之后，你的 Agent 说的就不是「建议分散投资」了——它会告诉你「你三只基金里茅台占了 18%，这不是分散，这是赌白酒」。