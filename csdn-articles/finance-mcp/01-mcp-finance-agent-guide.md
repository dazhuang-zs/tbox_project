# 用 MCP 给你的 AI 接上一个理财助手——从行情查询到持仓分析的完整方案

上周我让 Claude Code 帮我看看最近纳指的走势。它说："我无法获取实时数据。"

那一刻我意识到：AI 编程助手的金融盲区太大了。不是它不够聪明，是它没有手和眼睛去触摸金融市场。

MCP 协议恰好解决了这个问题。这篇文章从 GitHub 上 22 个金融类 MCP Server 出发，给你一套完整方案——用 Claude Desktop 或 OpenClaw，接上免费的金融数据源，让你的 AI 能查行情、看财报、读新闻、分析持仓。所有代码都能跑。

---

## 第一步：选数据源——不是每个 API 都能用

金融数据 API 分三类：

**第一类：官方付费 API**（Bloomberg、Wind、聚宽）。数据最全最准，但个人用不起。Bloomberg 终端一年两万美元，Wind 一年也要几千。这条路对个人开发者不通。

**第二类：免费/低价数据源**。Yahoo Finance（美股免费）、东方财富/同花顺（A股部分免费）、Tushare（A股免费额度）、AKShare（开源免费）。这是个人开发者的主战场。

**第三类：爬虫**。不推荐。法律风险大，数据不稳定。

我这篇文章基于第二类数据源——够用、合法、零成本起步。

---

## 第二步：GitHub 上金融 MCP Server 怎么选

截至 2026 年 5 月，GitHub 上有 22+ 个金融方向 MCP Server。这里只挑最值得关注的五个：

**`yahoo-finance-mcp`** ⭐ 最成熟。实时行情、K线历史数据、财务报表、分析师评级、公司对比，全部封装成 MCP Tools。Python 实现，核心逻辑不到 150 行。装一个 `yfinance` 依赖就能跑。推荐作为起点。

**`A-Scope-Research`** 🇨🇳 唯一专注中国 A 股的 MCP Server。用多 Agent 协作——基本面 Agent + 技术面 Agent + 舆情 Agent 各司其职，最后汇总分析。思路好，但项目比较早期。

**`stockscope-mcp`** 📄 接入了 SEC EDGAR 系统，能查到美股公司的原始披露文件——财报原文、重大事项公告、内部人交易记录。想做深度美股研究，这个是绕不开的数据源。

**`FinanceNews-MCP`** 📰 金融新闻搜索，可以按关键词、公司名、时间段过滤。和行情数据配合——行情数字告诉你发生了什么，新闻文字告诉你为什么发生。

**`chart-library-mcp`** 📊 K 线图相似匹配——输入走势形态，在历史数据中找相似案例。对技术分析有用，但历史不会简单重复，谨慎参考。

**一个很多人忽略的点**：这些 MCP Server 的数据源几乎全是 Yahoo Finance。Yahoo Finance 对美股数据支持很好，但对 A 股、港股覆盖不全。如果你主要关注中国市场，可以用 `A-Scope-Research`，或者自己接 AKShare（一个开源免费的 A 股数据 Python 库）来替代 Yahoo Finance。

---

## 第三步：动手——从零搭一个股票分析 MCP Server

不直接用现成的，自己写一个。不是为了造轮子，是为了理解底层。

**先装依赖**：

```bash
pip install yfinance mcp
```

以下代码实现了三个核心能力：查行情、看财报、对比股票。数据源用 Yahoo Finance，完全免费。

