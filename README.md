# 智慧医疗问诊平台

基于 Vue 3、Flask 和 RAG（检索增强生成）的毕业设计项目，集患者信息管理、电子病历管理和医疗知识库问答于一体。系统支持电脑与手机浏览器访问，可通过 Docker Compose 部署，也可在本机分别启动前后端。

## 主要功能

| 模块 | 已实现功能 |
| --- | --- |
| 账号与登录 | 用户登录、JWT 身份认证、修改密码、管理员密码重设 |
| 首页统计 | 患者数量、病历数量、当日新增病历数量、知识片段数量 |
| 患者管理 | 患者列表、新增、删除；自动生成编号、重复编号校验、关联病历删除保护 |
| 病历管理 | 病历列表、新增、删除；患者关联校验、历史缺失关联提示 |
| 知识库 | 粘贴文本或上传 TXT、MD、JSON、CSV、文本型 PDF；分块、向量化与去重 |
| AI 问答 | 检索知识片段后生成单轮回答，并展示资料来源 |
| 运维 | 健康检查、数据备份、部署验证、AI 连通性检查和自动化测试 |

当前未实现患者与病历编辑、分页、用户注册和会话历史保存。项目用于毕业设计与功能演示，医疗问答结果仅供参考，不能替代医生诊断。

## 技术方案

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、Vite、Element Plus、Vue Router、Axios |
| 后端 | Python 3.11、Flask、Flask-SQLAlchemy、PyJWT、Waitress |
| 业务数据库 | MySQL 8.0 |
| 知识检索 | LangChain 组件、Chroma 本地持久化向量库 |
| 向量模型 | DashScope `text-embedding-v3`，使用 OpenAI 兼容接口 |
| 对话模型 | DeepSeek `deepseek-chat`，使用 OpenAI 兼容接口 |
| 部署与测试 | Docker Compose、Python unittest、Node.js test、Playwright |

问答流程：导入资料 → 文本分块 → 向量化并保存至 Chroma → 检索相关片段 → 模型结合资料生成回答与来源。

## 项目目录

```text
.
├── README.md                  # 项目介绍与使用入口
├── backend/                   # Flask 后端
│   ├── app.py                 # 应用工厂、本机启动入口
│   ├── config/                # 配置、数据库连接与约束维护
│   ├── controller/            # HTTP 接口
│   ├── service/               # 业务逻辑
│   ├── model/                 # 数据模型
│   ├── rag/                   # 向量检索与问答链
│   ├── utils/                 # 鉴权、密码、校验等工具
│   └── chroma_db/             # 本机知识库数据（不提交）
├── frontend/                  # Vue 前端
│   ├── src/                   # 页面、组件、路由与接口调用
│   ├── public/                # 公共静态资源
│   ├── tests/                 # 前端单元测试与浏览器测试
│   ├── dist/                  # 构建产物，本机后端提供页面时使用
│   └── package.json           # 前端依赖与运行命令
├── deploy/                    # 启动、备份、重设密码和诊断脚本
├── tests/                     # 后端与部署测试
├── docs/                      # 部署说明、技术文档与历史检查报告
├── backups/                   # 本机备份（不提交）
├── instance/                  # 本机 JWT 签名密钥等运行数据（不提交）
├── .env.example               # 环境变量模板
├── requirements.txt           # 后端依赖
├── requirements-docker.txt    # 后端依赖及 Waitress
├── Dockerfile                 # 多阶段镜像构建
└── compose.yaml               # 应用、MySQL 与持久化卷配置
```

本机 `.env`、虚拟环境、`node_modules`、数据库、备份和测试产物不纳入 Git。`frontend/dist` 可通过 `npm run build` 重新生成；本机直接从后端访问页面时需要保留或先构建它。Docker 会在镜像构建阶段生成前端文件。

## 快速启动：Docker

