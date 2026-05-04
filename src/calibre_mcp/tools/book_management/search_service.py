"""
Search service for book queries.

Provides search_books() as a direct replacement for the monolithic
search_books_helper() in book_tools.py.

This module ORCHESTRATES the helpers:
  1. Database initialization + validation
  2. Input parsing (intelligent query, fields)
  3. Filter assembly
  4. book_service.get_all() call
  5. Response formatting

The original search_books_helper in book_tools.py is kept as a safety copy.
Use this module for new code; switch over after verification.
"""

import time
from pathlib import Path
from typing import Any

from ...db.database import get_database, init_database
from ...config import CalibreConfig
from ...config_discovery import get_active_calibre_library
from ...logging_config import get_logger
from ...server import mcp, storage as server_storage
from ...services.book_service import book_service as _book_service

from .helpers.query_builder import (
    process_fields,
    parse_search_text,
    apply_parsed_params,
    build_search_queries,
    assemble_filters,
)
from .helpers.filter_assembler import extract_and_rebuild_params
from .helpers.result_formatter import format_search_response

logger = get_logger("calibremcp.tools.book_management.search_service")


async def ensure_database_ready(
    target_library_path: Path | None,
) -> None:
    """
    Ensure the database session is initialized and connected.

    Uses the same priority order as search_books_helper:
    1. Persisted library from storage
    2. config.local_library_path
    3. Active library from Calibre config discovery
    4. First discovered library (fallback)

    Args:
        target_library_path: If already determined, use this directly.

    Raises:
        ValueError: If no valid database can be found/initialized.
    """
    from ...config import CalibreConfig
    from ...config_discovery import get_active_calibre_library

    config = CalibreConfig()

    # Determine target library path if not provided
    if target_library_path is None:
        target_library_path, _ = await _discover_library_path(config)

    # Check and initialize database
    try:
        db = get_database()
        with db.session_scope() as session:
            from sqlalchemy import text as sa_text

            session.execute(sa_text("SELECT id FROM books LIMIT 1"))
    except Exception:
        if target_library_path and (target_library_path / "metadata.db").exists():
            init_database(
                str((target_library_path / "metadata.db").absolute()),
                echo=False,
                force=True,
            )
        else:
            raise ValueError(
                "No valid database available. "
                "Set CALIBRE_LIBRARY_PATH or configure a library first."
            )


async def _discover_library_path(config) -> tuple[Path | None, str | None]:
    """
    Discover the library path using the same priority as server startup.

    Returns:
        Tuple of (library_path, library_name)
    """
    target_library_path = None
    target_library_name = None

    # 1. Try persisted library from storage
    try:
        if server_storage and hasattr(server_storage, "get_current_library"):
            persisted_library = await server_storage.get_current_library()
            if persisted_library and config.discovered_libraries:
                persisted_lib_info = config.discovered_libraries.get(persisted_library)
                if (
                    persisted_lib_info
                    and persisted_lib_info.path.exists()
                    and (persisted_lib_info.path / "metadata.db").exists()
                ):
                    target_library_path = persisted_lib_info.path
                    target_library_name = persisted_library
    except Exception:
        pass

    # 2. Try config.local_library_path
    if not target_library_path and config.local_library_path:
        lib_path = Path(config.local_library_path)
        metadata_db = lib_path / "metadata.db"
        if lib_path.exists() and lib_path.is_dir() and metadata_db.exists():
            target_library_path = lib_path
            if config.discovered_libraries:
                for name, lib_info in config.discovered_libraries.items():
                    if Path(lib_info.path) == target_library_path:
                        target_library_name = name
                        break
            if not target_library_name:
                target_library_name = target_library_path.name

    # 3. Try active library from Calibre config
    if not target_library_path:
        active_lib = get_active_calibre_library()
        if (
            active_lib
            and active_lib.path.exists()
            and (active_lib.path / "metadata.db").exists()
        ):
            target_library_path = active_lib.path
            target_library_name = active_lib.name

    # 4. Fallback to first discovered library
    if not target_library_path and config.discovered_libraries:
        for lib_name, lib_info in config.discovered_libraries.items():
            if lib_info.path.exists() and (lib_info.path / "metadata.db").exists():
                target_library_path = lib_info.path
                target_library_name = lib_name
                break

    return target_library_path, target_library_name


