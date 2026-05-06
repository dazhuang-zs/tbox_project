# ArkTS 速通 + ArkUI 组件实战：30 分钟做出个人名片页面

> 读完这篇文章，你能：掌握 ArkTS 核心语法（够写 App 的），用五大基础组件做出漂亮的个人名片页面。

---

**前置条件**：读完第 1 篇，DevEco Studio 已装好，模拟器已启动。

---

## 一、ArkTS 语法速通：只学你需要用的

不要从头啃语言教程。写 App 常用的就这些，30 分钟拿下。

### 1.1 变量声明：`let` 和 `const`

```typescript
let name: string = '大壮'       // 普通变量，可以改
const MAX_COUNT: number = 100   // 常量，不能改
let isVip: boolean = true       // 布尔值
```

**规则：** 不知道会不会改就用 `let`，确定不会改用 `const`。

### 1.2 数据类型

```typescript
let age: number = 25                    // 数字
let title: string = '个人名片'           // 字符串（单引号双引号都行）
let tags: string[] = ['ArkTS', 'AI']    // 字符串数组
let info: object = { name: '大壮' }     // 对象
```

### 1.3 函数

```typescript
// 普通函数
function greet(name: string): string {
  return `你好，${name}！`
}

// 箭头函数（更常用）
const add = (a: number, b: number): number => {
  return a + b
}
```

### 1.4 条件判断

```typescript
let score: number = 85

if (score >= 90) {
  // 优秀
} else if (score >= 60) {
  // 及格
} else {
  // 不及格
}
```

### 1.5 循环

```typescript
// for 循环
for (let i = 0; i < 5; i++) {
  // 做 5 次
}

// 遍历数组（最常用方式）
let skills: string[] = ['ArkTS', 'ArkUI', '鸿蒙']
skills.forEach((skill: string) => {
  // 对每个 skill 做点什么
})
```

**够用了。** 上面这些就覆盖了 90% 的业务代码。遇到不会的再查。

---

## 二、ArkUI 五大组件：画界面的积木

### 2.1 Text — 显示文字

```typescript
Text('大壮')
  .fontSize(24)                    // 字号
  .fontColor('#333333')            // 颜色
  .fontWeight(FontWeight.Bold)     // 加粗
```

### 2.2 Image — 显示图片

```typescript
// 本地图片（放在 resources/rawfile 下）
Image($rawfile('avatar.png'))
  .width(80)
  .height(80)
  .borderRadius(40)                // 圆角 → 圆形头像

// 网络图片
Image('https://example.com/photo.jpg')
  .width(200)
  .height(200)
```

### 2.3 Button — 按钮

```typescript
Button('联系我')
  .fontSize(18)
  .backgroundColor('#FF6600')
  .borderRadius(8)
  .onClick(() => {
    // 点按钮后执行的代码
  })
```

### 2.4 Column — 纵向排列

```typescript
Column() {
  Text('第一行')
  Text('第二行')
  Text('第三行')
}
.width('100%')
```

Column 里的元素从上到下排列。

### 2.5 Row — 横向排列

```typescript
Row() {
  Text('左边')
  Text('右边')
}
.width('100%')
```

Row 里的元素从左到右排列。

### 布局诀窍

**Column + Row 套娃**是 ArkUI 布局的标配：

```
Column（整页从上到下）
├── Row（头像行：左头像 + 右名字）
├── Text（简介）
└── Row（技能标签行：标签1 + 标签2 + 标签3）
```

---

## 三、实战：做一个个人名片页面

### 3.1 最终效果预览

```
┌──────────────────────┐
│                      │
│      [ 头像 ]        │
│                      │
│      大壮            │
│      全栈开发者       │
│                      │
│   📧 dazhuang@xx.com │
│   📍 上海            │
│                      │
│  ArkTS  ArkUI  鸿蒙  │
│    AI  Python  TS    │
│                      │
│     [ 联系我 ]       │
│                      │
└──────────────────────┘
```

### 3.2 完整代码

新建一个页面文件 `pages/CardPage.ets`：

