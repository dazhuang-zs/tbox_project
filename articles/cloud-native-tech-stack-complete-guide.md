# 容器化部署与云端运维技术全景：从小白到能上手

> 假设你刚写完第一个 Web 应用，想知道怎么把它部署到网上让别人访问。这篇文章从零讲起，不用任何前置知识。

---

## 第一章：你写的代码，怎么变成别人能访问的网站？

### 1.1 最原始的部署方式

写完代码，你要让别人访问，最笨的办法：

1. 买一台云服务器（比如阿里云 ECS）
2. SSH 登录上去
3. 装 Node.js / Python / Java
4. 把代码传上去
5. `npm start` 或者 `python app.py`
6. 配个 Nginx，把域名指过来

听起来还行？但问题马上来了：

- 你同事的电脑是 macOS，服务器是 CentOS，本地能跑服务器报错「glibc 版本不对」
- 你用的 Node 18，服务器预装了 Node 14，语法不兼容
- 过了三个月你想加个 Redis，又得 SSH 上去装一遍
- 老板说「再加两台服务器」，你手动配了三遍，其中一台漏了环境变量，凌晨三点报警

**核心矛盾：** 代码可以 Git 管，但环境没法 Git 管。

### 1.2 虚拟机时代（已经被淘汰，但先理解它）

第一代解决方案：虚拟机（VM）。把整个操作系统打包成一个镜像文件，在哪都能启动。

```
┌─────────────────┐
│   你的应用       │
├─────────────────┤
│  依赖库（Node等）│
├─────────────────┤
│  操作系统（Ubuntu）│  ← 一个完整的 OS，几个 GB
├─────────────────┤
│  虚拟化层        │
├─────────────────┤
│  物理服务器       │
└─────────────────┘
```

**缺点：** 太胖了。一个虚拟机镜像动辄几个 GB，启动要几十秒，一台物理机只能跑几个 VM。而且每台 VM 都要单独装操作系统——你有 10 个应用就要 10 套 Ubuntu，光操作系统就占了 10GB × 10 = 100GB。

### 1.3 容器登场——共享操作系统，只打包应用

容器换了个思路：我不虚拟整个操作系统了，我直接和宿主机共享内核，只打包应用和它的依赖。

```
┌──────────┐ ┌──────────┐ ┌──────────┐
│ 应用 A    │ │ 应用 B    │ │ 应用 C    │
│ 依赖 A    │ │ 依赖 B    │ │ 依赖 C    │
└──────────┘ └──────────┘ └──────────┘
├─────────────────────────────────────┤
│        宿主机操作系统（Linux）         │  ← 只此一份
├─────────────────────────────────────┤
│              物理服务器               │
└─────────────────────────────────────┘
```

**好处立竿见影：**

- 容器镜像只有几十 MB 到几百 MB（vs VM 的几个 GB）
- 启动速度是秒级（vs VM 的几十秒）
- 一台物理机能跑几十上百个容器（vs 几个 VM）
- 最重要的是：**镜像在任何地方启动都一样**，彻底消灭了「我这能跑你那不行」

---

## 第二章：Docker — 每个开发者都该会的基本功

### 2.1 Docker 到底是什么

Docker 是一个让你可以方便地创建、运行、管理容器的工具。记住这句话：

> Docker 做的事 = 把「你的应用 + 它的所有依赖」打包成一个文件（镜像），然后这个文件在谁的电脑上跑结果都一样。

### 2.2 三个核心概念

| 概念 | 是什么 | 一句话类比 |
|------|--------|-----------|
| **镜像（Image）** | 一个只读的打包文件，包含应用运行所需的一切（代码、运行时、系统库、环境变量、配置文件） | 建筑图纸 |
| **容器（Container）** | 镜像运行起来的实例。一个镜像可以启动多个容器，互相隔离 | 按图纸盖出来的房子 |
| **仓库（Registry）** | 存放镜像的地方（如 Docker Hub） | 图纸档案馆 |

### 2.3 你写的第一份 Dockerfile

假设你有一个 Node.js 应用，项目结构是这样的：

```
my-app/
├── package.json
├── server.js
└── node_modules/
```

创建文件 `my-app/Dockerfile`（注意没有扩展名，就叫 Dockerfile）：

```dockerfile
# 👇 从哪个基础镜像开始（相当于「在装了 Node 18 的系统上操作」）
FROM node:18-alpine

# 👇 在镜像里创建一个 /app 目录，之后的操作都在这里进行
WORKDIR /app

# 👇 先把 package.json 复制进去（只复制这个是为了利用缓存）
COPY package.json ./

# 👇 安装依赖
RUN npm install

# 👇 把项目代码全部复制进去
COPY . .

# 👇 容器启动时执行的命令
CMD ["node", "server.js"]

# 👇 声明这个应用用哪个端口（文档用途，不影响实际网络）
EXPOSE 3000
```

