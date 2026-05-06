# 鸿蒙零基础入门：从安装 DevEco Studio 到第一个 Hello World

> 读完这篇文章，你能：在电脑上装好鸿蒙开发环境，跑通第一个鸿蒙 App，理解项目结构长什么样。

---

## 一、先搞清楚：鸿蒙、ArkTS、ArkUI 是什么关系？

很多零基础同学一上来就懵了——怎么又是"鸿蒙"又是"ArkTS"又是"ArkUI"？

用最简单的话说：

| 名词 | 大白话解释 |
|------|-----------|
| **HarmonyOS（鸿蒙）** | 华为开发的操作系统，装在手机/平板/手表/电视上。对标 Android、iOS。 |
| **DevEco Studio** | 写鸿蒙 App 的官方工具（IDE），对标 Android Studio、VS Code。 |
| **ArkTS** | 编程语言，写鸿蒙 App 用。基于 TypeScript 扩展，如果你学过 JavaScript 会觉得很亲切。 |
| **ArkUI** | UI 框架，用来画界面。你看到的按钮、文字、图片，都是通过 ArkUI 组件写出来的。 |

**一句话总结：用 DevEco Studio 这个工具，拿 ArkTS 这个语言，配合 ArkUI 这个框架，来写鸿蒙 App。**

截至 2026 年 5 月，最新稳定版是 **HarmonyOS 6.0（API 23）**，本文基于此版本。

---

## 二、安装 DevEco Studio（Windows/Mac 通用）

### 2.1 下载

1. 打开华为开发者官网：**https://developer.huawei.com/consumer/cn/download/**
2. 找到 **DevEco Studio**，点击下载最新版（本文基于 6.0 版本）
3. 需要注册华为开发者账号（用手机号注册就行，免费）

### 2.2 安装（Windows）

1. 双击下载的 `.exe` 文件
2. 一路点「下一步」，安装路径建议默认（C 盘空间要够，至少 10GB）
3. 勾选「创建桌面快捷方式」

### 2.3 安装（Mac）

1. 双击下载的 `.dmg` 文件
2. 把 DevEco Studio 拖进 Applications 文件夹
3. 首次打开如果提示「无法验证开发者」，去「系统设置 → 隐私与安全性」点「仍要打开」

### 2.4 首次启动配置

启动后会自动进入 Setup Wizard：

1. **选择 SDK**：默认勾选 API 23（HarmonyOS 6.0），直接 Next
2. **接受协议**：全部勾选，同意
3. **等待下载**：SDK 大约 2-3GB，取决于网速，等 10-30 分钟

> ⚠️ **常见坑 1**：SDK 下载卡住了怎么办？
> 关闭 DevEco Studio，手动去官网下载 SDK 离线包，解压到安装目录下的 `sdk` 文件夹。

> ⚠️ **常见坑 2**：安装路径有中文会出各种奇怪问题，一定用英文路径！

---

## 三、创建你的第一个鸿蒙项目

### 3.1 新建项目

1. 打开 DevEco Studio，点击 **Create Project**
2. 选择模板：**Empty Ability**（最干净的空模板）
3. 填写项目信息：

```
Project name: HelloHarmony
Bundle name:  com.example.helloharmony
Save location: 随意，放桌面就行
SDK: API 23 (HarmonyOS 6.0)
```

4. 点击 **Finish**，等项目加载完成（首次会慢一点，它在下载依赖）

### 3.2 项目结构解析

项目加载完后，左边会出来一坨文件和文件夹。新手最需要认识的只有这几个：

```
HelloHarmony/
├── AppScope/              # App 全局配置（icon、名称等）
│   └── app.json5
├── entry/                 # 主模块，你写的代码基本都在这里
│   └── src/
│       └── main/
│           ├── ets/       # 🔥 你所有的 ArkTS 代码都在这里写
│           │   ├── entryability/
│           │   │   └── EntryAbility.ets  # App 入口
│           │   └── pages/
│           │       └── Index.ets          # 🔥 首页，我们改这个文件
│           └── resources/                 # 图片、字符串等资源
└── oh-package.json5       # 依赖配置（类似 npm 的 package.json）
```

**新手只需要关注两个文件：**
- `Index.ets` — 你写页面的地方
- `EntryAbility.ets` — App 的入口（目前不需要改）

### 3.3 看看默认代码

打开 `Index.ets`，你会看到类似这样的代码：

```typescript
@Entry
@Component
struct Index {
  @State message: string = 'Hello World';

  build() {
    Row() {
      Column() {
        Text(this.message)
          .fontSize(50)
          .fontWeight(FontWeight.Bold)
      }
      .width('100%')
    }
    .height('100%')
  }
}
```

**别怕，逐行解释：**