```typescript
@Entry
@Component
struct CardPage {
  @State name: string = '大壮'
  @State title: string = '全栈开发者'
  @State email: string = 'dazhuang@example.com'
  @State location: string = '上海'
  @State skills: string[] = ['ArkTS', 'ArkUI', '鸿蒙', 'AI', 'Python', 'TypeScript']

  build() {
    Column() {
      // ===== 头像区域 =====
      Image($rawfile('avatar.png'))
        .width(100)
        .height(100)
        .borderRadius(50)
        .border({ width: 3, color: '#FF6600' })
        .margin({ top: 60 })

      // ===== 姓名 =====
      Text(this.name)
        .fontSize(28)
        .fontWeight(FontWeight.Bold)
        .fontColor('#1A1A1A')
        .margin({ top: 16 })

      // ===== 职位 =====
      Text(this.title)
        .fontSize(16)
        .fontColor('#666666')
        .margin({ top: 6 })

      // ===== 分隔线 =====
      Divider()
        .width('80%')
        .margin({ top: 20, bottom: 20 })

      // ===== 联系方式 =====
      Column() {
        Row() {
          Text('📧')
            .fontSize(16)
          Text(this.email)
            .fontSize(14)
            .fontColor('#555555')
            .margin({ left: 8 })
        }
        .margin({ bottom: 8 })

        Row() {
          Text('📍')
            .fontSize(16)
          Text(this.location)
            .fontSize(14)
            .fontColor('#555555')
            .margin({ left: 8 })
        }
      }
      .alignItems(HorizontalAlign.Start)
      .width('80%')

      // ===== 分隔线 =====
      Divider()
        .width('80%')
        .margin({ top: 20, bottom: 20 })

      // ===== 技能标签 =====
      Text('技能标签')
        .fontSize(14)
        .fontColor('#999999')
        .margin({ bottom: 12 })

      Row() {
        ForEach(this.skills, (skill: string) => {
          Text(skill)
            .fontSize(13)
            .fontColor('#FF6600')
            .backgroundColor('#FFF3E0')
            .borderRadius(12)
            .padding({ left: 12, right: 12, top: 5, bottom: 5 })
            .margin({ left: 4, right: 4 })
        })
      }
      .width('90%')
      .justifyContent(FlexAlign.Center)

      // ===== 联系按钮 =====
      Button('📩 联系我')
        .fontSize(18)
        .fontColor(Color.White)
        .backgroundColor('#FF6600')
        .borderRadius(24)
        .width('70%')
        .height(48)
        .margin({ top: 40 })
        .onClick(() => {
          // 后续可以接真正的联系功能
          console.log('按钮被点击了！')
        })

      // 底部留白
      Blank()
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#FAFAFA')
  }
}
```

### 3.3 让名片页面显示出来

在第 1 篇的 `EntryAbility.ets` 里，把首页改成 CardPage：

```typescript
// EntryAbility.ets
onWindowStageCreate(windowStage: window.WindowStage): void {
  windowStage.loadContent('pages/CardPage', (err, data) => {
    // ...
  })
}
```

或者直接在 `pages/Index.ets` 里替换上面的代码。

保存，模拟器实时刷新，一张完整的个人名片立刻显示。

### 3.4 代码拆解

| 代码段 | 作用 |
|--------|------|
| `@State name: string` | 声明一个响应式变量，值变了界面自动更新 |
| `Column() { ... }` | 页面最外层，让内容从上到下排列 |
| `Image($rawfile('avatar.png'))` | 加载本地图片，`.borderRadius(50)` 切成圆形 |
| `ForEach(this.skills, ...)` | 遍历技能数组，每个技能变成一个标签 |
| `Divider()` | 分隔线，让排版更清爽 |
| `Button(...).onClick(...)` | 按钮 + 点击事件 |
| `Blank()` | 占位空间，把内容往上推 |

---

## 四、进阶小贴士

### 4.1 颜色可以用 Hex 也可以用系统色

```typescript
.fontColor('#FF6600')       // Hex 写死
.fontColor(Color.Orange)     // 系统色
.backgroundColor(Color.White)
```

### 4.2 样式可以提取复用

如果你有多个按钮用一样样式：

```typescript
@Styles function orangeButton() {
  .fontColor(Color.White)
  .backgroundColor('#FF6600')
  .borderRadius(8)
}

// 使用时
Button('按钮A')
  .orangeButton()             // 直接复用

Button('按钮B')
  .orangeButton()
```

### 4.3 做个图片占位

如果没有头像图片，先用文字头像：

```typescript
Text(this.name.charAt(0))       // 取名字第一个字
  .fontSize(36)
  .fontColor(Color.White)
  .width(100)
  .height(100)
  .borderRadius(50)
  .backgroundColor('#FF6600')
  .textAlign(TextAlign.Center)
```

---

## 五、本节要点回顾

| 学会了什么 | 具体内容 |
|-----------|---------|
| ArkTS 核心语法 | 变量、类型、函数、条件、循环 |
| ArkUI 五大组件 | Text、Image、Button、Column、Row |
| 布局铁律 | Column + Row 套娃 |
| 实战项目 | 个人名片页面（头像+信息+标签+按钮） |
| 新特性 | @State 响应式变量、ForEach 列表渲染、本地图片加载 |

---

## 六、常见问题

**Q：`ForEach` 和普通 `for` 循环有什么区别？**
`ForEach` 是 ArkUI 专用的列表渲染语法，必须用它才能在界面上生成多个组件。普通 `for` 循环不行。

**Q：图片放哪里？**
放 `entry/src/main/resources/rawfile/` 文件夹，引用时用 `$rawfile('文件名.png')`。

**Q：为什么我的页面布局塌了？**
检查外层 Column 有没有设 `.width('100%').height('100%')`。没设高度的话页面撑不满。

---

## 下一篇预告

第 3 篇：《鸿蒙数据持久化实战：用 Preferences + 状态管理做一个待办清单》

你会学到：
- @State、@Prop、@Link 三种状态管理的区别
- 用 Preferences 把数据存到本地（关掉 App 再打开还在）
- 写一个完整的待办清单（增、删、改、查）
- 交互升级：输入框、弹窗、Toast 提示

---

> 📦 本系列代码仓库：https://github.com/dazhuang-zs/harmonyos-series
>
> 💬 有任何问题欢迎评论区交流，我会逐一回复。
>
> 🔔 这是《从零到实战：鸿蒙应用开发 5 篇系列》的第 2 篇，关注我接收后续更新！