逐行解释为什么这么写：

- **`FROM node:18-alpine`**：`node:18` 是装了 Node.js 18 的 Linux 精简版。`alpine` 是一个极小的 Linux 发行版（只有 5MB），让你的镜像尽可能小。
- **`WORKDIR /app`**：设定工作目录。相当于你在终端先 `cd /app`。
- **`COPY package.json ./`** 然后 **`RUN npm install`**：这是个重要的优化技巧。先只复制 `package.json`，装依赖，再复制其他代码。这样当你改了代码但没改依赖时，`npm install` 这层会被缓存，构建速度快很多。
- **`COPY . .`**：第一个 `.` 是你电脑上的项目目录，第二个 `.` 是镜像里的 `/app` 目录。
- **`CMD` vs `RUN`**：`RUN` 是构建镜像时执行（比如安装依赖），`CMD` 是容器启动时执行（比如启动服务器）。

### 2.4 构建和运行

```bash
# 在 my-app/ 目录下执行

# 构建镜像（-t 给镜像起个名字）
docker build -t my-app:v1 .

# 运行容器
# -d: 后台运行
# -p 3000:3000: 把你电脑的 3000 端口 映射到容器的 3000 端口
# --name: 给容器起个名字，方便后续操作
docker run -d -p 3000:3000 --name my-app-container my-app:v1

# 验证：浏览器打开 http://localhost:3000
```

现在你懂了：`docker run` 就是「启动一个容器」，`-p 3000:3000` 就是「把容器里的 3000 端口接到外面来」。

### 2.5 日常操作速查

```bash
# 查看正在运行的容器
docker ps

# 查看所有容器（包括已停止的）
docker ps -a

# 停止容器
docker stop my-app-container

# 删除容器（必须先停止）
docker rm my-app-container

# 查看镜像
docker images

# 删除镜像
docker rmi my-app:v1

# 进入正在运行的容器（调试用）
docker exec -it my-app-container sh

# 查看容器日志
docker logs my-app-container

# 查看容器日志（实时跟踪，Ctrl+C 退出）
docker logs -f my-app-container
```

### 2.6 Docker Compose — 当你的应用需要不止一个容器

你很快会发现：一个正经的 Web 应用需要：

- 应用容器（你的代码）
- 数据库容器（MySQL/PostgreSQL）
- 缓存容器（Redis）
- 可能还有 Nginx 容器（静态文件 + 反向代理）

如果每次都用 `docker run` 启动四个容器，还要配网络让它们能互相访问——太麻烦了。

`docker-compose.yml` 一次性解决：

```yaml
version: "3.8"
services:
  # 应用服务
  app:
    build: .                    # 用当前目录的 Dockerfile 构建
    ports:
      - "3000:3000"             # 端口映射
    environment:                 # 环境变量
      - DB_HOST=db              # 容器之间用服务名就能互相访问
      - DB_PORT=5432
      - REDIS_HOST=cache
    depends_on:                  # 启动顺序：等 db 和 cache 就绪后再启动 app
      - db
      - cache
    restart: unless-stopped      # 挂了自动重启

  # 数据库服务
  db:
    image: postgres:16-alpine   # 直接用官方镜像，不用自己写 Dockerfile
    environment:
      - POSTGRES_PASSWORD=mysecretpassword
      - POSTGRES_DB=myapp
    volumes:                     # 持久化：数据存在宿主机，容器删了数据还在
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  # 缓存服务
  cache:
    image: redis:7-alpine
    volumes:
      - redisdata:/data
    restart: unless-stopped

# 声明 volumes（告诉 Docker 在宿主机上留块地）
volumes:
  pgdata:
  redisdata:
```

一条命令启动所有服务：

```bash
docker compose up -d
```

一条命令全部停掉：

```bash
docker compose down
```

### 2.7 Docker 不是万能的——什么时候不用它

- **本地开发阶段**：Node.js 直接用 `npm run dev` 比反复构建 Docker 镜像快得多。Docker 更适合部署，开发期用它反而碍手碍脚。
- **你的应用就一个静态 HTML 页面**：GitHub Pages、Vercel 直接托管，不需要容器。
- **你需要完整的 OS 隔离**：容器共享宿主机的 Linux 内核，不能跑 Windows 容器和 Linux 容器混在一起（有 Windows 容器技术但不够成熟）。

---

## 第三章：Kubernetes (k8s) — 从一台机器到一群机器

### 3.1 什么时候你需要 k8s

先回答一个问题：你现在有几台服务器，几个应用？

| 你的情况 | 你需要的 |
|----------|----------|
| 1 台服务器，1-3 个应用 | Docker Compose 就够了 |
| 1 台服务器，但想要以后好扩展 | 先继续用 Compose，同时学 k8s 概念 |
| 3 台以上服务器，10 个以上服务 | 可以认真考虑 k8s |
| 你需要零停机部署、自动扩缩容、多环境管理 | 这就是 k8s 的用武之地 |

