# 鸿蒙 AI 实战：调用大模型 API，从零开发 AI 聊天助手

> 读完这篇压轴文章，你能：对接大模型 API（DeepSeek 等）、实现流式输出、管理多轮对话、开发一个完整的 AI 聊天助手 App——并真正部署到手机上使用。

---

**前置条件**：读完前 4 篇，掌握了网络请求、页面跳转、状态管理。

---

## 一、为什么要在鸿蒙 App 里集成 AI？

2026 年，AI 不是「加分项」，是「标配」。

一个「AI 聊天助手」App 能让你：
- 把前 4 篇学的 UI、数据、网络、状态管理**全部串起来**
- 做出一个真正能**展示给面试官/客户**的项目
- 作为你鸿蒙开发能力的代表作

---

## 二、准备工作：获取大模型 API Key

本文以 **DeepSeek** 为例（国内访问快、有免费额度），OpenAI/ChatGPT 接口兼容。

### 2.1 注册获取 Key

1. 访问 DeepSeek 开放平台：**https://platform.deepseek.com/**
2. 注册账号 → 进入 API Keys 页面 → 创建新 Key
3. 复制 Key（只显示一次，保存好）

### 2.2 API 接口说明

```
接口地址：https://api.deepseek.com/v1/chat/completions
请求方式：POST
Headers：
  Content-Type: application/json
  Authorization: Bearer <你的 API Key>

请求体：
{
  "model": "deepseek-chat",
  "messages": [
    { "role": "system", "content": "你是一个有用的助手" },
    { "role": "user", "content": "你好" }
  ],
  "stream": true,          // 🔑 true = 流式输出，false = 一次性返回
  "temperature": 0.7
}

响应（stream=false 时）：
{
  "choices": [
    {
      "message": {
        "content": "你好！有什么可以帮助你的？"
      }
    }
  ]
}

响应（stream=true 时，多段返回）：
data: {"choices":[{"delta":{"content":"你"}}]}
data: {"choices":[{"delta":{"content":"好"}}]}
data: {"choices":[{"delta":{"content":"！"}}]}
data: [DONE]
```

---

## 三、流式输出（SSE）的核心实现

### 3.1 什么是流式输出？

普通请求：发过去 → 等 3 秒 → 一次性拿到全部回复

流式输出：发过去 → 一个字一个字往外蹦 → 像 ChatGPT 聊天一样的效果

### 3.2 鸿蒙中实现 SSE 流式读取

```typescript
import { http } from '@kit.NetworkKit'

// 流式发送请求
function requestStreaming(
  apiKey: string,
  messages: Array<{role: string, content: string}>,
  onChunk: (text: string) => void,
  onDone: () => void
): void {
  let httpRequest = http.createHttp()

  // 关键：设置 responseType 为 0（默认文本流）
  let requestBody = JSON.stringify({
    model: 'deepseek-chat',
    messages: messages,
    stream: true,
    temperature: 0.7
  })

  httpRequest.request('https://api.deepseek.com/v1/chat/completions', {
    method: http.RequestMethod.POST,
    header: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    extraData: requestBody,
    expectDataType: http.HttpDataType.STRING
  }).then((response) => {
    if (response.responseCode === 200) {
      // 手动解析 SSE 流
      let fullText = response.result as string
      let lines = fullText.split('\n')

      for (let line of lines) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          try {
            let jsonStr = line.substring(6)   // 去掉 "data: " 前缀
            let data = JSON.parse(jsonStr)
            let content = data['choices'][0]['delta']['content']
            if (content) {
              onChunk(content)               // 每收到一个字就回调
            }
          } catch (e) {
            // 解析失败的跳过
          }
        }
      }
      onDone()
    }
  }).catch((error) => {
    console.error('请求失败：' + JSON.stringify(error))
    onDone()
  }).finally(() => {
    httpRequest.destroy()
  })
}
```

> ⚠️ 注意：鸿蒙的 `http` 模块对 SSE 原生支持有限，上面的方法是把整段流当一次响应处理再手动分行。如果需要逐字实时显示，可以用 `@ohos.net.socket` 做 TCP 长连接。本文采用简化版：**先请求完整流，再逐字添加到对话框**，视觉上同样的打字机效果。

---

## 四、实战：AI 聊天助手 App

### 4.1 功能设计

