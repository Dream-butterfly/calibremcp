# Prometheus 代码修订深度计划

> **归档说明（2026-05-06）**: 本计划中描述的 5 个 Bug 已在源码层全部修复。
> 最新的项目状态请参见 `CLAUDE.md`（根目录）和 `memory/FACT.md`。
> 保留此文档作为历史参考。

> **目的**: 修复 CalibreMCP v1.8.0 中的所有已知 Bug，打通数据库连接，使全部 MCP 工具正常工作。
> **方法**: 4 阶段依序执行，每阶段可独立验证、可回滚。
> **状态**: ✅ 全部完成
>
> **源码验证**: 本计划所有文件行号均经过实际源码读取确认。

---

## 一、🔍 完整审查结果

### 1.1 架构真相：两条并行的发现管线

项目存在两个同名但不同模块的 `discover_calibre_libraries()`：

| 来源 | 返回类型 | 被谁使用 | 是否正确 |
|---|---|---|---|
| `utils/library_utils.py:11` | `dict[str, Path]` | `tools/library/library_management.py`（工具层） | ❌ 硬编码 `L:/` |
| `config_discovery.py:474` | `dict[str, CalibreLibrary]` | `config.py:302 → config_discovery.py:58`（配置层） | ✅ 能读取 `CALIBRE_LIBRARY_PATH` |

**本质问题**：工具层走的旧管线硬编码了路径；配置层的新管线正确但未被工具层使用。

### 1.2 已连接但始终返回空的工具

以下工具**已经连接**到 MCP，但全部返回空数据，根源是 **Bug 1（数据库未初始化）+ Bug 3（get_session 不存在）+ Bug 2（硬编码路径）** 的连锁反应：

- `query_books(operation="search")` — 空数据（Bug 1: 无数据库引擎）
- `query_books(operation="recent")` — AttributeError（Bug 4: 方法不存在）
- `get_tag_statistics`, `find_duplicate_books`, `get_series_analysis`, `analyze_library_health`, `unread_priority_list`, `reading_statistics` — 空数据（Bug 1 + Bug 3）
- `manage_libraries(operation="list/switch/stats")` — 空列表（Bug 2: 硬编码路径）

---

### 1.3 问题总览：5 大类 11 个问题点

#### 🚨 P0 — 阻塞级别（1 个致命 + 9 个硬编码路径）

**Bug 1: `init_database()` 从未被调用** ⚡最致命

| 项目 | 内容 |
|---|---|
| **文件** | `src/calibre_mcp/server.py` |
| **位置** | `server_lifespan()` 第 253-272 行；`main()` 第 616-820 行 |
| **根因** | `server_lifespan()` 第 268 行只调了 `await _probe_calibre_connectivity(lifespan_log)`，从未调 `init_database()`。`main()` 中同样无调用 |
| **对比** | `server_full.py` 第 204 行有正确的 `init_database(str(metadata_db.absolute()), echo=False)` |
| **影响机制** | `DatabaseService` 的 `_engine` 属性默认为 `None`。当工具调用 `session_scope()` 时，如果 `_engine is None` 则抛出 `RuntimeError("Database not initialized")`。该异常被工具的 `try/except` 吞噬 → 静默返回空数据 |

**Bug 2: 9 处硬编码 `L:/` 路径分布在 8 个文件中**

所有路径均指向 `L:/Multimedia Files/Written Word`（原开发者本机路径，在用户机器上不存在）。

| # | 文件 | 行号 | 代码 | 修复操作 |
|---|---|---|---|---|
| 2.1 | `utils/library_utils.py` | 8 | `CALIBRE_BASE_DIR = Path("L:/Multimedia Files/Written Word")` | 删除，委托给 config_discovery |
| 2.2 | `config_discovery.py` | 72 | `user_library_path = Path("L:/Multimedia Files/Written Word")` | 删除方法1硬编码 |
| 2.3 | `config_discovery.py` | 314 | `user_library_path = Path("L:/Multimedia Files/Written Word")` | 改为从环境变量读 |
| 2.4 | `config.py` | 350-362 | `user_library_path = Path("L:/Multimedia Files/Written Word")` 及后续优先级排序逻辑 | 删除 |
| 2.5 | `server.py` | 598 | `base_dir = Path("L:/Multimedia Files/Written Word")` | 改用 config.local_library_path |
| 2.6 | `server_context.py` | 48 | `base_dir = Path("L:/Multimedia Files/Written Word")` | 删除硬编码块 |
| 2.7 | `storage/local.py` | 64 | `Path("L:/Multimedia Files/Written Word/Main Library/metadata.db")` | 从默认路径列表删除 |
| 2.8 | `tools/__init__.py` | 28 | `CALIBRE_BASE_DIR = Path("L:/Multimedia Files/Written Word")` | 删除未使用的常量 |
| 2.9 | `server_full.py` | 555 | `base_dir = Path("L:/Multimedia Files/Written Word")` | **保留不修**（旧版留档参考） |

> ❗ `config.py:350-362` 不仅仅是硬编码路径——它包含一段复杂的优先级排序逻辑：遍历所有已发现书库，检查其路径是否在 `L:/...` 下面，如果是则优先选择。需要一并删除。

---

#### ⚠️ P1 — 功能阻塞（2 个）

**Bug 3: `db.get_session()` 方法不存在**

| 项目 | 内容 |
|---|---|
| **文件** | `tools/analysis/library_analysis.py` |
| **位置** | 共 **6 处**：L71 (`get_tag_statistics`), L189 (`find_duplicate_books`), L261 (`get_series_analysis`), L425 (`analyze_library_health`), L496 (`unread_priority_list`), L525 (`reading_statistics`) |
| **错误代码** | 全部使用 `db.get_session()`，但 `DatabaseService` 类中不存在该方法 |
| **正确方法** | `DatabaseService` 提供两个合法会话获取方式：<br>1. `db.session` — 属性，获取 scoped session<br>2. `db.session_scope()` — 上下文管理器，自动 commit/rollback/close |
| **后果** | `AttributeError` 被各函数的 `except Exception` 吞噬 → 返回空数据 |

