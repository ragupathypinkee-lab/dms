# AI 需求登记系统 (DMS)

基于 FastAPI 的 AI 需求登记与管理 Web 应用，支持 Session 登录、需求 CRUD、状态自动流转。使用 uv 管理依赖与运行环境。

## 功能概览

- 需求登记、列表、编辑、删除
- 按部门、优先级筛选
- 卡片统计（总数、待评估、高优先级、涉及部门）
- 需求状态一键流转
- Session 登录与角色权限控制
- Bootstrap 5 商务蓝白风格界面

## 技术栈

| 组件 | 说明 |
|------|------|
| [uv](https://docs.astral.sh/uv/) | Python 包管理与虚拟环境 |
| [FastAPI](https://fastapi.tiangolo.com/) | Web 框架 |
| [SQLite](https://www.sqlite.org/) | 嵌入式数据库 |
| [SQLAlchemy 2.x](https://www.sqlalchemy.org/) | ORM |
| [Jinja2](https://jinja.palletsprojects.com/) | 模板引擎 |
| [Bootstrap 5](https://getbootstrap.com/) | 前端 UI（CDN） |
| SessionMiddleware | Cookie Session 登录（非 JWT） |

## 环境要求

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## 快速开始

### 1. 克隆并安装依赖

```bash
uv sync
```

安装开发依赖（pytest、ruff）：

```bash
uv sync --group dev
```

### 2. 配置环境变量（可选）

在项目根目录创建 `.env` 文件：

```env
APP_NAME=AI需求登记系统
DEBUG=true
SECRET_KEY=请替换为随机字符串
DATABASE_URL=sqlite:///./dms.db

# AI 相关（可选，后续 ai.py 使用）
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-api-endpoint/v1
OPENAI_MODEL=your-model
```

> 生产环境务必修改 `SECRET_KEY`，不要使用默认值。

### 3. 启动服务

开发模式（推荐，支持热重载）：

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

生产模式：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. 访问地址

| 地址 | 说明 |
|------|------|
| <http://127.0.0.1:8000/> | 首页（自动跳转需求列表，未登录则跳转登录页） |
| <http://127.0.0.1:8000/auth/login> | 登录页 |
| <http://127.0.0.1:8000/demand/list> | 需求列表 |
| <http://127.0.0.1:8000/demand/create> | 登记需求 |
| <http://127.0.0.1:8000/health> | 健康检查 |
| <http://127.0.0.1:8000/docs> | Swagger API 文档 |

首次启动会自动创建 SQLite 数据库 `dms.db`，并初始化数据表与默认用户。

## 默认账号

系统启动时自动写入以下账号（密码明文仅用于初始登录，数据库中存储哈希值）：

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| `admin` | `admin` | 管理员 | 全部需求的查看、编辑、删除、状态流转 |
| `user` | `user` | 普通用户 | 查看全部需求；仅可编辑/删除/流转自己创建的需求 |

登录页：<http://127.0.0.1:8000/auth/login>

退出登录：`/auth/logout`

## 权限说明

| 操作 | 管理员 (admin) | 普通用户 (user) |
|------|----------------|-----------------|
| 查看需求列表 | ✅ 全部 | ✅ 仅自己的需求 |
| 登记需求 | ✅ | ✅（创建人固定为当前用户名） |
| 编辑需求 | ✅ 全部 | ✅ 仅自己的需求 |
| 删除需求 | ✅ 全部 | ✅ 仅自己的需求 |
| 状态流转 | ✅ 全部 | ✅ 仅自己的需求 |

未登录访问 `/demand/*` 会自动跳转到登录页。

## 需求状态流转

需求状态可在列表页或编辑页自由切换，可选值：

```
待评估 · 分析中 · 开发中 · 测试中 · 已完成
```

更新接口：`POST /demand/status/{id}`（表单字段 `status`）

## 路由一览

### 认证 `/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/auth/login` | 登录页 |
| POST | `/auth/login` | 提交登录 |
| GET | `/auth/logout` | 退出登录 |

### 需求 `/demand`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/demand/` | 跳转列表 |
| GET | `/demand/list` | 需求列表（支持 `?department=&priority=` 筛选） |
| GET | `/demand/create` | 创建表单 |
| POST | `/demand/create` | 提交创建 |
| GET | `/demand/edit/{id}` | 编辑表单 |
| POST | `/demand/edit/{id}` | 提交更新 |
| POST | `/demand/status/{id}` | 更新需求状态（任意状态） |
| POST | `/demand/delete/{id}` | 删除需求 |

## 数据模型

### users 用户表

| 字段 | 说明 |
|------|------|
| id | 主键 |
| username | 用户名（唯一） |
| password_hash | 密码哈希 |
| role | 角色：`admin` / `user` |
| created_at | 创建时间 |

### demands 需求表

| 字段 | 说明 |
|------|------|
| id | 主键 |
| title | 需求标题 |
| description | 需求描述 |
| department | 所属部门 |
| priority | 优先级：`high` / `medium` / `low` |
| status | 状态：`evaluating` / `analyzing` / `developing` / `testing` / `completed` |
| creator | 创建人 |
| ai_analysis | AI 分析结果（可选） |
| created_at | 创建时间 |
| updated_at | 更新时间 |

## 目录结构

```
dms/
├── app/                          # 应用主包
│   ├── main.py                   # FastAPI 入口、中间件、路由挂载
│   ├── api/                      # API 层
│   │   ├── deps.py               # 依赖注入（登录、权限）
│   │   └── v1/
│   │       ├── router.py         # v1 路由聚合
│   │       └── endpoints/        # 业务端点
│   │           ├── auth.py       # 认证
│   │           ├── demand.py     # 需求 CRUD / AI 分析
│   │           └── user.py       # 用户管理 / 改密
│   ├── core/                     # 核心配置
│   │   ├── config.py             # 应用配置（.env）
│   │   └── security.py           # 密码哈希
│   ├── db/                       # 数据库层
│   │   ├── base.py               # SQLAlchemy Base
│   │   └── session.py            # 连接、Session、初始化
│   ├── models/                   # ORM 模型
│   │   ├── user.py
│   │   └── demand.py
│   ├── services/                 # 业务服务
│   │   └── ai.py                 # AI 分析
│   ├── utils/                    # 工具模块
│   │   ├── messages.py           # Flash 消息
│   │   └── status.py             # 需求状态定义
│   └── web/                      # Web 呈现层
│       ├── templating.py         # Jinja2 引擎
│       ├── templates/            # HTML 模板
│       └── static/               # 静态资源（CSS / JS）
├── scripts/
│   └── seed_demo.py              # 演示数据写入脚本
├── tests/                        # 测试
├── pyproject.toml
├── uv.lock
├── .env                          # 环境变量（本地，勿提交密钥）
└── dms.db                        # SQLite 数据库（启动后生成）
```

写入演示数据：

```bash
uv run python scripts/seed_demo.py
```

## 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | `AI需求登记系统` | 应用名称 |
| `DEBUG` | `true` | 调试模式（开启 SQL 日志） |
| `SECRET_KEY` | `change-me-in-production` | Session 签名密钥 |
| `DATABASE_URL` | `sqlite:///./dms.db` | 数据库连接地址 |

## 常见问题

**访问页面返回 `{"detail":"Not Found"}`**

通常是旧进程未加载最新路由。请重启服务，开发时建议始终使用 `--reload`：

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**端口被占用**

```bash
lsof -i :8000
kill <PID>
```

**重置数据库**

删除 `dms.db` 后重启服务，会自动重建表结构和默认账号。

## 开发

运行测试：

```bash
uv run pytest
```

代码检查：

```bash
uv run ruff check .
```
