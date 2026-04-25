# iOS 开发进阶之路：从能跑到能维护

> 写一个能跑的 App 只需要三天，写一个三年后还能改的 App，需要的不止是代码。

## 一、选对语言，事半功倍

iOS 开发现在两条主线：

| 语言 | 框架 | 适用场景 | 特点 |
|------|------|----------|------|
| Swift | SwiftUI | 新项目、iOS 16+ | 声明式、跨平台（iOS/macOS/watchOS）、代码量少 |
| Swift | UIKit | 需要精细控制、兼容旧版本 | 命令式、成熟稳定、生态丰富 |
| Objective-C | UIKit | 老项目维护、底层桥接 | 逐步退出历史舞台 |

**建议**：2025 年以后的新项目，直接 Swift + SwiftUI 起步。UIKit 不需要全会，但要能读能改——太多存量项目了。

## 二、架构不是玄学，是经验压缩

### 从 MVC → MVVM → TCA，经历了什么？

**MVC (Massive View Controller)**

```
┌─────────────────────────────────┐
│         ViewController          │
│  ┌──────────┐  ┌─────────────┐  │
│  │   View   │  │  Networking  │  │
│  ├──────────┤  ├─────────────┤  │
│  │  Model   │  │   Storage    │  │
│  ├──────────┤  ├─────────────┤  │
│  │ Delegate │  │   Routing    │  │
│  └──────────┘  └─────────────┘  │
│        一个 VC 干了所有事          │
└─────────────────────────────────┘
```

一个 ViewController 动辄 2000 行，改个颜色要翻半小时——这就是 MVC 的日常。

**MVVM — 把逻辑抽出来**

```swift
// ViewModel 不 import UIKit，纯逻辑层
class ProfileViewModel: ObservableObject {
    @Published var user: User?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let userService: UserServiceProtocol

    func loadProfile() async {
        isLoading = true
        defer { isLoading = false }
        do {
            user = try await userService.fetchProfile()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
```

关键约束：

- ViewModel **不引用** UIKit，可纯 Swift 测试
- View 只做展示和交互转发，不做业务判断
- 依赖注入走 Protocol，不直接 `URLSession.shared`

**TCA (The Composable Architecture)** 适合复杂状态管理，但学习曲线陡峭。中小团队 MVVM 完全够用，别为了用而用。

### 我推荐的轻量架构方案

```
View (SwiftUI)          ←  只管画
    ↓ @StateObject / @ObservedObject
ViewModel               ←  业务逻辑，纯 Swift
    ↓ Protocol
Service Layer           ←  网络、数据库、缓存
    ↓
Data Layer              ←  Core Data / SwiftData / Realm
```

三层够用，别搞成六层地狱。

## 三、你一定会踩的五个坑

### 1. 内存泄漏 — 闭包循环引用

```swift
// ❌ 经典错误 —— 闭包强引用了 self
viewModel.onDataLoaded = { data in
    self?.tableView.reloadData()
}

// ✅ 正确姿势
viewModel.onDataLoaded = { [weak self] data in
    guard let self = self else { return }
    self.tableView.reloadData()
}
```

**工具**：Xcode → Debug Memory Graph，定期检查，养成习惯。

### 2. 线程 — UI 更新必须在主线程

```swift
// ❌ 后台线程更新 UI → 随机崩溃
Task {
    let data = await fetchData()
    label.text = data.title  // 💥 必崩
}

// ✅ 方案一：MainActor.run
Task {
    let data = await fetchData()
    await MainActor.run { label.text = data.title }
}

// ✅ 方案二：标记整个方法
@MainActor
func updateUI(with data: MyData) {
    label.text = data.title
}
```

### 3. App 生命周期 — SceneDelegate 的变化

iOS 13 之后引入了 SceneDelegate 支持多窗口，很多老教程还是 AppDelegate 单窗口模式。

```swift
// SwiftUI 直接用 @main App 结构体
@main
struct MyApp: App {
    @Environment(\.scenePhase) var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .onChange(of: scenePhase) { newPhase in
                    switch newPhase {
                    case .active:      print("回前台了")
                    case .inactive:    break
                    case .background:  print("存数据，快！")
                    }
                }
        }
    }
}
```

### 4. 包管理 — 别乱加依赖

SPM（Swift Package Manager）很好用，但：

- **能自己写的别加库**：200 行工具类不值得一个外部依赖
- **Star 多 ≠ 维护好**：看 commit 频率和 issue 响应速度
- **锁版本**：`Package.resolved` 必须提交到 Git
- **依赖审计**：定期检查还有哪些库在更新、哪些已经死了

