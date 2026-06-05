# myStu API

基于 [FastAPI](https://fastapi.tiangolo.com/) 的 Python Web API 基础框架，采用分层目录与统一响应格式，便于后续扩展业务接口。

## 环境要求

- Python 3.11+（本地开发）
- Docker & Docker Compose（容器部署）
- 推荐使用项目内虚拟环境 `.venv`

## 快速开始

### 本地开发

```bash
# 创建并激活虚拟环境（若尚未创建）
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
cp .env.example .env

# 启动服务
python main.py
```

也可直接使用 uvicorn（需先 `export $(grep -v '^#' .env | xargs)` 或自行传入环境变量）：

```bash
uvicorn app.main:app --reload --host $HOST --port $PORT
```

服务监听地址由 `.env` 中 `HOST`、`PORT` 决定，默认 `http://127.0.0.1:8000`。

### Docker 部署

```bash
# 复制环境变量配置（首次部署）
cp .env.example .env

# 构建并启动（后台运行）
docker compose up -d --build

# 查看日志
docker compose logs -f api

# 停止服务
docker compose down
```

容器会读取 `.env` 中的 `HOST`、`PORT` 等配置；端口映射同样由 `PORT` 决定，修改后需重新执行 `docker compose up -d`。

仅使用 Docker（不通过 Compose）时：

```bash
docker build -t mystu-api .
docker run -d --name mystu-api --env-file .env -p ${PORT}:${PORT} mystu-api
```

> 修改代码后必须**完全停止**旧进程再启动。若仍看到 `code, message, data` 或根路径只有 `{"message":...}`，说明 8000 端口上还在跑旧服务。可先执行：`lsof -iTCP:8000 -sTCP:LISTEN` 查 PID，再 `kill <PID>`。

## 项目结构

```
myStu/
├── main.py                 # 启动入口
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
└── app/
    ├── main.py             # 应用工厂 create_app()
    ├── config.py           # 配置（pydantic-settings）
    ├── api/v1/
    │   ├── router.py       # v1 路由聚合
    │   └── endpoints/      # 具体接口
    ├── core/
    │   ├── exceptions.py   # 业务异常
    │   └── db_handlers.py  # 数据库异常
    ├── db/
    │   ├── database.py     # Database 组件（连接池、反射表）
    │   ├── deps.py         # get_db / UserRepo 依赖注入
    │   ├── tables.py       # 表名常量
    │   └── repositories/   # 数据访问层
    └── schemas/
        └── common.py       # 统一响应模型 ApiResponse
```

## 配置说明

**所有配置均从 `.env` 读取**，代码中不设默认值。启动前请复制并修改：

```bash
cp .env.example .env
```

| 变量 | 说明 |
|------|------|
| `APP_NAME` | 应用名称 |
| `APP_VERSION` | 版本号 |
| `DEBUG` | 调试模式（影响热重载、SQL 日志） |
| `HOST` | 监听地址 |
| `PORT` | 监听端口 |
| `API_PREFIX` | API 路径前缀 |
| `CORS_ORIGINS` | 跨域来源（JSON 数组，如 `["*"]`） |
| `DB_DRIVER` | 数据库驱动，如 `mysql+aiomysql` |
| `DB_HOST` | 数据库主机 |
| `DB_PORT` | 数据库端口 |
| `DB_USER` | 数据库用户名 |
| `DB_PASSWORD` | 数据库密码 |
| `DB_NAME` | 数据库名 |

数据库连接串由上述 `DB_*` 变量自动拼接，无需单独配置 `DATABASE_URL`。

业务表名在代码中维护（见 `app/db/tables.py`），如用户表 `c_users`、业务表前缀 `c_`。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 欢迎信息（统一响应格式） |
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/users/1` | 测试：查询 `c_users` 中 id=1 的用户 |

所有接口（含参数校验失败、HTTP 异常）均返回 `code` → `data` → `message` 顺序的 JSON。

### 响应格式

业务接口统一使用 `ApiResponse`：

```json
{
  "code": 0,
  "data": { },
  "message": "ok"
}
```

- `code`: 业务状态码，`0` 表示成功
- `data`: 业务数据，可为 `null`
- `message`: 提示信息

## 交互式文档

启动服务后访问：

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 扩展新接口

1. 在 `app/api/v1/endpoints/` 下新增路由模块，例如 `users.py`：

```python
from fastapi import APIRouter
from app.schemas.common import ApiResponse

router = APIRouter(tags=["users"])

@router.get("/users")
async def list_users() -> ApiResponse[list]:
    return success(data=[])
```

2. 在 `app/api/v1/router.py` 中注册：

```python
from app.api.v1.endpoints import health, users

api_router.include_router(users.router)
```

3. 需要查库时，在 `app/db/repositories/` 新增 Repository，在 `app/db/deps.py` 注册依赖，接口中注入使用：

```python
from app.db.deps import UserRepo

@router.get("/users/1")
async def get_user(repo: UserRepo):
    user = await repo.get_by_id(1)
    ...
```

## 业务异常

抛出 `AppException` 会由全局处理器转换为统一 JSON 响应：

```python
from app.core.exceptions import AppException

raise AppException("资源不存在", code=404)
```

## 依赖

- [FastAPI](https://fastapi.tiangolo.com/) — Web 框架
- [Uvicorn](https://www.uvicorn.org/) — ASGI 服务器
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — 配置管理
