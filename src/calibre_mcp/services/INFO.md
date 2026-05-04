# `services/` 业务逻辑层

> **职责**: 封装业务逻辑，调用 Repository 层进行数据访问。工具层（tools/）调用此层。
> 共 15 个 Service 文件，其中以 `BaseService` 为核心的 5 个 CRUD Service 使用泛型模式。
>
> **⚠️ 旧版 INFO.md 中的 Bug 描述已过时**: `get_recent_books()` 已不存在缺失问题（L1299 已实现）。

---

## 核心 Service（基于 BaseService 泛型）

### `base_service.py` (12KB) — 基类
- `ServiceError`, `NotFoundError`, `ValidationError` — 异常类
- **`BaseService[Model, Create, Update, Response]`** — 泛型 CRUD 基类
  - `__init__(db, model_class, response_class)` — 初始化，自动获取 repository
  - `get_by_id(id)` → Response dict
  - `get_all(...)` — 多条件搜索（search, author, tag, series, rating, skip, limit）
  - `create(data)`, `update(id, data)`, `delete(id)`
  - `count()`, `exists(id)`

### `book_service.py` (~1KB) ⭐ Facade（Phase 3 已拆分）
- **Phase 3 拆分（2026-05-06）**: 原 63KB 文件按管理域拆分为 3 个文件:
  - **`book_query_service.py`** (~30KB) — 只读方法（`get_all`, `get_by_id`, `get_book_formats`, 等）
  - **`book_management_service.py`** (~7KB) — 写方法（`create`, `update`, `delete`）
  - **`book_service.py`** (~1KB) — 薄 Facade，多继承合并两者
- **`BookService(BookQueryService, BookManagementService)`** — 多继承 Facade
- 所有 26 处 `from ...services.book_service import book_service` 导入不受影响 ✅
- 关键方法一览:
  - `get_by_id(book_id)` — 获取书籍详情（含关联数据）— book_query_service
  - `get_all(...)` — **主搜索入口**（✅ Phase 1 修复）— book_query_service
  - `create(book_data, file_path)` — 添加书籍并导入文件 — book_management_service
  - `update(book_id, book_data)` — 更新元数据（✅ 已修复注释写入）— book_management_service
  - `delete(book_id)` — 删除书籍 — book_management_service
  - `get_book_formats(book_id)` — 获取文件格式 — book_query_service
  - `get_book_cover(book_id)` — 获取封面图片 — book_query_service
  - `get_recent_books(limit)` — 最近添加书籍 — book_query_service
  - `get_books_by_series(series_id)` — 系列内所有书籍 — book_query_service

### `tag_service.py` (18KB)
- `TagService(BaseService[Tag, TagCreate, TagUpdate, TagResponse])`
- 扩展方法: `get_tag_statistics()` — 标签使用统计

### `author_service.py` (13KB)
- `AuthorService(BaseService[Author, AuthorCreate, AuthorUpdate, AuthorResponse])`
- 扩展方法: `get_author_statistics()`, `get_books_by_author(author_id)`

### `series_service.py` (8KB)
- `SeriesService` — 系列管理
- 方法: `get_series_with_books(series_id)`, `get_reading_order(series_id)`

### `publisher_service.py` (16KB)
- `PublisherService` — 出版社管理

### `library_service.py` (20KB)
- `LibraryService(BaseService[Library, LibraryCreate, LibraryUpdate, LibraryResponse])`
- 扩展方法: `get_library_statistics()`, `switch_library(...)`

---

## 专用 Service

### `viewer_service.py` (9KB) — 阅读器
### `user_service.py` (2KB) — 用户认证
### `user_comment_service.py` (7KB) — 用户评论
### `description_service.py` (7KB) — 书籍描述管理
### `extended_metadata_service.py` (7KB) — 扩展元数据
### `times_service.py` (7KB) — 阅读时间追踪

---

## 索引/导入 Service

### `deep_ingestor.py` (5KB) — 深度索引
### `rag_ingestor.py` (6KB) — RAG 索引器

---

## 数据流依赖
```
tools/ (portmanteau)
    │
    ▼
services/ (BookService, TagService, etc.)
    │  ✅ get_recent_books() 已实现（L1299）
    ▼
repositories/ (BookRepository, etc.)
    ▼
database.py (DatabaseService + session_scope)
```

## ⚠️ 注意事项
- **两个不同的 `Book` 模型**: `book_service.py` 使用 `db.models.Book`（`series` 是直接 `relationship`），`book_repository.py` 使用 `models.Book`（`series` 是 `@property`，`series_rel` 是关系）
- **`has_empty_comments` 过滤**: ✅ 已在 Phase 1 修复（`**filters` 循环特例处理 + 子查询/JOIN）

### 文件大小一览
| 文件 | 大小 | 备注 |
|---|---|---|
| `book_query_service.py` | ~30KB | Phase 3 从 book_service.py 拆分 |
| `library_service.py` | 20KB | |
| `tag_service.py` | 18KB | |
| `publisher_service.py` | 16KB | |
| `author_service.py` | 13KB | |
| `base_service.py` | 12KB | 泛型基类 |
| `viewer_service.py` | 9KB | |
| `series_service.py` | 8KB | |
| `book_management_service.py` | ~7KB | Phase 3 从 book_service.py 拆分 |
| `user_comment_service.py` | 7KB | |
| `description_service.py` | 7KB | |
| `extended_metadata_service.py` | 7KB | |
| `times_service.py` | 7KB | |
| `rag_ingestor.py` | 6KB | |
| `deep_ingestor.py` | 5KB | |
| `user_service.py` | 2KB | |
| `book_service.py` | ~1KB | Phase 3 重构为薄 Facade |

## 相关文档
- `db/INFO.md` — 数据库层（Repository）
- `models/INFO.md` — 数据模型
