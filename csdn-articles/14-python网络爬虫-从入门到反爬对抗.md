# Python网络爬虫从入门到实践：你能爬到的远比想象的多——附带反爬对抗实录

> **摘要**：网上大多数爬虫教程只教到`requests.get()`+`BeautifulSoup`就结束了。但真实世界的爬虫面对的是一整套反爬体系——IP封锁、验证码、JS渲染、请求头校验、行为检测。本文从实战出发，覆盖：requests+AIOHTTP双轨策略、动态渲染（Selenium/Playwright）、反爬对抗10招（含代理池+指纹伪装）、Scrapy框架完整项目、数据存储方案。附带一个爬取CSDN热榜的完整项目代码。

---

## 目录

- [开篇：我第一次写爬虫就被封IP了](#开篇)
- [一、基础篇：requests + BeautifulSoup](#一基础篇)
- [二、进阶篇：异步爬虫 + 动态渲染](#二进阶篇)
- [三、反爬对抗：10个你一定会遇到的情况](#三反爬对抗)
- [四、工程篇：Scrapy框架完整项目](#四工程篇)
- [五、数据存储：从CSV到MongoDB](#五数据存储)
- [六、完整项目：爬取CSDN热榜文章](#六完整项目)
- [七、法律与道德边界](#七法律与道德边界)

---

## 开篇：我第一次写爬虫就被封IP了

2017年我写第一个爬虫，想爬某个小说网站的全部章节。开了50个线程并发请求，3分钟后IP就被封了。

后来才知道，那个网站的反爬策略是：**同一IP每秒超过5个请求就封24小时。**

这就是真实世界的爬虫和教程的区别。教程教你`requests.get(url)`，真实世界你得同时处理代理IP、请求频率、Cookie管理、User-Agent轮换、验证码识别——少一个都不行。

本文不教"怎么安装requests库"——这种内容搜索引擎上有5000篇。本文假设你已经会写Python，直接上讲实战中真正有用的东西。

---

## 一、基础篇：requests + BeautifulSoup（但是正确的写法）

### 1.1 一个不会死的Session

```python
import requests
from bs4 import BeautifulSoup
import time
import random

class SafeCrawler:
    """一个不会被秒封的基础爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        })
        # 请求计数（用于频率控制）
        self.request_count = 0
        self.last_request_time = 0
    
    def get(self, url, min_interval=1.0):
        """带频率控制的GET请求"""
        # 控制请求频率
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed + random.uniform(0, 0.5))
        
        resp = self.session.get(url, timeout=10)
        self.last_request_time = time.time()
        
        # 检查状态码
        if resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', 60))
            print(f"被限流了, 等{retry_after}秒...")
            time.sleep(retry_after)
            return self.get(url, min_interval)  # 重试
        
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {url}")
        
        return resp
    
    def parse(self, html):
        """解析HTML"""
        return BeautifulSoup(html, 'lxml')  # lxml比html.parser快3-5倍


# 使用
crawler = SafeCrawler()
resp = crawler.get("https://www.csdn.net/")
soup = crawler.parse(resp.text)
```

**关键点**：
- 一定要用 `requests.Session()`——它自动管理Cookie，模拟真实浏览器行为
- 请求头不只要UA，至少要带上Accept系列和Accept-Language
- `lxml`解析器比`html.parser`快3-5倍（`pip install lxml`）
- 频率控制不是"睡固定时间"，是计算实际间隔——代码跑得快时不浪费等待时间

---

## 二、进阶篇：异步爬虫 + 动态渲染

### 2.1 aiohttp异步并发（速度提升5-20倍）

```python
import asyncio
import aiohttp
from bs4 import BeautifulSoup

class AsyncCrawler:
    """异步爬虫：50个请求同时发出"""
    
    def __init__(self, max_concurrent=10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 ...',
        }
    
    async def fetch(self, session, url):
        """获取单个页面"""
        async with self.semaphore:  # 控制并发
            try:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        print(f"状态码异常 {resp.status}: {url}")
                        return None
            except Exception as e:
                print(f"请求失败 {url}: {e}")
                return None
    
    async def crawl(self, urls):
        """并发爬取多个URL"""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            tasks = [self.fetch(session, url) for url in urls]
            return await asyncio.gather(*tasks)
    
    def parse(self, html):
        return BeautifulSoup(html, 'lxml')


# 使用
async def main():
    crawler = AsyncCrawler(max_concurrent=5)
    urls = [f"https://example.com/page/{i}" for i in range(50)]
    
    import time
    start = time.time()
    results = await crawler.crawl(urls)
    success = sum(1 for r in results if r is not None)
    elapsed = time.time() - start
    
    print(f"50个URL: {success}成功, 耗时{elapsed:.2f}s")
    # 同步约25秒 → 异步约3-5秒

asyncio.run(main())
```

### 2.2 Playwright——对付JS渲染页面

有些网站的内容是JS动态加载的，`requests.get()`拿到的只是空壳HTML。

```python
from playwright.async_api import async_playwright

async def js_render_page(url):
    """用Playwright渲染JS页面，获取完整DOM"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 关键：等待页面加载完成
        await page.goto(url, wait_until='networkidle')
        
        # 等特定元素出现（表明数据加载完毕）
        await page.wait_for_selector('.article-list', timeout=10000)
        
        # 获取完整HTML
        html = await page.content()
        
        # 或者直接在浏览器里执行JS获取数据
        data = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.article-item')).map(el => ({
                title: el.querySelector('.title').innerText,
                url: el.querySelector('a').href
            }))
        }''')
        
        await browser.close()
        return data
```

**什么时候用Selenium/Playwright而不是requests？**

- 页面数据是Ajax加载的 → Playwright
- 需要登录后操作 → Playwright
- 需要点击"加载更多"按钮 → Playwright
- 普通HTML页面 → requests（速度快100倍，优先用这个！）

---

## 三、反爬对抗：10个你一定会遇到的情况

### 第1招：IP被封 → 代理池

```python
import random

class ProxyPool:
    """简单的代理池"""
    
    def __init__(self):
        self.proxies = [
            'http://proxy1:8080',
            'http://proxy2:8080',
            # 从免费代理网站获取或购买付费代理
        ]
    
    def get_random_proxy(self):
        return {'http': random.choice(self.proxies)}
    
    def remove_proxy(self, proxy):
        """移除失效代理"""
        self.proxies = [p for p in self.proxies if p != proxy['http']]

# 使用
proxy_pool = ProxyPool()
resp = requests.get(url, proxies=proxy_pool.get_random_proxy(), timeout=10)
```

> ⚠️ 免费代理99%不稳定。如果爬取重要，花几十块买付费代理API，省去90%的代理维护时间。

### 第2招：请求头校验 → 伪造完整请求头

```python
# 浏览器的完整请求头（在Chrome开发者工具→Network里复制）
HEADERS = {
    'User-Agent': '...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Referer': 'https://www.google.com/',  # 有些网站检查来源
}
```

### 第3招：Cookie校验 → 先访问首页拿Cookie

```python
session = requests.Session()
# 先访问首页，获取Cookie
session.get('https://example.com')
# Cookie已自动保存在session中
# 再访问目标页面
resp = session.get('https://example.com/data')
```

### 第4招：验证码 → OCR识别

```python
# 简单验证码用 tesserocr
import tesserocr
from PIL import Image

def crack_captcha(image_path):
    image = Image.open(image_path)
    # 预处理：灰度+二值化
    image = image.convert('L')
    image = image.point(lambda x: 0 if x < 128 else 255)
    return tesserocr.image_to_text(image).strip()
```

### 第5招：行为检测 → 随机化操作间隔

```python
import random

# ❌ 每次间隔1秒 → 机器行为
time.sleep(1)

# ✅ 2-5秒随机间隔 → 更像人类
time.sleep(random.uniform(2, 5))

# ✅ 偶尔"休息"一下（模拟人类走神）
if random.random() < 0.05:  # 5%概率
    time.sleep(random.uniform(10, 30))
```

### 第6招：反爬字段 → 破解参数加密

这部分太复杂，讲核心思路：

```
1. 打开Chrome DevTools → Network → 找到数据请求的XHR
2. 看请求参数里有没有奇怪的加密字段（如 sign、token、_signature）
3. 在Sources面板搜索这个字段名 → 找到生成逻辑
4. 用Python重写加密逻辑（通常就是MD5/SHA256+时间戳+盐）
```

### 第7招：字体反爬 → 分析字体文件

有些网站把数字替换成了自定义字体，HTML里显示`&#x1234;`这种编码，但浏览器渲染出来是数字"5"。

**破解方法**：

```python
# 1. 找到字体文件URL（在CSS里搜 @font-face）
# 2. 下载字体文件
import requests
font_url = "https://example.com/fonts/custom.woff"
with open("custom.woff", "wb") as f:
    f.write(requests.get(font_url).content)

# 3. 用 fontTools 解析字体文件
from fontTools.ttLib import TTFont

font = TTFont("custom.woff")
# 获取cmap表（Unicode码 → 字形名称的映射）
cmap = font.getBestCmap()
print(cmap)  # {0x1001: 'glyph001', 0x1002: 'glyph002', ...}

# 4. 手动建立映射关系（打开网页截图，肉眼对照数字和编码）
# 或者在字体查看工具中观察每个字形对应的数字
char_map = {
    '&#x1001;': '0',
    '&#x1002;': '1',
    '&#x1003;': '2',
    # ... 根据实际对照结果填充
}

# 5. 替换HTML中的编码为真实数字
def decode_font(html, char_map):
    for code, char in char_map.items():
        html = html.replace(code, char)
    return html
```

现实中，有些网站的字体映射关系是动态变化的（每次请求字体文件都不一样）。对付这种情况，需要OCR截图识别数字，绕开字体解析。

### 第8招：CSS伪元素 → 用Playwright取完整渲染结果

```python
from playwright.sync_api import sync_playwright

def get_pseudo_element_content(url, selector):
    """获取::before / ::after伪元素的内容"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        
        # BeautifulSoup拿不到伪元素，但浏览器可以！
        content = page.evaluate(f'''() => {{
            const el = document.querySelector("{selector}");
            const before = window.getComputedStyle(el, "::before");
            return before.content;  // 返回伪元素的content值
        }}''')
        
        browser.close()
        return content.strip('"')  # content属性自带引号

# 使用
price = get_pseudo_element_content(
    "https://example.com/product", 
    ".price-tag"
)
print(f"伪元素中的价格: {price}")
```

### 第9招：蜜罐链接 → 正则过滤 + 域名白名单

爬全站时，有些链接是故意放给爬虫的（如`/admin/delete-all`这种）。加黑名单正则过滤：
```python
BLACKLIST = [r'/admin/', r'/delete', r'/logout', r'javascript:']
```

### 第10招：请求频率检测 → Token Bucket限流

不要"等1秒发一个"——用令牌桶算法平滑请求速率：

```python
import time

class TokenBucket:
    """令牌桶限流器"""
    def __init__(self, rate, capacity):
        self.rate = rate        # 每秒生成的令牌数
        self.capacity = capacity  # 桶容量
        self.tokens = capacity
        self.last_time = time.time()
    
    def consume(self, tokens=1):
        """消耗一个令牌，如果没有则等待"""
        now = time.time()
        # 补充令牌
        elapsed = now - self.last_time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_time = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        else:
            # 等待足够的令牌
            wait_time = (tokens - self.tokens) / self.rate
            time.sleep(wait_time)
            self.tokens = 0
            return True
```

---

## 四、工程篇：Scrapy框架完整项目

当爬取规模超过"一次性脚本"的范畴，就该上Scrapy了。

```bash
pip install scrapy
scrapy startproject csdn_spider
```

```python
# csdn_spider/spiders/hotlist.py
import scrapy

class CSDNHotlistSpider(scrapy.Spider):
    name = 'csdn_hotlist'
    
    # Scrapy自动处理并发、重试、频率控制
    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'DOWNLOAD_DELAY': 2,
        'ROBOTSTXT_OBEY': True,
        'USER_AGENT': 'Mozilla/5.0 ...',
    }
    
    def start_requests(self):
        urls = ['https://blog.csdn.net/nav/ai']
        for url in urls:
            yield scrapy.Request(url, callback=self.parse)
    
    def parse(self, response):
        """解析列表页"""
        for article in response.css('.blog-list-box'):
            yield {
                'title': article.css('h3 a::text').get(),
                'url': article.css('h3 a::attr(href)').get(),
                'reads': article.css('.read-num::text').get(),
                'likes': article.css('.like-num::text').get(),
            }
        
        # 自动翻页
        next_page = response.css('.next-page::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)


# 运行: scrapy crawl csdn_hotlist -o articles.json
```

Scrapy帮你自动处理了：并发控制、请求重试、去重、数据管道、中间件——这些都是手写要几百行代码的功能。

---

## 五、数据存储：从CSV到MongoDB

### 小数据（<10万条）→ CSV

```python
import csv

def save_to_csv(data, filename):
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
```

### 中数据（10万-100万）→ SQLite

```python
import sqlite3

conn = sqlite3.connect('crawler.db')
conn.execute('''CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, url TEXT UNIQUE, reads INTEGER, crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
conn.execute('INSERT OR IGNORE INTO articles (title, url, reads) VALUES (?, ?, ?)', 
             (title, url, reads))
conn.commit()
```

### 大数据（100万+）→ MongoDB

```python
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['crawler_db']
collection = db['articles']
# upsert: 存在就更新，不存在就插入
collection.update_one(
    {'url': url},
    {'$set': {'title': title, 'reads': reads}},
    upsert=True
)
```

---

## 六、完整项目：爬取CSDN热榜文章

结合上面所有知识，一个完整的CSDN热榜爬虫（可以直接跑）：

```python
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import sqlite3
import time
import random
from urllib.parse import urljoin

class CSDNCrawler:
    """CSDN AI频道热榜爬虫"""
    
    def __init__(self):
        self.base_url = 'https://blog.csdn.net/nav/ai'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://www.csdn.net/',
        }
        self.semaphore = asyncio.Semaphore(3)
        self.init_db()
    
    def init_db(self):
        self.conn = sqlite3.connect('csdn_hotlist.db')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT UNIQUE,
            author TEXT,
            reads TEXT,
            likes TEXT,
            crawled_at TEXT
        )''')
    
    async def fetch_page(self, session, url):
        """获取页面HTML"""
        async with self.semaphore:
            await asyncio.sleep(random.uniform(1, 3))  # 礼貌间隔
            async with session.get(url, headers=self.headers) as resp:
                return await resp.text()
    
    def parse_hotlist(self, html):
        """解析热榜页面"""
        soup = BeautifulSoup(html, 'lxml')
        articles = []
        
        # CSDN热榜的典型结构（需根据实际页面调整选择器）
        for item in soup.select('.blog-list-box'):
            title_el = item.select_one('h3 a')
            if not title_el:
                continue
            
            articles.append({
                'title': title_el.get_text(strip=True),
                'url': title_el.get('href', ''),
                'author': self._safe_extract(item, '.author-name'),
                'reads': self._safe_extract(item, '.read-num'),
                'likes': self._safe_extract(item, '.like-num'),
            })
        
        return articles
    
    def _safe_extract(self, element, selector):
        """安全提取文本"""
        el = element.select_one(selector)
        return el.get_text(strip=True) if el else ''
    
    def save_articles(self, articles):
        """保存到数据库"""
        import datetime
        now = datetime.datetime.now().isoformat()
        
        for article in articles:
            try:
                self.conn.execute(
                    '''INSERT OR REPLACE INTO articles 
                       (title, url, author, reads, likes, crawled_at)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (article['title'], article['url'], article['author'],
                     article['reads'], article['likes'], now)
                )
            except Exception as e:
                print(f"保存失败: {article['title'][:30]}... - {e}")
        
        self.conn.commit()
    
    async def run(self):
        """主流程"""
        print("🚀 开始爬取CSDN热榜...")
        
        async with aiohttp.ClientSession() as session:
            html = await self.fetch_page(session, self.base_url)
            articles = self.parse_hotlist(html)
            
            print(f"📊 解析到 {len(articles)} 篇文章")
            
            self.save_articles(articles)
            
            # 打印前5篇
            for i, article in enumerate(articles[:5], 1):
                print(f"  {i}. {article['title'][:50]}... ({article['reads']}阅读)")
        
        print(f"✅ 完成！数据已保存到 csdn_hotlist.db")


if __name__ == '__main__':
    crawler = CSDNCrawler()
    asyncio.run(crawler.run())
```

---

## 七、法律与道德边界

爬虫的底线，三条铁律：

### 1. 看 robots.txt

```
在浏览器输入: https://example.com/robots.txt

User-agent: *
Disallow: /admin/     ← 不能爬
Disallow: /api/       ← 不能爬
Allow: /              ← 可以爬

遵守robots.txt是最基本的爬虫礼仪。
```

### 2. 控制频率，别把别人服务器打挂

- 单个网站每秒不超过3-5个请求
- 不要用几百个并发去打小网站
- 如果返回429/503，退避等待

### 3. 不要爬个人隐私和付费内容

- 公开的列表页和文章 → OK
- 需要登录才能看的内容 → 看网站条款
- 用户个人信息（手机号、邮箱） → **绝对不行**
- 付费课程视频/文档 → **绝对不行**

---

> 💡 **最后一句话**：爬虫是工具，不是武器。掌握它能让你获取数据的能力提升100倍，但用在哪、怎么用，是你自己的底线。

**你写过什么有趣的爬虫？被哪些反爬策略坑过？评论区分享你的爬虫故事。**
