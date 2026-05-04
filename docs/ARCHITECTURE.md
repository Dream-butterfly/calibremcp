# CalibreMCP 项目架构总览

## 项目定位
CalibreMCP 是一个基于 FastMCP (>=3.2.0) 的 Calibre 电子书库 MCP 服务器。提供对 Calibre 本地 SQLite 书库的 MCP 协议访问，支持查询、管理、RAG 搜索、阅读、导入导出等功能。

## 项目根级结构

```
calibremcp/                      # 项目根目录
├── pyproject.toml               # 项目元数据、依赖（FastMCP>=3.2.0）
├── setup.py                     # 旧式安装配置
├── uv.lock                      # uv 依赖锁文件（559KB）
├── Cargo.toml / Cargo.lock      # Rust 组件（WASM 扩展）
├── extension.wasm               # 编译后的 WASM 二进制（498KB）
├── config.json                  # 默认配置文件
├── .env                         # 环境变量配置
├── CLAUDE.md                    # AI 编程助手指令
├── ENVIRONMENT.md               # 本地环境说明
├── CHANGELOG.md / README.md / CONTRIBUTING.md / TODO.md / SECURITY.md
│
├── src/calibre_mcp/             # Python 主包（全部业务逻辑）
├── docs/                        # 文档（40+ 个 md 文件）
├── tests/                       # 测试套件（pytest）
├── scripts/                     # PowerShell + Python 工具脚本
├── calibre_plugin/              # Calibre 桌面端插件
├── webapp/                      # Web 应用（Docker + 前后端）
├── mcpb/                        # MCP Build Package
├── skills/                      # 技能目录
├── prompts/                     # 提示模板
├── config/                      # YAML 配置文件
├── assets/                      # 静态资源
├── samples/                     # 示例文件
├── logs/                        # 运行时日志
└── .github/workflows/           # CI/CD 工作流（6 个 yml）
```

## 源码层结构（`src/calibre_mcp/`）

```
calibre_mcp/
├── server.py                   # ⭐ 入口：FastMCP 实例、lifespan、main()
├── config.py                   #   配置：CalibreConfig (Pydantic)
├── config_discovery.py         #   书库发现：CalibreConfigDiscovery
├── transport.py                #   传输层：stdio / HTTP
├── prompts.py                  #   FastMCP 提示模板
├── db/                         # 📦 数据库层 → `db/INFO.md`
├── services/                   # 📦 业务逻辑层 → `services/INFO.md`
├── models/                     # 📦 数据模型 → `models/INFO.md`
├── tools/                      # 📦 MCP 工具层（核心，130+ 文件）→ `tools/INFO.md`
├── rag/                        # 📦 RAG 引擎 → `rag/INFO.md`
├── api/                        # 📦 REST API → `api/INFO.md`
├── viewers/                    # 📦 阅读器 → `viewers/INFO.md`
├── storage/                    # 📦 持久化存储 → `storage/INFO.md`
├── utils/                      #   工具函数
├── server/                     #   备用服务器入口（另一套实现）
├── skills/                     #   内置 MCP skills
├── templates/                  #   HTML 模板
└── static/                     #   前端静态资源
```

## 层间依赖关系图

```
MCP Host (CherryStudio)
    │
    ▼  stdio protocol
transport.py ───> server.py
    │                  │
    │         ┌────────┴──────────────┐
    │         ▼                       ▼
    │   config.py ──────────> config_discovery.py
    │         │                  (发现书库)
    │         ▼
    │   server_lifespan()
    │         │
    │         ▼
    │   db/database.py (SQLAlchemy)
    │         │
    │         ▼
    │   db/models.py (ORM) ←── 映射 metadata.db
    │         │
    │         ▼
    │   db/repositories/ (CRUD)
    │         │
    │         ▼
    │   services/ (BookService, TagService, ...)
    │         │
    │         ▼
    │   tools/ (portmanteau)
    │         │
    │         └──> @mcp.tool() 暴露给 MCP Host
    │
    ├───> rag/ (LanceDB 向量检索)
    ├───> api/ (REST → webapp/)
    ├───> viewers/ (在线阅读器)
    └───> storage/ (持久化状态)
```

## 当前 Bug 与架构问题的关联