**一个关键认识：** k8s 解决的是「规模化」问题。如果你还没有规模，k8s 本身会成为问题（运维 k8s 本身就需要一个懂行的人）。

### 3.2 k8s 到底做了什么——用民宿来类比

假设你开了一家民宿平台，要管理 10 间房间：

- **没有 Docker**：客人来了，你现场搭床、装空调、接水电（每个房间的环境都要现场配）。
- **有了 Docker**：所有房间统一标准——每个房间一个集装箱，箱子里床、空调、水电都配好了。拉过来就能用。
- **有了 k8s**：你不再管单个房间了。你告诉 k8s「我要在这片场地上时刻保持 5 个可用的房间、2 个前台、1 个厨房」——k8s 自动安排哪个箱子放哪里、某个坏了换新的、人多时加箱子、人少时收箱子。

### 3.3 k8s 的「集群」长什么样

一个 k8s 集群由两部分组成：

```
┌──────────────────────────────────────────────┐
│                  控制平面（Master）             │
│  ┌─────────┐ ┌──────────┐ ┌───────────────┐  │
│  │API Server│ │Scheduler │ │Controller Mgr │  │
│  │ （调度台）│ │（调度员） │ │  （大总管）    │  │
│  └─────────┘ └──────────┘ └───────────────┘  │
│  ┌──────────┐                                 │
│  │  etcd    │  ← 存所有配置（集群的数据库）     │
│  └──────────┘                                 │
└──────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│                   工作节点（Worker）            │
│  ┌────────────┐ ┌────────────┐              │
│  │  kubelet   │ │ kube-proxy │              │
│  │（监工）     │ │（网络员）  │              │
│  └────────────┘ └────────────┘              │
│  ┌──────────────────────────────┐           │
│  │  Pod          Pod          Pod│          │
│  │ ┌──────┐    ┌──────┐  ┌──────┐│         │
│  │ │容器 A │    │容器 B │  │容器 C ││        │
│  │ └──────┘    └──────┘  └──────┘│         │
│  └──────────────────────────────┘           │
└─────────────────────────────────────────────┘
```

**控制平面（Master）** 是大脑：
- **API Server**：所有操作的统一入口。你运行 `kubectl apply` 就是跟它说话。
- **Scheduler**：新 Pod 应该放在哪个 Worker 节点上？哪个节点资源够用就放哪。
- **Controller Manager**：不停的对比「当前状态」和「期望状态」。Deployment 说要有 3 个副本，实际只有 2 个？那就再启动一个。
- **etcd**：一个分布式键值存储，存着整个集群的所有配置数据。整个集群的「记忆」。

**工作节点（Worker）** 是手脚：
- **kubelet**：每个 Worker 上的 agent，接收 Master 的指令，管理本机的 Pod。
- **kube-proxy**：负责网络规则，让请求能被正确路由到 Pod。

**Pod** 是 k8s 最小的调度单位。一个 Pod 可以包含一个或多个容器，这些容器共享网络和存储。大多数情况下一个 Pod 只跑一个容器——所以你可以近似地把「Pod」理解为「容器的包装盒」。

### 3.4 你用 k8s 时会写的第一个 YAML — Deployment

假设你要部署那个 Node.js 应用，3 个副本（保证一个挂了还有两个顶住）：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app          # Deployment 的名字
  labels:
    app: my-app
spec:
  replicas: 3            # 我要 3 个 Pod（3 个副本）
  selector:
    matchLabels:
      app: my-app        # 用标签找到属于这个 Deployment 的 Pod
  template:              # Pod 模板——每个 Pod 按这个模子造
    metadata:
      labels:
        app: my-app      # Pod 的标签（和上面 selector 匹配）
    spec:
      containers:
        - name: my-app
          image: my-app:v1           # 用哪个镜像
          ports:
            - containerPort: 3000    # 容器里应用监听的端口
          env:                        # 环境变量
            - name: NODE_ENV
              value: "production"
          resources:                   # 资源限制（非常重要！）
            requests:                  # 最小保证
              memory: "128Mi"         # k8s 保证分配这么多
              cpu: "100m"             # 100 millicores = 0.1 核
            limits:                    # 上限
              memory: "256Mi"         # 超过这个就杀掉 Pod
              cpu: "500m"             # 超过 0.5 核就限流
