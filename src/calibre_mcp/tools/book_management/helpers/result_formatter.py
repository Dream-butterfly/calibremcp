"""
Result formatter for book search.

Extracted from search_books_helper in book_tools.py (lines 1269-1317 + _format_books_table).
Converts book_service.get_all() results into the final response format,
including optional table rendering.
"""

from typing import Any


def format_search_response(
    result: dict[str, Any],
    limit: int,
    offset: int,
    format_table: bool = False,
) -> dict[str, Any]:
    """
    Convert a get_all() result dict into the final search response format.

    Args:
        result: Raw result from book_service.get_all()
        limit: Items per page
        offset: Pagination offset
        format_table: If True, include formatted table string

    Returns:
        Response dict with items, total, page info, and optional table.
    """
    items = result.get("items", [])
    total = result.get("total", 0)
    page = (offset // limit) + 1 if limit > 0 else 1
    total_pages = (total + limit - 1) // limit if limit > 0 else 1

    response = {
        "items": items,
        "total": total,
        "page": page,
        "per_page": limit,
        "total_pages": total_pages,
        "suggestions": result.get("suggestions", []),
        "max_score": result.get("max_score", 0),
    }

    if format_table:
        table_text = _format_books_table(
            items,
            total,
            page,
            total_pages,
            limit,
            include_description=True,
            description_max_length=80,
        )
        response["table"] = table_text
        response["format"] = "table"

    return response


def _format_books_table(
    items: list[dict[str, Any]],
    total: int,
    page: int,
    total_pages: int,
    per_page: int,
    include_description: bool = True,
    description_max_length: int = 80,
) -> str:
    """
    Format books as a pretty text table.

    Args:
        items: List of book dicts
        total: Total matching count
        page: Current page
        total_pages: Total pages
        per_page: Items per page
        include_description: Whether to include truncated description
        description_max_length: Max chars for description

    Returns:
        Formatted table string
    """
    if not items:
        return "No books found matching your search criteria."

    lines = []
    header = f"Results {page}/{total_pages} (showing {len(items)}/{total} books)"
    lines.append(header)
    lines.append("=" * len(header))
    lines.append("")

    for item in items:
        # ID
        book_id = item.get("id", "?")

        # Title
        title = item.get("title", "Unknown Title")

        # Authors
        authors_raw = item.get("authors", [])
        if authors_raw and isinstance(authors_raw, list):
            authors_str = ", ".join(
                a.get("name", "?") if isinstance(a, dict) else str(a) for a in authors_raw
            )
        else:
            authors_str = str(authors_raw) if authors_raw else "Unknown"

        # Year from pubdate
        pubdate = item.get("pubdate", "")
        year = ""
        if pubdate and isinstance(pubdate, str) and len(pubdate) >= 4:
            year = pubdate[:4]
        elif pubdate and hasattr(pubdate, "year"):
            year = str(pubdate.year)

        # Rating (stars)
        rating = item.get("rating")
        if rating is not None:
            try:
                rating_int = int(rating)
                stars = "⭐" * rating_int + "☆" * (5 - rating_int)
            except (ValueError, TypeError):
                stars = ""
        else:
            stars = ""

        # Tags
        tags_raw = item.get("tags", [])
        if tags_raw and isinstance(tags_raw, list):
            tags_str = ", ".join(
                t.get("name", "?") if isinstance(t, dict) else str(t) for t in tags_raw
            )
        else:
            tags_str = ""

        # Build table row
        row_parts = [
            f"ID: {book_id}",
            f"Title: {title}",
            f"Author(s): {authors_str}",
        ]
        if year:
            row_parts.append(f"Year: {year}")
        if stars:
            row_parts.append(f"Rating: {stars}")
        if tags_str:
            row_parts.append(f"Tags: {tags_str}")

        # Description (from comments)
        if include_description:
            description = item.get("comments", "") or item.get("description", "")
            if description:
                if len(description) > description_max_length:
                    description = description[:description_max_length] + "..."
                row_parts.append(f"Description: {description}")

        # Series info
        series = item.get("series")
        if series:
            series_name = series.get("name", "") if isinstance(series, dict) else str(series)
            series_idx = item.get("series_index", "")
            if series_name:
                series_str = f"Series: {series_name}"
                if series_idx:
                    series_str += f" [#{series_idx}]"
                row_parts.append(series_str)

        lines.append(" | ".join(row_parts))
        lines.append("-" * 80)

    return "\n".join(lines)
