"""
DEPRECATED: Individual file operation tools are deprecated in favor of the manage_files
portmanteau tool (see tools/files/manage_files.py). These functions are kept
as helpers but are no longer registered with FastMCP 2.13+.

Use manage_files(operation="...") instead:
- convert_book_format() → manage_files(operation="convert", conversion_requests=...)
- download_book() → manage_files(operation="download", book_id=..., format_preference=...)
- bulk_format_operations() → manage_files(operation="bulk", operation_type=..., ...)
"""

from typing import Any

# Import the MCP server instance
# Import response models
from ...server import ConversionRequest, ConversionResponse


# NOTE: @mcp.tool() decorator removed - use manage_files portmanteau tool instead
async def convert_book_format_helper(
    conversion_requests: list[ConversionRequest],
) -> list[ConversionResponse]:
    """
    Convert books between different formats (EPUB, PDF, MOBI, etc.).

    Handles format conversion requests for single or multiple books,
    supporting various input and output formats with quality options.

    Args:
        conversion_requests: List of conversion requests with source and target formats

    Returns:
        List[ConversionResponse]: Results of conversion operations
    """
    # Implementation will be moved from server.py
    pass


# NOTE: @mcp.tool() decorator removed - use manage_files portmanteau tool instead
async def download_book_helper(
    book_id: int, format_preference: str = "EPUB", output_dir: str | None = None
) -> dict[str, Any]:
    """
    Download a book file in the specified format.

    Retrieves and returns the file path for a book in the preferred format.
    If the preferred format is not available, checks for alternative formats
    and returns the best available match. The file path can be used to
    download or access the book file.

    Args:
        book_id: Unique identifier of the book to download
        format_preference: Preferred file format (e.g., "EPUB", "PDF", "MOBI").
                          Case-insensitive. Common formats: EPUB, PDF, MOBI, AZW3, TXT
        output_dir: Optional directory path to copy the file to.
                    If provided, copies the file to the specified directory.
                    If not provided, only returns the file path.

    Returns:
        Dictionary containing:
        {
            "book_id": int - ID of the book
            "format": str - Format of the returned file (may differ from preference)
            "file_path": str - Full path to the book file
            "size": int - File size in bytes
            "available_formats": List[str] - All formats available for this book
            "format_found": bool - Whether preferred format was found
            "output_path": str - (only if output_dir set) Path to the copied file
        }

    Raises:
        ValueError: If book not found or no formats available

    Example:
        # Download book in preferred EPUB format
        result = download_book(book_id=123, format_preference="EPUB")
        print(f"File: {result['file_path']}")

        # Download in PDF if available
        result = download_book(book_id=123, format_preference="PDF")
        if result['format_found']:
            print(f"PDF available at: {result['file_path']}")
        else:
            print(f"PDF not available, got {result['format']} instead")
    """
    from pathlib import Path

    from ...config import CalibreConfig
    from ...logging_config import get_logger
    from ...services.book_service import book_service

    logger = get_logger("calibremcp.tools.file_operations")

    try:
        # Get book formats
        formats = book_service.get_book_formats(book_id)

        if not formats:
            raise ValueError(f"Book {book_id} has no available formats")

        # Get book info for path
        book = book_service.get_by_id(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found")

        # Get library path
        config = CalibreConfig.load_config()
        if not config.local_library_path:
            raise ValueError("No library path configured")

        library_path = Path(config.local_library_path)
        book_path = library_path / book.get("path", "")

        # Normalize format preference
        format_pref_upper = format_preference.upper()

        # Find preferred format
        preferred_format = None
        for fmt_info in formats:
            if fmt_info["format"].upper() == format_pref_upper:
                preferred_format = fmt_info
                break

        # If preferred format not found, use first available
        if not preferred_format:
            preferred_format = formats[0]
            logger.warning(
                f"Format {format_preference} not available for book {book_id}, using {preferred_format['format']}"
            )

        # Construct file path from format name + book path
        # Format name comes from the Data table (already loaded via get_book_formats relationship)
        fmt_name = preferred_format.get("name", str(book_id))
        file_path = book_path / f"{fmt_name}.{preferred_format['format'].lower()}"

        # Verify file exists
        if not file_path.exists():
            raise ValueError(f"File not found at path: {file_path}")

        # Get file size
        file_size = file_path.stat().st_size

        # Get all available formats
        available_formats = [fmt["format"] for fmt in formats]

        result = {
            "book_id": book_id,
            "format": preferred_format["format"],
            "file_path": str(file_path),
            "size": file_size,
            "available_formats": available_formats,
            "format_found": preferred_format["format"].upper() == format_pref_upper,
            "title": book.get("title", "Unknown"),
        }

        # Copy to output_dir if specified
        if output_dir:
            import shutil
            output_path = Path(output_dir).expanduser().resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            dest = output_path / file_path.name
            shutil.copy2(str(file_path), str(dest))
            result["output_path"] = str(dest)
            result["copied"] = True

        return result

    except ValueError as ve:
        logger.error(f"Validation error downloading book: {ve}")
        raise
    except Exception as e:
        logger.error(f"Error downloading book {book_id}: {e}", exc_info=True)
        raise ValueError(f"Failed to download book: {str(e)}")


# NOTE: @mcp.tool() decorator removed - use manage_files portmanteau tool instead
async def bulk_format_operations_helper(
    operation_type: str, target_format: str | None = None, book_ids: list[int] | None = None
) -> dict[str, Any]:
    """
    Perform bulk operations on book formats across multiple books.

    Supports bulk conversion, format validation, and cleanup operations
    for efficient management of large book collections.

    Args:
        operation_type: Type of operation (convert, validate, cleanup)
        target_format: Target format for conversion operations
        book_ids: List of book IDs to process (processes all if None)

    Returns:
        Dict[str, Any]: Results of bulk operations with statistics
    """
    # Implementation will be moved from server.py
    pass