准备 Docker Desktop，启用 Linux 容器并等待引擎就绪。在项目根目录打开 PowerShell：

```powershell
# 首次配置时复制模板；已有 .env 时保留现有配置。
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
docker compose up -d --build --wait --wait-timeout 240
```

默认访问地址：<http://localhost:8080>。健康检查：<http://localhost:8080/api/health>。

全新 Docker 数据库默认创建管理员 `admin`，初始密码为 `Admin123456`；首次部署前可在 `.env` 中修改 `DOCKER_ADMIN_USERNAME` 与 `DOCKER_ADMIN_PASSWORD`，登录后也可通过右上角修改密码。初始化变量不会覆盖已有账号的密码。

常用命令：

```powershell
docker compose ps
docker compose logs --tail=100 app
docker compose restart app
docker compose down
```

`docker compose down` 保留数据卷；添加 `-v` 会删除数据库、知识库和签名密钥卷。修改代码后重新构建，修改 `.env` 后执行 `docker compose up -d` 以加载配置。

## 本机开发

准备 Python 3.11、Node.js 22 和 MySQL 8.0；创建 UTF-8 数据库 `smart_medical`，按 `.env.example` 配置本机数据库连接。

在项目根目录的 PowerShell 中启动后端：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-docker.txt
$env:BOOTSTRAP_ADMIN_USERNAME = 'admin'
$initialPassword = Read-Host '首次创建管理员的密码' -AsSecureString
$env:BOOTSTRAP_ADMIN_PASSWORD = [System.Net.NetworkCredential]::new('', $initialPassword).Password
.\.venv\Scripts\python.exe -m deploy.start
```

已有虚拟环境时可跳过创建步骤。管理员初始化仅创建缺失账号；环境准备完成后，日常启动执行最后一行即可。后端默认监听 `5000` 端口。

另开一个 PowerShell 窗口，在项目根目录执行：

```powershell
Set-Location frontend
npm ci
npm run dev
```

访问 <http://localhost:5173>，开发服务器将 `/api` 请求代理到后端。若需直接从后端访问前端页面，先在 `frontend` 目录执行 `npm run build`，再访问 <http://localhost:5000>。

## AI 配置与数据保存

在根目录 `.env` 中填写 `DASHSCOPE_API_KEY` 和 `DEEPSEEK_API_KEY`；自定义服务地址分别使用 `DASHSCOPE_BASE_URL` 和 `DEEPSEEK_BASE_URL`。没有 AI 密钥时，登录、患者和病历功能仍可使用。请勿提交含实际密钥的 `.env`。

本机业务数据保存在 `.env` 指定的 MySQL 中，知识库存放于 `backend/chroma_db/`，自动生成的签名密钥存放于 `instance/`。Docker 使用独立的 `mysql_data`、`chroma_data` 和 `instance_data` 命名卷，不会自动导入本机旧数据。

## 测试与维护

后端回归测试使用独立测试数据库，前端浏览器测试使用独立测试目录。安装依赖后，在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Set-Location frontend
npm test
npm run build
npm run test:e2e
```

浏览器测试按当前配置使用 Microsoft Edge 和根目录 `.venv`。Docker 数据备份及密码维护命令（项目根目录执行）：

```powershell
.\.venv\Scripts\python.exe deploy/backup.py
docker compose exec app python -m deploy.reset_password admin
```

本机账号重设密码使用 `.\.venv\Scripts\python.exe -m deploy.reset_password admin`。更多操作、上传限制、接口说明和部署边界见以下文档。

## 详细文档

- [部署与启动](docs/部署与启动.md)：环境变量、手机访问、日志、备份与回归命令。
- [技术文档](docs/智慧医疗平台技术文档.md)：架构、接口、数据约束、鉴权与 RAG 实现。
- [系统检查与修复报告](docs/系统检查与修复报告.md)：2026-10-16 的检查记录与已知限制，属于历史记录，不代表当前服务状态。
