# 重构依赖地图（Phase 1 完成）

> 最新更新: 2026-05-04 (Phase 1)
> 初始生成: 2026-05-04 (Phase 0)
> 目的: 记录所有 MCP 工具的依赖关系，为后续重构提供安全参考

---

## 一、工具-服务依赖矩阵

### 🔴 依赖 `book_service` 的工具族（Phase 1-3 重构核心目标）

| # | MCP 工具 | 端口文件 | 使用的 `book_service` 方法 | 依赖强度 |
|---|---|---|---|---|
| 1 | **query_books** | `book_management/query_books.py` → `book_tools.search_books_helper()` | `get_all()` 全部功能 | 🔴 超重度 (1075行helper) |
| 2 | **manage_books** | `book_management/manage_books.py` → 4 helpers | `get_by_id`, `create`, `update`, `delete` | 🔴 重度 (CRUD) |
| 3 | **manage_metadata** | `metadata/manage_metadata.py` → `metadata_management` | `update()` | 🟡 中度 |
| 4 | **manage_libraries** | `library/manage_libraries.py` → `library_management.py` | `get_all()`, 统计 | 🟢 轻度 |
| 5 | **rag/manage_rag** | `rag/manage_rag.py` (直接导入) | 书籍信息查询 | 🟢 轻度 |
| 6 | **library_operations** | `library_operations/list_books.py` | `get_all()` | 🟢 轻度 |

### 🟢 完全独立的工具（各自有专属 service）

| # | MCP 工具 | 端口文件 | 使用的 Service |
|---|---|---|---|
| 7 | **manage_authors** | `authors/manage_authors.py` → `author_helpers.py` | `author_service` |
| 8 | **manage_tags** | `tags/manage_tags.py` → `tag_helpers.py` | `tag_service` |
| 9 | **manage_series** | `series/manage_series.py` → `series_helpers.py` | `series_service` |
| 10 | **manage_publishers** | `publishers/manage_publishers.py` → `publisher_helpers.py` | `publisher_service` |
| 11 | **manage_comments** | `comments/manage_comments.py` → `comment_helpers.py` | 无 |
| 12 | **manage_viewer** | `viewer/manage_viewer.py` | `viewer_service` |
| 13 | **manage_files** | `files/manage_files.py` → `file_operations.py` | 无 |
| 14 | **manage_analysis** | `analysis/manage_analysis.py` → `library_analysis.py` | `DatabaseService` 直连 |
| 15 | **manage_system** | `system/manage_system.py` → `system_tools.py` | `DatabaseService` 直连 |
| 16 | **export_books** | `import_export/export_books_portmanteau.py` → `export_helpers.py` | 无 |
| 17 | **help_tool** | `help_tools/help.py` | 无 |
| 18 | **search_fulltext** | `book_management/fulltext_search.py` | FTS SQLite 直连 |

### 🟣 完全独立的工具（外部 API / 引擎）

| # | MCP 工具 | 端口文件 | 依赖 |
|---|---|---|---|
| 19-22 | **media_*** | `portmanteau/media_agentic.py` | 外部 Web API |
| 23-25 | **rag_*, calibre_rag, calibre_metadata_*** | `rag/manage_rag.py` | LanceDB 引擎 |
| 26-27 | **prefab_card*** | `prefab/` | `prefab_ui` 库 |
| 28 | **fetch_volume_synopses** | `metadata/linovelib_synopses.py` | Web 爬虫 |
| 29 | **enrich_book_metadata** | `metadata/web_enrichment.py` | Web 爬虫 |

### 📦 Beta 工具（CALIBRE_BETA_TOOLS=true）
| 工具 | 端口 |
|---|---|
| manage_bulk, content_sync, agentic, AI, descriptions, extended_metadata, import, organization, specialized, times, user_comments, users | `advanced_features/`, `agentic/`, `ai/`, `descriptions/`, 等 |

---

## 二、`book_service.py` 方法归属（按工具域标注）

