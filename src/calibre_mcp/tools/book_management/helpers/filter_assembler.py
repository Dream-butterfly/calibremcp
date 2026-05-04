"""
Filter assembler for book search.

Extracted from search_books_helper in book_tools.py (lines 1116-1180).
Extracts individual filter values from a combined filters dict,
recomputes the raw search_text, and builds the get_all_filters dict
that book_service.get_all() expects.
"""

from typing import Any


def extract_and_rebuild_params(
    filters: dict[str, Any],
    text: str | None,
    query: str | None,
) -> dict[str, Any]:
    """
    Extract individual filter parameters from a combined filters dict,
    recompute raw search_text, and build the final params for get_all().

    This mirrors the logic in search_books_helper lines 1116-1180.

    Args:
        filters: Combined filters dict (from query_builder.assemble_filters)
        text: Original search text parameter (to recompute raw search_text)
        query: Backward-compat query alias

    Returns:
        Dict with keys for every get_all() parameter:
        search, author_name, authors_list, exclude_authors_list,
        tag_name, tags_list, exclude_tags_list,
        series_name, exclude_series_list,
        comment, get_all_filters (dict of extra filters)
    """
    # Pop individual filters (lines 1118-1142)
    search_query = filters.pop("search", None)
    author_name = filters.pop("author_name", None)
    authors_list = filters.pop("authors_list", None)
    exclude_authors_list = filters.pop("exclude_authors_list", None)
    tag_name = filters.pop("tag_name", None)
    tags_list = filters.pop("tags_list", None)
    exclude_tags_list = filters.pop("exclude_tags_list", None)
    series_name = filters.pop("series_name", None)
    exclude_series_list = filters.pop("exclude_series_list", None)
    comment = filters.pop("comment", None)
    has_empty_comments = filters.pop("has_empty_comments", None)
    rating = filters.pop("rating", None)
    min_rating = filters.pop("min_rating", None)
    max_rating = filters.pop("max_rating", None)
    unrated = filters.pop("unrated", None)
    publisher = filters.pop("publisher", None)
    publishers = filters.pop("publishers", None)
    has_publisher = filters.pop("has_publisher", None)
    pubdate_start = filters.pop("pubdate_start", None)
    pubdate_end = filters.pop("pubdate_end", None)
    added_after = filters.pop("added_after", None)
    added_before = filters.pop("added_before", None)
    min_size = filters.pop("min_size", None)
    max_size = filters.pop("max_size", None)
    formats = filters.pop("formats", None)

    # Recompute search_text from original params (lines 1144-1153)
    # The fancy query string in search_query was decorative; the real search
    # text is the raw input. book_service.get_all() handles LIKE matching.
    if search_query:
        search_text = text or query
    else:
        search_text = None

    # Build get_all_filters dict (lines 1155-1180)
    get_all_filters = {}
    if rating is not None:
        get_all_filters["rating"] = rating
    if min_rating is not None:
        get_all_filters["min_rating"] = min_rating
    if max_rating is not None:
        get_all_filters["max_rating"] = max_rating
    if has_empty_comments is not None:
        get_all_filters["has_empty_comments"] = has_empty_comments
    if unrated is not None:
        get_all_filters["unrated"] = unrated
    if pubdate_start:
        get_all_filters["pubdate_start"] = pubdate_start
    if pubdate_end:
        get_all_filters["pubdate_end"] = pubdate_end
    if added_after:
        get_all_filters["added_after"] = added_after
    if added_before:
        get_all_filters["added_before"] = added_before
    if min_size is not None:
        get_all_filters["min_size"] = min_size
    if max_size is not None:
        get_all_filters["max_size"] = max_size
    if formats:
        get_all_filters["formats"] = formats

    return {
        "search": search_text,
        "author_name": author_name if not authors_list else None,
        "authors_list": authors_list,
        "exclude_authors_list": exclude_authors_list,
        "tag_name": tag_name if not tags_list else None,
        "tags_list": tags_list,
        "exclude_tags_list": exclude_tags_list,
        "series_name": series_name,
        "exclude_series_list": exclude_series_list,
        "comment": comment,
        "get_all_filters": get_all_filters,
    }
