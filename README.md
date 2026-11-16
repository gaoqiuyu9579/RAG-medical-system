# 智慧医疗问诊平台

基于 Vue 3、Flask、MySQL 和 Chroma 的 RAG 医疗系统，提供患者管理、电子病历、医学知识库、流式 AI 问诊和数据统计分析。支持电脑与手机浏览器。

## 启动项目

安装并打开 **Docker Desktop**，使用 Linux 容器，等待引擎就绪。在 PowerShell 中执行：

```powershell
Set-Location 'E:\Thesis\thesis medical'
.\start.ps1
```

脚本会创建缺失的 `.env`、构建最新前后端、启动 MySQL 和应用，并等待健康检查通过。正常部署默认访问 **[http://localhost:8081](http://localhost:8081)**；若在 `.env` 中设置了 `DOCKER_HTTP_PORT`，以脚本输出的 `Ready:` 地址为准。Docker 模式只需启动这一套服务。

全新数据库的初始账号为 `admin`，密码为 `Admin123456`；已有数据库继续使用原账号密码。可在 `.env` 设置 `DOCKER_ADMIN_USERNAME`、`DOCKER_ADMIN_PASSWORD`，初始化变量只创建缺失账号。登录后可在右上角修改密码。

如果 PowerShell 提示禁止运行脚本，可只对本次执行使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

### 使用拟真演示数据

```powershell
.\start.ps1 -Demo
```

访问 **[http://localhost:8081](http://localhost:8081)**，初始账号 `admin`，密码 `Admin123456`。演示模式使用独立的 `smart-medical-demo` Compose 项目和数据卷，首次空库预置 **12 位患者、56 份近 30 天随访病历**，包含张某某、65 岁、高血压既往史等合成档案。之后的操作会保存在该演示数据卷中。

| 操作 | 正常部署 | 独立演示 |
| --- | --- | --- |
| 启动 / 同步最新代码 | `.\start.ps1` | `.\start.ps1 -Demo` |
| 查看状态 | `.\start.ps1 status` | `.\start.ps1 status -Demo` |
| 查看应用日志 | `.\start.ps1 logs` | `.\start.ps1 logs -Demo` |
| 停止服务，保留数据 | `.\start.ps1 stop` | `.\start.ps1 stop -Demo` |

脚本基于 `docker compose up -d --build --wait --wait-timeout 240`。代码更新后重新运行启动命令即可；首次构建需要联网。`docker compose down` 保留数据卷，添加 `-v` 会删除数据卷。

## AI 配置与数据保存

编辑项目根目录 `.env`：

| 配置 | 用途 |
| --- | --- |
| `DEEPSEEK_API_KEY` | 对话模型 `deepseek-chat` 的密钥 |
| `DASHSCOPE_API_KEY` | 向量模型 `text-embedding-v3` 的密钥 |
| `DEEPSEEK_BASE_URL` / `DASHSCOPE_BASE_URL` | 对应服务的 OpenAI 兼容接口地址 |
| `DOCKER_HTTP_PORT` | 正常部署的网页端口，默认 `8080` |
| `DOCKER_MYSQL_*` | Docker 内数据库初始化配置 |
| `DOCKER_SEED_DEMO_DATA` | 正常部署是否向空库导入合成资料，默认 `0`；`-Demo` 自动启用 |

修改配置后重新运行启动命令。未配置 AI 密钥时，登录、患者、病历与统计功能仍可使用。使用 AI 问诊前，先在问诊页上传医学资料。

MySQL、知识库和 JWT 签名密钥分别保存在 Docker 命名卷中，重建应用镜像会沿用数据。正常部署和演示部署的数据相互独立。项目仅用于教学演示，AI 回答不能替代医生诊断。

## 已实现功能

| 模块 | 功能 |
| --- | --- |
| 账号 | 登录、JWT 鉴权、修改密码、管理员密码重设 |
| 患者 / 病历 | 新增、编辑、删除确认、30 秒撤销、关联病历删除保护 |
| 患者查询 | 患者管理页提供查询、重置、性别及年龄筛选、分页和详情；电子病历页可直接进入患者查询，见[接口文档](docs/患者查询接口.md) |
| 操作反馈 | 保存 loading 与绿色对勾、原行高亮渐隐、失败行内提示和重试 |
| 表单 | 必填红边、抖动、行内提示、首个错误项自动聚焦 |
| 知识库 | 文本及 TXT / MD / JSON / CSV / 文本型 PDF；分阶段进度、去重、侧栏状态、站内切页后继续处理 |
| AI 问诊 | SSE 流式逐字回答、思考三点动画、禁用重复发送、失败气泡和重试、原文引用展开及匹配高亮 |
| 统计分析 | ECharts 患者年龄分布、近 7 / 30 / 90 天病历趋势，按数据库记录汇总 |
| 运维 | 健康检查、备份、部署同步验证和自动化测试 |

## 患者查询接口

提供本系统患者档案查询，适用于按姓名查找、按编号或电话定位患者，以及按性别、年龄范围筛选。接口沿用 JWT 登录鉴权，请求头需携带 `Authorization: Bearer <token>`。

登录后进入“患者管理”，页面上方的“患者查询”区域可输入姓名、完整患者编号或电话，选择性别、年龄范围后点击“查询”（或按 Enter）；“重置”恢复全部患者。列表底部可翻页、切换每页条数；每行的查看按钮展示地址和既往病史等完整档案。“电子病历”页右上角的“查询患者”按钮也可进入此页面。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/patient/search` | 多条件分页查询，返回患者基本识别信息 |
| GET | `/api/patient/detail/<id>` | 按选中患者的系统 ID 获取完整档案 |
| GET | `/api/patient/list` | 兼容现有页面的全量患者列表 |

查询参数支持 `keyword`、`name`、`patient_no`、`phone`、`gender`、`age_min`、`age_max`、`page`、`page_size`。姓名采用包含匹配，患者编号和电话采用完整匹配；不同筛选条件同时生效。默认每页 20 条，最多 100 条，年龄范围为 0～150 岁。

例如，查询姓名包含“张”的 60～80 岁男性患者：

```http
GET /api/patient/search?name=%E5%BC%A0&gender=%E7%94%B7&age_min=60&age_max=80&page=1&page_size=20
Authorization: Bearer <token>
```

成功响应的 `data` 包含 `items`、`total`、`page`、`page_size`、`pages`。查询列表保留患者 `id` 和 `patient_no`，便于区分同名患者；地址和既往病史通过详情接口获取。参数错误返回 HTTP 400，未登录或登录失效返回 HTTP 401，患者不存在返回 HTTP 404。

患者管理页面使用 `searchPatients(params)` 查询分页列表，查看详情和打开编辑表单时使用 `getPatientDetail(id)` 读取完整档案。保存、删除或撤销后按当前筛选条件刷新结果。本次接口读取本系统档案，尚未对接医院 HIS/EMR。完整参数、响应和 PowerShell 调用示例见[患者查询接口文档](docs/患者查询接口.md)。修改代码后重新执行启动命令，即可将接口更新到 Docker 服务。

## 目录说明

```text
thesis medical/
├── start.ps1                 # 日常入口：启动、状态、日志、停止
├── README.md                 # 项目介绍与快速启动
├── compose.yaml              # MySQL、应用与持久化卷
├── Dockerfile                # 构建前端和 Python 运行镜像
├── .env.example              # 配置模板；实际配置在本机 .env
├── backend/                  # Flask 接口、业务服务、数据模型与 RAG
├── frontend/                 # Vue 页面、组件、接口与浏览器测试
├── deploy/                   # 服务入口、演示数据、备份和部署诊断
├── tests/                    # 后端与部署回归测试
├── scripts/                  # 本机演示及已有交付材料的重建工具
├── docs/                     # 部署说明、技术文档、验收和整理记录
├── output/                   # 最终交付：pdf/、presentation/、video/
├── backups/                  # 本机数据备份，不提交 Git
├── instance/                 # 本机签名密钥，不提交 Git
└── requirements*.txt         # 应用、开发和交付工具依赖
```

`.venv/`、`frontend/node_modules/` 是本机开发依赖，`frontend/dist/` 是本机构建产物。测试临时目录、缓存和视频中间素材可以重新生成。整理规则及本次清理记录见 [目录整理与部署同步](docs/目录整理与部署同步.md)。

## 开发与测试

日常运行使用上面的 Docker 入口。需要修改代码并实时预览时，安装 Python 3.11、Node.js 22 和 MySQL 8.0，按 [详细部署说明](docs/部署与启动.md) 分别启动后端与前端。

常用验证命令在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m deploy.verify_deployment --restart
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

部署验证会核对容器内 Python 源码与本机是否一致，并检查统计接口、网页资源、鉴权与重启后的会话。独立演示的验证命令：

```powershell
.\.venv\Scripts\python.exe -m deploy.verify_deployment --project smart-medical-demo --url http://127.0.0.1:8081
```

备份正常 Docker 数据：`.\.venv\Scripts\python.exe deploy/backup.py`。忘记正常部署的管理员密码时，执行 `docker compose exec app python -m deploy.reset_password admin`，按提示输入新密码。

## 文档与交付

- [部署与启动](docs/部署与启动.md)：开发启动、配置、手机访问、日志和备份。
- [患者查询接口](docs/患者查询接口.md)：查询参数、分页响应、患者详情、鉴权与调用示例。
- [交互反馈改进与验收](docs/交互反馈改进与验收.md)：交互改进、统计分析和测试结果。
- [目录整理与部署同步](docs/目录整理与部署同步.md)：清理内容和 Docker 验证记录。
- [技术文档](docs/智慧医疗平台技术文档.md)、[评审源稿](docs/评审技术文档.md)、[交付检查清单](docs/交付检查清单.md)。
- [技术 PDF](output/pdf/智慧医疗系统技术文档.pdf)、[已有演示视频](output/video/智慧医疗系统演示.mp4)；汇报 PPT 位于 `output/presentation/`。
- [演示材料复现](docs/演示视频与复现.md)、[历史验收](docs/验收测试报告.md)、[历史检查](docs/系统检查与修复报告.md)。

代码仓库：[gaoqiuyu9579/RAG-medical-system](https://github.com/gaoqiuyu9579/RAG-medical-system)。本次不制作新视频。

## 团队

项目负责人：**高秋雨**。成员：高秋雨、栾子璇、郝崇泽。

| 成员 | 分工 |
| --- | --- |
| 高秋雨（负责人） | 需求分析、总体架构、后端与数据库、部署与版本管理、论文和核心技术文档、进度统筹 |
| 郝崇泽 | 前端页面、组件封装、页面样式与接口联调 |
| 栾子璇 | 功能与回归测试、Bug 记录、用户手册和素材整理 |
