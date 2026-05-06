# 鸿蒙数据持久化实战：用 Preferences + 状态管理做一个待办清单

> 读完这篇文章，你能：理解 ArkTS 状态管理机制，用 Preferences 实现数据持久化存储，从零写出一个能增删改查的待办清单 App。

---

**前置条件**：读完第 1、2 篇，掌握 ArkTS 基础语法和 ArkUI 五大组件。

---

## 一、为什么需要「状态管理」和「数据持久化」？

先看一个问题：

```typescript
// 你做了一个计数器
let count = 0
Button('点我').onClick(() => { count++ })
// 点了几下 count 变成 5，但界面上还是 0 —— 为什么？
```

**因为普通变量 `count` 变了，界面不知道。**

这就是 `@State` 要解决的问题：**让变量和界面绑定，变量一变，界面自动刷新。**

### 1.1 @State — 组件自己的状态

```typescript
@State count: number = 0   // 界面会自动更新
```

**规则：** 
- 只在当前组件用 → 用 `@State`
- 要传给子组件 → 用 `@Prop`

### 1.2 @Prop — 父传子的单向数据

```typescript
// 父组件
@State parentMsg: string = '爸爸的消息'
ChildItem({ msg: this.parentMsg })    // 传给子组件

// 子组件
@Component
struct ChildItem {
  @Prop msg: string       // 接收，但不能改父组件的数据
}
```

### 1.3 @Link — 父子双向同步

```typescript
// 父组件
@State shared: number = 10
ChildItem({ value: $shared })   // 注意 $ 符号

// 子组件
@Component
struct ChildItem {
  @Link value: number     // 子组件改了 value，父组件 shared 也变
}
```

**状态管理速查表：**

| 装饰器 | 用途 | 记忆口诀 |
|--------|------|---------|
| `@State` | 当前组件内部状态 | 「我的地盘我做主」 |
| `@Prop` | 父传子，单向 | 「给你看看，别乱动」 |
| `@Link` | 父传子，双向 | 「给你用，改了我也知道」 |

---

## 二、数据持久化：Preferences（轻量级本地存储）

### 2.1 类比理解

| 概念 | 类比 |
|------|------|
| Preferences | 手机的「备忘录」或「便签」 |
| Key | 便签标题（唯一标识） |
| Value | 便签内容 |
| 存数据 | 写一张便签贴墙上 |
| 取数据 | 按标题找便签 |
| 删数据 | 撕掉便签 |

### 2.2 基础用法

```typescript
import { preferences } from '@kit.ArkData'

// 1. 获取 Preferences 实例
let pref = preferences.getPreferencesSync(getContext(), { name: 'myAppData' })

// 2. 存数据
pref.putSync('userName', '大壮')          // 存字符串
pref.putSync('taskCount', 5)              // 存数字
pref.putSync('isDarkMode', false)         // 存布尔

// 3. 持久化到磁盘（重要！不调用这个不会真正保存）
pref.flush()

// 4. 取数据
let name: string = pref.getSync('userName', '默认值') as string      // 第二个参数是默认值
let count: number = pref.getSync('taskCount', 0) as number

// 5. 删数据
pref.deleteSync('taskCount')
pref.flush()
```

**⚠️ 关键点：`flush()` 一定要调，否则数据不会保存到磁盘，关掉 App 就没了。**

---

## 三、实战：待办清单 App

### 3.1 功能设计

```
┌────────────────────────┐
│    📝 我的待办清单       │
├────────────────────────┤
│ [输入框: 添加新任务...]  │
│ [         添加按钮     ] │
├────────────────────────┤
│ ☑ 买咖啡豆       🗑️   │
│ ☐ 写鸿蒙教程      🗑️   │
│ ☐ 去健身房        🗑️   │
│ ☑ 提交周报        🗑️   │
├────────────────────────┤
│   共 4 项，已完成 2 项   │
└────────────────────────┘
```

功能：
- ✅ 添加新任务
- ✅ 勾选完成/取消完成
- ✅ 删除任务
- ✅ 显示统计
- ✅ 关掉 App 再打开，数据还在（持久化）

### 3.2 数据模型设计

```typescript
// 单个任务的数据结构
class TaskItem {
  id: number       // 唯一 ID
  title: string    // 任务标题
  done: boolean    // 是否完成

  constructor(id: number, title: string, done: boolean) {
    this.id = id
    this.title = title
    this.done = done
  }
}
```

