# 残差网络 ResNet 原理深度解读：从梯度消失到跳跃连接，破解深度学习"越深越弱"困局

> 2015年，He Kaiming 等人在 ImageNet 上用 ResNet 拿下了图像分类、检测、定位三项冠军，错误率首次低于人类直觉（3.6%）。论文标题只有两个词：《Deep Residual Learning for Image Recognition》。两年后，它被引用超过 10 万次，成为深度学习历史上被引用最多的论文之一。这篇文章不带公式恐惧症，带你从梯度消失的本质出发，搞懂残差到底在"残"什么，以及它为什么有效。

---

## 一、深度学习的"越深越弱"困局

2015年之前，业界普遍认为：网络越深，性能越好。

这个直觉很合理——每加深一层，网络就能学习更复杂的特征。浅层学边缘，深层学纹理，再深层学物体部件，最后学语义。堆层数，理论上能堆出更强的表达能力。

但实际训练时，事情走向了反面。

当网络深度超过某个临界点（大约 20 层），训练 loss 开始不降反升。测试集准确率饱和后反而下降。这不是过拟合——过拟合是训练集好、测试集差。这里是训练集本身就开始变差，意味着网络连拟合能力都没有了。

这个现象当时让很多人困惑，后来被系统性研究后有了明确的名字：**退化问题（Degradation Problem）**。

为什么会退化？常见的解释是梯度消失/爆炸。让我们先把这个解释说清楚。

### 梯度消失：不是"消失"，是"指数衰减"

反向传播时，梯度需要从最后一层逐层传回第一层。链式法则下，每经过一层就要乘以一个激活函数的导数。

以 Sigmoid 为例：σ'(x) = σ(x)(1 - σ(x))，最大值是 0.25。

经过 20 层后，梯度变成：0.25²⁰ ≈ 10⁻¹²。传到第一层时，几乎为零。

这就是"梯度消失"。网络深处的参数几乎收不到梯度信号，学不到东西。

**但这里有个矛盾**：Batch Normalization 和 ReLU 出现后，梯度消失已经大幅缓解。He et al. 在 2015 年的实验里用了 Batch Norm，照样出现了退化问题。

这说明退化问题的根因不只是梯度消失。

### 退化问题的真正根因：优化难度

更准确的说法是：深层网络的**优化难度**远高于浅层网络。即使更深的网络理论上拥有更强的表达能力，标准的随机梯度下降却很难找到一个好的解。

假设我们要学习一个恒等映射 H(x) = x（输入等于输出）。

一个普通网络想要学到 H(x) = x，必须让所有参数在梯度下降过程中恰好拟合出一个恒等变换。这不是理所当然的事——非线性层天然会扭曲信号，让简单的恒等关系变得难以拟合。

反过来想：如果我们让网络学习 F(x) = H(x) - x，即**残差**（输入与输出之间的差异），那么恒等映射只需要让 F(x) = 0。参数全设为零，就自动实现了恒等映射。相比拟合一个完整的 H(x)，让 F(x) 学习零要容易得多。

这个思路的数学形式，就是残差连接的核心：**H(x) = F(x) + x**。

---

## 二、残差连接：把"解题"变成"改作业"

想象你在做数学题。

**普通网络的做法**：从头算一遍 357 + 289 = 646。

**ResNet 的做法**：先抄一遍答案（跳过连接），然后检查哪里不对，专注修正错误（残差分支）。

如果题目很简单（接近恒等映射），修正量很小，几乎不用动。

如果题目很难（需要完全重新计算），修正量很大，网络专注于学习真正的差异。

这就是跳跃连接（Skip Connection / Shortcut）的直观含义：将输入 x 直接跨过若干层传到后面，与这若干层的输出相加。

```python
import torch
import torch.nn as nn

class ResidualBlock(nn.Module):
    """单个残差块：F(x) + x"""
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        residual = x                              # 保存原始输入
        out = self.relu(self.bn1(self.conv1(x))) # F(x) 第一层
        out = self.bn2(self.conv2(out))           # F(x) 第二层
        out = out + residual                      # 核心：F(x) + x
        out = self.relu(out)                      # 激活
        return out
```

这段代码里的核心只有一行：`out = out + residual`。

但就是这一行，把网络的优化目标从"学习完整的 H(x)"变成了"学习 F(x) = H(x) - x"。

### 维度不匹配怎么办

当残差块的输入和输出通道数不同时（常见于网络开始下采样时），不能直接相加。有两种处理方式：

**方式一：填充零（zero-padding shortcut）**——通道差的部分填 0，最早的 ResNet 论文用过。缺点是信息传递不完整。