```

**`resources` 为什么重要？** 如果你不设限制，一个 Pod 内存泄漏可能吃掉整个节点的内存，把同一台机器上的其他服务全拖死。

提交到集群：
```bash
kubectl apply -f deployment.yaml
```

### 3.5 Service — 给 Pod 一个稳定的「手机号」

Pod 是临时的——它挂了重启后 IP 地址会变。Service 解决这个问题：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-service
spec:
  type: LoadBalancer        # 从云厂商分配一个公网 IP（云环境专用）
  # type: ClusterIP          # 集群内部用这个
  # type: NodePort           # 从节点 IP 的某个端口暴露
  selector:
    app: my-app              # 所有带 app=my-app 标签的 Pod 都会被这个 Service 代理
  ports:
    - port: 80               # Service 自己的端口（外部访问用这个）
      targetPort: 3000       # 转发到 Pod 的哪个端口
```

**理解三种 Service 类型：**

| 类型 | 访问方式 | 什么时候用 |
|------|---------|-----------|
| ClusterIP | 只有集群内部能访问（给一个内部 IP） | 服务之间互相调用。比如应用容器访问数据库 |
| NodePort | 通过集群任意节点的 `IP:端口` 访问 | 测试环境、裸金属服务器 |
| LoadBalancer | 云厂商分配一个公网 IP，自动创建负载均衡器 | 生产环境、需要从公网访问 |

### 3.6 Ingress — 多个 Service 共用同一个入口

你有一个域名 `myapp.com`，想这样路由：
- `myapp.com/api` → 后端 Service
- `myapp.com/` → 前端 Service

不需要为每个 Service 申请一个公网 IP，用 Ingress 一个入口搞定：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
spec:
  rules:
    - host: myapp.com           # 域名
      http:
        paths:
          - path: /api           # URL 路径 /api
            pathType: Prefix
            backend:
              service:
                name: backend-service
                port:
                  number: 3000
          - path: /              # URL 路径 /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```

### 3.7 ConfigMap 和 Secret — 配置与密码管理

**永远不要把密码写在 Deployment 的 YAML 里。**

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  NODE_ENV: "production"
  LOG_LEVEL: "info"
  API_TIMEOUT: "30s"
---
# secret.yaml（值需要 base64 编码）
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  DB_PASSWORD: bXlzdXBlcnNlY3JldHBhc3N3b3Jk  # echo -n 'mypassword' | base64
  API_KEY: c2stYWJjZGVmMTIzNDU2Nzg5MA==
```

然后在 Deployment 中引用：

```yaml
containers:
  - name: my-app
    envFrom:
      - configMapRef:
          name: app-config    # 整个 ConfigMap 的所有 key 变成环境变量
      - secretRef:
          name: app-secrets   # 整个 Secret 的所有 key 变成环境变量
```

### 3.8 Helm — 别手写 10 个 YAML 文件了

一个简单应用到 k8s 上可能需要这些文件：

```
deployment.yaml     # Pod 定义
service.yaml        # 网络入口
configmap.yaml      # 配置
secret.yaml         # 密码
ingress.yaml        # 域名路由
hpa.yaml           # 自动扩缩容
pvc.yaml           # 存储
```

Helm 把它们打包成一个 **Chart**：

```bash
# 创建一个 Chart 模板
helm create my-chart

# 安装（就等于把所有 YAML 提交到集群）
helm install my-release ./my-chart

# 升级
helm upgrade my-release ./my-chart

# 回滚到上一个版本
helm rollback my-release

# 查看已安装的
helm list
```

**Helm vs Kustomize 怎么选：**

- **Helm**：看中社区生态，想一键安装别人的应用（比如安装 Redis：`helm install redis bitnami/redis`）。适合对外分发的应用。
- **Kustomize**：管理自己的多个环境更自然。一个 base 目录 + dev/staging/prod 三个 overlay，只写差异部分。适合管理自己的部署配置。

---

## 第四章：在云端跑这些 — 不用自己买服务器

### 4.1 你有哪些选择

```
控制权从高到低 ↓              便利性从低到高 ↓