### 3.3 完整代码

文件：`pages/TodoPage.ets`

```typescript
import { preferences } from '@kit.ArkData'

// 任务数据模型
class TaskItem {
  id: number
  title: string
  done: boolean

  constructor(id: number, title: string, done: boolean = false) {
    this.id = id
    this.title = title
    this.done = done
  }
}

@Entry
@Component
struct TodoPage {
  @State taskList: TaskItem[] = []           // 所有任务
  @State inputText: string = ''              // 输入框内容
  @State nextId: number = 1                  // 自增 ID
  private pref = preferences.getPreferencesSync(getContext(), { name: 'todoData' })

  // 页面出现时加载数据
  aboutToAppear(): void {
    this.loadTasks()
  }

  // 从 Preferences 加载任务列表
  loadTasks(): void {
    let savedJson: string = this.pref.getSync('taskList', '[]') as string
    // 解析 JSON 字符串还原为 TaskItem 数组
    let rawList: Array<{id: number, title: string, done: boolean}> = JSON.parse(savedJson)
    this.taskList = rawList.map(item => new TaskItem(item.id, item.title, item.done))

    // 还原 nextId
    this.nextId = this.pref.getSync('nextId', 1) as number
  }

  // 保存任务列表到 Preferences
  saveTasks(): void {
    let jsonStr = JSON.stringify(this.taskList)
    this.pref.putSync('taskList', jsonStr)
    this.pref.putSync('nextId', this.nextId)
    this.pref.flush()   // ⚠️ 必须调用
  }

  // 添加新任务
  addTask(): void {
    if (this.inputText.trim() === '') {
      return    // 空内容不添加
    }
    let newTask = new TaskItem(this.nextId, this.inputText.trim())
    this.taskList.unshift(newTask)   // 新任务加到最前面
    this.nextId++
    this.inputText = ''              // 清空输入框
    this.saveTasks()                 // 立即持久化
  }

  // 切换完成状态
  toggleTask(index: number): void {
    this.taskList[index].done = !this.taskList[index].done
    this.saveTasks()
  }

  // 删除任务
  deleteTask(index: number): void {
    this.taskList.splice(index, 1)   // 从数组中移除
    this.saveTasks()
  }

  // 计算统计
  getDoneCount(): number {
    return this.taskList.filter(t => t.done).length
  }

  build() {
    Column() {
      // ===== 顶部标题 =====
      Text('📝 我的待办清单')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .width('100%')
        .padding(20)
        .backgroundColor('#FF6600')
        .fontColor(Color.White)

      // ===== 输入区域 =====
      Row() {
        TextInput({ placeholder: '输入新任务，回车添加...' })
          .fontSize(16)
          .layoutWeight(1)
          .height(44)
          .backgroundColor(Color.White)
          .borderRadius(8)
          .padding({ left: 12, right: 12 })
          .onChange((value: string) => {
            this.inputText = value
          })
          .onSubmit(() => {
            // 按回车时触发
          })

        Button('添加')
          .fontSize(15)
          .height(44)
          .margin({ left: 10 })
          .backgroundColor('#FF6600')
          .borderRadius(8)
          .onClick(() => {
            this.addTask()
          })
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 12, bottom: 12 })
      .backgroundColor('#F5F5F5')

      // ===== 任务列表 =====
      if (this.taskList.length === 0) {
        // 空状态提示
        Column() {
          Text('📋')
            .fontSize(48)
            .margin({ top: 80 })
          Text('还没有任务，添加一个吧~')
            .fontSize(16)
            .fontColor('#999999')
            .margin({ top: 12 })
        }
        .width('100%')
      } else {
        List() {
          ForEach(this.taskList, (task: TaskItem, index: number) => {
            ListItem() {
              Row() {
                // 勾选框
                Row() {
                  if (task.done) {
                    Text('✅')
                      .fontSize(20)
                  } else {
                    Text('⬜')
                      .fontSize(20)
                  }
                }
                .width(44)
                .height(44)
                .justifyContent(FlexAlign.Center)
                .onClick(() => {
                  this.toggleTask(index)
                })

                // 任务标题
                Text(task.title)
                  .fontSize(16)
                  .fontColor(task.done ? '#BBBBBB' : '#333333')
                  .decoration({ type: task.done ? TextDecorationType.LineThrough : TextDecorationType.None })
                  .layoutWeight(1)
                  .margin({ left: 8 })

                // 删除按钮
                Button('🗑️')
                  .fontSize(18)
                  .backgroundColor(Color.Transparent)
                  .onClick(() => {
                    this.deleteTask(index)
                  })
              }
              .width('100%')
              .padding({ left: 16, right: 8, top: 10, bottom: 10 })
              .alignItems(VerticalAlign.Center)
            }
            .border({
              width: { bottom: 0.5 },
              color: '#F0F0F0'
            })
          })
        }
        .layoutWeight(1)
        .width('100%')
        .backgroundColor(Color.White)
      }

      // ===== 底部统计栏 =====
      Row() {
        Text(`共 ${this.taskList.length} 项`)
          .fontSize(14)
          .fontColor('#666666')

        Blank()

        Text(`已完成 ${this.getDoneCount()} 项`)
          .fontSize(14)
          .fontColor('#FF6600')
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 12, bottom: 12 })
      .backgroundColor('#FAFAFA')
      .border({
        width: { top: 1 },
        color: '#EEEEEE'
      })
    }
    .width('100%')
    .height('100%')
  }
}
```

