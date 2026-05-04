# `utils/` 工具函数

> **职责**: 杂项工具函数，不属于核心业务逻辑。
> 共 6 个文件。
>
> **⚠️ 旧版 INFO.md 中的 Bug 描述已过时**: `library_utils.py` 的硬编码路径问题已于 2026-05-04/05-06 修复。

---

## 文件清单

### `library_utils.py` (3KB) ⚠️ 曾为 Bug 2 根因
- **函数**: `discover_calibre_libraries()` → `dict[str, Path]`
- **历史**: 曾含 `CALIBRE_BASE_DIR = Path("L:/Multimedia Files/Written Word")` 硬编码路径
- **当前**: ✅ 硬编码路径已删除，功能委托给 `config_discovery.py` 的新管线
- **函数**: `get_library_metadata(path)` → 通过 `sqlite3` 直连 `metadata.db` 获取书库信息
- **函数**: `get_current_library()` → 获取当前活跃书库

### `book_formatter.py` (7KB) — 书籍格式化
- **函数**: `format_book(book_dict)` → 将书籍数据格式化为多行可读文本
- **函数**: `format_book_list(books)` → 格式化书籍列表
- **被谁导入**: 多个 tools/ 中的输出格式化

### `finereader.py` (18KB) — FineReader OCR
- **类**: `FineReaderEngine` — ABBYY FineReader CLI 封装

### `got_ocr.py` (9KB) — 通用 OCR
- **类**: `GOTOCREngine` — GOT-OCR2.0 封装

### `fts_location_resolver.py` (5KB) — 全文搜索路径
- **函数**: `resolve_location(book_id, format, location_hint)` → 位置转换

### `fts_utils.py` (16KB) — 全文搜索工具
- **函数**:
  - `find_fts_database(metadata_db_path)` — 寻找 FTS 数据库
  - `query_fts(...)` — 搜索 FTS 数据库（FTS5 → LIKE 回退）
  - `query_fts_detailed(...)` — 详细查询（含偏移量）
- **依赖**: SQLite FTS5 扩展

---

## 导入依赖图

```
tools/library/library_management.py
    └──> utils.library_utils           (✅ 硬编码路径已删除)

tools/book_management/fulltext_search.py
    └──> utils.fts_utils.search_fts()

tools/metadata/web_enrichment.py
    └──> utils.fts_location_resolver

多处的输出格式化
    └──> utils.book_formatter.format_book()
```

## 当前已知问题
- **无安全删除**: `library_utils.py` 的部分功能与 `config_discovery.py` 存在重复，可考虑后续清理

## 相关文档
- `tools/INFO.md` — MCP 工具层（工具们导入这些 utils）
- `ARCHITECTURE.md` — 架构总览
