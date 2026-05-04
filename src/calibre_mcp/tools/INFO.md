# `tools/` MCP 工具层（核心）

> **职责**: 所有 MCP 工具的注册和实现。采用 Portmanteau 模式——每个工具以 `operation` 参数区分多个子操作。
> 共 22 个子目录 + 12 个根层文件。工具通过 `tools/__init__.py` 的 `register_tools()` 注册到 FastMCP。
>
> **⚠️ 旧版 INFO.md 中的 Bug 描述已过时**：硬编码路径、get_session()、get_recent_books() 问题已全部修复。

---

## 根层文件（遗留/辅助）

| 文件 | 大小 | 说明 |
|---|---|---|
| `__init__.py` | 11KB | **`register_tools(mcp)`** — 核心入口，导入所有 portmanteau |
| `base_tool.py` | 6KB | `BaseTool` 抽象类 + `mcp_tool` 装饰器（旧式注册机制） |
| `compat.py` | 2KB | 兼容层 |
| `book_tools.py` | 64KB | **⚠️ 旧式书籍工具**（可能被 portmanteau 替代，最大文件） |
| `tag_tools.py` | 21KB | ⚠️ 旧式标签工具 |
| `library_tools.py` | 6KB | ⚠️ 旧式书库工具 |
| `viewer_tools.py` | 2KB | 视图工具 |
| `author_schemas.py` | 9KB | 作者 schema |
| `agentic.py` | 8KB | 代理工作流工具 |
| `agentic_workflow.py` | 29KB | 高级代理工作流 |
| `ocr_output_schema.py` | 1KB | OCR 输出 schema |

---

## Portmanteau 工具子目录

### `library/` — ⭐ manage_libraries
- `manage_libraries.py` (12KB) — portmanteau 注册入口（@mcp.tool()）
- `library_management.py` (33KB) — **核心实现**（list/switch/stats/search）
- `library_discovery.py` (13KB) — discover 操作实现

**操作**: list → switch → stats → search → test_connection → discover

### `book_management/` — ⭐ manage_books + query_books
- `manage_books.py` (13KB) — 书籍 CRUD portmanteau（add/get/details/update/delete）
- `query_books.py` (15KB) — **搜索 portmanteau**（search/list/recent/by_author/by_series）
  - ✅ `operation="recent"` 已修复（`get_recent_books()` 存在）
  - ⚠️ `text` 搜索参数无效（参见下方已知问题）
- `add_book.py` (11KB), `add_books.py` (3KB), `delete_book.py` (9KB)
- `get_book.py` (8KB), `update_book.py` (14KB)
- `fulltext_search.py` (8KB) — 全文搜索

### `system/` — ⭐ manage_system
- `manage_system.py` (8KB) — 系统管理 portmanteau（help/status/health_check/hello_world）
- `system_tools.py` (45KB) — **系统工具实现**

### `analysis/` — ⭐ manage_analysis
- `manage_analysis.py` (6KB) — 分析 portmanteau
- `library_analysis.py` (21KB) — ✅ 已修复（6 处 `get_session()` 已改为 `session_scope()`）
  - 函数: `get_tag_statistics`, `find_duplicate_books`, `get_series_analysis`, `analyze_library_health`, `unread_priority_list`, `reading_statistics`
- `analyze_library.py` (13KB), `analysis_helpers.py` (3KB)

### `portmanteau/` — 跨域 Portmanteau
- `media_agentic.py` (32KB) — 媒体研究：`media_critical_reception`, `media_deep_research`, `media_research_book`, `media_synopsis`
- `search.py` (6KB) — `calibre_rag` portmanteau

### `prefab/` — 卡片 UI 组件
- `book_card.py` (7KB) — `show_book_prefab_card`
- `libraries_card.py` (5KB) — `show_libraries_prefab_card`

### `rag/` — RAG 工具
- `manage_rag.py` (12KB) — `calibre_rag`, `rag_index_build`, `rag_retrieve`

### `shared/` — 共享工具
- `error_handling.py` (8KB) — `format_error_response()`, `handle_tool_error()`
- `query_parsing.py` (17KB) — `parse_intelligent_query()` — 智能查询解析

### `metadata/` — ⭐ manage_metadata
- `manage_metadata.py` (16KB) — **show/update/organize_tags/fix_issues**
  - ✅ `operation="update", field="comments"` 已修复（`book_service.py` 的 Comment 关系处理）
  - ✅ `operation="show"` 已修复（导入 bug + datetime 格式 + 改用 title 参数搜索）
  - `metadata_management.py` — update 操作实现

---

## 普通工具子目录

| 目录 | 文件 | 大小 | 主要操作 |
|---|---|---|---|
| `authors/` | `manage_authors.py` | 8KB | `list`, `search`, `merge`, `stats` |
| `tags/` | `manage_tags.py` | 14KB | `list`, `search`, `merge`, `rename`, `delete`, `stats` |
| `series/` | `manage_series.py` | 5KB | `list`, `search`, `merge`, `stats` |
| `publishers/` | `manage_publishers.py` | 5KB | `list`, `search`, `stats` |
| `comments/` | `manage_comments.py` | 8KB | `list`, `add`, `update`, `delete` |
| `files/` | `manage_files.py` | 7KB | `list_formats`, `add_format`, `remove_format` |
| `viewer/` | `manage_viewer.py` | 34KB | `open`, `open_random`, `get_page`, `get_toc` |
| `core/` | `library_operations.py` | 7KB | 核心库操作 |
| `help_tools/` | `help.py` | 24KB | 帮助系统 |

---

## 工具注册流程
```
server.main()
    └──> tools.__init__.register_tools(mcp)
              │
              ▼
        导入所有 portmanteau 模块
              │
              ├── library/manage_libraries.py    → @mcp.tool() manage_libraries()
              ├── book_management/manage_books.py → @mcp.tool() manage_books()
              ├── book_management/query_books.py  → @mcp.tool() query_books()
              ├── analysis/manage_analysis.py     → @mcp.tool() manage_analysis()
              ├── system/manage_system.py         → @mcp.tool() manage_system()
              ├── series/manage_series.py         → @mcp.tool() manage_series()
              ├── tags/manage_tags.py             → @mcp.tool() manage_tags()
              ├── authors/manage_authors.py       → @mcp.tool() manage_authors()
              └── 等等
```

## 当前已知问题
- **text 搜索无效**: `book_service.get_all(search=...)` 的 LIKE 过滤不生效，返回全部 914 本书
  - 绕过: 使用 `series`、`title`、`author` 等独立参数
- **has_empty_comments 过滤无效**: `Book` 模型无该字段，且未作为特例处理，静默忽略

## 相关文档
- `services/INFO.md` — 被 tools 调用的业务逻辑层
- `ARCHITECTURE.md` — 项目架构总览