### 3.4 代码逐段讲解

**① 数据模型 TaskItem**
```typescript
class TaskItem {
  id: number       // 每条任务有唯一 ID，方便删除时定位
  title: string    // 如「买咖啡豆」
  done: boolean    // 是否打勾
}
```

**② 加载与保存**
```typescript
loadTasks()  →  从 Preferences 读 JSON → 还原为 TaskItem[]
saveTasks()  →  把 TaskItem[] 转 JSON → 存进 Preferences → flush()
```

**③ 添加任务**
```typescript
addTask()  →  判空 → new TaskItem → unshift 到数组最前面 → 保存
```

**④ 勾选/取消**
```typescript
toggleTask(index)  →  done = !done → 保存
// 利用 @State 的特性：改了 taskList[index].done，界面自动刷新
```

**⑤ 删除**
```typescript
deleteTask(index)  →  splice 移除 → 保存
```

**⑥ 删除线效果**
```typescript
.decoration({ type: task.done ? TextDecorationType.LineThrough : TextDecorationType.None })
// 打勾的任务自动加删除线
```

---

## 四、启动页面配置

在 `EntryAbility.ets` 中改为加载 TodoPage：

```typescript
windowStage.loadContent('pages/TodoPage', (err, data) => {
  // ...
})
```

运行，你的待办清单 App 就上线了！关掉 App 再打开，任务全都还在。

---

## 五、本节要点回顾

| 学会什么 | 具体内容 |
|---------|---------|
| @State | 组件内状态，变了界面自动刷新 |
| @Prop | 父传子，单向 |
| @Link | 父传子，双向绑定 |
| Preferences | 轻量级 KV 存储，`flush()` 必须调 |
| 实战项目 | 完整待办清单（增删改查 + 持久化） |
| 新组件 | TextInput、List、ListItem、ForEach |

---

## 六、常见问题

**Q：`aboutToAppear()` 是什么？**
页面即将显示时自动调用的生命周期函数。在这里加载数据最合适。

**Q：为什么存 JSON 而不是一条条单独存？**
一条条存会增加代码复杂度。整个数组转成 JSON 字符串一次存进去最简单。

**Q：Preferences 能存多少数据？**
轻量级存储，建议几千条以内。如果数据量大，后续可以升级到关系型数据库。

**Q：刷新后输入框内容不见了？**
输入框需要绑定 `@State` 变量。检查 `.onChange()` 有没有正确更新变量。

---

## 下一篇预告

第 4 篇：《鸿蒙网络编程入门：接入 GitHub API，做一个热门项目浏览器》

你会学到：
- HTTP 网络请求的完整流程
- JSON 数据解析与 TypeScript 模型
- 页面跳转与参数传递
- 下拉刷新 + 上拉加载
- 实战：搜索 GitHub 项目 + 详情页

---

> 📦 本系列代码仓库：https://github.com/dazhuang-zs/harmonyos-series
>
> 💬 欢迎评论区讨论，每条都会看。
>
> 🔔 这是《从零到实战：鸿蒙应用开发 5 篇系列》的第 3 篇，第 4 篇明天见！
