"""
Query builder helpers for book search.

Extracted from search_books_helper in book_tools.py (lines 849-1107).
Handles: field processing, intelligent query parsing, search query building,
and filters dict assembly from raw input parameters.
"""

import json
import re
from typing import Any

from ...shared.query_parsing import parse_intelligent_query

from ....logging_config import get_logger

logger = get_logger("calibremcp.tools.book_management.helpers.query_builder")


def process_fields(fields: str | list[str] | None) -> tuple[list[str], dict[str, float]]:
    """
    Process field specifications with boost factors.

    Args:
        fields: Field spec, e.g. ["title^3", "authors^2"] or None for defaults

    Returns:
        Tuple of (processed_fields list, field_boosts dict)
    """
    if fields is None:
        fields = ["title^3", "authors^2", "tags^2", "series^1.5", "comments^1"]
    elif isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except json.JSONDecodeError:
            fields = [f.strip() for f in fields.split(",") if f.strip()]

    field_boosts = {}
    processed_fields = []
    for field in fields:
        if "^" in field:
            field_name, boost = field.split("^", 1)
            try:
                field_boosts[field_name] = float(boost)
                processed_fields.append(field_name)
            except (ValueError, TypeError):
                processed_fields.append(field)
        else:
            processed_fields.append(field)

    return processed_fields, field_boosts


def parse_search_text(
    text: str | None, query: str | None = None
) -> tuple[str | None, dict[str, Any]]:
    """
    Parse raw search text using intelligent query parser.

    Args:
        text: Raw search text from user
        query: Backward-compat alias for text

    Returns:
        Tuple of (search_text string or None, parsed dict)
    """
    raw = text or query
    search_text = str(raw).strip() if isinstance(raw, str) else None
    parsed = (
        parse_intelligent_query(search_text)
        if search_text
        else {
            "text": "",
            "author": None,
            "tag": None,
            "pubdate": None,
            "rating": None,
            "series": None,
        }
    )
    return search_text, parsed


def apply_parsed_params(
    parsed: dict[str, Any],
    author: str | None,
    tag: str | None,
    series: str | None,
    pubdate_start: str | None,
    pubdate_end: str | None,
    rating: int | None,
) -> tuple[
    str | None, str | None, str | None, str | None, str | None, int | None
]:
    """
    Apply parsed structured params from intelligent query, falling back
    to explicit parameters when available.

    Args:
        parsed: Dict from parse_intelligent_query
        author: Explicit author parameter (takes priority)
        tag: Explicit tag parameter (takes priority)
        series: Explicit series parameter (takes priority)
        pubdate_start: Explicit pubdate_start (takes priority)
        pubdate_end: Explicit pubdate_end (takes priority)
        rating: Explicit rating (takes priority)

    Returns:
        Updated (author, tag, series, pubdate_start, pubdate_end, rating)
    """
    if parsed.get("author") and not author:
        author = parsed["author"]
    if parsed.get("tag") and not tag:
        tag = parsed["tag"]
    if parsed.get("series") and not series:
        series = parsed["series"]
    if parsed.get("pubdate") and not pubdate_start and not pubdate_end:
        pubdate_start = f"{parsed['pubdate']}-01-01"
        pubdate_end = f"{parsed['pubdate']}-12-31"
    if parsed.get("rating") and not rating:
        rating = parsed["rating"]

    return author, tag, series, pubdate_start, pubdate_end, rating


def build_search_queries(
    search_text: str,
    processed_fields: list[str],
    field_boosts: dict[str, float],
    operator: str = "OR",
    fuzziness: int | str = "AUTO",
    min_score: float = 0.1,
    highlight: bool = False,
) -> tuple[list[str], list[str], dict[str, Any], dict[str, Any]]:
    """
    Build search queries and FTS-related filter entries from raw search text.

    ⚡ Note: The fancy FTS query syntax built here is largely decorative.
    book_service.get_all() ignores the field-specific query string and uses
    simple SQL LIKE matching on the raw text. True FTS requires SQLite FTS5.

    Args:
        search_text: Raw search text
        processed_fields: List of field names to search across
        field_boosts: Dict of field → boost factor
        operator: AND/OR/FUZZY operator
        fuzziness: Fuzziness setting for FUZZY mode
        min_score: Minimum relevance score
        highlight: Whether to enable result highlighting

    Returns:
        Tuple of (search_queries list, search_terms list, extra_filters dict,
                  field_boosts dict (unchanged))
    """
    search_terms = []
    phrases = []
    extra_filters = {}

    if search_text:
        phrases = re.findall(r'"(.*?)"', search_text)
        remaining_text = re.sub(r'"(.*?)"', "", search_text)
        search_terms = [term.strip() for term in remaining_text.split() if term.strip()]

    if not processed_fields:
        processed_fields = ["title", "authors", "tags", "series", "comments"]

    search_queries = []
    for phrase in phrases:
        if not phrase:
            continue
        phrase_queries = []
        for field in processed_fields:
            field_name = field.split("^")[0]
            phrase_queries.append(f'{field_name}:"{phrase}"')
        if phrase_queries:
            search_queries.append(f"({' OR '.join(phrase_queries)})")

    if operator.upper() == "FUZZY":
        fuzz_str = f"~{fuzziness}" if fuzziness != "AUTO" else "~"
        for term in search_terms:
            term_queries = []
            for field in processed_fields:
                field_name = field.split("^")[0]
                boost = field_boosts.get(field_name, 1.0)
                boost_str = f"^{boost}" if boost != 1.0 else ""
                term_queries.append(f"{field_name}:{term}{fuzz_str}{boost_str}")
            if term_queries:
                search_queries.append(f"({' OR '.join(term_queries)})")

    elif operator.upper() == "AND":
        for term in search_terms:
            term_queries = []
            for field in processed_fields:
                field_name = field.split("^")[0]
                boost = field_boosts.get(field_name, 1.0)
                boost_str = f"^{boost}" if boost != 1.0 else ""
                term_queries.append(f"{field_name}:{term}{boost_str}")
            if term_queries:
                search_queries.append(f"({' OR '.join(term_queries)})")

    else:  # OR operator (default)
        term_queries = []
        for field in processed_fields:
            field_name = field.split("^")[0]
            boost = field_boosts.get(field_name, 1.0)
            boost_str = f"^{boost}" if boost != 1.0 else ""
            field_terms = [f"{field_name}:{term}{boost_str}" for term in search_terms]
            if field_terms:
                term_queries.append(f"({' OR '.join(field_terms)})")
        if term_queries:
            search_queries.extend(term_queries)

    if search_queries:
        join_operator = " AND " if operator.upper() in ["AND", "FUZZY"] else " OR "
        extra_filters["search"] = join_operator.join(search_queries)
        if min_score > 0:
            extra_filters["min_score"] = min_score
        if highlight:
            extra_filters["highlight"] = {
                "fields": {
                    field: {}
                    for field in processed_fields
                    if field not in ["authors", "tags"]
                },
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
            }

    return search_queries, search_terms, extra_filters, field_boosts


