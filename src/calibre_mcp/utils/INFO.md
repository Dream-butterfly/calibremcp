# `utils/` 工具函数

> **职责**: 杂项工具函数，不属于核心业务逻辑。
> 共 5 个文件。
>
> **Phase 4 清理（2026-05-06）**: `library_utils.py` 已删除，功能迁至 `config_discovery.py`：
> - `discover_calibre_libraries()` → `config_discovery`（原已是转发层）
> - `get_library_metadata(path)` → `config_discovery` 新增模块级函数
> - `get_current_library()` → 无人使用，删除

---

## 文件清单

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
    └──> config_discovery (library_utils 已合并至此，模块已删除 ✅)

tools/book_management/fulltext_search.py
    └──> utils.fts_utils.search_fts()

tools/metadata/web_enrichment.py
    └──> utils.fts_location_resolver

多处的输出格式化
    └──> utils.book_formatter.format_book()
```

## 相关文档
- `tools/INFO.md` — MCP 工具层（工具们导入这些 utils）
- `ARCHITECTURE.md` — 架构总览