| 代码 | 含义 |
|------|------|
| `@Entry` | 标记这是个页面入口 |
| `@Component` | 标记这是个自定义组件 |
| `struct Index` | 组件名叫 Index |
| `@State message` | 一个变量，跟 UI 绑定（值变了界面自动更新） |
| `build()` | 描述这个页面长什么样 |
| `Row() / Column()` | 横向/纵向布局容器 |
| `Text(this.message)` | 显示文字 |
| `.fontSize(50)` | 文字大小 50 |

---

## 四、运行你的第一个 App

### 4.1 方式一：用模拟器（推荐新手）

1. 在 DevEco Studio 右上角找到设备选择下拉框
2. 点击 **Device Manager**
3. 点击 **Create Device**，选 **Phone**，选一个分辨率（比如默认的），Next
4. 下载系统镜像（会下载一个 .zip，解压后约 5GB）
5. 启动模拟器，看到手机屏幕亮起来了

然后回到 DevEco Studio，点顶部绿色 ▶️ 按钮（或按 Shift+F10），等几秒，模拟器上就会显示你的 App：

```
┌──────────────────┐
│                  │
│   Hello World    │  ← 你的第一个鸿蒙 App！
│                  │
└──────────────────┘
```

### 4.2 方式二：用真机（如果手头有华为手机）

1. 手机打开「设置 → 关于手机」，连续点 7 次「版本号」开启开发者模式
2. 回到设置，找到「系统和更新 → 开发人员选项」
3. 打开「USB 调试」
4. 用数据线连接电脑
5. DevEco Studio 会自动识别，选它，点运行

> ⚠️ **常见坑 3**：真机连不上？检查数据线是不是只能充电不能传数据。换一根 USB 数据线。

> ⚠️ **常见坑 4**：模拟器启动报 "HAXM not installed"？在 BIOS 里开启 Intel VT-x（Intel 虚拟化技术），或者改用 ARM 镜像。

---

## 五、动手改造：让文字变化

理论讲再多不如动手改一改。把 `Index.ets` 改成这样：

```typescript
@Entry
@Component
struct Index {
  @State message: string = '你好，鸿蒙！';
  @State count: number = 0;

  build() {
    Column() {
      // 标题
      Text(this.message)
        .fontSize(36)
        .fontWeight(FontWeight.Bold)
        .fontColor('#FF6600')
        .margin({ top: 100 })

      // 计数器显示
      Text(`你点了 ${this.count} 次`)
        .fontSize(24)
        .margin({ top: 30 })

      // 按钮
      Button('点我 +1')
        .fontSize(20)
        .margin({ top: 30 })
        .onClick(() => {
          this.count++  // 点一次 count 加 1
        })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}
```

保存后，模拟器上立刻刷新（热更新，不用重新编译），你会看到：
- 橙色的"你好，鸿蒙！"
- 一个计数器，点按钮数字变大
- 浅灰色背景

**恭喜！你已经完成了一个有交互的鸿蒙 App。** 🎉

---

## 六、本节要点回顾

| 学会了什么 | 具体内容 |
|-----------|---------|
| 鸿蒙开发三件套 | HarmonyOS（系统）+ ArkTS（语言）+ ArkUI（界面） |
| 安装 DevEco Studio | 下载 → 安装 → 配置 SDK → 启动模拟器 |
| 创建第一个项目 | Empty Ability → 理解 Index.ets 和 EntryAbility.ets |
| ArkTS 基础语法雏形 | @Entry、@Component、@State、build() |
| 运行 App | 模拟器 / 真机 / 热更新 |
| 动手改动 | 加了按钮 + 计数器交互 |

---

## 七、常见问题汇总

**Q：电脑配置有什么要求？**
- Windows：8GB 以上内存，i5 以上 CPU，Win10/11
- Mac：8GB 以上内存，M1/M2/M3 芯片或 Intel i5 以上，macOS 12+

**Q：没有华为手机能开发吗？**
能。用模拟器完全够，前 4 篇教程都在模拟器上跑。

**Q：DevEco Studio 占用太多硬盘空间了？**
首次安装全套 SDK + 模拟器大约占用 12-15GB。如果硬盘吃紧，只装手机 SDK，别装 TV、手表 SDK。

**Q：我之前学过 JavaScript/TypeScript，有帮助吗？**
非常有！ArkTS 本质上是 TypeScript 的扩展，语法 90% 相通。

---

## 下一篇预告

第 2 篇：《ArkTS 速通 + ArkUI 组件实战：30 分钟做出个人名片页面》

我们会学到：
- ArkTS 最常用的 10 个语法
- Text、Image、Button、Column、Row 五大组件
- 布局排版的诀窍
- 实战：做一张漂亮的个人名片页面

---

> 📦 完整代码已上传到 GitHub：https://github.com/dazhuang-zs/harmonyos-series
> 
> 💬 有问题欢迎评论区留言，我会逐条回复。
> 
> 🔔 这个系列共 5 篇，关注我不错过后续更新！