**方式二：1×1 卷积投影（projection shortcut）**——用一个 1×1 卷积调整维度。这是后来最常用的方式：

```python
class ResidualBlockWithProjection(nn.Module):
    """输入输出维度不同时的残差块"""
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels,
                                kernel_size=3, stride=stride, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels,
                                kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

        # 维度不同时，用投影 shortcut
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels,
                          kernel_size=1, stride=stride),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        residual = self.shortcut(x)      # 投影到相同维度
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + residual
        return self.relu(out)
```

---

## 三、ResNet 的整体架构

ResNet 不是一个网络，而是一族网络。常见的有 ResNet-18/34/50/101/152。

区别在于**残差块的数量和通道数**。ResNet-18/34 用基础残差块，ResNet-50/101/152 用瓶颈残差块（Bottleneck）：

```
基础残差块：  conv3x3 → conv3x3
瓶颈残差块：  conv1x1(降维) → conv3x3 → conv1x1(升维)
```

瓶颈块用 1×1 卷积减少中间计算量，使得在相同参数量下可以堆更多层。

```python
class BottleneckBlock(nn.Module):
    """ResNet-50+ 使用的瓶颈残差块
    out_channels 指中间层通道数，实际输出通道 = out_channels * expansion
    """
    expansion = 4  # 输出通道数是中间层的 4 倍

    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        # out_channels 是中间层通道数，输出为 out_channels * 4
        self.conv1 = nn.Conv2d(in_channels, out_channels, 1)   # 降维
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels,
                                3, stride=stride, padding=1)    # 空间卷积
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.conv3 = nn.Conv2d(out_channels, out_channels * self.expansion, 1)  # 升维
        self.bn3 = nn.BatchNorm2d(out_channels * self.expansion)
        self.relu = nn.ReLU(inplace=True)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels * self.expansion:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels * self.expansion,
                          1, stride=stride),
                nn.BatchNorm2d(out_channels * self.expansion)
            )

    def forward(self, x):
        residual = self.shortcut(x)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        out += residual
        return self.relu(out)
```

完整 ResNet 的结构很规律：stem（初始卷积）→ 4 个 stage（每个 stage N 个残差块，逐步下采样）→ 全局平均池化 → 全连接层。

以 ResNet-34 为例：

| Stage | 输出尺寸 | 通道数 | 残差块数 |
|-------|----------|--------|---------|
| conv1 | 112×112 | 64 | 1 个初始卷积 |
| stage1 | 56×56 | 64 | 3 |
| stage2 | 28×28 | 128 | 4 |
| stage3 | 14×14 | 256 | 6 |
| stage4 | 7×7 | 512 | 3 |
| avgpool + fc | 1×1 | 512 | 分类头 |

34 层指前馈卷积层数（不含 Shortcut），实际参数量约 21.8M。

---

## 四、为什么残差连接能解决梯度消失

这是最关键的问题。数学上可以严格解释：

设**单个残差块**的输入为 x，输出为 H(x) = F(x) + x。

反向传播时，梯度流向两条路径：

**路径一（主路）**：∂L/∂x = ∂L/∂H · ∂H/∂F · ∂F/∂x
链式法则传递，多层相乘 → 指数衰减风险依然存在

**路径二（短路）**：∂L/∂x = ∂L/∂H · 1（直接传回去）
梯度跳过所有非线性层，**几乎无衰减地传回**

两条路径并联，总梯度 = 路径一 + 路径二：

```
∂L/∂x = ∂L/∂H · (∂H/∂F · ∂F/∂x + 1)
```

即使 ∂H/∂F · ∂F/∂x 这条路径的梯度趋近于零，+1 保证了梯度不会消失。

换个角度：**残差连接让梯度拥有了一条"高速公路"**，从输出层直达输入层，中途不会被链式乘法稀释。

这从根本上解决了深层网络的梯度传播问题，使得训练 100+ 层的网络成为可能。

原论文的消融实验直接验证了这一点：plain-34 在 ImageNet 上的 top-1 error 为 25.02%，而 ResNet-34 降到了 21.53%——残差连接带来了 3.5 个百分点的提升。

---

## 五、踩坑实录：ResNet 训练常见问题

### 踩坑 1：BatchNorm 必须放在 ReLU 前面

残差块里顺序是 `Conv → BN → ReLU`，不是 `Conv → ReLU → BN`。

BatchNorm 放在 ReLU 前面，能对未激活的特征做归一化，保持梯度流更稳定。如果 BN 放在 ReLU 后面，ReLU 的零值输出会被 BN 归一化为非零，破坏了稀疏性。很多开源实现写反了，训练结果会有细微差距。

```python
# ✅ 正确顺序
out = self.relu(self.bn(self.conv(x)))

# ❌ 错误顺序（信息损失）
out = self.bn(self.relu(self.conv(x)))
```