┌──────────────────────────────┐
│ 物理服务器（机房自建）          │  你管一切：硬件、网络、OS、k8s、应用
├──────────────────────────────┤
│ 云虚拟机（ECS/EC2/VM）         │  你管 OS 及以上，云厂商管硬件
├──────────────────────────────┤
│ 托管 k8s（ACK/EKS/GKE）       │  你管应用，云厂商管 k8s 控制面
├──────────────────────────────┤
│ Serverless 容器（Cloud Run）  │  你只写代码，平台自动扩缩 + 按调用计费
├──────────────────────────────┤
│ PaaS（Vercel/Railway）        │  你 git push，剩下的全自动
└──────────────────────────────┘
```

### 4.2 托管 k8s 是什么感觉

拿阿里云 ACK 举例：

1. 在阿里云控制台点「创建 k8s 集群」
2. 选 3 台 ECS 作为 Worker 节点
3. 等 10 分钟
4. 你本地 `kubectl` 直接连上去，用起来和本地 k8s 一模一样

**你不用管的事：** Master 节点的健康、etcd 备份、API Server 高可用、k8s 版本升级——阿里云帮你做了。

**你仍然要管的事：** 应用的 Deployment/Service/Ingress、Worker 节点的扩容、监控告警配置。

### 4.3 三大国际云速览

| 云厂商 | 一句话特点 | 托管 k8s | 适合 |
|--------|-----------|---------|------|
| AWS | 产品最多最全，学习曲线最陡 | EKS | 有专职 DevOps 的团队 |
| Azure | 和微软全家桶绑定深 | AKS | .NET 技术栈、传统企业 |
| Google Cloud | k8s 原生最好（k8s 本来就是 Google 开源的） | GKE | 技术驱动型团队、初创 |

### 4.4 三大国内云速览

| 云厂商 | 一句话特点 | 托管 k8s | 适合 |
|--------|-----------|---------|------|
| 阿里云 | 国内市场份额最大，中文文档最完善 | ACK | 大多数国内企业 |
| 腾讯云 | 游戏/音视频/微信生态强 | TKE | 游戏公司、社交应用 |
| 华为云 | 政企市场强，自研芯片生态 | CCE | 政企客户、信创需求 |

### 4.5 如果你不想管任何基础设施——PaaS

「我就想 git push 一下代码就上线」——这是 PaaS 的承诺。

| 平台 | 适合什么 | 免费额度 |
|------|---------|---------|
| Vercel | 前端、Next.js、静态网站 | 有免费套餐，够个人项目用 |
| Railway | 全栈应用（前后端+数据库），体验接近 Heroku | 有免费额度，超出按用量计费 |
| Fly.io | 需要全球低延迟部署的服务 | 有免费套餐 |
| Cloud Run | 已经有 Google Cloud 账号、需要更灵活的环境 | 按调用量计费，低流量约等于免费 |

---

## 第五章：CI/CD —「改代码 → 测试 → 部署」全自动

### 5.1 为什么要 CI/CD

手工部署流程（痛苦版）：

1. 本地写好代码
2. 运行测试（「好像跑过了？不记得了」）
3. SSH 到服务器
4. `git pull`
5. `npm install`
6. `npm run build`
7. `pm2 restart app`
8. 发现漏了一个环境变量，再来一遍
9. 凌晨三点发布，手抖打错命令，全站挂了

CI/CD 让这一切自动发生：

```
git push → 自动跑测试 → 自动构建镜像 → 自动部署到测试环境 
→ 自动部署到生产环境
```

### 5.2 GitHub Actions 入门

在项目里创建 `.github/workflows/deploy.yml`：

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]      # main 分支有 push 就触发

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      # 第一步：把代码拉到 CI 环境
      - name: Checkout code
        uses: actions/checkout@v4

      # 第二步：构建 Docker 镜像
      - name: Build Docker image
        run: docker build -t my-app:${{ github.sha }} .

      # 第三步：推送到镜像仓库
      - name: Push to registry
        run: |
          docker tag my-app:${{ github.sha }} registry.example.com/my-app:latest
          docker push registry.example.com/my-app:latest

      # 第四步：更新 k8s 部署
      - name: Deploy to k8s
        run: kubectl set image deployment/my-app my-app=registry.example.com/my-app:latest
```

**核心触发条件：**

| 触发条件 | 含义 |
|----------|------|
| `push` | 代码推送到仓库时 |
| `pull_request` | 创建或更新 PR 时 |
| `schedule` | 定时触发（类似 cron） |
| `workflow_dispatch` | 手动触发（在 GitHub 网页上点按钮） |

### 5.3 ArgoCD — GitOps 的落地方式

ArgoCD 的核心理念：**Git 仓库是唯一真相来源。**

传统 CD：CI 主动推送新版本到集群。  
GitOps：ArgoCD 定时看 Git 仓库，发现不一致就自动同步。

```
你的 Git 仓库（期望状态）           k8s 集群（实际状态）
┌──────────────────┐              ┌──────────────────┐
│ deployment.yaml   │              │  Pod × 3          │
│ replicas: 3       │   ArgoCD    │  Service          │
│ image: app:v2     │   盯着看    │  Ingress          │
│                    │◄──────────►│                    │
│                    │  发现不同   │  （跑的是 v1？）   │
│                    │  就同步     │                    │
└──────────────────┘              └──────────────────┘
```

**好处：**
- 所有变更都在 Git 里有记录（谁、什么时候、改了什么）
- 改代码改出问题？`git revert` 然后 ArgoCD 自动回滚
- 集群挂了？重建集群后 ArgoCD 自动把应用恢复到 Git 里定义的状态

---

## 第六章：服务网格 — 微服务太多时的通信管家

### 6.1 问题：微服务多了，通信怎么办

你的架构从 3 个服务变成 20 个：

