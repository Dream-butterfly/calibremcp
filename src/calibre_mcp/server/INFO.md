# `server/` 备用服务器入口

> **用途**: 项目另一套 FastMCP 服务器实现，与根层 `server.py` 平行。
> 当前可能未启用。如果主服务器出现问题，可评估此替代方案作为参考。
> ⚠️ 不确定性：不确认当前是否被引用或已废弃。

---

## 文件清单

### `main.py` (2KB) — 独立服务器入口
- **函数**: `main()` — 独立的 FastMCP 启动入口
- **与 `server.py` 的区别**: 不使用 `transport.py`，直接创建 FastMCP 并启动

### `mcp_server.py` (7KB) — MCP 实现
- **类**: `CalibreMCPServer` — 另一套 FastMCP 配置和工具注册
- **方法**: `register_tools()`, `run()`
- **与 `server.py` 的区别**:
  - 不使用 FastMCP `@mcp.tool()` 装饰器模式
  - 改用类内注册机制

### `config.py` (1KB) — 配置
- **类**: `ServerConfig` — 使用 Pydantic `BaseSettings`（而非 `CalibreConfig`）
- **来源**: 从环境变量或 `.env` 文件读取

### `core/exception_handlers.py` (4KB) — 异常处理
- **函数**: `setup_exception_handlers(app, mcp)` — 为 FastMCP 注册统一异常处理中间件
- **用途**: 统一错误响应格式

### `middleware/request_logging.py` (2KB) — 请求日志
- **函数**: `LoggingMiddleware` — HTTP 请求日志记录
- **用途**: 记录所有 HTTP 请求的路径、方法、状态码

---

## 与主 server.py 的对比

| 特性 | `server.py`（主入口） | `server/`（备用） |
|---|---|---|
| 工具注册 | `@mcp.tool()` 装饰器 | 类方法注册 |
| 配置 | `CalibreConfig` (Pydantic BaseModel) | `ServerConfig` (Pydantic BaseSettings) |
| 传输层 | `transport.py` | 直接 FastMCP |
| 当前状态 | **活跃** | 可能未启用 |
| 完善度 | 完整（含 lifespan、日志、auth 等） | 较简陋 |

## 相关文档
- `INFO.md`（根层）— 主入口 `server.py` 的详细信息
- `ARCHITECTURE.md` — 项目架构总览
