"""
Service for handling book management/write operations in the Calibre MCP application.

Split from book_service.py in Phase 3 — contains all mutation methods (create/update/delete).
Intended to be combined with BookQueryService via multiple inheritance in a facade.
"""

from typing import Any

from ..db.database import DatabaseService
from ..db.models import (  # Use db.models for query models
    Author,
    Book,  # Use db.models.Book for queries (has series relationship)
    Comment,
    Rating,
    Series,
    Tag,
)
from ..logging_config import get_logger
from ..models.book import (
    BookCreate,
    BookResponse,
    BookUpdate,
)  # Use models.book for Pydantic schemas
from .base_service import BaseService, NotFoundError, ValidationError

logger = get_logger("calibremcp.services.book_management_service")


class BookManagementService(BaseService[Book, BookCreate, BookUpdate, BookResponse]):
    """
    Service class for handling book management/write operations.

    Provides create, update, and delete operations for books.
    Designed to be combined with BookQueryService via multiple inheritance.
    """

    def __init__(self, db: DatabaseService, *args, **kwargs):
        # Note: *args/**kwargs capture forwarded params from MRO chain.
        # We only pass what BaseService needs — don't forward *args to avoid duplication.
        super().__init__(db, Book, BookResponse)

    # @domain: manage_books (add_book helper)
    def create(self, book_data: BookCreate) -> dict[str, Any]:
        """
        Create a new book with the given data.

        Args:
            book_data: Data for creating the book

        Returns:
            Dictionary containing the created book data

        Raises:
            ValidationError: If the input data is invalid
        """
        with self._get_db_session() as session:
            # Create book instance
            book_dict = book_data.dict(
                exclude={"author_ids", "series_id", "tag_ids", "rating"}, exclude_unset=True
            )
            book = Book(**book_dict)

            # Handle relationships
            if book_data.author_ids:
                authors = session.query(Author).filter(Author.id.in_(book_data.author_ids)).all()
                if len(authors) != len(book_data.author_ids):
                    found_ids = {a.id for a in authors}
                    missing_ids = set(book_data.author_ids) - found_ids
                    raise ValidationError(f"Authors not found: {', '.join(map(str, missing_ids))}")
                book.authors = authors

            if book_data.series_id is not None:
                series = session.query(Series).get(book_data.series_id)
                if not series:
                    raise ValidationError(f"Series with ID {book_data.series_id} not found")
                book.series = [series]

            if book_data.tag_ids:
                tags = session.query(Tag).filter(Tag.id.in_(book_data.tag_ids)).all()
                if len(tags) != len(book_data.tag_ids):
                    found_ids = {t.id for t in tags}
                    missing_ids = set(book_data.tag_ids) - found_ids
                    raise ValidationError(f"Tags not found: {', '.join(map(str, missing_ids))}")
                book.tags = tags

            if book_data.rating is not None:
                rating = Rating(rating=book_data.rating, book=book)
                session.add(rating)

            session.add(book)
            session.commit()
            session.refresh(book)

            return self._to_response(book)

    # @domain: manage_books (update_book helper), manage_metadata (update_book_metadata helper)
    def update(self, book_id: int, book_data: BookUpdate | dict[str, Any]) -> dict[str, Any]:
        """
        Update an existing book with the given data.

        Args:
            book_id: ID of the book to update
            book_data: Data for updating the book

        Returns:
            Dictionary containing the updated book data

        Raises:
            NotFoundError: If the book is not found
            ValidationError: If the input data is invalid
        """
        if isinstance(book_data, dict):
            update_data = book_data
        else:
            update_data = book_data.dict(exclude_unset=True)

        with self._get_db_session() as session:
            # Get the existing book
            book = session.query(Book).get(book_id)
            if not book:
                raise NotFoundError(f"Book with ID {book_id} not found")

            # Update simple fields
            for field, value in update_data.items():
                if hasattr(book, field) and field not in [
                    "author_ids",
                    "series_id",
                    "tag_ids",
                    "rating",
                    "comments",
                ]:
                    setattr(book, field, value)

            # Handle relationships if provided
            if "author_ids" in update_data:
                authors = (
                    session.query(Author).filter(Author.id.in_(update_data["author_ids"])).all()
                )
                if len(authors) != len(update_data["author_ids"]):
                    found_ids = {a.id for a in authors}
                    missing_ids = set(update_data["author_ids"]) - found_ids
                    raise ValidationError(f"Authors not found: {', '.join(map(str, missing_ids))}")
                book.authors = authors

            if "series_id" in update_data:
                if update_data["series_id"] is not None:
                    series = session.query(Series).get(update_data["series_id"])
                    if not series:
                        raise ValidationError(
                            f"Series with ID {update_data['series_id']} not found"
                        )
                    book.series = [series]
                else:
                    book.series = []

            if "tag_ids" in update_data:
                tags = session.query(Tag).filter(Tag.id.in_(update_data["tag_ids"])).all()
                if len(tags) != len(update_data["tag_ids"]):
                    found_ids = {t.id for t in tags}
                    missing_ids = set(update_data["tag_ids"]) - found_ids
                    raise ValidationError(f"Tags not found: {', '.join(map(str, missing_ids))}")
                book.tags = tags

            if "rating" in update_data:
                # Update or create rating
                rating = session.query(Rating).filter(Rating.book_id == book.id).first()

                if update_data["rating"] is None and rating:
                    session.delete(rating)
                elif update_data["rating"] is not None:
                    if rating:
                        rating.rating = update_data["rating"]
                    else:
                        rating = Rating(rating=update_data["rating"], book=book)
                        session.add(rating)

            if "comments" in update_data:
                # Update or create comment (text synopsis/description)
                text = update_data["comments"]
                existing = book.comments  # uselist=False, single Comment or None
                if not text and existing:
                    session.delete(existing)
                elif text:
                    if existing:
                        existing.text = text
                    else:
                        session.add(Comment(book_id=book.id, text=text))

            session.add(book)
            session.commit()
            session.refresh(book)

            return self._to_response(book)

    # @domain: manage_books (delete_book helper)
    def delete(self, book_id: int) -> bool:
        """
        Delete a book by its ID.

        Args:
            book_id: ID of the book to delete

        Returns:
            True if the book was deleted successfully

        Raises:
            NotFoundError: If the book is not found
        """
        with self._get_db_session() as session:
            book = session.query(Book).get(book_id)
            if not book:
                raise NotFoundError(f"Book with ID {book_id} not found")

            session.delete(book)
            session.commit()
            return True


# Create a singleton instance
book_management_service = BookManagementService(DatabaseService())