def assemble_filters(
    *,
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
    suggest: bool = False,
    search_text: str | None = None,
    search_terms: list[str] | None = None,
) -> dict[str, Any]:
    """
    Assemble all filter parameters into a single filters dict.

    This is the complete filter assembly logic from search_books_helper
    (lines 1010-1107). Validates rating constraints inline.

    Args:
        All raw search parameters from the user.

    Returns:
        filters dict ready for extraction by filter_assembler.
    """
    filters: dict[str, Any] = {}

    # Author filters
    if authors:
        filters["authors_list"] = authors if isinstance(authors, list) else [authors]
    elif author:
        filters["author_name"] = author

    # Tag filters
    if tags:
        filters["tags_list"] = tags if isinstance(tags, list) else [tags]
    elif tag:
        filters["tag_name"] = tag

    # Tag exclusions
    if exclude_tags:
        filters["exclude_tags_list"] = (
            exclude_tags if isinstance(exclude_tags, list) else [exclude_tags]
        )

    # Author exclusions
    if exclude_authors:
        filters["exclude_authors_list"] = (
            exclude_authors if isinstance(exclude_authors, list) else [exclude_authors]
        )

    # Series
    if series:
        filters["series_name"] = series

    # Series exclusions
    if exclude_series:
        filters["exclude_series_list"] = (
            exclude_series if isinstance(exclude_series, list) else [exclude_series]
        )

    # Comment
    if comment is not None:
        filters["comment"] = comment

    # has_empty_comments
    if has_empty_comments is not None:
        filters["has_empty_comments"] = has_empty_comments

    # Rating — validate inline
    if rating is not None:
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        filters["rating"] = rating

    if min_rating is not None:
        if min_rating < 1 or min_rating > 5:
            raise ValueError("Minimum rating must be between 1 and 5")
        filters["min_rating"] = min_rating

    if max_rating is not None:
        if max_rating < 1 or max_rating > 5:
            raise ValueError("Maximum rating must be between 1 and 5")
        if min_rating is not None and max_rating < min_rating:
            raise ValueError("Maximum rating must be >= minimum rating")
        filters["max_rating"] = max_rating

    if unrated is not None:
        filters["unrated"] = unrated

    # Publisher
    if publisher is not None:
        filters["publisher"] = publisher

    if publishers is not None:
        if isinstance(publishers, str):
            try:
                publishers = json.loads(publishers)
            except json.JSONDecodeError:
                publishers = [p.strip() for p in publishers.split(",") if p.strip()]
        if publishers:
            filters["publishers"] = publishers

    if has_publisher is not None:
        filters["has_publisher"] = has_publisher

    # Date ranges
    if pubdate_start:
        filters["pubdate_start"] = pubdate_start
    if pubdate_end:
        filters["pubdate_end"] = pubdate_end
    if added_after:
        filters["added_after"] = added_after
    if added_before:
        filters["added_before"] = added_before

    # File sizes
    if min_size is not None:
        filters["min_size"] = min_size
    if max_size is not None:
        filters["max_size"] = max_size

    # Formats
    if formats is not None:
        if isinstance(formats, str):
            try:
                formats = json.loads(formats)
            except json.JSONDecodeError:
                formats = [f.strip().upper() for f in formats.split(",") if f.strip()]
        if formats:
            filters["formats"] = [
                f.upper() if isinstance(f, str) else str(f).upper() for f in formats
            ]

    # Search suggestions
    if suggest and search_text and search_terms and len(search_terms) > 0:
        filters["suggest"] = {
            "text": search_text,
            "term": {"field": "_all", "sort": "score", "suggest_mode": "popular"},
        }

    return filters
