# 【AI Agent 系统教学 36】Agent 个性化与角色定制

> 同样一个 Agent，对程序员和对设计师应该有不同的说话方式。
> 个性化，让 Agent 从"通用工具"变成"你的工具"。

---

## 前言：为什么需要个性化

没有个性化的 Agent：

```
程序员：帮我写一个二分查找
Agent：好的，以下是一个二分查找的实现...

设计师：帮我找一些配色方案
Agent：好的，以下是一些配色方案...

（两个回复的语气、风格、详细程度完全一样）
```

有个性化的 Agent：

```
程序员：帮我写一个二分查找
Agent：给你一个 Python 实现，时间复杂度 O(log n)，注意边界条件：
[代码]

设计师：帮我找一些配色方案
Agent：推荐几组配色方案，附带色值和应用场景：
🎨 方案 1：#2C3E50 + #E74C3C ... 适合科技感设计
```

**个性化让 Agent 的回复更贴合用户的习惯和需求。**

---

## 一、用户画像

### 1.1 画像数据

```python
class UserProfile:
    """用户画像"""
    def __init__(self, user_id):
        self.user_id = user_id
        self.profile = {
            "basic": {},      # 基本信息
            "preferences": {}, # 偏好
            "behavior": {},    # 行为模式
            "capabilities": {}, # 能力水平
            "history": [],     # 交互历史
        }
    
    def update_from_interaction(self, interaction):
        """从交互中更新画像"""
        # 1. 提取偏好
        preferences = self._extract_preferences(interaction)
        self.profile["preferences"].update(preferences)
        
        # 2. 更新行为模式
        self.profile["behavior"]["avg_response_length"] = (
            self._calculate_avg_length(interaction)
        )
        
        # 3. 更新能力评估
        self.profile["capabilities"]["technical_level"] = (
            self._assess_technical_level(interaction)
        )
    
    def get_persona_prompt(self):
        """生成个性化提示"""
        pref = self.profile["preferences"]
        return f"""
用户偏好：
- 回复风格：{pref.get('style', 'normal')}
- 详细程度：{pref.get('detail_level', 'medium')}
- 技术深度：{pref.get('technical_level', 'medium')}
- 语言偏好：{pref.get('language', '中文')}
"""
```

### 1.2 画像推断

```python
class ProfileInferrer:
    """从对话中推断用户画像"""
    def infer(self, conversations):
        prompt = f"""
        从以下对话中推断用户画像：
        {conversations}
        
        输出 JSON：
        {{
            "technical_level": "beginner/intermediate/expert",
            "preferred_style": "concise/detailed/conversational",
            "interests": ["编程", "设计", ...],
            "language": "中文/英文",
            "personality": "正式/随意/幽默"
        }}
        """
        return llm.generate(prompt)
```

---

## 二、角色定制

### 2.1 角色定义

```python
class AgentPersona:
    """Agent 角色定义"""
    def __init__(self, name, role, style):
        self.name = name
        self.role = role
        self.style = style
        self.knowledge_base = []
        self.behavior_rules = []
    
    def generate_system_prompt(self):
        return f"""
你是一个 {self.role}。
名字：{self.name}
风格：{self.style}

{self._format_knowledge()}
{self._format_rules()}

请记住你的角色，并始终以这个角色与用户互动。
"""
    
    def _format_knowledge(self):
        return "\n".join([f"- {k}" for k in self.knowledge_base])
    
    def _format_rules(self):
        return "\n".join([f"- {r}" for r in self.behavior_rules])


# 角色示例
teacher_persona = AgentPersona(
    name="导师",
    role="技术导师",
    style="耐心、详细、引导式",
)
teacher_persona.knowledge_base = [
    "用户可能是初学者",
    "解释要深入浅出",
    "多问引导性问题",
]
teacher_persona.behavior_rules = [
    "先理解用户的问题，再给出答案",
    "鼓励用户自己思考",
    "给出代码时附带解释",
]

assistant_persona = AgentPersona(
    name="助手",
    role="效率助手",
    style="简洁、直接、高效",
)
assistant_persona.behavior_rules = [
    "直接给出答案，不需要寒暄",
    "用最少的词表达最多的信息",
    "优先使用工具，不凭记忆回答",
]
```

### 2.2 角色切换

```python
class PersonaManager:
    """角色管理器"""
    def __init__(self):
        self.personas = {}
        self.current_persona = None
    
    def register_persona(self, name, persona):
        self.personas[name] = persona
    
    def switch_to(self, name):
        if name in self.personas:
            self.current_persona = self.personas[name]
            return True
        return False
    
    def detect_persona(self, user_input):
        """根据用户输入自动选择角色"""
        prompt = f"""
        用户输入：{user_input}
        可选角色：{list(self.personas.keys())}
        
        根据用户输入的语气、内容、正式程度，选择合适的角色：
        """
        persona_name = llm.generate(prompt)
        return self.switch_to(persona_name)
```

---

## 三、风格控制

### 3.1 风格参数

```python
class StyleConfig:
    """风格配置"""
    def __init__(self):
        self.params = {
            "formality": 0.5,         # 正式程度 0-1
            "detail_level": 0.5,      # 详细程度 0-1
            "technical_depth": 0.5,   # 技术深度 0-1
            "verbosity": 0.5,         # 啰嗦程度 0-1
            "empathy": 0.5,           # 共情程度 0-1
            "humor": 0.0,             # 幽默程度 0-1
        }
    
    def generate_style_prompt(self):
        """生成风格提示"""
        prompts = []
        if self.params["formality"] > 0.7:
            prompts.append("使用正式、礼貌的语气")
        elif self.params["formality"] < 0.3:
            prompts.append("使用随意、自然的语气")
        
        if self.params["detail_level"] > 0.7:
            prompts.append("提供详细解释和背景信息")
        elif self.params["detail_level"] < 0.3:
            prompts.append("直接给出答案，不需要解释")
        
        if self.params["technical_depth"] > 0.7:
            prompts.append("使用专业术语，深入技术细节")
        elif self.params["technical_depth"] < 0.3:
            prompts.append("避免专业术语，用通俗语言解释")
        
        return "\n".join(prompts)
```