```python
# stock_mcp.py - 股票分析 MCP Server
import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("stock-analyzer")

@mcp.tool()
def get_stock_price(ticker: str) -> str:
    """获取股票实时行情。ticker 如 AAPL、TSLA、BABA"""
    stock = yf.Ticker(ticker)
    info = stock.info
    return (
        f"{info.get('longName', ticker)}\n"
        f"价格: ${info.get('currentPrice', 'N/A')}\n"
        f"涨跌幅: {info.get('regularMarketChangePercent', 0):+.2f}%\n"
        f"市值: ${info.get('marketCap', 0)/1e9:.1f}B\n"
        f"市盈率: {info.get('trailingPE', 'N/A')}\n"
        f"52周最高: ${info.get('fiftyTwoWeekHigh', 'N/A')}"
    )

@mcp.tool()
def get_financials(ticker: str) -> str:
    """获取公司最新季度财务数据"""
    stock = yf.Ticker(ticker)
    q = stock.quarterly_financials
    if q.empty:
        return "暂无财务数据"
    latest = q.iloc[:, 0]
    return (
        f"总收入: ${latest.get('Total Revenue', 0)/1e6:.0f}M\n"
        f"毛利: ${latest.get('Gross Profit', 0)/1e6:.0f}M\n"
        f"净利润: ${latest.get('Net Income', 0)/1e6:.0f}M\n"
        f"研发费用: ${latest.get('Research Development', 0)/1e6:.0f}M"
    )

@mcp.tool()
def compare_stocks(ticker_a: str, ticker_b: str) -> str:
    """对比两只股票的关键指标"""
    def get_values(t):
        s = yf.Ticker(t).info
        return (s.get('currentPrice'), s.get('trailingPE'), s.get('marketCap', 0)/1e9)
    pa, pb = get_values(ticker_a), get_values(ticker_b)
    return (
        f"{'指标':<12} {ticker_a:<10} {ticker_b:<10}\n"
        f"{'价格':<12} ${pa[0]:<9} ${pb[0]:<9}\n"
        f"{'市盈率':<12} {pa[1]:<9} {pb[1]:<9}\n"
        f"{'市值(B)':<12} {pa[2]:<9.1f} {pb[2]:<9.1f}"
    )

if __name__ == "__main__":
    mcp.run()
```

接上 Claude Desktop。不同系统的配置文件位置不同：

- macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows：`%APPDATA%\Claude\claude_desktop_config.json`
- Linux：`~/.config/Claude/claude_desktop_config.json`

编辑这个文件（首次使用可能需要自己创建），加上：

```json
{
  "mcpServers": {
    "stock-analyzer": {
      "command": "python",
      "args": ["/绝对路径/stock_mcp.py"]
    }
  }
}
```

**注意三点**：路径必须用绝对路径，不能用 `~/` 开头的相对路径；Python 环境要确认有 `yfinance` 和 `mcp` 两个包；改完配置后必须完全退出 Claude Desktop 再重新打开，不是重新加载窗口。

- 「帮我看看 TSLA 现在什么价位」
- 「对比一下 AAPL 和 MSFT 的市盈率」
- 「帮我查一下 NVDA 上个季度的收入」

---

## 第四步：给 Agent 加上数据缓存和容错

Yahoo Finance 免费 API 有两个坑：调用太频繁会被限流，网络波动时请求会超时。

我在实际跑了几天后发现，需要加两层保护：

```python
import time
from functools import lru_cache

# 第一层：缓存——同一只股票 5 分钟内不重复查
@lru_cache(maxsize=128)
def _cached_info(ticker: str, cache_key: int) -> dict:
    """cache_key 是时间戳除以 300 秒，保证 5 分钟内复用缓存"""
    stock = yf.Ticker(ticker)
    return stock.info

@mcp.tool()
def get_stock_price(ticker: str) -> str:
    # 用 5 分钟粒度的时间戳做缓存键
    cache_key = int(time.time()) // 300
    info = _cached_info(ticker.upper(), cache_key)
    # ... 格式化输出
    return formatted_output

# 第二层：重试机制
@mcp.tool()
def get_stock_price_retry(ticker: str, retries: int = 2) -> str:
    for attempt in range(retries + 1):
        try:
            return get_stock_price(ticker)
        except Exception as e:
            if attempt == retries:
                return f"查询失败（已重试{retries}次）: {e}"
            time.sleep(2 ** attempt)  # 指数退避
```

