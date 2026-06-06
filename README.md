# simonFastAPI API

基于 [FastAPI](https://fastapi.tiangolo.com/) 的 Python Web API 框架，采用 **MVC 分层**、统一响应格式、异步 MySQL、Redis 缓存与 JWT 鉴权，便于扩展业务接口。

## 环境要求

- Python 3.11+（本地开发）
- MySQL 5.7+ / 8.0+
- Redis 6+
- Docker & Docker Compose（可选，容器部署）
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
# 编辑 .env，填写数据库、Redis、JWT 等配置

# 启动服务
python main.py
# 或
./start.sh
```

也可直接使用 uvicorn（需先加载 `.env` 环境变量）：

```bash
uvicorn app.main:app --reload --host $HOST --port $PORT
```

服务监听地址由 `.env` 中 `HOST`、`PORT` 决定，默认 `http://127.0.0.1:8000`。

### Docker 部署

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f api
docker compose down
```

> 修改代码后需**完全停止**旧进程再启动。若响应格式或路由异常，可先查端口占用：`lsof -iTCP:8000 -sTCP:LISTEN`

## 项目结构（MVC）

```
myStu/
├── main.py                      # 启动入口
├── start.sh                     # 启动脚本（检测端口占用）
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── scripts/
│   ├── hash_password.py         # 生成 bcrypt 密码哈希
│   ├── test_db.py               # 数据库连接测试
│   └── test_redis.py            # Redis 连接测试
└── app/
    ├── main.py                  # 应用工厂 create_app()
    ├── config.py                # 配置（pydantic-settings，全部来自 .env）
    │
    ├── controllers/v1/          # C 控制器 — HTTP 入参 / ApiResponse 出参
    │   ├── router.py            # v1 路由聚合
    │   ├── auth.py              # 登录 / 登出 / 鉴权示例
    │   ├── users.py             # 用户接口
    │   ├── demo.py              # 并发查库示例（多线程 / asyncio）
    │   ├── health.py            # 健康检查
    │   └── redis_demo.py        # Redis 示例接口
    │
    ├── services/                # 业务逻辑层
    │   ├── auth_service.py      # 登录、JWT 验签、登出
    │   ├── user_service.py      # 用户查询、缓存、更新
    │   ├── concurrent_service.py # 多线程 / asyncio 并行查库
    │   └── deps.py              # Service 依赖注入
    │
    ├── db/
    │   ├── database.py          # 异步连接池（aiomysql）
    │   ├── sync_database.py     # 同步连接池（pymysql，供线程池使用）
    │   ├── deps.py              # DbSession / UserRepo 注入
    │   ├── models/              # M 数据模型（ORM，一表一 Model）
    │   │   └── users.py
    │   ├── repositories/        # 数据访问（Repository）
    │   │   ├── base.py          # BaseRepository
    │   │   └── user.py
    │   └── field_query.py       # 按字段查询
    │
    ├── schemas/                 # V 入参 / 出参 DTO
    │   ├── common.py            # ApiResponse、success()
    │   ├── auth.py              # LoginRequest、TokenData
    │   ├── user.py              # UserUpdate
    │   ├── query.py             # 分页、fields、lookup 参数
    │   └── pagination.py
    │
    ├── auth/
    │   └── deps.py              # CurrentUser / OptionalUser 鉴权依赖
    │
    ├── core/
    │   ├── security.py          # JWT 签发/解析、bcrypt 密码
    │   ├── exceptions.py        # AppException
    │   ├── logging.py           # 日志（控制台 + 轮转文件）
    │   └── db_handlers.py
    │
    ├── redis/
    │   ├── client.py            # Redis 连接
    │   ├── operations.py        # RedisOps 命令封装
    │   ├── keys.py              # 缓存 key 命名
    │   └── deps.py              # RedisCacheDep
    │
    └── middleware/
        └── api_response.py      # 统一 JSON 字段顺序 code → data → message
```

### 分层职责

| 层 | 目录 | 职责 |
|----|------|------|
| **Controller (C)** | `controllers/v1/` | 解析 HTTP 参数，调用 Service，封装 `success()` 出参 |
| **Service** | `services/` | 业务逻辑：校验、缓存、组合 Repository |
| **Model (M)** | `db/models/` | SQLAlchemy ORM 表结构 |
| **Repository** | `db/repositories/` | 数据访问：CRUD、分页、按字段查询 |
| **View (V)** | `schemas/` | Request / Response 数据结构 |

**请求链路：**

```
HTTP → Controller → Service → Repository → MySQL
                      ↓
                    Redis（缓存 / Token 会话）
```

## 配置说明

**所有配置均从 `.env` 读取**，代码中不设默认值。启动前请：

```bash
cp .env.example .env
```

| 变量 | 说明 |
|------|------|
| `APP_NAME` | 应用名称 |
| `APP_VERSION` | 版本号 |
| `DEBUG` | 调试模式（影响 SQL 日志等） |
| `HOST` / `PORT` | 监听地址与端口 |
| `API_PREFIX` | API 路径前缀，默认 `/api/v1` |
| `CORS_ORIGINS` | 跨域来源（JSON 数组，如 `["*"]`） |
| `DB_DRIVER` | 数据库驱动，如 `mysql+aiomysql` |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MySQL 连接 |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` / `REDIS_DB` | Redis 连接 |
| `REDIS_CACHE_TTL` | 用户缓存默认过期秒数 |
| `LOG_DIR` / `LOG_LEVEL` / `LOG_FILE` | 日志目录、级别、文件名 |
| `JWT_SECRET_KEY` | JWT 签名密钥（生产环境请使用足够长的随机字符串） |
| `JWT_ALGORITHM` | JWT 算法，默认 `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token 有效分钟数 |

数据库连接串由 `DB_*` 变量自动拼接；Redis URL 由 `REDIS_*` 自动拼接。

用户表 ORM：`app/db/models/users.py`，表名 `c_users`。

## API 接口

### 通用

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/` | 欢迎信息 | 无 |
| GET | `/api/v1/health` | 健康检查 | 无 |

### 认证（JWT + Redis）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/v1/auth/login` | 登录，返回 `access_token` | 无 |
| POST | `/api/v1/auth/logout` | 登出，删除 Redis 中的 token | 必须 |
| GET | `/api/v1/auth/me` | 当前登录用户 | 必须 |
| GET | `/api/v1/auth/demo/public` | 不验签示例 | 无 |
| GET | `/api/v1/auth/demo/protected` | 必须验签示例 | 必须 |
| GET | `/api/v1/auth/demo/optional` | 可选验签示例 | 可选 |

**登录示例：**

```http
POST /api/v1/auth/login
Content-Type: application/json

{"username": "admin", "password": "123456"}
```

**带 Token 访问：**

```http
Authorization: Bearer <access_token>
```

**验签原理：** JWT 验签（签名 + 过期）→ 用 payload 中的 `jti` 查 Redis 键 `auth:token:{jti}` → 不存在则视为已登出。

**密码哈希：** `users.password_hash` 需为 bcrypt 格式：

```bash
.venv/bin/python scripts/hash_password.py 123456
```

### 用户

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/v1/users` | 分页列表，参数 `page`、`page_size`、`fields` | 无 |
| GET | `/api/v1/users/all` | 全量列表（固定返回 `id`、`username`） | 无 |
| GET | `/api/v1/users/lookup` | 按字段查询，参数 `field`、`value`、`type` | 无 |
| GET | `/api/v1/users/{user_id}` | 按 id 查询（全字段时走 Redis 缓存） | 无 |
| PUT | `/api/v1/users/{user_id}` | 更新用户（更新后清除缓存） | 无 |

**指定返回字段：**

```http
GET /api/v1/users?page=1&page_size=10&fields=id,username
GET /api/v1/users/1?fields=id,username
```

**按字段查询：**

```http
GET /api/v1/users/lookup?field=username&value=admin&type=one
GET /api/v1/users/lookup?field=is_admin&value=1&type=list&page=1&page_size=10
GET /api/v1/users/lookup?field=username&value=admin&type=id
```

`type` 取值：`one`（单条）、`id`（仅返回 id）、`list`（分页列表）。

### Redis 示例

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/redis/{key}` | 读取字符串 |
| PUT | `/api/v1/redis/{key}` | 写入字符串 |
| DELETE | `/api/v1/redis/{key}` | 删除键 |
| POST | `/api/v1/redis/examples/run` | 运行 Redis 命令示例 |

### 并发查库示例

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/v1/demo/concurrent-users` | 并行按 id 查用户 | 无 |

**请求参数：**

| 参数 | 说明 |
|------|------|
| `ids` | 逗号分隔的用户 id，如 `1,2,3`（单次最多 20 个） |
| `mode=thread` | **多线程**：`ThreadPoolExecutor` + 同步 Session（每线程独立连接） |
| `mode=async` | **协程并发**：`asyncio.gather`（FastAPI 常规写法，对比用） |

**示例：**

```http
GET /api/v1/demo/concurrent-users?ids=1,2,3&mode=thread
GET /api/v1/demo/concurrent-users?ids=1,2,3&mode=async
```

**返回示例：**

```json
{
  "code": 200,
  "data": {
    "mode": "thread_pool",
    "description": "ThreadPoolExecutor + 同步 Session，每线程独立连接",
    "worker_count": 3,
    "query_count": 3,
    "items": [
      {"user_id": 1, "found": true, "user": {"id": 1, "username": "admin"}},
      {"user_id": 2, "found": true, "user": {"id": 2, "username": "wangxing"}}
    ]
  },
  "message": "ok"
}
```

**实现说明：**

- 主链路使用异步 SQLAlchemy（`mysql+aiomysql`），`AsyncSession` **不能跨线程共享**
- 多线程模式在线程池内使用同步驱动（`mysql+pymysql`），每次查询独立 `with session()`
- 日常业务推荐 `mode=async`；阻塞驱动或 CPU 密集场景可参考 `mode=thread`
- 相关代码：`app/services/concurrent_service.py`、`app/db/sync_database.py`

## 响应格式

所有接口（含参数校验失败、HTTP 异常）均返回固定顺序 JSON：

```json
{
  "code": 200,
  "data": {},
  "message": "ok"
}
```

- `code`：业务状态码，`200` 表示成功
- `data`：业务数据，可为 `null`
- `message`：提示信息

## 交互式文档

启动服务后访问：

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 扩展新业务（MVC）

### 1. Schema — 定义入参 / 出参

```python
# app/schemas/order.py
from pydantic import BaseModel

class OrderCreate(BaseModel):
    product_id: int
    quantity: int
```

### 2. Model + Repository — 数据层

```python
# app/db/models/order.py
class Orders(Base):
    __tablename__ = "c_orders"
    ...

# app/db/repositories/order.py
class OrderRepository(BaseRepository):
    model = Orders

# app/db/deps.py
OrderRepo = Annotated[OrderRepository, Depends(repository_factory(OrderRepository))]
```

### 3. Service — 业务逻辑

```python
# app/services/order_service.py
class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo

    async def create(self, data: dict) -> dict:
        # 业务校验、组合多个 Repository 等
        return await self._repo.get_one_by_id(...)

# app/services/deps.py
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
```

### 4. Controller — 只写入参 / 出参

```python
# app/controllers/v1/order.py
@router.post("")
async def create_order(body: OrderCreate, service: OrderServiceDep):
    order = await service.create(body.model_dump())
    return success(data=order, message="创建成功")
```

### 5. 注册路由

```python
# app/controllers/v1/router.py
from app.controllers.v1 import order
api_router.include_router(order.router)
```

### 接口鉴权

在 Controller 参数上声明依赖即可：

```python
from app.auth.deps import CurrentUser, OptionalUser

# 必须登录
async def protected_api(user: CurrentUser, service: AuthServiceDep): ...

# 可选登录（未登录也能访问）
async def optional_api(user: OptionalUser): ...

# 完全公开 — 不加鉴权依赖
async def public_api(): ...
```

## Repository 常用方法

```python
# 按主键 / 条件
user = await repo.get_one_by_id(1, columns=["id", "username"])
user = await repo.get_one(username="admin")

# 分页 / 全量
page = await repo.get_list(page=1, page_size=10, columns=["id", "username"])
items = await repo.get_all(columns=["id", "username"])

# 按字段链式查询
user = await repo.by_field("username", "admin").one()
user_id = await repo.by_field("username", "admin").id()
page = await repo.by_field("is_admin", 1).page(page=1, page_size=10)

# 统一 FieldQuery 对象
query = FieldQuery.create(field="username", value="admin", mode="one")
result = await repo.query_field(query)
```

## 业务异常

```python
from app.core.exceptions import AppException

raise AppException("资源不存在", code=404)
raise AppException("未登录，请先获取 Token", code=401)
```

## 依赖

- [FastAPI](https://fastapi.tiangolo.com/) — Web 框架
- [Uvicorn](https://www.uvicorn.org/) — ASGI 服务器
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — 配置管理
- [SQLAlchemy](https://www.sqlalchemy.org/) — 异步 ORM（aiomysql）+ 同步驱动（pymysql，线程池查库）
- [Redis](https://redis.io/) — 缓存与 Token 会话
- [PyJWT](https://pyjwt.readthedocs.io/) — JWT 签发与验签
- [Passlib](https://passlib.readthedocs.io/) — bcrypt 密码哈希
- [PyMySQL](https://pypi.org/project/PyMySQL/) — 同步 MySQL 驱动（多线程查库示例）