### 5. App Store 审核 — 血的教训

- 隐私清单（Privacy Manifest）必须完整，第三方 SDK 的也要加
- 权限描述别写"需要使用相册"，写成"用于上传头像和分享图片"
- 内购统一走 StoreKit 2，别自己搞支付
- Guideline 4.3（马甲包）现在查得非常严，别心存侥幸

## 四、写测试，不是可选项

```swift
// 测试 ViewModel，不需要启动 App
func testLoadProfile_Success() async {
    let mockService = MockUserService()
    mockService.mockUser = User(name: "测试用户")

    let vm = ProfileViewModel(userService: mockService)
    await vm.loadProfile()

    XCTAssertEqual(vm.user?.name, "测试用户")
    XCTAssertFalse(vm.isLoading)
    XCTAssertNil(vm.errorMessage)
}
```

核心原则：

- **ViewModel 层必须可测试**（走协议注入，Mock 驱动）
- **UI 层可以不测**（变化太快，投入产出比低）
- **关键业务逻辑必须有测试**（支付流程、数据转换、权限校验）

## 五、持续学习路线图

```
阶段一（0-3月）     Swift 基础 → SwiftUI 入门 → 简单 Todo App
阶段二（3-6月）     UIKit 补齐 → 网络层 → 数据库 → 完整上线项目
阶段三（6-12月）    架构设计 → 单元测试 → CI/CD → App Store 上架
阶段四（1年+）      性能优化 → 底层原理 → 开源贡献 → 技术选型决策
```

每个阶段的关键产出物要能跑、能展示、能写到简历里。

## 六、好用的工具和资源

### 调试工具

| 工具 | 用途 |
|------|------|
| Charles / Proxyman | HTTP/HTTPS 抓包，排查接口问题 |
| Reveal | 3D 视图层级调试，找出布局问题 |
| Instruments | 性能分析（内存、CPU、能耗） |

### 代码质量

| 工具 | 用途 |
|------|------|
| SwiftLint | 代码风格统一，自动检查规范 |
| Periphery | 找出未使用的代码，清理死代码 |
| SwiftFormat | 自动格式化代码 |

### CI/CD

| 工具 | 特点 |
|------|------|
| Xcode Cloud | Apple 官方，无缝集成 |
| Fastlane | 最灵活的自动化工具 |
| GitHub Actions | 免费额度够用，社区 Action 丰富 |

### 学习资源

- [Hacking with Swift](https://www.hackingwithswift.com) — 最好的免费教程，没有之一
- [Swift By Sundell](https://www.swiftbysundell.com) — 深度文章和工作坊
- [Kavsoft](https://kavsoft.dev) — SwiftUI 动效和复杂交互示例
- iOS Dev Weekly — 每周精选，保持信息不落后
- SwiftLee — 实战技巧，每周更新

## 七、一个真实项目的目录结构参考

```
MyApp/
├── App/
│   └── MyApp.swift                    # @main 入口
├── Features/
│   ├── Home/
│   │   ├── HomeView.swift
│   │   └── HomeViewModel.swift
│   ├── Profile/
│   │   ├── ProfileView.swift
│   │   └── ProfileViewModel.swift
│   └── Settings/
│       ├── SettingsView.swift
│       └── SettingsViewModel.swift
├── Core/
│   ├── Network/
│   │   ├── APIClient.swift
│   │   └── Endpoint.swift
│   ├── Storage/
│   │   └── UserDefaultsManager.swift
│   └── Extensions/
│       └── View+Extensions.swift
├── Models/
│   ├── User.swift
│   └── Post.swift
├── Resources/
│   ├── Assets.xcassets
│   └── Localizable.strings
└── Tests/
    ├── HomeViewModelTests.swift
    └── APIClientTests.swift
```

按 Feature 而不是按类型分——这样加新功能时不用在十几个文件夹之间跳。

## 写在最后

iOS 开发生态跟五年前完全不同了。Swift 从青涩走向成熟，SwiftUI 从玩具变成生产力，Vision Pro 和 Apple Watch 让跨 Apple 平台开发成了真实的日常需求。

但不管技术怎么变，有几件事永远不会过时：

1. **写能改的代码，而不是能跑的代码。**
2. **理解 Apple 的设计哲学，比背 API 重要一百倍。**
3. **保持小步迭代，别追求一次完美。**

---

*本文适合有半年以上 iOS 开发经验、希望系统提升工程能力的开发者阅读。如果你是纯新手，建议先从 Hacking with Swift 的 100 Days of SwiftUI 开始。*
