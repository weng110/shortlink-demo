# ShortLink Demo 短链接生成与统计平台

一个基于 **FastAPI + MySQL + Redis** 的短链接生成与统计平台：长链接转短链、302 跳转、点击统计、Redis 缓存、IP 限流、Docker 一键启动。

面试演示闭环：**输入长链接 → 生成短链 → 302 跳转 → 点击量 +1 → Dashboard 图表实时刷新**。

## 功能

- 长链接转短链（MySQL 自增 ID + Base62 短码）
- `/s/{code}` 302 跳转（不用 301，避免浏览器缓存导致统计不到）
- 点击统计：Redis 计数 + 定时任务批量落库 MySQL
- Redis 缓存短链映射（`link:code:{code}`），命中缓存不查库
- 每 IP 每分钟 60 次限流（Redis `INCR + EXPIRE`）
- 短链列表 / 统计 / 禁用
- Dashboard：Chart.js 点击量图表 + 实时计数（已落库 + Redis 待落库）
- Swagger 接口文档（FastAPI 自带 `/docs`）
- Docker Compose 一键启动（MySQL 8 + Redis 7 + App）
- pytest 测试：Base62 / 创建 / 跳转 / 计数 / 落库 / 禁用 / 限流

## 技术栈

| 层 | 技术 |
| --- | --- |
| 语言/框架 | Python 3.12 / FastAPI |
| ORM | SQLAlchemy 2.0 |
| 存储 | MySQL 8 + Redis 7 |
| 前端 | Jinja2 + Bootstrap 5 + Chart.js |
| 部署 | Docker + Docker Compose |
| 测试 | pytest + httpx + fakeredis |

## 架构图

```mermaid
flowchart LR
    A[浏览器/客户端] -->|POST /api/links 创建| B[FastAPI App]
    A -->|GET /s/{code}| B
    A -->|GET /dashboard 图表| B
    B --> C[Redis 缓存/计数/限流]
    B --> D[MySQL 短链表]
    C -->|定时任务每10s 批量落库| D
```

### 核心流程：跳转

```text
GET /s/{code}
  1. 限流检查（Redis INCR + EXPIRE，超 60 次/分 -> 429）
  2. 查 Redis 缓存 link:code:{code}
     命中   -> 302 跳转
     未命中 -> 查 MySQL -> 回填 Redis -> 302 跳转
     不存在 -> 404
  3. Redis 点击计数 link:click:{code} +1
  4. 定时任务每 10s 把计数累加到 MySQL
```

### Redis Key 约定

| Key | 说明 |
| --- | --- |
| `link:code:{code}` | 短码 -> 长链接缓存（TTL 1 天） |
| `link:click:{code}` | 短码 -> Redis 点击计数（待落库） |
| `link:click:dirty` | 有待同步计数的短码集合 |
| `limit:ip:{ip}` | 限流计数（60 秒过期） |

## 快速启动（Docker）

```bash
docker compose up -d
```

启动后访问：

| 地址 | 说明 |
| --- | --- |
| http://localhost:8080 | 首页：生成短链 |
| http://localhost:8080/dashboard | Dashboard：列表 + 图表 |
| http://localhost:8080/docs | Swagger 接口文档 |
| http://localhost:8080/api/health | 健康检查 |

## 本地一键演示（Windows，无需 Docker）

演示模式用 **本机 Redis + SQLite**，一条命令启动：

```powershell
.\start-demo.ps1
# 打开 http://localhost:8080
# 另开终端跑闭环验证：python scripts/demo_e2e.py
```

> Redis 通过 `winget install taizod1024.redis-windows-fork` 安装；MySQL 由 Docker Compose 提供（正式演示建议走 Docker）。

## 本地开发（不用 Docker）

```bash
# 1. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt

# 2. 准备 MySQL 和 Redis（或用 Docker 只起这两个）
docker compose up -d mysql redis

# 3. 配置环境变量（可选，默认连 localhost）
copy .env.example .env

# 4. 启动
uvicorn app.main:app --reload --port 8080
```

> 注：启动时自动建表（`Base.metadata.create_all`），无需手动执行 SQL；`scripts/init.sql` 供手动建库/截图演示用。

## 运行测试

```bash
pytest -q          # SQLite + fakeredis，无需 Docker，12 个用例
```

## REST API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/links` | 创建短链 |
| GET | `/api/links` | 短链列表（含实时点击量） |
| GET | `/api/links/{code}/stats` | 单个短链统计 |
| DELETE | `/api/links/{code}` | 禁用短链 |
| GET | `/s/{code}` | 302 跳转 |