- A 调用 B，B 调用 C、D、E……请求链越来越长。
- B 挂了，重试几次？超时多长时间？
- A 和 C 之间的通信怎么加密？
- 想把 10% 的流量切到新版本测试一下？

这些需求如果每个服务自己实现，代码量暴增且容易不一致。

### 6.2 服务网格的思路：把通信逻辑抽到外面

```
没有服务网格：                      有服务网格：
┌────────┐  直连  ┌────────┐       ┌────────┐    ┌────────┐
│  应用 A  │───────►│  应用 B  │       │  应用 A  │    │  应用 B  │
│ 通信逻辑  │       │         │       │ 只管业务 │    │ 只管业务 │
└────────┘        └────────┘       └───┬────┘    └───┬────┘
                                        │              │
                                    ┌───▼────┐    ┌───▼────┐
                                    │ Sidecar│────│ Sidecar│
                                    │ 代理    │    │ 代理    │
                                    │         │    │         │
                                    │ 重试/超时│   │ 加密/限流│
                                    └────────┘    └────────┘
```

Sidecar 的好处：

- **应用不用管网络**：你写的代码只管业务逻辑，Sidecar 自动处理重试、超时、熔断、加密。
- **统一配置**：所有服务的超时策略在网格层统一配，不需要改 20 个服务的代码。
- **流量控制**：10% 流量切到金丝雀版本、按用户分组路由——改网格配置就行。

### 6.3 Istio vs Linkerd

| 对比维度 | Istio | Linkerd |
|---------|-------|---------|
| 功能完整度 | 最全（流量管理、安全、可观测） | 够用但不全 |
| 复杂度 | 高（需要学好几个 CRD） | 低（几分钟就能部署） |
| 资源消耗 | 较高 | 很低 |
| 适合 | 大公司、有专人维护 | 中小团队、想快速上手 |

**⚠️ 重要警告：** 服务网格不是必需品。10 个以下微服务不需要它。它解决的问题（服务间通信治理）在这些情况下根本不存在。不要把「将来可能需要」的东西现在就塞进来。

---

## 第七章：可观测性 — 出问题了能快速定位

### 7.1 三种信号：Metrics、Logs、Traces

```
一个用户请求你的网站，加载很慢。你怎么知道问题在哪？

Metrics（指标）：     "过去 5 分钟，数据库查询的 P99 延迟从 50ms 涨到了 2 秒"
                       → 告诉你「有问题」

Logs（日志）：         "[2026-05-19 14:30:01] ERROR: connection pool exhausted, 
                        waiting for connection..."
                       → 告诉你「什么问题」

Traces（链路追踪）：    "请求经过 Gateway(10ms) → Auth(30ms) → Order(50ms) → 
                        Database(1900ms)"
                       → 告诉你「问题在哪个环节」
```

三者结合，你才能在 200 个微服务里快速定位到那一个慢查询。

### 7.2 Prometheus + Grafana — 监控标配

**Prometheus 怎么工作的：**

```
┌─────────────┐       定期抓取（Pull）       ┌──────────────┐
│  你的应用     │◄──────────────────────────│  Prometheus   │
│ (暴露 /metrics│                            │  (时序数据库)  │
│  端点)        │                            │               │
└─────────────┘                             └───────┬───────┘
                                                     │ 查询
                                              ┌──────▼───────┐
                                              │   Grafana     │
                                              │ (图表 + 告警)  │
                                              └──────────────┘
```

**PromQL 入门（Prometheus 的查询语言）：**

```promql
# 过去 5 分钟，所有请求的平均速率（每秒请求数）
rate(http_requests_total[5m])

# 过去 5 分钟，99% 的请求延迟是多少秒
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# 错误率（5xx 响应占总请求的比例）
sum(rate(http_requests_total{status=~"5.."}[5m])) 
/ 
sum(rate(http_requests_total[5m]))
```

**实践建议：** 先做四个核心面板（RED 方法论）就够了，别贪多：

1. **Rate**（请求速率）— 每秒来了多少请求？
2. **Errors**（错误率）— 有多少失败的？
3. **Duration**（延迟）— 处理一个请求平均花多少时间？
4. **Resource**（资源）— CPU/内存/磁盘使用情况？

### 7.3 日志：ELK vs Loki

**ELK（Elasticsearch + Logstash + Kibana）**：
- Elasticsearch 存日志，Logstash 收集和解析，Kibana 展示。
- 功能强大但资源消耗大——ES 是个 Java 程序，吃内存。
- 适合：大公司、已有 ES 基础设施的团队。

**Loki + Grafana**：
- Grafana 家的日志方案，存储极省（不索引全文，只索引标签）。
- 查询用 LogQL，语法和 PromQL 很像。
- 适合：新项目、中小团队、不想维护 ES 的。

**选用建议：** 新项目无脑上 Loki。运维成本比 ES 低一个数量级。