**Bug 4: `BookService` 缺少 `get_recent_books()` 方法**

| 项目 | 内容 |
|---|---|
| **文件1** | `services/book_service.py`（1447 行）—— **方法不存在**。最后一个方法是 `_to_response()` 第 1313-1442 行 |
| **文件2** | `tools/book_management/query_books.py` 第 285 行调用 `book_service.get_recent_books(limit=limit)` → **AttributeError** |
| **文件3** | `db/repositories/book_repository.py` 第 130-152 行——**方法已存在且正确**。使用 `self._db.session_scope()` 查询并返回 `list[dict[str, Any]]` |
| **附加问题** | `query_books.py:288` 用 `book.dict()` 遍历结果，期望 element 是 Pydantic `BaseModel`。但 `_to_response()` 第 1442 行返回 `return book_dict`（纯 `dict`）。所以即使添加了 `get_recent_books()`，也需要适配 dict vs BaseModel 的不匹配 |

---

#### 🔧 P2 — 配置不完善（1 个）

**Bug 5: `CALIBRE_LIBRARY_PATH` 未映射到 `config.py`**

| 项目 | 内容 |
|---|---|
| **文件** | `config.py` 第 175-190 行 |
| **env_mappings** | 映射了 14 个环境变量，包括 `CALIBRE_BASE_PATH`、`CALIBRE_LIBRARY_PATHS`（复数，JSON 格式）、`user_config.calibre_library_path`（Claude Desktop 专用） |
| **遗漏** | **`CALIBRE_LIBRARY_PATH`**（单数，单个库路径）—— 项目中实际的配置方式 |
| **后果** | `config.local_library_path` 始终为 `None`（除非通过 `CALIBRE_LIBRARY_PATHS` 或 `discover_libraries()` 自动发现）。`_probe_calibre_connectivity()` 也检查不到这个变量 → 启动探测说"什么都没配置" |
| **现有 workaround** | `config_discovery.py:369` 的 `_discover_from_environment()` 直接读 `os.environ["CALIBRE_LIBRARY_PATH"]`，所以发现层仍能正确找到书库。但配置层看不到它 |

---

## 二、📋 修复计划（4 阶段）

### 2.1 总体执行策略

所有修复按 **依赖顺序** 分 4 个阶段。每阶段可独立验证，完成后提交一次 git commit。阶段之间无代码冲突。

```
阶段1 ──init_database()──→ 打通数据库连接          [Bug 1 + Bug 3]
  │     ├── query_books(operation="search")   从空 → 有数据
  │     └── 所有分析工具 (6 个)                 从空 → 有数据

阶段2 ──删除所有硬编码路径──→ 修复书库发现         [Bug 2: 9 处路径]
  │     └── manage_libraries(list/switch/stats)  从空 → 显示轻小说书库

阶段3 ──补 get_recent_books──→ 修复 recent 查询  [Bug 4]
  │     └── query_books(operation="recent")    AttributeError → 返回数据

阶段4 ──补 env_mappings──→ 完善配置层             [Bug 5]
  │     └── CalibreConfig.load_config()        能识别 CALIBRE_LIBRARY_PATH
```

### 2.2 阶段 1：打通数据库（Bug 1 + Bug 3）

**涉及文件**：
- `src/calibre_mcp/server.py`
- `src/calibre_mcp/tools/analysis/library_analysis.py`

#### 步骤 1.1 — `_probe_calibre_connectivity()` 添加 `CALIBRE_LIBRARY_PATH` 检查

**文件**: `src/calibre_mcp/server.py` 第 149-250 行

在 `CALIBRE_BASE_PATH` 检查块（第 169-197 行）之后、`CALIBRE_SERVER_URL` 检查（第 199 行）之前，插入：

```python
    # --- 1.5 CALIBRE_LIBRARY_PATH probe (singular, single library path) ---
    lib_path_str = os.environ.get("CALIBRE_LIBRARY_PATH", "").strip().strip('"')
    if lib_path_str and not base_path_ok:
        lib_path = Path(lib_path_str)
        if lib_path.exists() and (lib_path / "metadata.db").exists():
            base_path_ok = True
            startup_log.info(
                "STARTUP PROBE: local library OK via CALIBRE_LIBRARY_PATH — %s",
                lib_path,
            )
```

#### 步骤 1.2 — `server_lifespan()` 添加 `init_database()` 调用

**文件**: `src/calibre_mcp/server.py` 第 253-272 行

在 `await _probe_calibre_connectivity(lifespan_log)`（第 268 行）之后、`yield`（第 271 行）之前，插入：

```python
    # —— Initialize database connection for SQLAlchemy queries ——
    try:
        from calibre_mcp.config import CalibreConfig
        from calibre_mcp.db.database import init_database

        config = CalibreConfig.load_config()
        if config.local_library_path:
            metadata_db = config.local_library_path / "metadata.db"
            if metadata_db.exists():
                init_database(str(metadata_db.absolute()), echo=False)
                lifespan_log.info("Database initialized: %s", metadata_db)
        else:
            lifespan_log.warning(
                "No local_library_path configured — database init deferred. "
                "Set CALIBRE_LIBRARY_PATH or CALIBRE_BASE_PATH environment variable."
            )
    except Exception as e:
        lifespan_log.warning("Database init deferred (non-fatal): %s", e)
```

> **注意**：`config.local_library_path` 在第 4 阶段修复前可能为 `None`（因为 `CALIBRE_LIBRARY_PATH` 未映射到配置层）。如果该值为 `None`，数据库降级启动（不初始化），不影响后续阶段修复。

