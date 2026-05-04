# `viewers/` 阅读器实现

> **职责**: 不同格式书籍的在线阅读器实现。
> 被 `api/viewer.py`（REST）和 `tools/viewer/manage_viewer.py`（MCP）调用。
> 共 4 个文件（含 `__init__.py`）。

---

## 文件清单

### `__init__.py` (2KB) — 阅读器工厂
- **函数**: `get_viewer(book_format, book_path, library_path)` → 根据文件格式自动选择阅读器
- **映射**: `epub` → `EpubViewer`, `pdf` → `PdfViewer`, `cbz/cbr` → `MangaViewer`

### `comic/manga_viewer.py` (20KB) ⭐ 漫画阅读器
- **类**: `MangaViewer` — 漫画/图片类书籍翻页阅读
- **方法**:
  - `get_page(page_num)` → 返回图片页数据
  - `get_total_pages()` → 总页数
  - `get_metadata()` → 漫画元数据
- **支持格式**: CBZ, CBR, 图片文件夹

### `epub/epub_viewer.py` (17KB) ⭐ EPUB 阅读器
- **类**: `EpubViewer` — EPUB 格式章节解析和渲染
- **方法**:
  - `get_table_of_contents()` → 目录树
  - `get_chapter(chapter_id)` → 章节内容（HTML）
  - `get_spine()` → 阅读顺序（spine）
- **依赖**: `zipfile`（EPUB 本质是 zip）, HTML 解析

### `pdf/pdfjs_viewer.py` (16KB) ⭐ PDF 阅读器
- **类**: `PdfViewer` — 基于 PDF.js 的 PDF 渲染
- **方法**:
  - `get_page(page_num)` → 渲染页为图片
  - `get_total_pages()` → 总页数
  - `get_text(page_num)` → 提取页面文本（用于搜索）
- **依赖**: PDF.js（前端），`PyMuPDF` 或 `pdfminer`（后端文本提取）

---

## 数据流

```
tools/viewer/manage_viewer.py (MCP)
api/viewer.py (REST)
    │
    ▼
viewers.__init__.get_viewer(format, path)
    │
    ├── epub  → EpubViewer (get_chapter, get_toc)
    ├── pdf   → PdfViewer (get_page, get_text)
    └── cbz   → MangaViewer (get_page, get_total_pages)
    │
    ▼
返回结构化阅读数据
```

## 相关文档
- `api/INFO.md` — REST API 层（通过 viewer.py 调用阅读器）
- `tools/INFO.md` — MCP 工具层（manage_viewer 工具）