### 7.4 OpenTelemetry — 一次埋点，到处可用

以前的做法：你用 AWS X-Ray SDK 埋点，数据只能看 X-Ray。换成 Datadog 要重写埋点代码。

OpenTelemetry 的标准做法：在代码里用一套 API 埋点，**导出时**配置发到哪。

```python
# 用 OpenTelemetry 埋点（和具体后端无关）
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order"):
    # 你的业务逻辑
    result = create_order(user_id, items)
    span = trace.get_current_span()
    span.set_attribute("order.id", result.id)
    span.set_attribute("order.amount", result.total)
```

然后在配置里指定导出目标：
```bash
# 你可以同时导出到 Jaeger（tracing）和 Prometheus（metrics），
# 不需要改任何代码
export OTEL_EXPORTER_OTLP_ENDPOINT="http://jaeger:4317"
```

---

## 第八章：其他你大概率会用到的组件

### 8.1 Harbor — 私有镜像仓库

**什么时候需要：**
- 不想把公司代码的镜像放在 Docker Hub 公网上
- 需要镜像安全扫描（检查有没有已知漏洞）
- 需要镜像审计日志（谁在什么时候上传/下载了什么）

Harbor 是 CNCF 毕业项目，部署简单，有 Web UI，支持 LDAP/AD 认证。

### 8.2 HashiCorp Vault — 密钥管家

**它解决了什么问题：**

```
❌ 坏做法：                                ✅ Vault 的做法：

在代码里写：                             应用启动时请求 Vault：
const DB_PWD = "abc123"                 vault read database/creds/myapp
                                        → 返回一次性临时账号密码
提交到 GitHub                            → 即使被截获，密码几分钟后自动失效
→ 全网可见
```

Vault 还能：自动轮转密码、加密即服务（应用不用知道加密细节）、生成动态云厂商凭证。

### 8.3 Ingress Controller — 流量守门人

k8s 的 Ingress 只是一个「配置对象」，真正处理流量的是 Ingress Controller。你必须部署一个它才能工作。

**两种主流选择：**

- **Nginx Ingress**：社区最大，文档最多，遇到问题一搜就有答案。稳，但配置比较「老派」。
- **Traefik**：更现代，自动发现新 Service 并生成路由，自带 Web Dashboard，自动 Let's Encrypt 证书。适合不想写太多 YAML 的。

### 8.4 Cert-Manager — 证书全自动

以前配 TLS/HTTPS 证书：
1. 去 CA 网站买证书（或申请免费 Let's Encrypt）
2. 下载证书文件
3. 上传到服务器
4. 配 Nginx
5. 设闹钟提醒自己 90 天后手动续期
6. 闹钟没响，证书过期，网站打不开

有了 Cert-Manager：
```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: myapp-tls
spec:
  secretName: myapp-tls-secret
  dnsNames:
    - myapp.com
    - www.myapp.com
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
```

提交这个 YAML 之后：自动申请 → 自动验证域名 → 自动部署到 Ingress → 自动续期。你不需要手动做任何事。

### 8.5 Velero — k8s 的「备份还原」

Velero 能把你的整个 k8s 应用（Deployment、Service、Ingress、PVC 数据……）备份到对象存储（S3/OSS），然后：

- **灾难恢复**：集群炸了，一键恢复到新集群
- **集群迁移**：从阿里云 k8s 迁移到腾讯云 k8s
- **复制环境**：把生产环境的数据脱敏后复制到测试环境

---

## 第九章：从零到一 — 不同阶段的选型方案

### 🟢 阶段一：「我刚写好第一个项目，想上线看看」

**你需要：** Docker + Docker Compose + 一个 PaaS

```
步骤：
1. 写 Dockerfile（上面第二章有模板）
2. 本地 docker compose up 确认能跑
3. 注册 Railway 或 Vercel → 连你的 GitHub 仓库
4. git push → 自动部署完成
```

**月费：** 大概率在免费额度内。超出的话每月几美元。  
**不需要学：** k8s、Helm、Terraform、服务网格。上述这些对这个阶段都是负担。

### 🟡 阶段二：「小团队，有 dev/staging/prod 三个环境」

**你需要：** 托管 k8s + Helm + GitHub Actions

```
步骤：
1. 在云厂商开一个托管 k8s 集群（ACK/EKS/GKE，选最近的区域）
2. 把应用打包成 Helm Chart
3. 用 GitHub Actions 自动化：push → build image → 部署到 dev
4. dev 验证通过 → 手动触发部署到 staging → 再到 prod
```

**月费：** 一个小集群（2-3 节点）大约 ¥500-2000/月（云厂商不同差异很大）。  
**不需要学：** 服务网格、自建 k8s、Pulumi。

### 🟠 阶段三：「20+ 个微服务，团队 20+ 人」