async def search_books(
    text: str | None = None,
    title: str | None = None,
    fields: str | list[str] | None = None,
    operator: str = "OR",
    fuzziness: int | str = "AUTO",
    min_score: float = 0.1,
    highlight: bool = False,
    suggest: bool = False,
    query: str | None = None,
    author: str | None = None,
    authors: list[str] | None = None,
    exclude_authors: list[str] | None = None,
    tag: str | None = None,
    tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
    series: str | None = None,
    exclude_series: list[str] | None = None,
    comment: str | None = None,
    has_empty_comments: bool | None = None,
    rating: int | None = None,
    min_rating: int | None = None,
    max_rating: int | None = None,
    unrated: bool | None = None,
    publisher: str | None = None,
    publishers: list[str] | None = None,
    has_publisher: bool | None = None,
    pubdate_start: str | None = None,
    pubdate_end: str | None = None,
    added_after: str | None = None,
    added_before: str | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    formats: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
    format_table: bool = False,
) -> dict[str, Any]:
    """
    Search and list books with various filters.

    Direct replacement for search_books_helper in book_tools.py.
    For full parameter documentation, see search_books_helper docstring.

    Args:
        All standard search parameters (identical to search_books_helper).

    Returns:
        Paginated dict with items, total, page info, and optional table.
    """
    import time as _time

    start_time = _time.time()

    logger.info(
        "Starting book search (v2 search_service)",
        extra={
            "service": "search_service",
            "action": "search_books",
            "text": text,
            "title": title,
            "author": author,
            "query": query,
        },
    )

    try:
        # Step 1: Input validation
        if limit < 1 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        # Step 2: Ensure database is ready
        await ensure_database_ready(target_library_path=None)

        # Step 3: Process fields and boosts
        processed_fields, field_boosts = process_fields(fields)

        # Step 4: Parse search text
        search_text, parsed = parse_search_text(text, query)

        # Step 5: Apply parsed structured params
        author, tag, series, pubdate_start, pubdate_end, rating = apply_parsed_params(
            parsed, author, tag, series, pubdate_start, pubdate_end, rating
        )

        # Step 6: Build search queries (decorative FTS query string)
        search_queries, search_terms, search_extra_filters, _ = build_search_queries(
            search_text=search_text,
            processed_fields=processed_fields,
            field_boosts=field_boosts,
            operator=operator,
            fuzziness=fuzziness,
            min_score=min_score,
            highlight=highlight,
        )

        # Step 7: Assemble all filters into combined dict
        combined_filters = assemble_filters(
            author=author,
            authors=authors,
            exclude_authors=exclude_authors,
            tag=tag,
            tags=tags,
            exclude_tags=exclude_tags,
            series=series,
            exclude_series=exclude_series,
            comment=comment,
            has_empty_comments=has_empty_comments,
            rating=rating,
            min_rating=min_rating,
            max_rating=max_rating,
            unrated=unrated,
            publisher=publisher,
            publishers=publishers,
            has_publisher=has_publisher,
            pubdate_start=pubdate_start,
            pubdate_end=pubdate_end,
            added_after=added_after,
            added_before=added_before,
            min_size=min_size,
            max_size=max_size,
            formats=formats,
            suggest=suggest,
            search_text=search_text,
            search_terms=search_terms,
        )

        # Merge search extra filters into combined_filters
        if "search" in search_extra_filters:
            combined_filters["search"] = search_extra_filters["search"]

        # Step 8: Extract and rebuild params for get_all()
        params = extract_and_rebuild_params(combined_filters, text, query)

        # Step 9: Call book_service.get_all()
        logger.info(
            "Calling book_service.get_all (search_service)",
            extra={
                "service": "search_service",
                "action": "call_service",
                "skip": offset,
                "limit": limit,
                "search": params["search"],
            },
        )
        result = _book_service.get_all(
            skip=offset,
            limit=limit,
            search=params["search"],
            title=title,
            author_name=params["author_name"],
            authors_list=params["authors_list"],
            exclude_authors_list=params["exclude_authors_list"],
            tag_name=params["tag_name"],
            tags_list=params["tags_list"],
            exclude_tags_list=params["exclude_tags_list"],
            series_name=params["series_name"],
            exclude_series_list=params["exclude_series_list"],
            comment=params["comment"],
            **params["get_all_filters"],
        )

        # Step 10: Format response
        response = format_search_response(
            result=result,
            limit=limit,
            offset=offset,
            format_table=format_table,
        )

        duration = _time.time() - start_time
        logger.info(
            "Book search completed successfully (search_service)",
            extra={
                "service": "search_service",
                "action": "search_complete",
                "total": response["total"],
                "items_returned": len(response["items"]),
                "duration_seconds": round(duration, 3),
            },
        )
        return response

    except ValueError:
        raise
    except Exception as e:
        duration = _time.time() - start_time
        logger.error(
            "Search failed (search_service)",
            extra={
                "service": "search_service",
                "action": "search_error",
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": round(duration, 3),
            },
            exc_info=True,
        )
        raise ValueError(
            f"ERROR: Search failed: {str(e)}\n\n"
            "**Possible solutions:**\n"
            "1. Use `manage_libraries(operation='list')` to see available libraries\n"
            "2. Use `manage_libraries(operation='switch', library_name='Library Name')` "
            "to select a library\n"
            "3. Verify the library path exists and contains metadata.db"
        ) from e