```
┌──────────────────────────────┐
│  🤖 AI 聊天助手               │
├──────────────────────────────┤
│                              │
│                     ┌──────┐ │
│                     │ 你好 │ │  ← 用户消息（右侧，蓝色气泡）
│                     └──────┘ │
│  ┌──────────────────────┐    │
│  │ 你好！有什么可以帮助   │    │  ← AI 回复（左侧，灰色气泡）
│  │ 你的？               │    │
│  └──────────────────────┘    │
│                     ┌──────┐ │
│                     │鸿蒙...│ │
│                     └──────┘ │
│  ┌──────────────────────┐    │
│  │ 鸿蒙是华为开发的...   │    │
│  └──────────────────────┘    │
│                              │
│  ┌──────────────────────┐    │
│  │ 正在输入...           │    │  ← 加载状态
│  └──────────────────────┘    │
├──────────────────────────────┤
│  [输入消息...]      [发送]   │
└──────────────────────────────┘
```

功能：
- ✅ 发送消息 → AI 流式回复
- ✅ 多轮对话历史
- ✅ 对话气泡 UI
- ✅ 加载状态显示
- ✅ 配置自己的 API Key

### 4.2 完整代码

文件：`pages/ChatPage.ets`

```typescript
import { http } from '@kit.NetworkKit'
import { preferences } from '@kit.ArkData'

// 对话消息模型
class ChatMessage {
  id: number
  role: string          // 'user' 或 'assistant'
  content: string
  isStreaming: boolean  // 是否正在流式输出中

  constructor(id: number, role: string, content: string = '') {
    this.id = id
    this.role = role
    this.content = content
    this.isStreaming = false
  }
}

@Entry
@Component
struct ChatPage {
  @State messageList: ChatMessage[] = []
  @State inputText: string = ''
  @State isLoading: boolean = false     // 是否等待 AI 回复
  @State apiKey: string = ''
  @State showKeyInput: boolean = false   // 是否显示 Key 输入框
  private nextId: number = 1
  private pref = preferences.getPreferencesSync(getContext(), { name: 'chatData' })

  // 系统提示词
  private systemPrompt: string = '你是一个友好的 AI 助手，用中文简洁回答用户的问题。回答请控制在 300 字以内。'

  aboutToAppear(): void {
    this.loadApiKey()
    // 添加欢迎消息
    if (this.messageList.length === 0) {
      this.messageList.push(new ChatMessage(this.nextId++, 'assistant', '👋 你好！我是 AI 聊天助手。\n\n我已经接入了 DeepSeek 大模型，可以帮你写代码、回答问题、翻译等等。下方输入你的问题，开始聊天吧！\n\n💡 首次使用请在顶部配置 API Key。'))
    }
  }

  loadApiKey(): void {
    this.apiKey = this.pref.getSync('apiKey', '') as string
  }

  saveApiKey(): void {
    this.pref.putSync('apiKey', this.apiKey)
    this.pref.flush()
  }

  // 发送消息
  sendMessage(): void {
    if (this.inputText.trim() === '' || this.isLoading) return

    let userMsg = this.inputText.trim()
    this.inputText = ''

    // 添加用户消息
    this.messageList.push(new ChatMessage(this.nextId++, 'user', userMsg))

    // 调用 AI
    this.callAI(userMsg)
  }

  // 调用 AI API
  callAI(userMessage: string): void {
    if (this.apiKey === '') {
      // 没有 API Key，给用户模拟回复
      setTimeout(() => {
        this.messageList.push(new ChatMessage(this.nextId++, 'assistant',
          '⚠️ 请先设置 API Key！\n\n点击页面右上角「⚙️ 设置 Key」，填入你的 DeepSeek API Key。\n\n获取方式：访问 https://platform.deepseek.com/ 注册并创建 Key。'))
      }, 500)
      return
    }

    this.isLoading = true

    // 构造消息历史（只发最近 10 条，避免 token 太长）
    let recentMessages = this.messageList.slice(-10)
    let messages = [
      { role: 'system', content: this.systemPrompt },
      ...recentMessages.map(m => ({ role: m.role, content: m.content }))
    ]

    // 创建一条空的 assistant 消息，准备流式填充
    let aiMsg = new ChatMessage(this.nextId++, 'assistant', '')
    aiMsg.isStreaming = true
    this.messageList.push(aiMsg)

    // 发送请求
    this.streamRequest(messages, aiMsg)
  }

  // 流式请求方法
  streamRequest(
    messages: Array<{role: string, content: string}>,
    aiMsg: ChatMessage
  ): void {
    let httpRequest = http.createHttp()

    let requestBody = JSON.stringify({
      model: 'deepseek-chat',
      messages: messages,
      stream: false,         // 简化：先拿完整响应，再模拟流式效果
      temperature: 0.7,
      max_tokens: 1000
    })

    httpRequest.request('https://api.deepseek.com/v1/chat/completions', {
      method: http.RequestMethod.POST,
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      extraData: requestBody,
      expectDataType: http.HttpDataType.STRING
    }).then((response) => {
      if (response.responseCode === 200) {
        let data = JSON.parse(response.result as string)
        let reply = data['choices'][0]['message']['content'] as string

        // 模拟流式效果：逐字显示
        this.simulateStream(reply, aiMsg)
      } else {
        aiMsg.content = `❌ 请求失败 (${response.responseCode})`
        aiMsg.isStreaming = false
        this.isLoading = false
      }
    }).catch((error) => {
      aiMsg.content = '❌ 网络错误，请检查网络连接和 API Key 是否正确'
      aiMsg.isStreaming = false
      this.isLoading = false
      console.error(JSON.stringify(error))
    }).finally(() => {
      httpRequest.destroy()
    })
  }

  // 模拟流式打字机效果
  simulateStream(fullText: string, aiMsg: ChatMessage): void {
    let index = 0
    let chars = fullText.split('')
    let timer = setInterval(() => {
      if (index < chars.length) {
        aiMsg.content += chars[index]
        index++
      } else {
        clearInterval(timer)
        aiMsg.isStreaming = false
        this.isLoading = false
      }
    }, 30)   // 每 30ms 显示一个字，模拟打字
  }

  // 滚动列表（后续可扩展）

  build() {
    Column() {
      // ===== 顶部栏 =====
      Row() {
        Text('🤖 AI 聊天助手')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .layoutWeight(1)

        Button('⚙️ 设置 Key')
          .fontSize(12)
          .height(32)
          .backgroundColor('#4A90D9')
          .borderRadius(16)
          .padding({ left: 12, right: 12 })
          .onClick(() => {
            this.showKeyInput = !this.showKeyInput     // 切换 Key 输入框显隐
          })
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 8, bottom: 8 })
      .backgroundColor('#24292F')
      .fontColor(Color.White)

      // ===== API Key 输入区（点击设置后显示）=====
      if (this.showKeyInput) {
        Row() {
          TextInput({ placeholder: '输入 DeepSeek API Key...', text: this.apiKey })
            .fontSize(13)
            .layoutWeight(1)
            .height(36)
            .backgroundColor(Color.White)
            .borderRadius(4)
            .padding({ left: 10, right: 10 })
            .onChange((value: string) => {
              this.apiKey = value
            })

          Button('保存')
            .fontSize(13)
            .height(36)
            .margin({ left: 8 })
            .backgroundColor('#4A90D9')
            .borderRadius(4)
            .onClick(() => {
              this.saveApiKey()
              this.showKeyInput = false
            })
        }
        .width('100%')
        .padding({ left: 12, right: 12, top: 8, bottom: 8 })
        .backgroundColor('#F5F5F5')
      }

      // ===== 对话列表 =====
      List() {
        ForEach(this.messageList, (msg: ChatMessage) => {
          ListItem() {
            // 用户和 AI 消息用不同样式
            if (msg.role === 'user') {
              // 用户消息（右对齐，蓝色气泡）
              Row() {
                Blank()
                Text(msg.content)
                  .fontSize(15)
                  .fontColor(Color.White)
                  .backgroundColor('#4A90D9')
                  .borderRadius({ topLeft: 12, topRight: 12, bottomLeft: 12 })
                  .padding({ left: 14, right: 14, top: 10, bottom: 10 })
                  .maxWidth('75%')
              }
              .width('100%')
              .padding({ left: 12, right: 12, top: 6, bottom: 6 })
            } else {
              // AI 消息（左对齐，灰色气泡）
              Row() {
                Column() {
                  Text(msg.content)
                    .fontSize(15)
                    .fontColor('#222222')
                    .backgroundColor('#F0F0F0')
                    .borderRadius({ topLeft: 12, topRight: 12, bottomRight: 12 })
                    .padding({ left: 14, right: 14, top: 10, bottom: 10 })
                    .lineHeight(22)

                  // 如果正在流式输出，显示光标动画
                  if (msg.isStreaming) {
                    Text('▍')
                      .fontSize(16)
                      .fontColor('#999999')
                      .margin({ left: 10, top: 2 })
                  }
                }
                .alignItems(HorizontalAlign.Start)

                Blank()
              }
              .width('100%')
              .padding({ left: 12, right: 12, top: 6, bottom: 6 })
            }
          }
        })

        // 滚动到最底部（新消息出现时）
        ListItem() {
          Blank().height(4)
        }
      }
      .layoutWeight(1)
      .width('100%')
      .backgroundColor('#EDEDED')

      // ===== 底部输入区域 =====
      Row() {
        TextInput({ placeholder: '输入消息...', text: this.inputText })
          .fontSize(15)
          .layoutWeight(1)
          .height(44)
          .backgroundColor(Color.White)
          .borderRadius(22)
          .padding({ left: 18, right: 18 })
          .enabled(!this.isLoading)        // 等待回复时禁用
          .onChange((value: string) => {
            this.inputText = value
          })
          .onSubmit(() => {
            this.sendMessage()
          })

        Button(this.isLoading ? '⏳' : '发送')
          .fontSize(15)
          .height(44)
          .margin({ left: 8 })
          .backgroundColor(this.isLoading ? '#CCCCCC' : '#4A90D9')
          .borderRadius(22)
          .padding({ left: 20, right: 20 })
          .enabled(!this.isLoading)
          .onClick(() => {
            this.sendMessage()
          })
      }
      .width('100%')
      .padding({ left: 12, right: 12, top: 8, bottom: 12 })
      .backgroundColor(Color.White)
      .border({ width: { top: 0.5 }, color: '#E0E0E0' })
    }
    .width('100%')
    .height('100%')
  }
}
```