```http
POST /api/links
{"longUrl": "https://www.baidu.com"}

→ 200
{"code": "1aB", "short_url": "http://localhost:8080/s/1aB", "long_url": "https://www.baidu.com"}
```

## 数据库表

```sql
CREATE TABLE link (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  short_code VARCHAR(16) NOT NULL UNIQUE,
  long_url VARCHAR(2048) NOT NULL,
  click_count BIGINT DEFAULT 0,
  status TINYINT DEFAULT 1,          -- 1=启用 0=禁用
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 项目结构

```text
shortlink-demo
├── app/
│   ├── main.py            # FastAPI 入口（生命周期、静态资源、路由装配）
│   ├── config.py          # 环境变量配置
│   ├── database.py        # SQLAlchemy engine / Session
│   ├── models.py          # link 表模型
│   ├── schemas.py         # Pydantic 请求/响应模型
│   ├── redis_client.py    # 全局 Redis 客户端（可替换 fakeredis）
│   ├── tasks.py           # 定时任务：Redis 计数批量落库
│   ├── routers/
│   │   ├── api.py         # REST API
│   │   ├── redirect.py    # /s/{code} 302 跳转 + 限流
│   │   └── pages.py       # 首页 / Dashboard
│   ├── services/
│   │   ├── link_service.py    # 核心业务
│   │   └── rate_limit.py      # IP 限流
│   ├── utils/base62.py    # Base62 编解码
│   ├── templates/         # index.html / dashboard.html
│   └── static/            # css / js
├── tests/                 # pytest 用例
├── scripts/init.sql       # 手动建表脚本
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 截图

| 页面 | 预览 |
| --- | --- |
| 首页：生成短链 | [homepage.png](docs/screenshots/homepage.png) |
| Dashboard 图表 | [dashboard_chart.png](docs/screenshots/dashboard_chart.png) |
| Dashboard 列表 | [dashboard_table.png](docs/screenshots/dashboard_table.png) |
| Swagger 文档 | [swagger.png](docs/screenshots/swagger.png) |
| MySQL / Redis 数据 | 终端命令见 [docs/db-snapshot.txt](docs/db-snapshot.txt)，可自行截图 |

## 压测

Windows 下用自带脚本 `scripts/load_test.py`（asyncio 并发，等价于 wrk 思路）：

```bash
# 压列表接口（原始吞吐）
python scripts/load_test.py http://localhost:8080 /api/links 10 100

# 压跳转接口（会先撞上 IP 限流，验证限流效果）
python scripts/load_test.py http://localhost:8080 /s/2 8 30
```

实测结果（Docker 版 MySQL + Redis，默认单进程 uvicorn，同一台机器）：

```text
GET /api/links   并发100 / 10s   QPS 116.2   P50 817ms   P95 977ms   P99 1062ms   5xx 0%
GET /s/2         并发30  / 8s    QPS 85.1    全部返回 429（每 IP 每分钟限流 60 次，符合预期）
```

> 说明：默认 uvicorn 单 worker + 同步 SQLAlchemy，P99 偏高主要来自线程池排队；
> 生产可用 `uvicorn app.main:app --workers 4`、异步驱动或加本地缓存（Caffeine）提升吞吐。
> `/s/{code}` 跳转接口被每 IP 每分钟 60 次的限流保护，压测会稳定触发 429，属预期行为。

## 面试讲解点

1. **为什么用 302 不用 301？** 301 会被浏览器缓存，后续点击不再请求服务端，统计不到；302 每次都请求服务端。
2. **短码怎么生成？** MySQL 自增 ID + Base62 编码，`short_code` 唯一索引兜底。
3. **Redis 和 MySQL 一致性？** 先写 MySQL（权威数据），Redis 只做读缓存，写后回填，接受最终一致；禁用时主动清缓存。
4. **点击量准不准？** Redis 原子计数，定时批量落库；极端并发下可能丢失极少计数，要精确可引入 MQ 削峰。
5. **限流怎么实现？** Redis `INCR + EXPIRE` 固定窗口，每 IP 每分钟 60 次，超限 429。
6. **QPS 高了怎么办？** 本地缓存（Caffeine）二级缓存、MQ 异步落库、分库分表、多级缓存 + 集群。

## 后续可扩展（选做）

- 短链过期时间（`expires_at` 字段 + 定时清理）
- 二维码生成
- 访问日志表（IP、UA、时间）
- 每日/每时趋势图（引入定时聚合任务）