#### 步骤 1.3 — `library_analysis.py` 修正 6 处 `get_session()` → `session_scope()`

**文件**: `src/calibre_mcp/tools/analysis/library_analysis.py`

全部 6 处做统一替换：

| 行号 | 函数 | 修改前 | 修改后 |
|---|---|---|---|
| 71 | `get_tag_statistics` | `with db.get_session() as session:` | `with db.session_scope() as session:` |
| 189 | `find_duplicate_books` | 同上 | 同上 |
| 261 | `get_series_analysis` | 同上 | 同上 |
| 425 | `analyze_library_health` | 同上 | 同上 |
| 496 | `unread_priority_list` | 同上 | 同上 |
| 525 | `reading_statistics` | 同上 | 同上 |

`DatabaseService` 类提供的方法是 `session_scope()`（上下文管理器），不是 `get_session()`。`get_session()` 不存在。

#### ✅ 阶段 1 验证

| # | 测试项 | 当前状态 | 期望状态 |
|---|---|---|---|
| 1a | `query_books(operation="search", limit=5)` | 空数据 | 返回书籍列表 |
| 1b | `get_tag_statistics()` | 空数据 | 返回真实标签统计 |
| 1c | `manage_system(operation="status")` | 无数据库状态 | 显示数据库初始化信息 |

#### ↩️ 阶段 1 回滚

```bash
git checkout -- src/calibre_mcp/server.py src/calibre_mcp/tools/analysis/library_analysis.py
```

---

### 2.3 阶段 2：修复书库发现（Bug 2 — 9 处硬编码路径）

**核心策略**：
- `utils/library_utils.py` → 删除硬编码，委托给 `config_discovery` 的新管线
- 其余 7 个文件中的硬编码路径 → 删除或替换为配置读取
- `server_full.py:555` → **保留不修**（旧版留档）

#### 步骤 2.1 — 重写 `utils/library_utils.py`

**文件**: `src/calibre_mcp/utils/library_utils.py`

```python
"""
Utility functions for discovering and managing Calibre libraries.
"""
from pathlib import Path


def discover_calibre_libraries() -> dict[str, Path]:
    """
    Discover all Calibre libraries on the system.

    Delegates to config_discovery for actual discovery logic.
    Converts the CalibreLibrary objects to simple Path values
    for backward compatibility with callers expecting dict[str, Path].

    Returns:
        Dict mapping library names to their Paths
    """
    from calibre_mcp.config_discovery import discover_calibre_libraries as _new_discovery
    discovered = _new_discovery()
    return {name: lib.path for name, lib in discovered.items()}


def get_library_metadata(library_path: Path) -> dict[str, any]:
    """...（保留原函数不变）..."""


def get_current_library() -> Path | None:
    """...（保留原函数不变）..."""
```

#### 步骤 2.2 — 删除 `config_discovery.py:72` 硬编码路径

**文件**: `src/calibre_mcp/config_discovery.py` 第 58-94 行

修改 `discover_all_libraries()` 方法：删除方法 1（第 71-75 行）的硬编码路径扫描。让发现直接从方法 2（Calibre 配置解析）和方法 3（环境变量）开始。

```python
def discover_all_libraries(self) -> dict[str, CalibreLibrary]:
    """Discover all available Calibre libraries."""
    libraries = {}

    # Method 1: [已删除] 硬编码 L:/ 路径扫描

    # Method 2: Parse Calibre's JSON config files
    calibre_api_libraries = self._discover_from_calibre_api()
    libraries.update(calibre_api_libraries)
    calibre_libraries = self._discover_from_calibre_config()
    libraries.update(calibre_libraries)

    # Method 3: Environment variable override (always checked)
    env_libraries = self._discover_from_environment()
    libraries.update(env_libraries)

    self.discovered_libraries = libraries
    ...
```

同时更新文档字符串第 63 行：
```python
# 修改前:
"""1. Explicitly given directory (L:/Multimedia Files/Written Word) - highest priority"""
# 修改后:
"""1. CALIBRE_LIBRARY_PATH environment variable - highest priority"""
```

#### 步骤 2.3 — 修复 `config_discovery.py:314` `_scan_common_locations()`

**文件**: `src/calibre_mcp/config_discovery.py` 第 308-362 行

```python
def _scan_common_locations(self) -> dict[str, CalibreLibrary]:
    """Scan common locations where Calibre libraries might be stored"""
    libraries = {}
    common_bases = []

    # 优先从环境变量读取
    if "CALIBRE_LIBRARY_PATH" in os.environ:
        common_bases.append(Path(os.environ["CALIBRE_LIBRARY_PATH"]))

    # 然后添加常见默认路径（作为后备）
    common_bases.extend([
        Path.home() / "Documents" / "Calibre Library",
        Path.home() / "Books" / "Calibre Library",
        Path("C:/Users") / os.getenv("USERNAME", "") / "Calibre Library",
    ])
    # ... 后续扫描逻辑不变 ...
```

#### 步骤 2.4 — 删除 `config.py:349-371` 硬编码优先级逻辑

**文件**: `src/calibre_mcp/config.py` 第 302-385 行

删除 `discover_libraries()` 方法中第 349-371 行的硬编码路径优先级块（`user_library_path = Path("L:/Multimedia Files/Written Word")` 及后续的 `is_relative_to` 检查逻辑）。替换为：

```python
            # Set default library path if not specified
            if not self.local_library_path and libraries:
                active_library = get_active_calibre_library()
                if active_library:
                    self.local_library_path = active_library.path
                else:
                    # 直接使用第一个发现的书库（不再优先选择 L:/ 路径）
                    first_library = list(libraries.values())[0]
                    self.local_library_path = first_library.path
```