| Bug# | 文件 | 根因类型 | 架构层次 | 影响范围 |
|---|---|---|---|---|
| Bug 1 | `server.py` | **初始化遗漏** — `server_lifespan()` 未调用 `init_database()` | 入口层 → 数据库层 | 所有 SQLAlchemy 查询失败 |
| Bug 2 | `utils/library_utils.py` | **硬编码路径** — `L:/...` 不存在 | 工具层依赖 | `manage_libraries` 全部失效 |
| Bug 3 | `server.py:598` | **硬编码路径** — `L:/...` | 入口层 | `discover_libraries()` 失效 |
| Bug 4 | `config_discovery.py:72,314,350` | **硬编码路径** — `L:/...` | 配置层 | fallback 路径错误 |
| Bug 5 | `library_analysis.py` | **方法不存在** — `get_session()` → `session_scope()` | 工具层 | 6 个分析工具返回空 |
| Bug 6 | `services/book_service.py` | **方法缺失** — 未暴露 `get_recent_books()` | 业务逻辑层 | `query_books(recent)` 报错 |
| Bug 7 | `config.py:175-189` | **env_mappings 遗漏** — 未映射 `CALIBRE_LIBRARY_PATH` | 配置层 | 配置层感知不到该环境变量 |
| Bug 8 | `tools/__init__.py:28` | **硬编码路径** — 未引用的残余 | 工具层 | 潜在风险 |

**Bug 分布热力图：**
```
入口层: ████████████████████ 3 个 (Bug 1, 3, 8)
配置层: ████████████████    2 个 (Bug 4, 7)
业务逻辑层: ██████         1 个 (Bug 6)
工具层:   ████████████████ 2 个 (Bug 2, 5)
数据库层: 无
```

## 5 个历史遗留痕迹

1. **两条书库发现管线** — `utils/library_utils.py`（旧，返回 `dict[str, Path]`）vs `config_discovery.py`（新，返回 `dict[str, CalibreLibrary]`）→ 工具层用的旧管线
2. **两个服务器入口** — `server.py`（当前主入口）vs `server_full.py`（旧版留档，第 204 行有正确的 `init_database()` 调用示例）
3. **两套工具注册机制** — `@mcp.tool()` 装饰器（新式）vs `BaseTool` + `TOOL_REGISTRY`（旧式，未被移除）
4. **备用服务器** — `server/` 目录下的另一套 FastMCP 实现（另一套 `mcp_server.py`）
5. **Rust WASM 组件** — `extension.wasm` (498KB) + Cargo.toml — 当前用途不明

## 数据流（含 Bug 断裂点）

```
MCP Host
  │
  ▼ ①
server.py / transport.py
  │
  ├──> config.py / config_discovery.py → dict[str, CalibreLibrary]
  │
  ├──> server_lifespan()
  │      │
  │      ▼
  │    _probe_calibre_connectivity()
  │      │   ⚠️ 只检查 CALIBRE_BASE_PATH 和 CALIBRE_SERVER_URL
  │      │   漏掉了 CALIBRE_LIBRARY_PATH
  │      │
  │      ▼
  │    init_database(metadata.db)   ← ❌ **Bug 1: 此处未调用**
  │      │
  │      ▼ ②
  │    DatabaseService.initialize() → create_engine()
  │      │                            scoped_session()
  │      │                            init repositories
  │      ▼
  │    db.session_scope() → SQLAlchemy Session
  │
  └──> tools/register_tools()
         │
         ▼ ③
       portmanteau tools
         │
         ├── manage_libraries()
         │      └──> utils.library_utils.discover_calibre_libraries()
         │             ⚠️ **Bug 2: 硬编码 L:/ 路径** → 返回空 dict
         │
         ├── query_books(operation="search")
         │      └──> BookService.get_all()
         │             └──> BookRepository.get_all()
         │                    ⚠️ **Bug 1 影响: DatabaseService._engine=None**
         │
         ├── query_books(operation="recent")
         │      └──> BookService.get_recent_books()  ← ❌ **Bug 6: 方法不存在**
         │
         └── manage_analysis()
                └──> library_analysis.get_tag_statistics()
                       └──> db.get_session()  ← ❌ **Bug 5: 方法不存在**
```

断裂点说明：
- **①→②**: Bug 1 阻断 — `init_database()` 未调用，没有数据库引擎
- **②→③**: Bug 1 的连锁反应 — 所有需要 SQLAlchemy 的工具都返回空
- **③→utils**: Bug 2/3/4 — 硬编码路径导致书库发现失败
- **③→services**: Bug 6 — 方法缺失
- **③→analysis**: Bug 5 — 方法名错误

## 相关文档
- `README.md` — AI 入口（阅读顺序）
- `ENVIRONMENT.md` — 本地环境说明
- `memory/FACT.md` — 完整事实记录、Bug 清单、精确修复计划
- `CLAUDE.md` — AI 编程助手指令
- 各层 `INFO.md` — 每层的详细地图
