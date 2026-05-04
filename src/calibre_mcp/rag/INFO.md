# `rag/` RAG 引擎

> **职责**: 语义搜索和向量数据库（LanceDB）组件。用于构建和查询书籍内容的语义索引。
> 入口在 `tools/rag/manage_rag.py`，实际 rag 逻辑在此目录。
> 共 10 个文件。

---

## 文件清单

### `chunking.py` (5KB) — 文本分块
- **函数**: `chunk_text(text, chunk_size, overlap)` — 将书籍文本分割为适合向量化的块
- **策略**: 按段落/句子/固定大小分块，包含重叠机制

### `embedding.py` (2KB) — 嵌入生成
- **函数**: `generate_embeddings(texts)`, `get_embedding_dimension()`
- **后端**: 默认 Ollama，可配置

### `indexer.py` (2KB) — 索引器
- **类**: `Indexer` — 构建全文→向量的索引
- **方法**: `build_index(chunks, embeddings)`, `save_index(path)`, `load_index(path)`

### `retriever.py` (2KB) — 检索器
- **类**: `Retriever` — 语义检索
- **方法**: `retrieve(query_embedding, top_k)` → 返回最相似块

### `store.py` (3KB) — 向量存储抽象接口
- **类**: `VectorStore` — 抽象基类
- **方法**: `add(embeddings, metadata)`, `search(query, top_k)`, `delete(ids)`, `clear()`

### `lancedb_vector_store.py` (4KB) — LanceDB 实现
- **类**: `LanceDBVectorStore(VectorStore)` — 基于 LanceDB 的向量存储
- **方法**: `add()`, `search()`, `delete()`, `clear()`
- **依赖**: lancedb Python 包

### `metadata_export.py` (4KB) — 元数据导出
- **函数**: `export_metadata_to_json(library_path)` → 将书库元数据导出为 JSON
- **用途**: 为 RAG 索引提供结构化元数据输入

### `metadata_rag.py` (13KB) ⭐ 元数据 RAG
- **函数**: `build_metadata_index(library_path)`, `search_metadata(query, top_k)`
- **用途**: 对书籍元数据（标题、作者、标签、评论）做语义搜索
- **不依赖** 书籍全文，仅搜索元数据字段

### `text_utils.py` (2KB) — 文本工具
- **函数**: `clean_text(text)`, `truncate_text(text, max_length)`, `normalize_whitespace(text)`

### `storage_paths.py` (1KB) — 存储路径
- **函数**: `get_index_path(library_name)`, `get_metadata_index_path(library_name)`
- **用途**: LanceDB 索引文件的路径管理

---

## RAG 管线数据流

```
书籍全文 / 元数据
    │
    ▼
chunking.py → chunk_text() → 文本块列表
    │
    ▼
embedding.py → generate_embeddings() → 向量
    │
    ▼
indexer.py → build_index() → 写入 lancedb_vector_store.py (LanceDB)
    │
    ▼
         ┌── query (用户输入)
         │
         ▼
    embedding.py → query_embedding
         │
         ▼
    retriever.py → retrieve(top_k)
         │
         ▼
    lancedb_vector_store.py → search()
         │
         ▼
    返回最相似文本块 + 元数据
```

## MCP 工具入口
- `tools/rag/manage_rag.py` — 注册 `calibre_rag` 和 `rag_index_build` 等命令
- `tools/portmanteau/search.py` — `calibre_rag` portmanteau 入口（调用 rag/ 层实现）

## 相关文档
- `tools/INFO.md` — MCP 工具层（含 rag 工具入口）
- `ARCHITECTURE.md` — 项目架构总览
