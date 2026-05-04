# `models/` Pydantic 数据模型

> **职责**: 请求/响应的数据模型（Pydantic BaseModel），与 `db/models.py` 的 SQLAlchemy ORM 模型不同。
> 每个领域一个文件，遵循 `EntityBase → EntityCreate → EntityUpdate → EntityResponse` 模式。

---

## 文件清单

### `base.py` (1KB) — 基类和混入
- `BaseMixin` — 提供 `id`, `model_config` 等公共配置

### `book.py` (8KB) — 书籍模型
- `Book(Base, BaseMixin)` — ORM 映射（复用）
- `BookBase(BaseModel)` — 公共字段：title, author_sort, isbn, publisher, rating, series_index, comments
- `BookCreate(BookBase)` — 创建请求
- `BookUpdate(BaseModel)` — 更新请求（仅 patch 的字段）
- `BookResponse(BookBase)` — 响应（含 id, timestamp, last_modified, authors, series, formats, tags）

### `author.py` (2KB) — 作者模型
- `AuthorBase` — name, sort, link
- `AuthorCreate`, `AuthorUpdate`, `AuthorResponse`

### `series.py` (2KB) — 系列模型
- `SeriesBase` — name
- `SeriesCreate`, `SeriesUpdate`, `SeriesResponse`

### `tag.py` (2KB) — 标签模型
- `TagBase` — name
- `TagCreate`, `TagUpdate`, `TagResponse`

### `publisher.py` — 出版社模型（可能在 `__init__` 中复用）

### `comment.py` (2KB) — 评论模型
- `CommentBase` — text, book_id
- `CommentCreate`, `CommentUpdate`, `CommentResponse`

### `data.py` (3KB) — 文件格式模型
- `DataBase` — book_id, format, name, uncompressed_size
- `DataCreate`, `DataResponse`

### `identifier.py` (3KB) — 标识符模型
- `IdentifierBase` — type, value, book_id
- `IdentifierCreate`, `IdentifierUpdate`, `IdentifierResponse`

### `rating.py` (2KB) — 评分模型
- `RatingBase` — rating (1-10)
- `RatingCreate`, `RatingResponse`

### `library.py` (5KB) — 书库模型
- `LibraryBase` — name, path, metadata_db
- `LibraryCreate`, `LibraryUpdate`, `LibraryResponse`, `LibraryInfo`

---

## 模式
```
EntityBase(BaseModel)          ← 核心字段
    ├── EntityCreate(EntityBase)    ← 创建请求
    ├── EntityUpdate(BaseModel)     ← 更新请求（所有可选）
    └── EntityResponse(EntityBase)  ← 响应（含 id、时间戳等）
```

## 注意
- 这些模型是 Pydantic 数据验证模型，**不是** SQLAlchemy ORM 模型
- ORM 模型在 `db/models.py` 中
- `BookResponse` 包含关联对象（authors, series, formats, tags, identifiers 等列表）

## 模型使用速查

| 模型 | 在哪个 Service 中返回 | 对应 ORM 模型 | 对应 tools/ 入口 |
|---|---|---|---|
| `BookCreate/Update/Response` | `BookService` | `db/models.Book` | `query_books`, `manage_books` |
| `AuthorCreate/Update/Response` | `AuthorService` | `db/models.Author` | `manage_authors` |
| `SeriesBase/Response` | `SeriesService` | `db/models.Series` | `manage_series` |
| `TagCreate/Update/Response` | `TagService` | `db/models.Tag` | `manage_tags` |
| `PublisherBase/Response` | `PublisherService` | `db/models.Publisher` | `manage_publishers` |
| `CommentCreate/Update/Response` | — | `db/models.Comment` | `manage_comments` |
| `DataCreate/Response` | — | `db/models.Data` | `manage_files` |
| `IdentifierCreate/Update/Response` | — | `db/models.Identifier` | — |
| `RatingCreate/Response` | — | `db/models.Rating` | — |
| `LibraryCreate/Update/Response` | `LibraryService` | — | `manage_libraries` |