#### 步骤 2.5 — 修复 `server.py:598` `discover_libraries()`

**文件**: `src/calibre_mcp/server.py` 第 582-605 行

```python
async def discover_libraries() -> dict[str, str]:
    """Discover available Calibre libraries"""
    global available_libraries
    if available_libraries:
        return available_libraries

    from calibre_mcp.config import CalibreConfig
    config = CalibreConfig()
    libraries = {}

    # Check configured library path
    if config.local_library_path and config.local_library_path.exists():
        libraries["main"] = str(config.local_library_path)

    # Use config_discovery to find additional libraries
    from calibre_mcp.config_discovery import discover_calibre_libraries as _discover
    discovered = _discover()
    for name, lib in discovered.items():
        if lib.path.exists() and (lib.path / "metadata.db").exists():
            libraries[name] = str(lib.path)

    available_libraries = libraries
    return libraries
```

#### 步骤 2.6 — 删除 `server_context.py:48` 硬编码块

**文件**: `src/calibre_mcp/server_context.py` 第 35-55 行

```python
async def discover_libraries() -> dict[str, Any]:
    """Discover available Calibre libraries."""
    global available_libraries
    if available_libraries:
        return available_libraries

    from calibre_mcp.config import CalibreConfig
    config = CalibreConfig()
    libraries: dict[str, Any] = {}
    if config.local_library_path and config.local_library_path.exists():
        libraries["main"] = str(config.local_library_path)

    # [已删除: 硬编码 L:/ 路径扫描]
    # lib_path = os.environ.get("CALIBRE_LIBRARY_PATH", "").strip().strip('"')
    # if lib_path and Path(lib_path).exists():
    #     libraries["env_main"] = lib_path

    available_libraries = libraries
    return libraries
```

#### 步骤 2.7 — 删除 `storage/local.py:64` 默认路径

**文件**: `src/calibre_mcp/storage/local.py` 第 62-67 行

```python
        # Try default locations if not found in specified path
        default_paths = [
            # [已删除: Path("L:/Multimedia Files/Written Word/Main Library/metadata.db")]
            Path.home() / "Calibre Library/metadata.db",
            Path("C:/Calibre Library/metadata.db"),
        ]
```

#### 步骤 2.8 — 删除 `tools/__init__.py:28` 未使用的常量

**文件**: `src/calibre_mcp/tools/__init__.py` 第 27-28 行

```python
# [已删除]
# # Base directory for Calibre libraries
# CALIBRE_BASE_DIR = Path("L:/Multimedia Files/Written Word")
```

#### ✅ 阶段 2 验证

| # | 测试项 | 当前状态 | 期望状态 |
|---|---|---|---|
| 2a | `manage_libraries(operation="list")` | 空列表 | 显示至少 1 个书库（"env_main" 或 "轻小说"） |
| 2b | `manage_libraries(operation="switch")` | 找不到书库 | 成功切换 |
| 2c | `manage_libraries(operation="stats")` | 报错/空 | 显示统计数据 |
| 2d | `manage_system(operation="status")` | 发现 2 书库（空） | 显示已初始化书库 |

#### ↩️ 阶段 2 回滚

```bash
git checkout -- src/calibre_mcp/utils/library_utils.py src/calibre_mcp/server.py src/calibre_mcp/server_context.py src/calibre_mcp/config.py src/calibre_mcp/config_discovery.py src/calibre_mcp/storage/local.py src/calibre_mcp/tools/__init__.py
```

---

### 2.4 阶段 3：补缺方法（Bug 4）

**涉及文件**：
- `src/calibre_mcp/services/book_service.py`
- 可能还需要 `src/calibre_mcp/tools/book_management/query_books.py`

#### 步骤 3.1 — 添加 `get_recent_books()` 到 `BookService`

**文件**: `src/calibre_mcp/services/book_service.py`

在 `get_book_cover()` 方法后、`_get_cover_data()` 方法前插入（约第 1280-1285 行）：

```python
    def get_recent_books(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recently added books.

        Args:
            limit: Maximum number of books to return (default 10)

        Returns:
            List of recently added books as dictionaries
        """
        return self.repo.get_recent_books(limit=limit)
```

> `self.repo` 的类型是 `BookRepository`，其 `get_recent_books()` 方法（`book_repository.py:130-152`）已正确实现，使用 `self._db.session_scope()` 并返回 `list[dict[str, Any]]`。

#### 步骤 3.2 — 适配 `query_books.py:288` 的 `.dict()` 调用

**文件**: `src/calibre_mcp/tools/book_management/query_books.py` 第 285-291 行

`get_recent_books()` 返回的是 `list[dict[str, Any]]`（来自 `BookRepository._format_book()`），而不是 Pydantic BaseModel 列表。所以 `book.dict()` 会失败。

**方案选择（二选一）**：

**方案 A（推荐，最小改动）**：修改 `query_books.py` 将 `.dict()` 改为直接使用 dict：

```python
        elif operation == "recent":
            from calibre_mcp.services.book_service import book_service
            books = book_service.get_recent_books(limit=limit)
            return {
                "success": True,
                "books": list(books),  # 已为 dict 列表，无需 .dict() 转换
                "total": len(books),
                "limit": limit,
            }
```

**方案 B（更规范）**：在 `get_recent_books()` 中将 dict 包装为 `BookResponse` 再返回。但需要确保所有字段映射正确，且保持返回结构一致。

#### ✅ 阶段 3 验证

| # | 测试项 | 当前状态 | 期望状态 |
|---|---|---|---|
| 3a | `query_books(operation="recent", limit=5)` | AttributeError | 成功返回最近添加的 5 本书 |

#### ↩️ 阶段 3 回滚

```bash
git checkout -- src/calibre_mcp/services/book_service.py src/calibre_mcp/tools/book_management/query_books.py
```