---

## 五、运行与配置

### 5.1 在 EntryAbility 中启动聊天页

```typescript
// EntryAbility.ets
windowStage.loadContent('pages/ChatPage', (err, data) => {
  // ...
})
```

### 5.2 权限配置

```json5
// module.json5
{
  "module": {
    "requestPermissions": [
      {
        "name": "ohos.permission.INTERNET"
      }
    ]
  }
}
```

### 5.3 使用你自己的 API Key

打开 App → 点右上角「⚙️ 设置 Key」→ 填入 DeepSeek API Key → 保存。下次打开自动记住。

---

## 六、真机部署（签名 + 打包）

### 6.1 生成签名证书

1. DevEco Studio → Build → Generate Key and CSR
2. 填写信息（别名、密码），生成 `.p12` 密钥文件

### 6.2 配置签名

1. File → Project Structure → Signing Configs
2. 选择上一步生成的 `.p12` 文件，填写密码
3. 勾选「Automatically generate signature」

### 6.3 打包安装

1. Build → Build App(s) / Hap(s)
2. 生成 `.hap` 文件在 `build/outputs/default/` 目录
3. 用华为手机助手或数据线安装到真机

---

## 七、进阶扩展方向

这个 AI 聊天助手还可以继续升级：

| 方向 | 实现思路 |
|------|---------|
| **多模态** | 接入支持图片理解的模型（如 GPT-Image-2），上传图片 + 文字提问 |
| **Markdown 渲染** | 引入 Markdown 解析库，让 AI 回复支持代码高亮、表格 |
| **对话历史持久化** | 用 Preferences 存储 chatHistory，下次打开聊天记录还在 |
| **多会话管理** | 新建多个对话频道，每个独立上下文 |
| **语音输入** | 集成鸿蒙语音识别 API，语音转文字后发送 |

