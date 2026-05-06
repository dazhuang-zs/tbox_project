# 鸿蒙网络编程入门：接入 GitHub API，做一个热门项目浏览器

> 读完这篇文章，你能：在鸿蒙 App 中发起 HTTP 请求、解析 JSON 数据、实现页面跳转传递参数、做出下拉刷新和上拉加载效果。

---

**前置条件**：读完前 3 篇，掌握了 ArkTS 基础、组件使用、状态管理。

---

## 一、网络请求基础

### 1.1 引入网络模块

```typescript
import { http } from '@kit.NetworkKit'
```

### 1.2 发起一个 GET 请求（五步走）

```typescript
// 第 1 步：创建请求对象
let httpRequest = http.createHttp()

// 第 2 步：设置请求参数
let url = 'https://api.github.com/search/repositories?q=stars:>1000&sort=stars&per_page=10'

// 第 3 步：发起请求（异步）
httpRequest.request(url, {
  method: http.RequestMethod.GET,
  header: {
    'User-Agent': 'HarmonyOS-App',      // GitHub API 要求必须带 User-Agent
    'Accept': 'application/vnd.github+json'
  }
}).then((response) => {
  // 第 4 步：处理成功
  if (response.responseCode === 200) {
    let result = response.result as string    // 响应体是字符串
    let data = JSON.parse(result)             // 解析 JSON
    console.log(JSON.stringify(data))         // 打印看看长什么样
  } else {
    console.error('请求失败：' + response.responseCode)
  }
}).catch((error) => {
  // 第 5 步：处理异常
  console.error('网络错误：' + JSON.stringify(error))
}).finally(() => {
  // 释放资源
  httpRequest.destroy()
})
```

### 1.3 GitHub API 接口说明

我们用 GitHub 的公共搜索接口：

```
接口地址：https://api.github.com/search/repositories
参数：
  q        → 搜索关键词（如 stars:>1000 或 鸿蒙）
  sort     → 排序方式（stars / updated）
  order    → desc / asc
  per_page → 每页条数
  page     → 页码

示例：
  ?q=harmonyos&sort=stars&order=desc&per_page=20&page=1
```

**返回数据结构：**
```json
{
  "total_count": 12345,
  "items": [
    {
      "id": 123,
      "name": "项目名",
      "full_name": "作者/项目名",
      "description": "项目描述",
      "stargazers_count": 1000,
      "forks_count": 200,
      "language": "TypeScript",
      "html_url": "https://github.com/xxx/xxx",
      "owner": {
        "login": "作者名",
        "avatar_url": "头像地址"
      }
    }
  ]
}
```

---

## 二、数据模型定义

### 2.1 把 GitHub 返回的 JSON 映射为 TypeScript 类

```typescript
// 仓库数据模型
class RepoItem {
  id: number
  name: string
  fullName: string
  description: string
  stars: number
  forks: number
  language: string
  htmlUrl: string
  authorName: string
  avatarUrl: string

  constructor(item: Record<string, Object>) {
    this.id = item['id'] as number
    this.name = item['name'] as string
    this.fullName = item['full_name'] as string
    this.description = (item['description'] || '暂无描述') as string
    this.stars = item['stargazers_count'] as number
    this.forks = item['forks_count'] as number
    this.language = (item['language'] || '未知') as string
    this.htmlUrl = item['html_url'] as string
    this.authorName = item['owner']['login'] as string
    this.avatarUrl = item['owner']['avatar_url'] as string
  }
}
```

---

## 三、网络权限配置

在 `entry/src/main/module.json5` 中添加：

```json5
{
  "module": {
    "requestPermissions": [
      {
        "name": "ohos.permission.INTERNET"    // 🔑 必须加！否则网络请求全部失败
      }
    ]
  }
}
```

---

## 四、实战：GitHub 热门项目浏览器

### 4.1 功能设计

```
┌──────────────────────────┐
│  🔍 [搜索框：输入关键词]  │
├──────────────────────────┤
│  ┌──────────────────┐    │
│  │ 🟠 openclaw      │    │
│  │ AI 编程助手      │    │
│  │ ⭐ 5,200  🍴 800 │    │
│  │ 📝 TypeScript    │    │
│  │ 👤 作者头像 作者名 │    │
│  └──────────────────┘    │
│  ┌──────────────────┐    │
│  │ 🟢 harmonyos-app │    │
│  │ ...              │    │
│  └──────────────────┘    │
│  ...                     │
│        加载中...          │
└──────────────────────────┘
```

功能：
- ✅ 输入关键词搜索 GitHub 项目
- ✅ 列表展示项目基本信息
- ✅ 点击项目跳转到详情页
- ✅ 下拉刷新
- ✅ 上拉加载更多

### 4.2 首页代码：`pages/GithubPage.ets`