---

### 2.5 阶段 4：完善配置（Bug 5）

**涉及文件**：
- `src/calibre_mcp/config.py`

#### 步骤 4.1 — 添加 `CALIBRE_LIBRARY_PATH` 到 env_mappings

**文件**: `src/calibre_mcp/config.py` 第 175-190 行

```python
env_mappings = {
    "CALIBRE_SERVER_URL": "server_url",
    "CALIBRE_USERNAME": "username",
    "CALIBRE_PASSWORD": "password",
    "CALIBRE_TIMEOUT": "timeout",
    "CALIBRE_MAX_RETRIES": "max_retries",
    "CALIBRE_DEFAULT_LIMIT": "default_limit",
    "CALIBRE_MAX_LIMIT": "max_limit",
    "CALIBRE_LIBRARY_NAME": "library_name",
    "CALIBRE_BASE_PATH": "base_library_path",
    "CALIBRE_LIBRARY_PATH": "local_library_path",  # ← 新增
    "CALIBRE_LIBRARY_PATHS": "library_paths",
    "CALIBRE_BETA_TOOLS": "load_beta_tools",
    "CALIBRE_ANNAS_MIRRORS": "annas_mirrors",
    "CALIBRE_GUTENBERG_MIRROR": "gutenberg_mirror",
    "user_config.calibre_library_path": "local_library_path",
}
```

**为什么只需要加这一行？**
- `config.py` 第 218-246 行的环境变量处理循环已经覆盖了 `local_library_path` 键（第 239-241 行：`elif config_key == "local_library_path": config_data[config_key] = Path(env_value)`）
- 添加映射后，`CALIBRE_LIBRARY_PATH` 的值会被自动读取、转换为 `Path` 对象、赋给 `config.local_library_path`
- 这与第 189 行的 `user_config.calibre_library_path: local_library_path` 共享同一个处理逻辑

#### ✅ 阶段 4 验证

| # | 测试项 | 当前状态 | 期望状态 |
|---|---|---|---|
| 4a | `CalibreConfig.load_config().local_library_path` | `None` | 指向 `E:\A_Books\Calibre书库\轻小说` |

#### ↩️ 阶段 4 回滚

```bash
git checkout -- src/calibre_mcp/config.py
```

---

## 三、验证矩阵（全量测试）

### 3.1 13 项全量测试表

| # | 工具/操作 | 依赖阶段 | 当前状态 | 期望状态 |
|---|---|---|---|---|
| 1 | `query_books(operation="search", limit=5)` | 1 | 空数据 | 返回搜索书籍列表 |
| 2 | `get_tag_statistics()` | 1 | 空数据 | 真实标签统计 |
| 3 | `manage_analysis(operation="duplicates")` | 1 | 空 | 真实重复检测结果 |
| 4 | `manage_analysis(operation="series_analysis")` | 1 | 空 | 系列分析数据 |
| 5 | `reading_statistics()` | 1 | 空 | 阅读统计数据 |
| 6 | `unread_priority_list()` | 1 | 空 | 未读优先级列表 |
| 7 | `analyze_library_health()` | 1 | 空 | 书库健康检查报告 |
| 8 | `manage_libraries(operation="list")` | 1+2 | 空列表 | 显示书库 |
| 9 | `manage_libraries(operation="switch")` | 1+2 | 找不到书库 | 成功切换 |
| 10 | `manage_libraries(operation="stats")` | 1+2 | 报错/空 | 显示书库统计 |
| 11 | `manage_system(operation="status")` | 1+2 | 发现 2 书库（空） | 显示已初始化的书库 |
| 12 | `query_books(operation="recent", limit=5)` | 1+3 | AttributeError | 返回最近添加的书籍 |
| 13 | `CalibreConfig.load_config().local_library_path` | 4 | `None` | 指向轻小说路径 |

### 3.2 验收标准

全部 13 项测试通过时，项目进入可工作状态。

---

## 四、附

### 4.1 Bug 分布热力图

```
入口层（server.py, __init__.py, server_context.py）: ████████████████████ 5 个
配置层（config.py, config_discovery.py）:             ████████████████      4 个
业务逻辑层（book_service.py）:                        ██████               1 个
工具层（library_analysis.py, storage/local.py）:      ████████████████      2 个
旧版参考（server_full.py）:                           ████                 1 个（保留）
```

入口层和配置层是重灾区，共占 Bug 的 9/12（含旧版参考）。

### 4.2 执行后的最终状态

修复全部完成后，MCP 工具的预期行为一览：

| 工具 | 正常行为 |
|---|---|
| `manage_system(operation="status")` | 显示已发现书库 + 数据库已初始化 + 书籍总数 |
| `manage_libraries(operation="list")` | 列出"轻小说"书库（来自 CALIBRE_LIBRARY_PATH） |
| `manage_libraries(operation="switch")` | 切换到指定书库 |
| `manage_libraries(operation="stats")` | 显示书籍/作者/系列/标签等统计 |
| `query_books(operation="search")` | 返回书籍搜索结果（终于有数据了） |
| `query_books(operation="recent")` | 返回最近添加的书籍（不再 AttributeError） |
| `get_tag_statistics()` | 返回标签频次统计 |
| `find_duplicate_books()` | 返回疑似重复书籍 |
| `get_series_analysis()` | 返回系列完整性分析 |
| `analyze_library_health()` | 返回书库健康检查报告 |
| `reading_statistics()` | 返回阅读统计数据 |
| `unread_priority_list()` | 返回未读书籍优先级列表 |

### 4.3 关键源码引用速查

