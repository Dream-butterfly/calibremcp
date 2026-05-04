# `api/` REST API 层

> **职责**: 为 Web 应用（`webapp/`）提供 REST API 端点。
> 与 MCP 协议无关，仅服务于浏览器端 UI。
> 共 2 个文件。

---

## 文件清单

### `libraries.py` (7KB) — 书库 REST 端点
- **路由**: `/api/libraries/` 前缀
- **端点**:
  - `GET /api/libraries/` — 书库列表
  - `GET /api/libraries/{name}/` — 书库详情（含书籍数量、统计）
- **依赖**: `services/library_service.py`, `config.py`

### `viewer.py` (9KB) — 阅读器 REST 端点
- **路由**: `/api/viewer/` 前缀
- **端点**:
  - `GET /api/viewer/books/{id}/pages/` — 获取书籍页面
  - `GET /api/viewer/books/{id}/content/` — 获取渲染内容
- **依赖**: `viewers/` 内的特定阅读器实现

---

## 谁调用 REST API

```
浏览器 (webapp/ frontend)
    │  HTTP
    ▼
api/libraries.py  ───> services/LibraryService
api/viewer.py     ───> viewers/ (阅读器)
```

> **注意**: MCP Host（如 CherryStudio）**不**走 REST API，而是走 `transport.py` 的 MCP stdio/HTTP 协议。
> REST API 只服务 webapp 前端。

## 相关文档
- `viewers/INFO.md` — 被 viewer.py 调用的阅读器
- `services/INFO.md` — 被 libraries.py 调用的业务逻辑层
