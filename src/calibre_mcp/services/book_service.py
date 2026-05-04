"""
Facade for book services — combines BookQueryService and BookManagementService.

Maintains backward compatibility: all existing `from .book_service import book_service`
imports continue to work unchanged.

Split into:
  - book_query_service.py   → read-only methods (get_by_id, get_all, ...)
  - book_management_service.py → write methods (create, update, delete)
"""

from ..db.database import DatabaseService
from .book_management_service import BookManagementService
from .book_query_service import BookQueryService, BookSearchResult

__all__ = [
    "BookService",
    "BookSearchResult",
    "book_service",
]


class BookService(BookQueryService, BookManagementService):
    """
    Combined book service providing both query and management operations.

    Uses multiple inheritance to merge BookQueryService and BookManagementService,
    so that all methods (get_all, get_by_id, create, update, delete, etc.)
    are available on a single instance.
    """

    def __init__(self):
        """Initialize the combined service with a default DatabaseService instance."""
        super().__init__(DatabaseService())


# Singleton instance — all existing importers get this same instance
book_service = BookService()