```typescript
import { http } from '@kit.NetworkKit'
import { router } from '@kit.ArkUI'

class RepoItem {
  id: number = 0
  name: string = ''
  fullName: string = ''
  description: string = ''
  stars: number = 0
  forks: number = 0
  language: string = ''
  htmlUrl: string = ''
  authorName: string = ''
  avatarUrl: string = ''

  constructor(item: Record<string, Object>) {
    this.id = item['id'] as number
    this.name = item['name'] as string
    this.fullName = item['full_name'] as string
    this.description = (item['description'] || '暂无描述') as string
    this.stars = item['stargazers_count'] as number
    this.forks = item['forks_count'] as number
    this.language = (item['language'] || '未知') as string
    this.htmlUrl = item['html_url'] as string
    this.authorName = item['owner']['login'] as string
    this.avatarUrl = item['owner']['avatar_url'] as string
  }
}

@Entry
@Component
struct GithubPage {
  @State repoList: RepoItem[] = []
  @State searchKeyword: string = ''
  @State isLoading: boolean = false
  @State hasMore: boolean = true
  @State currentPage: number = 1
  @State errorMsg: string = ''

  // 默认搜索关键词（页面刚打开时显示热门项目）
  aboutToAppear(): void {
    this.searchKeyword = ''
    this.searchRepos(true)
  }

  // 搜索仓库
  searchRepos(isRefresh: boolean = false): void {
    if (isRefresh) {
      this.currentPage = 1
      this.hasMore = true
      this.repoList = []
    }

    if (this.isLoading || !this.hasMore) return
    this.isLoading = true
    this.errorMsg = ''

    // 构造搜索 URL
    let keyword = this.searchKeyword.trim() || 'stars:>5000'   // 没填关键词时默认搜高分项目
    let url = `https://api.github.com/search/repositories?q=${encodeURIComponent(keyword)}&sort=stars&order=desc&per_page=15&page=${this.currentPage}`

    let httpRequest = http.createHttp()
    httpRequest.request(url, {
      method: http.RequestMethod.GET,
      header: {
        'User-Agent': 'HarmonyOS-App',
        'Accept': 'application/vnd.github+json'
      }
    }).then((response) => {
      if (response.responseCode === 200) {
        let data = JSON.parse(response.result as string)
        let items = data['items'] as Array<Record<string, Object>>

        if (items && items.length > 0) {
          let newRepos = items.map(item => new RepoItem(item))
          this.repoList = isRefresh ? newRepos : this.repoList.concat(newRepos)
          this.currentPage++
        } else {
          this.hasMore = false
        }
      } else {
        this.errorMsg = `请求失败 (${response.responseCode})`
      }
    }).catch((error) => {
      this.errorMsg = '网络错误，请检查网络连接和权限配置'
      console.error(JSON.stringify(error))
    }).finally(() => {
      this.isLoading = false
      httpRequest.destroy()
    })
  }

  // 格式化数字（10000 → 10.0k）
  formatCount(num: number): string {
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'k'
    }
    return num.toString()
  }

  // 跳转到详情页
  goDetail(repo: RepoItem): void {
    router.pushUrl({
      url: 'pages/RepoDetail',
      params: {
        name: repo.fullName,
        description: repo.description,
        stars: repo.stars,
        forks: repo.forks,
        language: repo.language,
        url: repo.htmlUrl,
        authorName: repo.authorName,
        avatarUrl: repo.avatarUrl
      }
    })
  }

  build() {
    Column() {
      // ===== 顶部标题栏 =====
      Text('🐙 GitHub 项目浏览器')
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .width('100%')
        .padding(16)
        .backgroundColor('#24292F')
        .fontColor(Color.White)

      // ===== 搜索框 =====
      Row() {
        TextInput({ placeholder: '搜索项目，如 harmonyos、AI...' })
          .fontSize(15)
          .layoutWeight(1)
          .height(40)
          .backgroundColor('#F0F0F0')
          .borderRadius(20)
          .padding({ left: 16, right: 16 })
          .onChange((value: string) => {
            this.searchKeyword = value
          })
          .onSubmit(() => {
            this.searchRepos(true)     // 回车搜索
          })

        Button('搜索')
          .fontSize(14)
          .height(40)
          .padding({ left: 16, right: 16 })
          .margin({ left: 8 })
          .backgroundColor('#24292F')
          .borderRadius(20)
          .onClick(() => {
            this.searchRepos(true)
          })
      }
      .width('100%')
      .padding({ left: 12, right: 12, top: 10, bottom: 10 })
      .backgroundColor(Color.White)

      // ===== 错误提示 =====
      if (this.errorMsg !== '') {
        Text(this.errorMsg)
          .fontSize(14)
          .fontColor('#FF4444')
          .width('100%')
          .padding(16)
      }

      // ===== 项目列表 =====
      List() {
        if (this.repoList.length === 0 && !this.isLoading) {
          ListItem() {
            Column() {
              Text('🔍')
                .fontSize(48)
                .margin({ top: 60 })
              Text('输入关键词搜索 GitHub 项目')
                .fontSize(16)
                .fontColor('#999999')
                .margin({ top: 12 })
            }
            .width('100%')
          }
        }

        ForEach(this.repoList, (repo: RepoItem) => {
          ListItem() {
            Column() {
              // 第一行：项目名 + 语言标签
              Row() {
                Text(repo.fullName)
                  .fontSize(16)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#0366D6')
                  .layoutWeight(1)
                  .maxLines(1)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })

                if (repo.language !== '未知') {
                  Text(repo.language)
                    .fontSize(11)
                    .fontColor('#666666')
                    .backgroundColor('#F0F0F0')
                    .borderRadius(8)
                    .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                }
              }
              .width('100%')
              .alignItems(VerticalAlign.Center)

              // 第二行：描述
              Text(repo.description)
                .fontSize(14)
                .fontColor('#555555')
                .margin({ top: 6 })
                .maxLines(2)
                .textOverflow({ overflow: TextOverflow.Ellipsis })

              // 第三行：数据 + 作者
              Row() {
                Row() {
                  Text('⭐ ' + this.formatCount(repo.stars))
                    .fontSize(13)
                    .fontColor('#666666')
                  Text('  🍴 ' + this.formatCount(repo.forks))
                    .fontSize(13)
                    .fontColor('#666666')
                    .margin({ left: 12 })
                }

                Blank()

                Image(repo.avatarUrl)
                  .width(20)
                  .height(20)
                  .borderRadius(10)

                Text(repo.authorName)
                  .fontSize(13)
                  .fontColor('#666666')
                  .margin({ left: 6 })
              }
              .width('100%')
              .margin({ top: 8 })
            }
            .width('100%')
            .padding({ left: 16, right: 16, top: 14, bottom: 14 })
          }
          .onClick(() => {
            this.goDetail(repo)
          })
          .border({
            width: { bottom: 0.5 },
            color: '#EEEEEE'
          })
        })

        // 底部加载提示
        ListItem() {
          Row() {
            if (this.isLoading) {
              LoadingProgress()
                .width(20)
                .height(20)
              Text('加载中...')
                .fontSize(13)
                .fontColor('#999999')
                .margin({ left: 8 })
            } else if (!this.hasMore) {
              Text('— 没有更多了 —')
                .fontSize(13)
                .fontColor('#CCCCCC')
            } else {
              Text('上拉加载更多')
                .fontSize(13)
                .fontColor('#CCCCCC')
                .onClick(() => {
                  this.searchRepos(false)
                })
            }
          }
          .width('100%')
          .height(50)
          .justifyContent(FlexAlign.Center)
        }
      }
      .layoutWeight(1)
      .width('100%')
      .backgroundColor(Color.White)
      .onReachEnd(() => {
        // 🔑 列表滚到底部自动加载更多
        if (!this.isLoading && this.hasMore) {
          this.searchRepos(false)
        }
      })
    }
    .width('100%')
    .height('100%')
  }
}
```

---

## 五、详情页：`pages/RepoDetail.ets`

```typescript
import { router } from '@kit.ArkUI'

