# CSDN API 参考手册

> 本文档记录已验证可用的 CSDN 公开 API 接口。用于数据驱动的选题分析、热榜追踪、竞品调研。
>
> ⚠️ 注意事项：
> - CSDN 部分接口有 Cloudflare WAF 防护，直接用 curl 可能返回 403。**必须带浏览器 User-Agent + Referer**。
> - 无头浏览器（Playwright/Puppeteer）也会被 WAF 拦截，不要在这上面浪费时间。
> - API 域名 `blog.csdn.net` 和静态资源 `csdnimg.cn` 的 WAF 规则不同，静态资源通常不设防。

---

## 一、博主/作者排行榜

### 1.1 新晋作者榜（周更）

> 这就是「新晋作者热榜」，CSDN 榜单页的"新晋作者榜"tab。

```
GET https://blog.csdn.net/phoenix/web/v2/rank?page=1&pageSize=25&rankType=new_author
```

**必带头部：**
```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Referer: https://blog.csdn.net/rank/list
Accept: application/json
```

**参数说明：**

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| page | int | 页码 | 1 |
| pageSize | int | 每页条数（最大25） | 25 |
| rankType | string | 榜单类型 | new_author |

**返回结构（关键字段）：**
```json
{
  "code": 200,
  "data": {
    "maxPage": 20,
    "list": [
      {
        "currentRank": "1",          // 排名
        "hotRankScore": 2744,        // 热度分
        "userName": "m0_37988015",   // CSDN 用户名
        "nickName": "AI砖家",        // 显示昵称
        "avatarUrl": "https://...",
        "articleId": "160534060",    // 代表文章 ID
        "articleTitle": "...",       // 代表文章标题
        "articleDetailUrl": "https://blog.csdn.net/.../article/details/..."
      }
    ]
  }
}
```

### 1.2 作者周榜

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=weekly&page=1&pageSize=25
```

### 1.3 作者总榜

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=total&page=1&pageSize=25
```

### 1.4 原力榜

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=force&page=1&pageSize=25
```

### 1.5 新人榜

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=contributor&page=1&pageSize=25
```

### 1.6 历史贡献榜

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=historical&page=1&pageSize=25
```

### 1.7 领军人物

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=role&page=1&pageSize=25
```

### 1.8 社区榜

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=community&page=1&pageSize=25
```

---

## 二、博文排行榜

### 2.1 全站综合热榜（72h，时更）

```
GET https://blog.csdn.net/phoenix/web/blog/hotRank?pageSize=50
```

### 2.2 领域内容榜（日更）

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=content&page=1&pageSize=25
```

可选领域参数（需从页面 JS 获取完整列表）：
`type=c/c++`, `type=java`, `type=python`, `type=人工智能`, `type=前端` 等

### 2.3 博文运行榜（日更）

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=blog_project&page=1&pageSize=25
```

### 2.4 热门专栏榜（日更）

```
GET https://blog.csdn.net/phoenix/web/v2/rank?rankType=column&page=1&pageSize=25
```

---

## 三、榜单页面 JS Bundle 分析

CSDN 排行榜是 Vue SPA，数据通过 AJAX 加载。如果需要探索新接口或接口变动：

1. 访问 `https://blog.csdn.net/rank/list` 获取 HTML
2. 从 HTML 中提取 JS bundle URL：
   ```
   grep -oP 'chunk/tpl/blog-rank/index\.[a-f0-9]+\.js'
   ```
3. 下载 JS bundle（`csdnimg.cn` 域名无 WAF）：
   ```
   curl -s 'https://csdnimg.cn/release/cmsfe/public/js/chunk/tpl/blog-rank/index.XXXXXX.js'
   ```
4. 从 bundle 中提取 API 端点：
   ```
   grep -oP '(get|post)\("([^"]+)"' bundle.js
   ```

---

## 四、榜单类型完整映射

| 榜单名称 | rankType | 更新频率 | 对应页面 tab |
|---------|----------|---------|------------|
| 全站综合热榜 | (使用 blog/hotRank) | 72h，时更 | 热榜首页 |
| 领域内容榜 | content | 日更 | 领域内容榜 |
| 博文运行榜 | blog_project | 日更 | 博文运行榜 |
| 热门专栏榜 | column | 日更 | 热门专栏榜 |
| 新晋作者榜 | new_author | 周更 | 新晋作者榜 |
| 作者周榜 | weekly | 周更 | 作者周榜 |
| 作者总榜 | total | 周更 | 作者总榜 |
| 历史贡献榜 | historical | 周更 | 历史贡献榜 |
| 原力榜 | force | 日更 | 原力榜 |
| 新人榜 | contributor | 日更 | 新人榜 |
| 领军人物 | role | 日更 | 领军人物 |
| 社区榜 | community | 日更 | 社区榜 |
| 里程碑专区 | milestone | 时更 | 里程碑专区 |

---

## 五、实用 curl 示例

```bash
# 获取新晋作者榜 TOP 5
curl -s 'https://blog.csdn.net/phoenix/web/v2/rank?page=1&pageSize=5&rankType=new_author' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' \
  -H 'Referer: https://blog.csdn.net/rank/list' \
  | python3 -m json.tool

# 获取全站热榜
curl -s 'https://blog.csdn.net/phoenix/web/blog/hotRank?pageSize=50' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' \
  -H 'Referer: https://blog.csdn.net/rank/list' \
  | python3 -m json.tool
```

---

## 六、常见问题

**Q: 为什么 curl 不加 Referer 也能用？**
A: 有时可以，但不可靠。WAF 规则会变动，加上 Referer 更稳定。

**Q: 无头浏览器（Playwright/Puppeteer）能用吗？**
A: 实测不行。CSDN 的 WAF 会检测 headless 特征并返回 403。直接用 HTTP API 是更可靠的方案。

**Q: 如何发现新的 rankType？**
A: 从 JS bundle 中搜索 `tablist` 数组，或搜索 `rankType` 字符串。bundle 文件路径格式固定，hash 值需从 HTML 提取。

**Q: pageSize 最大多少？**
A: 新晋作者榜等接口最大 25。全站热榜最大 50。