| 文件名 | 关键行号 | 说明 |
|---|---|---|
| `server.py` | 253-272 | `server_lifespan()` — 缺少 `init_database()` |
| `server.py` | 149-250 | `_probe_calibre_connectivity()` — 缺少 CALIBRE_LIBRARY_PATH 检查 |
| `server.py` | 582-605 | `discover_libraries()` — 第 598 行硬编码 |
| `server_context.py` | 35-55 | `discover_libraries()` — 第 48 行硬编码 |
| `server_full.py` | 120-217 | 正确实现参考（含第 204 行 init_database 调用） |
| `config.py` | 175-190 | `env_mappings` — 缺少 CALIBRE_LIBRARY_PATH |
| `config.py` | 349-371 | 硬编码路径优先级逻辑 |
| `config_discovery.py` | 58-94 | `discover_all_libraries()` — 第 72 行硬编码 |
| `config_discovery.py` | 308-362 | `_scan_common_locations()` — 第 314 行硬编码 |
| `config_discovery.py` | 364-391 | `_discover_from_environment()` — 正确实现（直接读 os.environ） |
| `utils/library_utils.py` | 8 | `CALIBRE_BASE_DIR` 硬编码 |
| `utils/library_utils.py` | 11-29 | `discover_calibre_libraries()` — 需要委托 |
| `tools/__init__.py` | 28 | `CALIBRE_BASE_DIR` 未使用常量 |
| `tools/analysis/library_analysis.py` | 71,189,261,425,496,525 | 6 处 `get_session()` |
| `tools/book_management/query_books.py` | 281-291 | `operation="recent"` 处理（Bug 4 调用点） |
| `services/book_service.py` | 1446 | `book_service` 单例创建 |
| `db/repositories/book_repository.py` | 130-152 | `get_recent_books()` — 正确实现 |
| `storage/local.py` | 62-74 | 第 64 行硬编码默认路径 |

---

## 五、🏗️ 架构清理计划（Bug 修复后执行）

> **目的**: Bug 修复完成后，清理项目中遗存的新旧架构混杂问题，降低维护成本。
> **方法**: 4 个阶段，按依赖顺序执行，每阶段可独立验证、可回滚。
> **状态**: ⏳ 计划就绪，待 Bug 修复全部完成后执行

### 5.1 架构债务总览

#### 3 套工具注册系统并存

| 系统 | 机制 | 活跃工具数 | 状态 |
|---|---|---|---|
| **A — FastMCP 原生** | `@mcp.tool()` 装饰器 | 40+ | ✅ 唯一活跃的注册方式 |
| **B — BaseTool 基类** | `BaseTool` + `mcp_tool()` 装饰器 | 1（OCR） | ⚠️ 需迁移到 A |
| **C — 本地 TOOL_REGISTRY** | `tool()` 装饰器 + 全局 dict | 0 | ❌ 死代码 |

**整改**: B → A 迁移 OCR 后删除 `base_tool.py`；C 整体删除。

#### 16 个孤儿/废弃文件

| # | 文件路径 | 行数 | 原因 |
|---|---|---|---|
| 1 | `src/calibre_mcp/server_full.py` | 750+ | 旧版留档，零引用 |
| 2 | `src/calibre_mcp/server_minimal.py` | 36 | 测试用，零引用 |
| 3 | `src/calibre_mcp/server_context.py` | 55 | 零引用（且含硬编码路径） |
| 4 | `src/calibre_mcp/mcp_instance.py` | 40 | 解循环引用尝试，从未被导入 |
| 5 | `src/calibre_mcp/tools/viewer_tools.py` | ~200 | 已声明 DEPRECATED |
| 6 | `src/calibre_mcp/tools/author_tools.py` | ~100 | 旧版作者工具 |
| 7 | `src/calibre_mcp/tools/author_schemas.py` | ~50 | 旧版作者 schema |
| 8 | `src/calibre_mcp/tools/library_tools.py` | ~200 | 旧版书库工具 |
| 9 | `src/calibre_mcp/tools/tag_tools.py` | 550+ | 所有装饰器已移除，空壳 |
| 10 | `src/calibre_mcp/tools/compat.py` | 69 | 兼容性垫片，未使用 |
| 11 | `src/calibre_mcp/server/config.py` | ~50 | FastAPI 配置，被 server.py 遮蔽 |
| 12 | `src/calibre_mcp/server/main.py` | 74 | FastAPI 入口（引用了不存在的 module） |
| 13 | `src/calibre_mcp/server/mcp_server.py` | ~? | MCP 服务器包装，被遮蔽 |
| 14 | `src/calibre_mcp/server/core/exception_handlers.py` | ~? | FastAPI 异常处理器 |
| 15 | `src/calibre_mcp/server/middleware/request_logging.py` | ~? | FastAPI 中间件 |
| 16 | `src/calibre_mcp/api/libraries.py` | ~? | FastAPI 路由 |
| — | `src/calibre_mcp/api/viewer.py` | ~? | FastAPI 路由（计入上表） |

#### 配置碎片化

| 配置入口 | 机制 | 状态 |
|---|---|---|
| `config.py` (CalibreConfig) | Pydantic 模型，读取 env | ✅ 主力 |
| `config_discovery.py` (CalibreConfigDiscovery) | 自动发现逻辑 | ✅ 需要 |
| `utils/library_utils.py` | 旧式硬编码 | ❌ 删除（已纳入 Bug 修复阶段 2） |
| `tools/__init__.py` CALIBRE_BASE_DIR | 死常量 | ❌ 删除（已纳入 Bug 修复阶段 2） |

#### 功能重复

| 功能域 | 旧路径（可删） | 新路径（保留） |
|---|---|---|
| Tags | `tag_tools.py` | `tools/tags/manage_tags.py` |
| Viewer | `viewer_tools.py` | `tools/viewer/manage_viewer.py` |
| Authors | `author_tools.py` | `tools/authors/manage_authors.py` |
| Library | `library_tools.py` | `tools/library/manage_libraries.py` |