**你需要：** k8s + Helm/Kustomize + ArgoCD + Prometheus/Grafana + Vault

```
新增组件：
- ArgoCD：GitOps，所有环境配置从 Git 自动同步
- Prometheus/Grafana：统一监控和告警
- Vault：统一管理所有服务的密钥和证书
- Harbor：私有镜像仓库（安全合规需求）
```

**月费：** 取决于节点数和规模，通常在几千到几万/月。  
**可以开始考虑：** 服务网格（Istio/Linkerd），但不是必须的。

### 🔴 阶段四：「多集群、多区域、全球部署」

**你需要：** Terraform + 多集群 k8s + 服务网格 + OpenTelemetry + 完整合规

```
这个阶段的特点：
- 多地部署（杭州 + 新加坡 + 法兰克福），用户就近访问
- 基础设施管理不可能手动——Terraform 管理所有云资源
- 必须统一可观测（OpenTelemetry）
- 合规要求明确（数据不出境、访问审计、SOC2/等保）
```

**月费：** 💸 这个阶段不看月费了，看的是「宕机一分钟损失多少钱」。

---

## 第十章：新手常见误区

### 误区一：「技术栈越全越专业」

见过有团队 3 个人、1 个后端服务，上了 k8s + Istio + ArgoCD + Terraform + Vault + Prometheus + Grafana + Loki + Jaeger。光维护这些基础设施就花了 40% 的时间。

**真相：** 每个组件都是维护成本。选最少组件解决当前问题，不是选最多组件证明自己厉害。

### 误区二：「不上 k8s 就不专业」

k8s 是一个很好的工具，但不是所有场景都需要它。Vercel 几十亿估值，它的用户绝大多数从来不知道什么是 k8s。

**判断标准：** 你现在手工部署是不是已经应付不来了？如果不是，就不要上 k8s。

### 误区三：「单体就是落后，必须微服务」

Netflix 的 API 层（处理所有流量的那个服务）直到 2020 年代都是一个巨型单体。GitHub 的主代码库也是一个庞大的 Rails 单体。

**真相：** 单体不是问题，无法维护的单体才是。先写单体，等真的拆不动了再拆。微服务解决的是组织伸缩问题，不是技术问题。

### 误区四：「用了云厂商就等于高可用」

你在阿里云上开了一台 ECS 部署了所有服务。ECS 宕机了，你的服务还是挂了。

**真相：** 高可用不是「云厂商保证你的机器不挂」，而是「你的架构假设所有机器都会挂，所以做了冗余」。至少两台机器、跨可用区部署、健康检查、自动切换——这些都需要你自己设计。

### 误区五：「我学过一遍就等于会了」

云原生领域变化极快。2021 年的最佳实践到 2024 年可能已经是反面教材。大方向不变（容器化、自动化、可观测），但具体工具和模式一直在演进。

**建议：** 掌握原理，而不是死记命令。Docker 的隔离原理、k8s 的控制器模型、GitOps 的声明式思想——这些 10 年内不会变。`kubectl` 的具体参数可能明年就变了，但理解「声明式 API + 控制器循环」这个模式，你就能迁移到任何编排系统。

---

## 附录：常用命令速查表

### Docker
| 操作 | 命令 |
|------|------|
| 构建镜像 | `docker build -t name:tag .` |
| 运行容器 | `docker run -d -p 8080:80 --name xxx name:tag` |
| 查看运行中容器 | `docker ps` |
| 停止容器 | `docker stop xxx` |
| 删除容器 | `docker rm xxx` |
| 查看日志 | `docker logs -f xxx` |
| 进入容器 | `docker exec -it xxx sh` |
| 清理无用资源 | `docker system prune -a` |

### kubectl
| 操作 | 命令 |
|------|------|
| 查看 Pod | `kubectl get pods` |
| 查看所有资源 | `kubectl get all` |
| 应用 YAML | `kubectl apply -f xxx.yaml` |
| 删除资源 | `kubectl delete -f xxx.yaml` |
| 查看 Pod 日志 | `kubectl logs -f pod-name` |
| 进入 Pod | `kubectl exec -it pod-name -- sh` |
| 查看 Pod 详情 | `kubectl describe pod pod-name` |
| 扩缩容 | `kubectl scale deployment xxx --replicas=5` |
| 切换命名空间 | `kubectl config set-context --current --namespace=xxx` |
| 端口转发（本地调试） | `kubectl port-forward pod-name 8080:3000` |

### Helm
| 操作 | 命令 |
|------|------|
| 安装 Chart | `helm install release-name ./chart` |
| 升级 | `helm upgrade release-name ./chart` |
| 回滚 | `helm rollback release-name` |
| 查看已安装 | `helm list` |
| 卸载 | `helm uninstall release-name` |
| 搜索仓库 | `helm search repo keyword` |
