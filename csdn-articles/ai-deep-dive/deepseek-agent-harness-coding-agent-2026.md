# DeepSeek正在做一件大事：做一个能写代码的AI Agent，对标Claude Code

2026年5月21日，DeepSeek在官方招聘页面上线了两个新岗位：

- Agent Harness 产品经理
- Agent Harness 研发工程师

岗位描述里有一句话，让所有做Coding Agent的人都愣了一秒：

> "深度使用过 Claude Code、Cursor、GitHub Copilot、OpenClaw、Hermes 等类似产品。"

把OpenClaw和Claude Code并列，放进招聘要求里——这是国内第一次有一家顶级AI公司，把"熟练使用AI编程工具"当成正经的岗位门槛。

这不是普通的"AI研究员"招聘。这是在做产品。

---

## 一、什么是Agent Harness？为什么DeepSeek要做这件事？

Harness在软件工程里指的是"测试/运行框架"，把模型能力"套上去"让它真正干活的工程体系。在DeepSeek的语境里，Harness团队专门负责把模型能力转化为用户可用的产品。

做一个大模型很难。把大模型变成一个好用的产品，更难。

Claude Code为什么好用？不是因为它用了什么特别强的模型，而是因为它的整个工程体系——上下文管理、工具调用、安全防护、用户交互——把这套体验打磨得很细。用户感觉到的"好用"，10%靠模型，90%靠Harness。

DeepSeek现在要做的，就是建这一套Harness体系。目标很明确：**对标Claude Code，做DeepSeek版本的桌面端编程Agent**（这一判断来自DeepSeek研究员陈德里在社交媒体的公开招聘帖，原文为"对标Claude Code，做DeepSeek Code Harness"）。

**类比**：模型能力是发动机，Harness是底盘、悬挂、方向盘。没有好的底盘，发动机再强也只能在原地轰鸣。

---

## 二、Coding Agent市场现在是什么格局？

2025年到2026年，AI编程工具市场经历了一次大洗牌。

**第一波：AI补全工具（2019-2023）**
代表：GitHub Copilot、Tabnine
你写一行，它补全下一行。简单、有用，但本质是辅助工具，不能独立完成任务。

**第二波：AI编程助手（2024-2025）**
代表：Cursor、Windsurf
能理解整个项目上下文，可以做多步操作，但仍然需要人工介入每一个关键节点。

**第三波：AI编程Agent（2025-现在）**
代表：Claude Code、OpenClaw
你给一个目标，它自己规划、拆解、执行、修复。你只需要说"把这个功能做出来"，剩下的它来。

2026年，这个市场正在从"工具"变成"平台"。

Cursor的估值快速攀升，Claude Code拿到了大量企业级客户，OpenClaw这类开源产品也在快速迭代。DeepSeek此时入场，目标不是分一杯羹——是要做头部。

---

## 三、DeepSeek做Coding Agent有什么独特优势？

你可能会问：已经有Claude Code、Cursor这些成熟产品了，DeepSeek为什么还要自己做？

答案就在DeepSeek的核心能力里：**模型性价比**。

DeepSeek-V3和R1的推理成本公开数据显示，比Claudeonnet低了一个数量级。这意味着：

- 同样的成本，DeepSeek可以让AI Agent执行更多的步骤
- 同样的预算，企业可以用DeepSeek服务更多的开发者

**说明**：具体成本对比数据因任务复杂度差异较大，本文不引用未核实的估算数字。如需准确数据请参考各厂商官方定价页。

本地部署能力可能成为重要差异化点（基于DeepSeek开源模型蒸馏能力的合理推测，非已发布产品）。这意味着企业用户对数据安全有顾虑的场景，DeepSeek可能有独特优势。

---

## 四、Agent Harness团队在做什么？JD深度解读

DeepSeek官网放出的JD原文值得仔细读。

**产品经理JD核心要求**：
1. 深度使用过Claude Code、Cursor、GitHub Copilot、OpenClaw等工具——不是"听说过"，是"真正用得很熟"
2. 对开发者体验（Developer Experience）有强烈感知
3. 能把"前沿模型能力"转化为"用户可用的产品形态"
4. 参与DeepSeek桌面端Agent产品的全过程

