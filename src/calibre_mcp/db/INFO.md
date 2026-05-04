# `db/` 数据库层

> **职责**: 管理 SQLAlchemy 数据库连接、ORM 模型映射、Repository 模式的数据访问。
> 连接 Calibre 的 `metadata.db` SQLite 文件，提供统一的 CRUD 接口。
>
> **⚠️ 旧版 INFO.md 中的 Bug 描述已过时**:
> - `init_database()` 已在 `server_lifespan()` 中调用 ✅
> - `get_recent_books()` 已通过 BookService 暴露 ✅

---

## 核心文件

### `database.py` (8KB) ⭐ 入口
- **`DatabaseService`** — 单例模式，管理数据库连接和会话
  - `initialize(db_url, echo, force)` — 初始化数据库引擎
  - `session` — 属性，获取一个数据库 Session
  - `session_scope()` — 上下文管理器，自动 commit/rollback/close
  - `get_repository(name)` — 获取指定 repository
  - `close()` — 关闭连接
  - `get_current_path()` — 获取当前数据库路径
- **顶层函数**:
  - `init_database(db_path, echo, force)` — 初始化全局数据库实例（✅ `server_lifespan()` 已调用）
  - `close_database()` — 关闭全局数据库
  - `get_database()` — 获取全局 DatabaseService 实例
- **依赖**: SQLAlchemy, scoped_session

### `models.py` (8KB) — SQLAlchemy ORM 模型
- **映射 Calibre metadata.db 的表**:
  - `Book` — 书籍（title, author_sort, timestamp, rating, series_index, last_modified, path, has_cover）
  - `Author` — 作者（name, sort, link）
  - `Series` — 系列（name）
  - `Tag` — 标签（name）
  - `Publisher` — 出版社（name）
  - `Rating` — 评分（rating 1-10）
  - `Comment` — 评论/描述（text）
  - `Data` — 文件格式（book_id, format, name, uncompressed_size）
  - `Identifier` — 标识符（type, value）
  - **关联关系**: books_authors 链接表, books_series_link, books_tags_link, books_publishers_link
- **用途**: 所有 SQLAlchemy 查询使用此处模型
- **注意**: `comments` 是 `Comment` 关系对象（`uselist=False`），不是字符串

### `base_repository.py` (5KB) — 抽象基类
- **`BaseRepository[T]`** — 泛型 CRUD 基类
  - `get(id)`, `get_all(...)`, `create(obj)`, `update(id, obj)`, `delete(id)`
  - `count()`, `search(query)`, `exists(id)`

### `concurrency.py` (4KB) — 并发控制
- `DatabaseConcurrencyManager` — 数据库并发管理器
- `ThreadSafeRepository` — 线程安全的 Repository 包装

### `user_data.py` (7KB) — 用户数据 DB
- **用途**: 非 Calibre 的用户数据（评论、元数据、用户认证）独立 SQLite
- **`UserDataDB`** — 用户数据库操作
- ORM: `UserComment`, `BookExtendedMetadata`, `User`
- 顶层: `init_user_data_db()`, `get_user_data_db()`

---

## Repository 实现 (`repositories/`)

### `book_repository.py` (15KB)
- **`BookRepository`** ⭐ 最大的 repository
  - `get_by_id(id)` — 按 ID 获取
  - `get_recent_books(limit)` — **最近添加的书籍**（✅ 已通过 BookService 暴露）
  - `get_all(...)` — 多条件搜索（author, tag, series, rating, search text）
  - `create(book_data)`, `update(book_id, book_data)`, `delete(book_id)`
  - `get_book_formats(book_id)`, `get_book_cover(book_id)`
  - `get_reading_progress(book_id)`, `update_reading_progress(...)`

### `author_repository.py` (11KB)
- **`AuthorRepository`** — 作者查询和统计
  - `get_all()`, `get_by_id(id)`, `search(name)`, `get_book_count(author_id)`
  - `get_author_statistics()` — 作者书籍分布统计

### `library_repository.py` (13KB)
- **`LibraryRepository`** — 书库级别统计
  - `get_library_statistics()` — 书籍/作者/系列/标签总数
  - `get_recently_added(limit)` — 最近添加
  - `get_recently_modified(limit)` — 最近修改
  - `get_format_distribution()` — 格式分布
  - `get_rating_distribution()` — 评分分布

### `user_repository.py` (1KB)
- **`UserRepository`** — 用户管理（基于 user_data.py 的 User 模型）

---

## 数据流
```
server_lifespan()
    └──> init_database("/path/to/metadata.db")     ✅ 已调用
              │
              ▼
        DatabaseService.initialize()
              │
              ├──> create_engine(sqlite:///...)
              ├──> scoped_session(sessionmaker)
              └──> init repositories
                      │
                      ▼
               tools/services → BookRepository.get_all()
                              → BookRepository.get_recent_books()
                              → BookRepository.get_by_id()
```

## 相关文档
- `services/INFO.md` — 业务逻辑层（使用 repositories）
- `models/INFO.md` — Pydantic 数据模型