---

## 八、五篇系列总结

恭喜！你跟完了《从零到实战：鸿蒙应用开发 5 篇系列》。回顾一下旅程：

| 篇 | 学到了什么 | 做出了什么 |
|----|-----------|-----------|
| 第 1 篇 | 开发环境搭建、项目结构 | Hello World 交互页面 |
| 第 2 篇 | ArkTS 语法、五大组件、布局 | 个人名片页面 |
| 第 3 篇 | 状态管理、Preferences 持久化 | 待办清单 App |
| 第 4 篇 | HTTP 请求、JSON 解析、页面跳转 | GitHub 项目浏览器 |
| 第 5 篇 | AI API 对接、流式输出 | AI 聊天助手 |

**从零开始的你，现在已经可以独立开发鸿蒙 App 了。** 🎉

---

## 九、常见问题

**Q：没有 API Key 怎么办？**
可以先不填 Key，App 会给出提示。DeepSeek 注册即送免费额度，够你调试用了。

**Q：可以换成 OpenAI / 其他模型吗？**
可以。改 `url` 和 `Authorization` 头就行。OpenAI 接口格式跟 DeepSeek 完全兼容。

**Q：流式输出为什么不是真的一个字一个字来？**
鸿蒙的 `http` 模块对 SSE 长连接支持有限。本文用了「获取完整响应 → 逐字显示」的方案，视觉效果一样。如果需要真正的实时流，可以用 Socket 实现。

**Q：怎么让聊天记录保存下来？**
在 `sendMessage()` 之后，把 `this.messageList` 序列化存到 Preferences 里（参考第 3 篇的方法）。

---

> 📦 本系列全部代码：https://github.com/dazhuang-zs/harmonyos-series
>
> 💬 5 篇教程到此完结！有任何问题欢迎评论区留言，看到必回。
>
> 🔔 关注我，后续还有更多鸿蒙 + AI 实战系列。下一个系列想学什么？评论区告诉我！