**研发工程师JD核心要求**：
1. 熟悉Agent框架（LangChain、LangGraph、AutoGen等）
2. 理解工具调用（Tool Use）、MCP协议
3. 有工程化能力：可靠性、可扩展性、安全性
4. 对标Claude Code的工程标准

**隐藏的软技能要求**：
- 你自己就是一个重度AI编程工具用户
- 你知道现有的产品哪里不好用、为什么不好用
- 你有能力把"痛点"翻译成"产品需求"

---

## 五、这个岗位适合什么样的人？

**适合**：
- 每天都在用Claude Code、Cursor写代码的开发者——你已经具备了面试的入场券
- 对Agent架构有实践经验的工程师（LangChain、工具调用、多步推理）
- 产品经理：用过大量AI编程工具，理解开发者需求
- 有强烈好奇心、愿意从零搭建一个新产品的创业者心态

**不适合**：
- 只做后端CRUD、没有用过AI编程工具的
- 对AI不感兴趣、觉得"传统开发够用"的
- 只想做纯算法研究、不愿意做工程落地产品的

**一句话总结**：这个岗位要的不是"写过很多AI论文的人"，而是"每天用AI工具写代码、而且用得很好"的人。

---

## 六、AI编程 Agent的下一站在哪？

DeepSeek入局，不只是多了一个竞争者。它改变了整个市场的竞争逻辑。

**竞争逻辑变化一：价格战来了**

当DeepSeek把推理成本压到十分之一，其他厂商要么降价，要么失去用户。AI编程工具会变得更便宜、更普及。

**竞争逻辑变化二：本地化是下一个战场**

Claude Code是云端服务。企业用户对数据安全有顾虑，不想把代码传到外部服务器。DeepSeek的本地部署能力（基于开源蒸馏模型的合理推测），可能会成为重要差异化点。

**竞争逻辑变化三：Harness能力会成为核心竞争力**

模型本身会越来越同质化（GPT-5出来，所有人都有了）。但Harness体系——上下文管理、安全防护、用户体验——才是真正的护城河。

DeepSeek显然意识到了这一点。它的招聘JD里写的是"Harness产品经理"和"Harness研发工程师"，不是"AI研究员"。

---

## 七、如果我想申请这个岗位，需要准备什么？

**硬技能清单**：
1. 用Claude Code或类似工具独立完成过至少5个项目（全流程：需求分析→实现→调试→部署）
2. 理解Tool Use和MCP协议，有实际使用经验
3. 了解Agent的常见架构模式（ReAct、Plan-and-Execute、Supervisor等）
4. 有Python或Go的工程化经验

**软技能清单**：
1. 能清晰表达"现有AI编程工具哪里不好用"
2. 有产品思维——不只是实现功能，而是思考用户体验
3. 关注AI编程工具的最新动态（Anthropic、Cursor、OpenClaw的新功能）

**面试准备方向**：
- 准备1-2个你用AI工具完成的有挑战性的项目案例
- 研究Claude Code和OpenClaw的技术架构，准备好对比分析
- 了解DeepSeek模型的独特能力（长上下文、推理优化），思考如何用到产品里

**简历上的加分项**：
- GitHub上有基于Claude Code或类似工具开发的开源项目
- 写过AI编程工具相关的技术博客（CSDN、知乎）
- 有实际使用OpenClaw、Cursor的经验（JD里明确提到了）

---

## 八、总结：这是一个信号

DeepSeek做Coding Agent，不只是一家公司的商业决策。这是整个AI行业的一个信号。

**信号一**：AI编程工具市场已经成熟，大厂正式入场
**信号二**：工程能力（Harness）开始和算法能力同等重要
**信号三**：用AI工具写代码的经验，正在变成一种正式的职业技能

以前，"会用Copilot"是简历上的一个小亮点。
以后，"深度使用Claude Code"可能是大厂面试的入场券。

这不是危言耸听。DeepSeek的JD已经写清楚了。

---

**参考资料**
- DeepSeek官方招聘页面：deepseek.com（底部"加入我们"）
- 凤凰网报道（2026-05-21）：https://tech.ifeng.com/c/8tIFrLyu8JB
- 中华网报道（2026-05-21）：https://m.tech.china.com/article/20260521/202605211874170.html
- Claude Code官方文档：https://docs.anthropic.com/en/docs/claude-code
- OpenClaw官方文档：https://openclaw.com