#### 目录名冲突（`server.py` vs `server/`）

> ⚠️ `server.py` 作为模块遮蔽了同目录下的 `server/` 子包，该子包下所有 FastAPI 代码**永不可达**。这是 Python 模块解析机制的常见陷阱。

---

### 5.2 清理路线图

```
Bug 修复（4 阶段）  ← 当前正在做
    ↓
阶段 A — 删除废弃文件        ← 16 个孤儿文件 → 0
    ↓
阶段 B — 统一工具注册系统     ← 3 套 → 1 套（@mcp.tool()）
    ↓
阶段 C — 合并配置层           ← 4 个入口 → 1 个（config.py）
    ↓
阶段 D — 解决 server/ 目录冲突 ← 删除子包或重命名
```

---

### 5.3 阶段 A：删除废弃文件（16 → 0）

> **前提**: 对所有拟删除的文件运行 `grep -r "module_name" src/calibre_mcp/` 确认零引用。

#### 步骤 A.1 — 直接删除的孤儿文件

```bash
# 孤儿服务器文件
rm src/calibre_mcp/server_full.py
rm src/calibre_mcp/server_minimal.py
rm src/calibre_mcp/server_context.py
rm src/calibre_mcp/mcp_instance.py

# 废弃工具文件
rm src/calibre_mcp/tools/viewer_tools.py
rm src/calibre_mcp/tools/author_tools.py
rm src/calibre_mcp/tools/author_schemas.py
rm src/calibre_mcp/tools/library_tools.py
rm src/calibre_mcp/tools/tag_tools.py

# 兼容垫片
rm src/calibre_mcp/tools/compat.py

# FastAPI 孤儿代码
rm -rf src/calibre_mcp/server/
rm -rf src/calibre_mcp/api/
```

#### 步骤 A.2 — 删除后确认 MCP 握手正常

```bash
uv run python -m calibre_mcp
# 确认无 ImportError
```

#### 注意点

- `server_full.py` 内含正确的 `init_database()` 调用示例（第 204 行）——建议先将其有用代码提取到文档，再删除
- `book_tools.py` **保留不删**——它不再注册工具，但被 `query_books.py`、`manage_metadata.py`、`manage_viewer.py` 作为内部 helper 引用

#### ✅ 阶段 A 验证

| # | 测试项 | 期望状态 |
|---|---|---|
| A1 | `uv run python -m calibre_mcp` | 0 个 ImportError，MCP 握手成功 |
| A2 | `manage_system(operation="status")` | 与清理前行为完全一致 |
| A3 | `query_books(operation="search", limit=5)` | 与清理前行为完全一致 |

#### ↩️ 阶段 A 回滚

```bash
git checkout -- src/calibre_mcp/server_full.py src/calibre_mcp/server_minimal.py src/calibre_mcp/server_context.py src/calibre_mcp/mcp_instance.py src/calibre_mcp/tools/viewer_tools.py src/calibre_mcp/tools/author_tools.py src/calibre_mcp/tools/author_schemas.py src/calibre_mcp/tools/library_tools.py src/calibre_mcp/tools/tag_tools.py src/calibre_mcp/tools/compat.py
git checkout -- src/calibre_mcp/server/ src/calibre_mcp/api/
```

---

### 5.4 阶段 B：统一工具注册系统（3 → 1）

#### 步骤 B.1 — OCR 工具迁移到 `@mcp.tool()`

**文件**: `src/calibre_mcp/tools/ocr/calibre_ocr_tool.py`

OCRTool 是唯一使用 `BaseTool` + `mcp_tool()` 装饰器的工具。需要重写为标准 `@mcp.tool()` 装饰器风格：

```python
# 修改前: class OCRTool(BaseTool) + @mcp_tool()
# 修改后: 模块级 async def 函数 + @mcp.tool()

@mcp.tool()
async def manage_ocr(
    operation: str = "recognize",
    image_path: str = "",
    language: str = "chi_sim+eng",
) -> dict[str, Any]:
    """OCR recognition for book covers and images."""
    # ... 原 OCRTool 的业务逻辑 ...
```

#### 步骤 B.2 — 删除 `base_tool.py`

**文件**: `src/calibre_mcp/tools/base_tool.py`

确认 OCR 迁移完成后，整个文件可删除（包含 `BaseTool` 类、`mcp_tool()` 装饰器、代码生成逻辑）。

#### 步骤 B.3 — 清理 `tools/__init__.py` 中的死代码

**文件**: `src/calibre_mcp/tools/__init__.py`

清理项：

| 行号 | 代码 | 操作 |
|---|---|---|
| 25 | `TOOL_REGISTRY: dict[str, dict[str, Any]] = {}` | 删除 |
| 27-28 | `CALIBRE_BASE_DIR = Path("L:/Multimedia Files/Written Word")` | 删除（已纳入 Stage 2 Bug 修复） |
| 37-72 | `tool()` 装饰器定义 + `def tool(name=None, ...)` | 删除 |
| 75-89 | `get_available_tools()` 函数 | 删除 |
| 92-124 | `discover_tools()` 函数 | 删除 |
| 238-242 | `from .ocr.calibre_ocr_tool import OCRTool` + `OCRTool.register(mcp)` | 删除（OCR 迁移后） |

**`register_tools(mcp)` 保留**——这是实际的工具注册入口，调用各 portmanteau 模块的导入。

#### 步骤 B.4 — 精简 `register_tools()` 函数

**文件**: `src/calibre_mcp/tools/__init__.py` 第 127-294 行

删除旧式导入，保留现代导入：

```python
def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with the server using explicit imports."""

    # --- Portmanteau tools (modern @mcp.tool() style) ---
    from .library import manage_libraries
    from .book_management import manage_books, query_books, search_fulltext
    from .analysis import manage_analysis, library_analysis
    # ... 保留所有现代导入 ...

    # [已删除] from .ocr.calibre_ocr_tool import OCRTool
    # [已删除] OCRTool.register(mcp)
```