### 踩坑 2：初始化方法用 He Init

残差连接让信号在加法后保持稳定，但如果权重初始化不当，主路和短路相加后的数值分布会失衡。

ResNet 使用 He 初始化（kaiming_normal），专门针对 ReLU：

```python
def _init_weights(m):
    if isinstance(m, nn.Conv2d):
        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
    elif isinstance(m, nn.BatchNorm2d):
        nn.init.constant_(m.weight, 1)
        nn.init.constant_(m.bias, 0)

model.apply(_init_weights)
```

### 踩坑 3：学习率设置比普通网络小

ResNet 的梯度流动比普通网络强，参数更新幅度会比普通网络大。如果学习率和普通网络相同，容易震荡。

通常使用余弦退火或分段衰减：

```python
optimizer = torch.optim.SGD(model.parameters(),
                            lr=0.1, momentum=0.9, weight_decay=1e-4)

# 余弦退火调度
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
    optimizer, T_max=90
)
```

ImageNet 训练 90 个 epoch，初始学习率 0.1，在第 30 和 60 个 epoch 时乘以 0.1（分段衰减）。或用余弦退火更平滑地衰减到接近零。

---

## 六、从 ResNet 出发的进化树

ResNet 之后，学术界在残差连接思想上发展出了多条路线：

**路线一：更宽的残差**
- ResNeXt：引入分组卷积（cardinality），在宽度和深度之外增加了第三个维度
- SE-ResNet：加入通道注意力（Squeeze-and-Excitation），让网络学会关注重要通道

**路线二：更密集的残差**
- DenseNet：每个残差块的输入是前面所有残差块输出的拼接（Concat 而非 Add）
- 参数量更少，但显存占用更大

**路线三：注意力增强**
- CBAM：将通道注意力和空间注意力先后加入残差块
- SKNet：选择性核卷积，用注意力动态选择卷积核大小

**路线四：Transformer 时代的残差**
- ViT（Vision Transformer）保留了残差结构：Multi-Head Self-Attention + FFN 前后都有 LayerNorm + Add
- ResNet 的 skip connection 思想，在 Transformer 架构中以 LayerNorm + Add 的形式继续存在

---

## 七、ResNet 在生产环境的实际应用

### 用 PyTorch 加载预训练模型

```python
import torchvision.models as models

# 加载 ResNet-50 预训练权重，直接用于迁移学习
model = models.resnet50(weights='IMAGENET1K_V2')
model.fc = nn.Linear(model.fc.in_features, 10)  # 替换分类头

# 冻结前面层，只训练分类头（可选）
for param in model.parameters():
    param.requires_grad = False
for param in model.fc.parameters():
    param.requires_grad = True
```

### 自定义数据集训练流程

```python
from torchvision import transforms, datasets

# 数据增强（训练集必须有的增强）
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.2, 0.2, 0.1),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                          [0.229, 0.224, 0.225])
])

train_ds = datasets.ImageFolder('data/train', train_transform)
train_loader = torch.utils.data.DataLoader(
    train_ds, batch_size=64, shuffle=True, num_workers=4
)

# 训练循环
for epoch in range(90):
    model.train()
    total_loss, correct = 0, 0
    for images, labels in train_loader:
        images, labels = images.cuda(), labels.cuda()
        optimizer.zero_grad()
        outputs = model(images)
        loss = nn.CrossEntropyLoss()(outputs, labels)
        loss.backward()
        optimizer.step()
    scheduler.step()
```

这段代码用 ResNet-50 + 迁移学习，在新数据集上通常能取得很好的效果——不需要从头训练，直接利用 ImageNet 预训练学到的视觉特征。

---

## 总结

ResNet 的核心贡献只有两行公式：**H(x) = F(x) + x**。

但这个简单的设计，解决了深度学习中最根本的问题：网络越深，优化越难。

残差连接的本质，是把"学习一个复杂函数 H(x)"变成"学习 H(x) - x 的残差"。恒等映射只需要让残差为 0，优化难度大幅降低。

同时，短路路径提供了一条梯度高速公路，让 100+ 层的网络训练成为现实。

从 2015 年到现在，ResNet 的思想已经渗透到视觉模型的每一个角落——CNN、Transformer、扩散模型，残差连接无处不在。

理解 ResNet，不只是理解一个网络架构，而是理解深度学习优化理论的一个关键转折点。

**参考资料**
- He Kaiming et al., "Deep Residual Learning for Image Recognition", CVPR 2016
- He Kaiming et al., "Identity Mappings in Deep Residual Networks", ECCV 2016
- torchvision.models.resnet50 官方实现