@Entry
@Component
struct RepoDetail {
  @State name: string = ''
  @State description: string = ''
  @State stars: number = 0
  @State forks: number = 0
  @State language: string = ''
  @State url: string = ''
  @State authorName: string = ''
  @State avatarUrl: string = ''

  // 接收上一页传来的参数
  aboutToAppear(): void {
    let params = router.getParams() as Record<string, Object>
    if (params) {
      this.name = params['name'] as string
      this.description = params['description'] as string
      this.stars = params['stars'] as number
      this.forks = params['forks'] as number
      this.language = params['language'] as string
      this.url = params['url'] as string
      this.authorName = params['authorName'] as string
      this.avatarUrl = params['avatarUrl'] as string
    }
  }

  formatCount(num: number): string {
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
    return num.toString()
  }

  build() {
    Column() {
      // 顶部栏
      Row() {
        Button('← 返回')
          .fontSize(15)
          .backgroundColor(Color.Transparent)
          .fontColor(Color.White)
          .onClick(() => {
            router.back()
          })

        Blank()

        Text('项目详情')
          .fontSize(18)
          .fontColor(Color.White)
          .fontWeight(FontWeight.Bold)

        Blank()
        Blank()   // 占位，让标题居中
      }
      .width('100%')
      .padding({ left: 12, right: 12, top: 8, bottom: 8 })
      .backgroundColor('#24292F')

      // 内容区
      Column() {
        // 作者信息
        Row() {
          Image(this.avatarUrl)
            .width(64)
            .height(64)
            .borderRadius(32)
          Text(this.authorName)
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .margin({ left: 16 })
        }
        .width('100%')
        .margin({ top: 24 })

        // 项目名
        Text(this.name)
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .fontColor('#0366D6')
          .width('100%')
          .margin({ top: 20 })

        // 描述
        Text(this.description)
          .fontSize(16)
          .fontColor('#555555')
          .width('100%')
          .margin({ top: 12 })
          .lineHeight(24)

        // 数据卡片
        Row() {
          Row() {
            Text('⭐')
              .fontSize(20)
            Text('  ' + this.formatCount(this.stars))
              .fontSize(18)
              .fontWeight(FontWeight.Bold)
          }
          .backgroundColor('#FFFDE7')
          .borderRadius(8)
          .padding({ left: 16, right: 16, top: 10, bottom: 10 })

          Row() {
            Text('🍴  ' + this.formatCount(this.forks))
              .fontSize(16)
          }
          .backgroundColor('#E8F5E9')
          .borderRadius(8)
          .padding({ left: 16, right: 16, top: 10, bottom: 10 })
          .margin({ left: 12 })

          if (this.language !== '未知') {
            Text(this.language)
              .fontSize(16)
              .fontColor('#666666')
              .backgroundColor('#F0F0F0')
              .borderRadius(8)
              .padding({ left: 16, right: 16, top: 10, bottom: 10 })
              .margin({ left: 12 })
          }
        }
        .width('100%')
        .margin({ top: 24 })

        // 跳转到 GitHub 按钮
        Button('🔗 在 GitHub 上查看')
          .fontSize(16)
          .width('80%')
          .height(48)
          .margin({ top: 40 })
          .backgroundColor('#24292F')
          .borderRadius(24)
          .onClick(() => {
            // 提示用户手动访问（后续可以用 WebView 内嵌打开）
            console.log('项目地址：' + this.url)
          })
      }
      .width('90%')
      .layoutWeight(1)
    }
    .width('100%')
    .height('100%')
  }
}
```

---

## 六、下拉刷新

在 List 上添加：

```typescript
List() {
  // ... 列表内容
}
.onRefresh(() => {
  // 用户下拉时触发
  this.searchRepos(true)
})
```

完整的 List 配置：

```typescript
List() {
  // ... ForEach 渲染
}
.onRefresh(() => {
  return new Promise<void>((resolve) => {
    // 这里直接调搜索，setTimeout 模拟最小等待
    this.searchRepos(true)
    setTimeout(() => resolve(), 500)
  })
})
.onReachEnd(() => {
  // 滚到底部加载更多
  if (!this.isLoading && this.hasMore) {
    this.searchRepos(false)
  }
})
```

---

## 七、本节要点回顾

| 学会什么 | 具体内容 |
|---------|---------|
| HTTP 请求 | `http.createHttp() → request() → .then/.catch → destroy()` |
| JSON 解析 | `JSON.parse()` + TypeScript 数据模型 |
| 网络权限 | `module.json5` 加 `ohos.permission.INTERNET` |
| 页面跳转 | `router.pushUrl()` 传参数，`router.getParams()` 接收 |
| 搜索功能 | 输入框 + 发送请求 + 刷新列表 |
| 分页加载 | `page` 自增 + `concat` 追加数据 |
| 实战项目 | GitHub 热门项目浏览器（搜索 + 列表 + 详情） |

---

## 八、常见问题

**Q：网络请求一直失败，返回 401/403？**
GitHub API 有频率限制，未认证时每小时 60 次。如果频繁调试被限了，等一小时就好。生产环境建议用 Token 认证。

**Q：页面跳转后返回数据不刷新？**
用 `router.back()` 返回上一页后，列表页的 `@State` 数据还在，不需要额外处理。

**Q：图片加载不出来？**
检查：1) URL 是否正确 2) 网络权限是否加了 3) 图片是否被防火墙拦截。

**Q：怎么调试网络请求？**
在 `.catch()` 里打印 `console.error(JSON.stringify(error))`，在 DevEco Studio 底部 Log 窗口看输出。

---

## 下一篇预告

第 5 篇（大结局）：《鸿蒙 AI 实战：调用大模型 API，从零开发 AI 聊天助手》

你会学到：
- 对接 DeepSeek / OpenAI 等大模型 API
- 流式输出（SSE）的实现
- 对话历史管理
- 真机部署与签名打包
- 完整的 AI 聊天助手 App（对话、流式回复、Markdown 渲染）

---

> 📦 本系列代码仓库：https://github.com/dazhuang-zs/harmonyos-series
>
> 💬 有问题直接评论区，一起交流进步。
>
> 🔔 这是《从零到实战：鸿蒙应用开发 5 篇系列》的第 4 篇，最后一篇压轴，关注别错过！
