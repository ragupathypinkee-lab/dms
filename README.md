# 需求管理系统 (DMS)

基于 FastAPI 的需求管理系统，使用 uv 管理依赖与运行环境。

## 技术栈

| 组件 | 说明 |
|------|------|
| [uv](https://docs.astral.sh/uv/) | Python 包管理与虚拟环境 |
| [FastAPI](https://fastapi.tiangolo.com/) | Web 框架 |
| [SQLite](https://www.sqlite.org/) | 嵌入式数据库 |
| [SQLAlchemy](https://www.sqlalchemy.org/) | ORM |
| [Jinja2](https://jinja.palletsprojects.com/) | 模板引擎 |
| [Bootstrap 5](https://getbootstrap.com/) | 前端 UI 框架（CDN 引用） |

## 环境要求

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

安装开发依赖（pytest、ruff 等）：

```bash
uv sync --group dev
```

### 2. 启动服务

开发模式（热重载）：

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

生产模式：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后访问：

- API 根路径：<http://127.0.0.1:8000/>
- 健康检查：<http://127.0.0.1:8000/health>
- 交互式文档：<http://127.0.0.1:8000/docs>
- ReDoc 文档：<http://127.0.0.1:8000/redoc>

应用启动时会自动初始化 SQLite 数据库，默认在项目根目录生成 `dms.db`。

## 目录结构

```
dms/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 入口，挂载静态资源 / Jinja2 / 路由
│   ├── config.py        # 应用配置（pydantic-settings）
│   ├── database.py      # SQLAlchemy engine、Session、数据库初始化
│   ├── models.py        # ORM 模型
│   ├── schemas.py       # Pydantic 请求/响应模型
│   ├── crud.py          # 数据库 CRUD 操作
│   ├── ai.py            # AI 相关逻辑
│   ├── routers/         # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py      # 认证路由（/auth）
│   │   └── demand.py    # 需求路由（/demand）
│   ├── templates/       # Jinja2 模板
│   └── static/          # 静态资源（CSS、JS、图片等）
├── pyproject.toml       # 项目配置与依赖
├── uv.lock              # 依赖锁定文件
└── dms.db               # SQLite 数据库（启动后自动生成，已 gitignore）
```

## 配置

配置通过 `app/config.py` 管理，支持在项目根目录创建 `.env` 文件覆盖默认值：

```env
APP_NAME=DMS
DEBUG=true
DATABASE_URL=sqlite:///./dms.db
```

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | `DMS` | 应用名称 |
| `DEBUG` | `true` | 调试模式 |
| `DATABASE_URL` | `sqlite:///./dms.db` | 数据库连接地址 |

Bootstrap 5 的 CDN 地址也在 `config.py` 中定义，后续在 Jinja2 模板中引用即可：

- `settings.bootstrap_css`
- `settings.bootstrap_js`

## 开发

运行测试：

```bash
uv run pytest
```

代码检查：

```bash
uv run ruff check .
```