加这两层之后，Agent 不会再因为重复查询同一只股票而浪费 API 额度，也不会因为一次网络波动就卡死。

## 第五步：不只是查行情——Agent 的真正用法

单独的行情查询没什么了不起。真正的价值在于让 AI Agent 用这些数据做多步推理：

**用法一：条件筛选**

AI 可以遍历你关注的股票池，按条件过滤。比如：「S&P 500 里市盈率低于 15 且市值超过 100 亿美元的公司有哪些？」这个查询对 AI 来说是 500 次 `get_stock_price` 调用——加上缓存后实际只需查一次，因为每次 Agent 循环都可能重复请求同一批股票。

**用法二：交叉分析**

AI 同时调多个工具：行情 + 财报 + 新闻。一张表给你看三者的关系——营收涨了股价跌了？找新闻看看同一天发生了什么。散户需要翻五个网站才能拼出来的全景图，AI 用三个 MCP 调用就完成了。

**用法三：定期报告**

AI Agent 定时跑一遍你的持仓，生成一份简报：今天关注的三只股票各自涨跌多少、发生了什么新闻、有没有触发你设定的预警线。不是替代基金经理，是帮你省掉每天 30 分钟的信息收集时间。

**用法四：多步推理的 Agent 循环**

这才是 Agent 真正区别于单次 API 调用的地方。

你可以对 Agent 说：「帮我看看我持仓的 AAPL 和 MSFT，如果任何一只跌了超过 5%，帮我查一下最近有没有负面新闻。」

Agent 的执行流程：
1. 查 AAPL 行情 → 跌了 3%，没触发
2. 查 MSFT 行情 → 跌了 7%，触发条件
3. 查 MSFT 新闻 → 发现有关于反垄断调查的报道
4. 汇总：MSFT 跌 7% 可能与反垄断调查有关，建议关注后续进展

这不是一次 API 调用能完成的。Agent 需要根据第一步的结果决定是否执行第三步——如果两只都没触发条件，第三步就不会被执行。这就是 Agent 的「条件决策」能力。

---

## 第五步：限制和风险

**数据质量不是 100%**。Yahoo Finance 的免费数据有延迟，有时会缺失某些指标。不要基于这些数据做日内交易决策。适合中长线研究的初步筛查。

**AI 的分析不可靠**。AI Agent 能读财报数字，但读不懂财报背后的商业逻辑。它告诉你营收下降了 5%，但不会告诉你这是因为整个行业在萎缩还是公司自己在掉队。后者需要人工判断。

**不要接交易接口**。这篇文章接的是查询接口，不涉及下单。一旦涉及资金操作，安全要求是指数级上升的。别拿 AI 自动炒股——那是在烧钱。

**费率风险**。Yahoo Finance 免费的 API 调用频率有限制。如果批量跑 500 只股票的数据，可能会被限流。正式项目建议换付费数据源（如 Alpha Vantage 或 Polygon.io）。

---

回到开头那个问题。你的 AI 编程助手每天都在帮你写代码，但它在金融市场面前是个瞎子。MCP 协议给了一个标准化的接口，Yahoo Finance 给了一个零成本的数据源。剩下的就是你把它们接起来。

不是要你用 AI 炒股。是要你不再被「我需要先查一下数据」这件事打断思路。让 AI 帮你查，你只做判断。

下一步可以做什么：
- 把新闻搜索和行情查询合并成一个 MCP Server
- 加一个定时任务，每天早上自动推一份持仓简报到飞书
- 接入 A 股数据（AKShare），做成中国版的 AI 理财助手
- 把 Agent 的分析结果定期存到一个 SQLite 里，跟踪预测准确率

---

*标签：#MCP #AI理财 #股票分析 #Agent #YahooFinance #MCP Server*