#### ✅ 阶段 B 验证

| # | 测试项 | 期望状态 |
|---|---|---|
| B1 | `uv run python -m calibre_mcp` | 启动正常，无 ImportError |
| B2 | 所有阶段 1-4 验证项 | 与清理前完全一致 |
| B3 | OCR 相关工具 | 功能正常（如适用） |

#### ↩️ 阶段 B 回滚

```bash
git checkout -- src/calibre_mcp/tools/base_tool.py src/calibre_mcp/tools/__init__.py src/calibre_mcp/tools/ocr/calibre_ocr_tool.py
```

---

### 5.5 阶段 C：合并配置层

#### 现状

配置逻辑分散在 3 个文件中：

```
config.py ············· Pydantic 模型，env → 属性映射（应该成为唯一入口）
config_discovery.py ··· 书库自动发现逻辑（应该成为 config.py 的子模块或方法）
utils/library_utils.py· 旧式发现（Bug 修复阶段 2 中已删除委托）
```

#### 建议方案

**短期方案**（推荐，最小改动）：
- Bug 修复阶段 2 已将 `utils/library_utils.py` 委托给 `config_discovery.py`
- 保持 `config.py` 和 `config_discovery.py` 分离——两者有明确职责划分：一个管配置加载，一个管书库发现
- 只需要确认 `config.py` 在使用发现结果时走 `config_discovery.py` 而非旧管线

**长期方案**（可选的后续优化）：
- 将 `config_discovery.py` 的 `CalibreConfigDiscovery.discover_libraries()` 合并为 `CalibreConfig` 的一个方法
- 但合并的收益有限：两个类已有独立职责，保持分离更清晰且不影响功能

#### ✅ 阶段 C 验证

与 Bug 修复阶段 2 验证项重叠，无需额外测试。

#### ↩️ 阶段 C 回滚

无需回滚（建议取短期方案，不涉及代码合并）。

---

### 5.6 阶段 D：解决 `server/` 目录冲突

#### 问题

```
src/calibre_mcp/
├── server.py          ← Python 模块（导入时优先匹配这个）
├── server/            ← 目录包（永远无法被导入，因为 server.py 遮蔽了它）
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── mcp_server.py
│   ├── core/
│   └── middleware/
```

Python 的模块解析规则：`server.py` 优先于 `server/` 子包。该目录下所有 FastAPI 代码虽然存在，但 `from server import ...` 永远解析不到它们。

#### 建议方案

删除 `server/` 子包（已在阶段 A 中涵盖）。如果未来需要 HTTP 传输层，应该：
1. 使用 FastMCP 内建的 SSE/Streamable HTTP 支持（FastMCP 3.2+ 已有此能力）
2. 或新建一个不冲突的目录名（如 `http_server/`）

#### ✅ 阶段 D 验证

与阶段 A 验证项重叠，无需额外测试。

#### ↩️ 阶段 D 回滚

```bash
git checkout -- src/calibre_mcp/server/
```

---

### 5.7 清理后目录结构（预期）

```
清理前: 43+ 个 .py 文件，3 套注册系统，16 个孤儿文件
清理后: ~25 个 .py 文件，1 套注册系统（@mcp.tool()），0 个孤儿文件
```

```
src/calibre_mcp/
├── __init__.py, __main__.py
├── server.py                        # 主入口（唯一 FastMCP 实例）
├── config.py                        # 配置（唯一配置入口）
├── config_discovery.py              # 书库发现逻辑
├── calibre_api.py                   # Calibre 远程 API
├── db/, models/, services/          # 数据层、模型层、服务层
├── tools/
│   ├── __init__.py                  # 仅有 register_tools()，无 TOOL_REGISTRY
│   ├── base_tool.py                 # [已删除]
│   ├── analysis/                    # 分析工具
│   ├── book_management/             # 书籍管理
│   ├── library/                     # 书库管理
│   └── ...                          # portmanteau 子包（保留）
├── server_full.py                   # [已删除]
├── server_minimal.py                # [已删除]
├── server_context.py                # [已删除]
├── mcp_instance.py                  # [已删除]
├── server/                          # [已删除]
└── api/                             # [已删除]
```

---

### 5.8 执行顺序 & 约束

| 执行顺序 | 阶段 | 前置条件 | 是否可以并行 |
|---|---|---|---|
| 第 1 | Bug 修复（4 阶段） | 无 | 否（顺序执行） |
| 第 2 | **A — 删除废弃文件** | Bug 修复完成 | 独立 |
| 第 3 | **B — 统一工具注册** | 阶段 A 完成 | 独立 |
| 第 4 | **C — 合并配置层** | Bug 修复阶段 2 完成 | 与 B 并行 |
| 第 5 | **D — 目录冲突解决** | 阶段 A 完成 | 与 B/C 并行 |

> ⚠️ 所有清理阶段均不得影响修复后的功能行为。每个阶段后运行验证矩阵确认回归。

---

### 5.9 风险 & 注意事项

1. **删除前必须全局搜索确认**：每个文件删除前需用 `grep -r` 确认零引用
2. **OCR 迁移优先级**：阶段 B 的 OCR 工具迁移需要理解 OCR 业务逻辑，如不熟悉可暂缓
3. **`book_tools.py` 保留**：虽名似旧工具文件，但作为内部 helper 被 3 个工具文件引用
4. **`server_full.py` 参考价值**：先将其正确的 `init_database()` 调用提取到文档再删除
5. **`compat.py` 垫片**：虽然未被当前代码引用，但如果未来集成第三方包可能依赖它。确认后再删
6. **git 分支隔离**：建议在独立分支上进行清理，方便逐阶段回滚
