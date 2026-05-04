# `calibre_mcp/` 根层文件地图

> 本目录包含 20 个 .py 文件，是 CalibreMCP 服务器的根层组件。

---

## 入口文件

### `server.py` (29KB) ⭐ 主入口
- **职责**: FastMCP 实例创建、server_lifespan、main()、所有 Response 模型定义
- **关键类**: 略
- **关键函数**:
  - `create_app(path)` — 返回 FastMCP ASGI app
  - `_probe_calibre_connectivity(startup_log)` — 启动时探测 Calibre 连通性（支持 CALIBRE_BASE_PATH、CALIBRE_LIBRARY_PATH、CALIBRE_SERVER_URL）
  - `server_lifespan(mcp_instance)` — FastMCP 生命周期（✅ 已调用 init_database()，见 L304-305）
  - `get_api_client()` — 获取 Calibre 远程 API 客户端
  - `discover_libraries()` — 发现书库
  - `get_mcp_instance()` — 获取 FastMCP 实例
  - `main()` — 服务器启动主入口
- **依赖**: FastMCP, Pydantic, 所有 tools/

### `__main__.py` (2KB) — CLI 入口
- **职责**: `python -m calibre_mcp` 的入口点
- **关键函数**: `run()` — 同步入口，`main()` 异步包装
- **特殊行为**: 在 stdio 模式下重定向 stderr 到 devnull

---

## 配置层

### `config.py` (18KB) — 配置管理
- **关键类**:
  - `CalibreConfig(BaseModel)` — 根配置类，含 `local_library_path`, `discovered_libraries`, `auto_discover_libraries`, `use_remote`, `load_beta_tools` 等字段
  - `RemoteServerConfig(BaseModel)` — 远程服务器配置
- **关键方法**:
  - `load_config()` — 从 JSON 文件 + 环境变量加载配置
  - `discover_libraries()` — 调用 config_discovery 发现书库
  - `set_active_library(name)` — 切换活跃书库
  - `get_active_library()` — 获取当前活跃书库
- **✅ env_mappings** 已包含 `CALIBRE_LIBRARY_PATH: local_library_path`（L185）

### `config_discovery.py` (20KB) — 书库发现
- **关键类**:
  - `CalibreLibrary` — 数据类：name, path, metadata_db, book_count, is_active
  - `CalibreConfigDiscovery` — 发现核心逻辑
- **关键方法**: `discover_all_libraries()`, `_discover_from_environment()`, `_scan_common_locations()`, `_discover_from_calibre_config()`, `_discover_from_calibre_api()`
- **顶层函数**: `discover_calibre_libraries()` → `dict[str, CalibreLibrary]`
- **✅ 硬编码路径已清除**（旧 3 处 L:/ 路径已删除）

---

## 基础设施

### `transport.py` (10KB) — 传输层
### `prompts.py` (12KB) — FastMCP 提示模板
### `logging_config.py` (9KB) — 日志配置
### `exceptions.py` (1KB) — 自定义异常
### `auth.py` (4KB) — 认证模块
### `calibre_api.py` (15KB) — Calibre REST API 客户端
### `utils.py` (15KB) — 通用工具

---

## 辅助文件

### `server_full.py` (24KB) — 旧版完整服务器（淘汰留档）
- 含旧硬编码路径 `L:/Multimedia Files/Written Word`（L555），仅供参考，不参与运行

### `server_minimal.py` (1KB) — 极简测试服务器
### `server_context.py` (2KB) — 服务器上下文工具
### `server_models.py` (3KB) — 额外响应模型
### `mcp_instance.py` (2KB) — FastMCP 实例单独导出
### `skills_encoding.py` (2KB) — Skills UTF-8 编码补丁
### `llm_http.py` (5KB) — LLM HTTP 客户端
### `models.py` (6KB) — 顶级模型（转发到 models/ 包）

---

## 根层文件导入依赖图

```
server.py
    ├──> config.py (CalibreConfig)
    ├──> config_discovery.py (discover_all_libraries)
    ├──> transport.py (get_transport_config, run_server)
    ├──> prompts.py (register_prompts)
    ├──> logging_config.py (setup_logging)
    ├──> exceptions.py (CalibreMCPError)
    ├──> auth.py (AuthHandler)
    ├──> calibre_api.py (CalibreAPIClient)
    ├──> utils.py
    ├──> mcp_instance.py
    ├──> tools/ (register_tools)
    └──> db/database.py (init_database ← ✅ 已调用)
```

## 子目录导航

| 子目录 | INFO.md | 内容 | 关键文件 |
|---|---|---|---|
| `db/` | `db/INFO.md` | 数据库层（SQLAlchemy） | database.py, models.py, 4 个 repository |
| `services/` | `services/INFO.md` | 业务逻辑层 | 15 个 service，最大 62KB |
| `models/` | `models/INFO.md` | Pydantic 数据模型 | 10 个模型文件 |
| `tools/` | `tools/INFO.md` | MCP 工具层（核心） | 22 子目录，130+ 文件 |
| `rag/` | `rag/INFO.md` | RAG 引擎 | 10 个文件，LanceDB |
| `api/` | `api/INFO.md` | REST API | libraries.py, viewer.py |
| `viewers/` | `viewers/INFO.md` | 阅读器 | manga/epub/pdf 各一个 |
| `storage/` | `storage/INFO.md` | 持久化存储 | persistence.py |
| `server/` | `server/INFO.md` | 备用服务器入口 | mcp_server.py |
| `utils/` | `utils/INFO.md` | 工具函数 | fts_utils.py 等 |
