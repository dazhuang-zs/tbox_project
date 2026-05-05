# Java编程思想：不只是设计模式，是5条让你代码脱胎换骨的思维原则

> **摘要**：学完Java语法和Spring Boot，发现自己写的代码还是"能用但不好看"？问题不在语法，在思维。本文不重复23种设计模式（网上有500篇），而是提炼5条真正改变代码质量的编程思想——组合大于继承、面向接口而非实现、不变性优先、失败-fast、显式优于隐式。每条思想都配有"大多数人写的代码"和"改一行思维后写的代码"的对比，以及真实的项目重构案例。

---

## 目录

- [开篇：三年经验的Java程序员和五年经验的到底差在哪](#开篇)
- [一、组合大于继承——你90%的extends都可以换成组合](#一组合大于继承)
- [二、面向接口而非实现——让代码经得起需求变更](#二面向接口而非实现)
- [三、不变性优先——bug最少的设计策略](#三不变性优先)
- [四、快速失败——让bug在最近的地方暴露](#四快速失败)
- [五、显式优于隐式——魔法越少维护越轻松](#五显式优于隐式)
- [六、项目重构实战：一个订单系统的改造全程](#六项目重构实战)

---

## 开篇：三年经验的Java程序员和五年经验的到底差在哪

面试过上百个Java开发后，我发现一个规律：**三年经验的和五年经验的，语法知识几乎没差别。** 大家都懂Spring Boot、都会用Stream API、都背过设计模式。

但代码一写出来，差距立现。

三年经验的代码："能跑，但改起来心惊胆战。"
五年经验的代码："一看就知道为什么要这么写，改起来心里有底。"

差距在哪？**不是设计模式背得多，是脑子里有"什么情况下该怎么做"的判断框架。**

本文不重复23种设计模式，只讲5条真正改变代码质量的编程思想。每条都带对比代码——左边是大多数人写的，右边是改了一行思维后写的。

---

## 一、组合大于继承——你90%的extends都可以换成组合

### 问题

Java教程里`class Dog extends Animal`是第一天就教的内容。但真实项目中，继承带来的问题远比解决的问题多。

**一个真实案例**：

```java
// ❌ 继承带来灾难
public class UserService extends BaseService {
    
    public User createUser(UserDTO dto) {
        validate(dto);  // BaseService的方法
        User user = convertToEntity(dto);  // BaseService的方法
        user = userRepository.save(user);  // 自己的
        sendNotification(user);  // BaseService的方法
        return user;
    }
}
```

看起来挺好？三个月后：

1. 产品说"VIP用户创建不需要发通知" → 你override了`sendNotification`，加了个`if`判断
2. 产品说"管理后台创建用户不需要校验手机号" → 你override了`validate`
3. 产品说"API注册和后台创建共用UserService" → 你发现逻辑已经纠缠在一起，拆不开了

**问题根源**：`UserService extends BaseService`把两个不同的关注点绑死了。你想要的只是"复用BaseService里的一些方法"，但继承给你的是"UserService is a BaseService"的强绑定。

### 解法：组合

```java
// ✅ 组合：各司其职
public class UserService {
    private final Validator validator;        // 注入校验逻辑
    private final UserRepository repository;  // 注入数据访问
    private final NotificationService notifier; // 注入通知逻辑
    
    public UserService(Validator validator, 
                       UserRepository repository,
                       NotificationService notifier) {
        this.validator = validator;
        this.repository = repository;
        this.notifier = notifier;
    }
    
    // 普通用户注册
    public User register(UserDTO dto) {
        validator.validate(dto);       // 校验可定制
        User user = User.from(dto);    // 转换在自己类里
        user = repository.save(user);
        notifier.sendWelcome(user);    // 通知可定制
        return user;
    }
    
    // 管理后台创建（不同的逻辑组合）
    public User adminCreate(UserDTO dto) {
        validator.validateBasic(dto);  // 只做基础校验
        User user = User.from(dto);
        user.setSource("ADMIN");       // 标记来源
        return repository.save(user);  // 不发通知
    }
}
```

**组合vs继承的判断标准**：

| 场景 | 用继承 | 用组合 |
|------|--------|--------|
| 需要复用5个以上的方法 | ⚠️ 慎重 | ✅ |
| 子类和父类是"is-a"关系（猫是动物） | ✅ | ❌ |
| 只是想复用父类的几个工具方法 | ❌ | ✅ |
| 未来可能换掉某个行为 | ❌ | ✅ |
| 多层级（>2层）继承链 | ❌ | ✅ |

---

## 二、面向接口而非实现——让代码经得起需求变更

### 问题：硬编码依赖

```java
// ❌ 紧耦合
public class OrderService {
    private AlipayPaymentService payment = new AlipayPaymentService();
    private EmailNotificationService notifier = new EmailNotificationService();
    
    public void createOrder(Order order) {
        // 处理订单...
        payment.pay(order.getAmount());
        notifier.send("订单已创建");
    }
}
```

某天老板说"我们要接入微信支付"。你傻眼了——`OrderService`的每行代码都在直接依赖支付宝。

### 解法：依赖倒置

```java
// ✅ 面向接口
public interface PaymentService {
    PaymentResult pay(BigDecimal amount);
}

public interface NotificationService {
    void send(String message);
}

public class OrderService {
    private final PaymentService payment;      // 依赖接口，不是实现
    private final NotificationService notifier;  // 依赖接口
    
    // Spring自动注入正确的实现
    public OrderService(PaymentService payment, 
                        NotificationService notifier) {
        this.payment = payment;
        this.notifier = notifier;
    }
    
    public void createOrder(Order order) {
        payment.pay(order.getAmount());
        notifier.send("订单已创建");
    }
}

// 接入微信支付 —— 只需加一个实现类，其他代码不动
@Service("wechat")
public class WechatPaymentService implements PaymentService {
    @Override
    public PaymentResult pay(BigDecimal amount) {
        // 微信支付逻辑
    }
}
```

**核心原则**：高层模块（OrderService）不应该依赖低层模块（AlipayPaymentService），两者都应该依赖抽象（PaymentService接口）。

---

## 三、不变性优先——bug最少的设计策略

### 什么是不可变对象

创建后状态就不能改变的对象。String、BigDecimal、LocalDate都是不可变的。

### 为什么不可变对象是bug最少的设计

```java
// ❌ 可变对象：隐患随时爆发
public class Order {
    private BigDecimal amount;
    private String status;
    
    // getter/setter...
}

// 某处代码
order.setAmount(new BigDecimal("99.00"));
// ... 100行之后 ...
order.setAmount(new BigDecimal("100.00")); // 谁改的？为什么改？追不到

// ✅ 不可变对象：零意外修改
public final class Order {
    private final BigDecimal amount;
    private final OrderStatus status;
    
    public Order(BigDecimal amount, OrderStatus status) {
        this.amount = amount;
        this.status = status;
    }
    
    // 没有setter！
    public BigDecimal getAmount() { return amount; }
    
    // "修改"返回新对象，旧对象不变
    public Order withStatus(OrderStatus newStatus) {
        return new Order(this.amount, newStatus);
    }
}
```

### 实战：用Builder创建复杂不可变对象

```java
@Builder  // Lombok
public final class User {
    private final String name;
    private final String email;
    private final List<String> roles;  // 防御性拷贝！
    
    public User(String name, String email, List<String> roles) {
        this.name = name;
        this.email = email;
        this.roles = List.copyOf(roles);  // 不可修改的副本
    }
    
    public List<String> getRoles() {
        return roles;  // 已经是不可变集合，安全返回
    }
}

// 使用Builder
User user = User.builder()
    .name("张三")
    .email("zhangsan@example.com")
    .roles(List.of("USER", "VIP"))
    .build();
// user创建后不可能被意外修改
```

### 什么时候不该用不可变对象？

- 对象状态需要频繁修改（如游戏角色的实时坐标）
- 对象特别大，拷贝成本高（如图像数据）
- 这些场景用可变对象，但要**尽量缩小可变范围**（如只让坐标可变，其他属性不可变）

---

## 四、快速失败——让bug在最近的地方暴露

### 什么是Fail-Fast

代码在问题发生的最早时刻就报错，而不是让错误数据在系统里流窜。

```java
// ❌ Fail-Slow：错误数据在系统里跑了5层才出错
public class UserController {
    public void register(UserDTO dto) {  // dto.getName()可能为null
        userService.register(dto);
    }
}
public class UserService {
    public void register(UserDTO dto) {
        // 没校验，直接往下传
        userRepository.save(dto.toEntity());  // 这里可能NullPointerException
    }
}

// ✅ Fail-Fast：在边界上立刻校验
public class UserDTO {
    private String name;
    
    public User toEntity() {
        Objects.requireNonNull(name, "用户名不能为null");  // 这里立刻报错！
        return new User(name);
    }
}
```

### Fail-Fast三件套

```java
// 1. 参数校验——在方法入口
public void process(Order order) {
    Objects.requireNonNull(order, "订单不能为null");
    if (order.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
        throw new IllegalArgumentException("订单金额必须大于0");
    }
    // 继续处理...
}

// 2. 状态校验——在操作前
public void pay(Order order) {
    if (order.getStatus() != OrderStatus.PENDING) {
        throw new IllegalStateException("只有待支付状态的订单才能支付，当前：" + order.getStatus());
    }
    // 执行支付...
}

// 3. 不可达代码——用default抛异常
public String getChannelName(Channel channel) {
    return switch (channel) {
        case ALIPAY -> "支付宝";
        case WECHAT -> "微信支付";
        // 没有default → 新增Channel类型忘记处理，编译器不会报错
    };
}
// ✅ 加了default：新加UNIONPAY时会编译错误，逼你处理
```

---

## 五、显式优于隐式——魔法越少维护越轻松

### Spring的隐式魔法何时变成毒药

```java
// ❌ 隐式：太多"魔法"让后来者无法理解
@Service
public class PriceCalculator {
    
    @Autowired  // 谁注入的？注入的是什么？IDE里按住Ctrl跳不过去
    private PriceStrategy strategy;
    
    @PostConstruct  // 这个方法什么时候被谁调用的？
    public void init() {
        strategy.loadFromCache();
    }
    
    @Transactional(rollbackFor = Exception.class)  // 事务边界在哪？
    public BigDecimal calculate(Order order) {
        // AOP代理下 this.xxx() 调用事务不生效，又是一个坑
        return strategy.calc(order);
    }
}
```

### 显式化改造

```java
// ✅ 显式：一目了然的依赖和执行流程
@Service
public class PriceCalculator {
    private final PriceStrategy strategy;
    private final CacheManager cacheManager;
    
    // 构造器注入 → 依赖关系一眼看穿
    public PriceCalculator(PriceStrategy strategy, CacheManager cacheManager) {
        this.strategy = strategy;
        this.cacheManager = cacheManager;
    }
    
    // 不再用@PostConstruct，显式调用
    public void init() {
        strategy.loadFromCache(cacheManager.getCache("price"));
    }
    
    // 事务逻辑提取到独立的TransactionalService
    // 不在同一个类里用this调用事务方法
    public BigDecimal calculate(Order order) {
        return transactionalExecutor.execute(() -> strategy.calc(order));
    }
}
```

**何时用隐式（注解/约定），何时用显式？**

| 场景 | 建议 |
|------|------|
| Web层：`@RestController`、`@GetMapping` | ✅ 隐式OK，约定成熟 |
| 依赖注入：`@Autowired`字段注入 | ❌ 改用构造器注入 |
| AOP事务：`@Transactional` | ⚠️ 简单场景OK，复杂逻辑提取到Service |
| 业务逻辑 | ❌ 必须显式，可读性第一 |
| 配置映射：`@ConfigurationProperties` | ✅ 隐式OK |

---

## 六、项目重构实战：一个订单系统的改造全程

### 改造前（典型的"能跑"代码）

```java
@Service
public class OrderService {
    @Autowired
    private OrderRepository orderRepository;
    @Autowired
    private AlipayService alipayService;
    @Autowired
    private InventoryService inventoryService;
    @Autowired
    private EmailService emailService;
    @Autowired
    private SmsService smsService;
    
    @Transactional
    public Order createOrder(OrderRequest req) {
        // 校验库存
        if (!inventoryService.checkStock(req.getProductId(), req.getQuantity())) {
            throw new RuntimeException("库存不足");
        }
        
        // 创建订单
        Order order = new Order();
        order.setUserId(req.getUserId());
        order.setProductId(req.getProductId());
        order.setQuantity(req.getQuantity());
        order.setAmount(req.getAmount());
        order.setStatus("CREATED");
        order = orderRepository.save(order);
        
        // 扣库存
        inventoryService.deduct(req.getProductId(), req.getQuantity());
        
        // 发起支付
        String payUrl = alipayService.createPayment(
            order.getId(), order.getAmount());
        order.setPayUrl(payUrl);
        
        // 发邮件
        emailService.send(req.getEmail(), "订单已创建", "您的订单" + order.getId() + "已创建");
        
        // 发短信
        smsService.send(req.getPhone(), "订单" + order.getId() + "已创建");
        
        return order;
    }
}
```

### 改造后（5条编程思想贯穿）

```java
// 1. 不可变领域对象
public record Order(
    OrderId id,
    UserId userId,
    ProductId productId,
    Quantity quantity,
    Money amount,
    OrderStatus status
) {
    // 工厂方法：创建新订单
    public static Order create(UserId userId, ProductId productId, 
                                Quantity quantity, Money amount) {
        return new Order(
            OrderId.generate(),
            userId, productId, quantity, amount,
            OrderStatus.CREATED
        );
    }
}

// 2. 面向接口
public interface PaymentGateway {
    PaymentResult initiatePayment(OrderId orderId, Money amount);
}
public interface NotificationChannel {
    void send(UserId userId, String subject, String body);
}

// 3. 组合 + 显式依赖
@Service
public class OrderService {
    private final OrderRepository repository;
    private final InventoryService inventory;
    private final PaymentGateway payment;        // 接口
    private final List<NotificationChannel> channels;  // 多通道组合
    
    // 构造器注入：依赖关系一眼看穿
    public OrderService(OrderRepository repository,
                        InventoryService inventory,
                        PaymentGateway payment,
                        List<NotificationChannel> channels) {
        this.repository = repository;
        this.inventory = inventory;
        this.payment = payment;
        this.channels = channels;
    }
    
    // 4. Fail-Fast + 清晰职责分离
    public Order createOrder(CreateOrderCommand cmd) {
        // 在入口处Fail-Fast校验
        Objects.requireNonNull(cmd, "命令不能为null");
        
        // 库存校验（独立的领域逻辑）
        inventory.ensureStock(cmd.productId(), cmd.quantity());
        
        // 创建不可变订单
        Order order = Order.create(
            cmd.userId(), cmd.productId(), 
            cmd.quantity(), cmd.amount()
        );
        order = repository.save(order);
        
        // 扣库存（独立的写操作）
        inventory.deduct(cmd.productId(), cmd.quantity());
        
        // 发起支付（通过接口，可替换实现）
        PaymentResult payResult = payment.initiatePayment(
            order.id(), order.amount());
        
        // 5. 通知通过组合的多通道（可增删通道而不改业务逻辑）
        String message = "订单" + order.id() + "已创建";
        channels.forEach(ch -> ch.send(cmd.userId(), "订单通知", message));
        
        return order;
    }
}
```

**改造后带来的实际变化**：

- 接入新支付方式 → 新增一个`PaymentGateway`实现类，其他代码不动
- 增加钉钉通知 → 新增`DingTalkNotification`实现，加到`List`里
- 订单字段变更 → 改`Order` record定义就行，构造器帮你找到所有使用点
- 单元测试 → 每个依赖都是接口，mock一行代码的事

---

> 💡 **五条思想一句话总结**：
> 1. **组合大于继承**：能组合就别继承，继承留着给真正的is-a关系
> 2. **面向接口**：依赖抽象不依赖具体，让代码经得起改
> 3. **不变性优先**：能不可变就不可变，找bug的时间减少一半
> 4. **快速失败**：错误在最近的地方暴露，别让它跑远
> 5. **显式优于隐式**：三个月后回来还能看懂自己在写什么

**你觉得哪条最难落地？或者你们项目里有哪个设计让你最头疼？评论区聊聊。**
