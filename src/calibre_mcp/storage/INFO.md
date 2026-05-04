# `storage/` 持久化存储层

> **职责**: 提供 FastMCP 持久化存储接口（py-key-value），
> 用于跨会话保持状态（如当前活跃书库、用户偏好）。
> 共 4 个文件（含 `__init__.py`）。

---

## 文件清单

### `__init__.py` (1KB) — 导出
- **函数**: `create_storage(storage_type, config)` — 存储工厂

### `persistence.py` (18KB) ⭐ 持久化核心
- **类**: `CalibreMCPStorage` — 存储核心
- **方法**:
  - `set_current_library(name)` — 设置当前活跃书库
  - `get_current_library()` → `str | None` — 获取当前活跃书库
  - `set_preference(key, value)` — 存储用户偏好
  - `get_preference(key, default)` — 读取用户偏好
  - `save()` / `load()` — 序列化/反序列化到磁盘
  - `clear()` — 清除所有存储数据
- **序列化格式**: JSON
- **存储位置**: 项目根目录下的 `calibre_mcp_data.json`（或自定义路径）

### `local.py` (7KB) — 本地文件存储
- **类**: `LocalStorage` — 基于文件系统的存储后端
- **方法**: `read(key)`, `write(key, value)`, `delete(key)`, `list_keys()`
- **用途**: 持久化到本地 JSON 文件

### `remote.py` (8KB) — 远程存储
- **类**: `RemoteStorage` — 远程 API 存储后端（未完全实现）
- **用途**: 跨设备同步状态

---

## 数据流

```
server_lifespan()
    │
    ▼
CalibreMCPStorage.__init__()
    │
    ├──> load() → 从 JSON 文件恢复状态
    │
    ▼
tools/library/manage_libraries → set_current_library("轻小说")
    │
    ▼
CalibreMCPStorage.set_current_library("轻小说")
    │
    └──> save() → 写入 JSON 文件
```

## 相关文档
- `ARCHITECTURE.md` — 项目架构总览