| 方法 | 域 | 给谁用 |
|---|---|---|
| `get_all()` | **query_books** | 搜索/过滤/排序/分页主入口 |
| `get_by_id()` | **manage_books** + **manage_metadata** | 书籍详情查询 |
| `create()` | **manage_books** | 新增书籍 |
| `update()` | **manage_books** + **manage_metadata** | 更新元数据（含 comments 特殊处理） |
| `delete()` | **manage_books** | 删除书籍 |
| `get_recent_books()` | **query_books** | 最近添加列表 |
| `get_book_formats()` | **manage_books** | 文件格式查询 |
| `get_book_cover()` | **manage_books** | 封面图片 |
| `_to_response()` | (内部) | 所有工具共用输出格式化 |
| `_get_library_base_path()` | (内部) | 库路径解析 |

---

## 三、已清理的死代码

### Phase 0.2-0.4 完成（2026-05-04）

| 原位置 | 处理 | 新位置/名称 |
|---|---|---|
| `src/calibre_mcp/server_full.py` (24KB) | ✅ 移入 archived/ | `archived/server_full.py` |
| `src/calibre_mcp/server/` (~16KB) | ✅ 整体移入 archived/ | `archived/server/` |
| `tools/__init__.py:TOOL_REGISTRY` | ✅ 加前缀 | `_DEPRECATED_TOOL_REGISTRY` |
| `tools/__init__.py:tool()` | ✅ 加前缀 | `_DEPRECATED_tool()` |
| `tools/__init__.py:get_available_tools()` | ✅ 加前缀 | `_DEPRECATED_get_available_tools()` |
| `tools/__init__.py:discover_tools()` | ✅ 加前缀 | `_DEPRECATED_discover_tools()` |

### 保留未处理（仍活跃）

| 代码 | 原因 |
|---|---|
| `BaseTool` 类 (`base_tool.py`) | `OCRTool(BaseTool)` 仍在使用 |
| `mcp_tool()` 装饰器 | OCR 工具使用 |
| `base_tool.py` | OCR 工具导入 |

---

## 四、功能冗余/重叠记录

| 重叠对 | 描述 | 后续处理建议 |
|---|---|---|
| `manage_books(update)` vs `manage_metadata(update)` | 同一条 `book_service.update()` 两条路径 | Phase 2 合并到 `manage_books` |
| `query_books(search)` vs `query_books(list)` | search 走 1075 行 helper, list 走另类实现 | Phase 1 统一 |
| `manage_analysis(tag_statistics)` vs `manage_tags(stats)` | 标签统计重叠 | Phase 3 清理 |
| `manage_metadata(show)` vs `query_books(search)` | 书籍详情重叠 | Phase 3 清理 |

---

## 五、Phase 1 修复记录（已完成）

### 修复 1: Session 生命周期 Bug ✅
- **文件**: `services/book_service.py:get_all()`
- **问题**: `with self._get_db_session() as session:` 退出 with 块后 session 自动关闭，后续所有查询操作使用已关闭的 session
- **修复**: 替换为 `session = self._get_db_session(); try: ... except: ... finally: session.close()`
- **影响**: 所有通过 `get_all()` 的路径（text 搜索、过滤、排序）不再因 session 关闭而出错

### 修复 2: has_empty_comments 过滤无效 ✅
- **文件**: `services/book_service.py:get_all()`（`**filters` 循环内）
- **问题**: `has_empty_comments` 作为 `**filters` 传入后，因 `Book` 模型无此字段且无特例处理，被静默忽略
- **修复**: 新增 `elif field == "has_empty_comments":` 处理分支
  - `True`: 子查询排除有非空 comments 的书 → 返回无 comments 或 comments 为空的书籍
  - `False`: JOIN comments 表并过滤 text 非空 → 返回有非空 comments 的书籍
- **影响**: `query_books(has_empty_comments=True/False)` 正确过滤

### 验证状态
- ⚠️ 代码变更已写入磁盘，需要重启 MCP 服务进程后生效
- 测试确认 title 搜索正常（11 条结果），参数传递链路完整

---

## 六、后续计划

```
Phase 2: book_tools.search_books_helper 拆入 book_management/helpers/
Phase 3: book_service.py 按工具域拆分
Phase 4: 遗留清理（library_utils 归并）
Phase 5: 测试加固
```