### 3.2 自适应风格

```python
class AdaptiveStyler:
    """自适应风格"""
    def __init__(self):
        self.style_history = []
    
    def adapt_to_user(self, user_input, user_profile):
        """根据用户输入自适应调整风格"""
        analysis = llm.generate(f"""
        用户输入：{user_input}
        用户画像：{user_profile}
        
        分析用户想要的回复风格：
        1. 正式还是随意？
        2. 详细还是简洁？
        3. 技术深度如何？
        4. 带不带情绪？
        
        输出 JSON 风格参数：
        """)
        
        self._apply_style(analysis)
```

---

## 四、个性化记忆

### 4.1 用户偏好存储

```python
class UserPreferenceStore:
    """用户偏好存储"""
    def __init__(self, db):
        self.db = db
    
    def save_preference(self, user_id, key, value):
        self.db.execute("""
            INSERT OR REPLACE INTO user_preferences
            (user_id, pref_key, pref_value, updated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, key, json.dumps(value), datetime.now()))
        self.db.commit()
    
    def get_preferences(self, user_id):
        cursor = self.db.execute("""
            SELECT pref_key, pref_value FROM user_preferences
            WHERE user_id = ?
        """, (user_id,))
        return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
    
    def get_preference_prompt(self, user_id):
        """生成偏好提示词"""
        prefs = self.get_preferences(user_id)
        if not prefs:
            return ""
        
        return f"""
用户偏好（请遵守）：
{json.dumps(prefs, indent=2, ensure_ascii=False)}
"""
```

### 4.2 学习型个性化

```python
class LearningPersonalizer:
    """学习型个性化"""
    def __init__(self):
        self.feedback_history = []
    
    def collect_feedback(self, user_id, response, user_reaction):
        """收集用户反馈"""
        self.feedback_history.append({
            "user_id": user_id,
            "response": response,
            "reaction": user_reaction,  # "like", "dislike", "neutral"
            "timestamp": time.time(),
        })
    
    def improve_persona(self, user_id):
        """根据反馈改进个性化"""
        recent = [f for f in self.feedback_history 
                  if f["user_id"] == user_id][-10:]
        
        analysis = llm.generate(f"""
        用户反馈历史：{recent}
        
        分析：
        1. 用户喜欢什么风格？
        2. 用户不喜欢什么风格？
        3. 应该怎么调整？
        
        调整建议：
        """)
        
        return analysis
```

---

## 五、多角色协作

### 5.1 角色配置

```python
class MultiRoleConfig:
    """多角色配置"""
    def __init__(self):
        self.roles = {
            "teacher": {
                "persona": teacher_persona,
                "trigger": ["教", "学", "解释", "理解"],
                "tools": ["search", "code_example"],
            },
            "assistant": {
                "persona": assistant_persona,
                "trigger": ["帮", "查", "做", "写"],
                "tools": ["search", "weather", "email"],
            },
            "consultant": {
                "persona": AgentPersona("顾问", "专业顾问", "分析、建议"),
                "trigger": ["建议", "分析", "评估", "方案"],
                "tools": ["search", "analyze"],
            },
        }
    
    def select_role(self, user_input):
        """选择角色"""
        for role_name, config in self.roles.items():
            if any(t in user_input for t in config["trigger"]):
                return role_name
        return "assistant"  # 默认
```

---

## 六、2026 年个性化趋势

### 6.1 超个性化

Agent 不再只是"适配用户"，而是"预判用户"：

```
用户还没说，Agent 已经知道：
- 这个用户喜欢什么风格
- 这个用户通常要什么信息
- 这个用户的技术水平
- 这个用户当前的心情
```

### 6.2 人格连续性

Agent 表现出稳定的人格特征：

```
今天的 Agent 和昨天的 Agent 是"同一个人"：
- 有相同的记忆
- 有相同的性格
- 有相同的表达习惯
```

### 6.3 社交感知

Agent 感知社交场景并调整：

```
群聊 vs 私聊：
- 群聊：更正式，不打断别人
- 私聊：更随意，可以更直接
```

---

## 总结

| 个性化维度 | 实现方式 | 效果 |
|-----------|---------|------|
| 用户画像 | 从交互中推断 | 更贴合用户 |
| 角色定制 | 定义角色和行为 | 统一风格 |
| 风格控制 | 参数化风格 | 灵活调整 |
| 个性化记忆 | 存储用户偏好 | 持续优化 |
| 学习型个性化 | 反馈驱动 | 不断进步 |

**个性化不是"让 Agent 变可爱"，是"让 Agent 更有效"。**

**模块五总结**：6 篇文章，从记忆系统、工具系统、规划推理、安全治理、可靠性工程到个性化定制，覆盖了 Agent 核心能力的完整体系。

**下一篇**：进入模块六——**多 Agent 系统**。

---

**思考题**：
1. 你的 Agent 现在有"个性化"吗？如果有，用户反馈怎么样？
2. 你认为"个性化"和"一致性"（不同用户用不同风格）哪个更重要？
3. 如果用户对 Agent 的个性化调整不满意，怎么处理？

---

> 上一篇：[35] Agent 可靠性工程
> 下一篇：[37] 多 Agent 架构导论
> 系列目录：[README.md](./README.md)